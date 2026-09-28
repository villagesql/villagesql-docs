#!/usr/bin/env python3
"""Re-run every SQL example in tutorial/ and compare it with what is published.

Each lesson pairs a ```sql block with the ```text block holding its output. This
runs each of those statements against a live server and compares three things:
the column header, the footer reporting how many rows came back, and every data
row the page prints. The first two go stale when a query or the data changes.
The third catches a row transcribed wrong, which reads exactly like a row
transcribed right.

Data rows are compared as a multiset, so a page whose query has no ORDER BY does
not fail when the server returns the same rows in a different order. A page may
elide rows with a line containing only "...", and the rows it does keep must all
be real.

The client is driven through a pseudo-terminal on purpose. The mysql client
drops the +---+ borders and the "(0.00 sec)" timing when its output is not a
terminal, so a capture taken any other way does not match what a reader sees.

Blocks using UPPER_SNAKE placeholders are syntax skeletons and are skipped, as
is anything that is not a query. Examples shown as shell commands are not
covered here and have to be run by hand.

A lesson that works in a different database says so with an MDX comment near the
top, and every statement in it runs there instead:

    {/* verify-db: sakila_practice */}

The lessons that change data need this, because they must not write into the
sample database every other lesson reads. Those lessons also change what the
next statement sees, so each one says

    {/* verify-reset */}

and scripts/tutorial-practice.sql is loaded again before the lesson runs. The
lesson's statements then run in the order the page prints them, from the state
the page tells the reader to start in.

A ```sql block holding more than one statement is compared whole, line for
line, rather than by header and row count. A transaction has to be typed into
one session, so it cannot be split into a block per statement.

    VSQL_CLIENT=/path/to/mysql VSQL_SOCKET=/tmp/mysql.sock \
        python3 scripts/verify-tutorial-examples.py

Exits non-zero when any example disagrees with the page.
"""

import fcntl, glob, os, pty, re, select, struct, subprocess, sys, termios, time

CLIENT = os.environ.get("VSQL_CLIENT", "mysql")
SOCKET = os.environ.get("VSQL_SOCKET", "/tmp/mysql.sock")
USER = os.environ.get("VSQL_USER", "root")
DB = os.environ.get("VSQL_DB", "sakila")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A syntax skeleton is recognised by its placeholders, which are upper case and
# always contain an underscore (COLUMN_LIST, SORT_COLUMN). Matching bare upper
# case words instead would swallow DISTINCT, ORDER BY and LIMIT, and silently
# leave most of the real examples unverified.
PLACEHOLDER = re.compile(r"\b[A-Z]+_[A-Z_]+\b")
REAL_KEYWORDS = {"GROUP_CONCAT", "LAST_INSERT_ID"}


VERIFY_DB = re.compile(r"\{/\*\s*verify-db:\s*([A-Za-z0-9_$]+)\s*\*/\}")
VERIFY_RESET = re.compile(r"\{/\*\s*verify-reset\s*\*/\}")
PRACTICE = os.path.join(REPO, "scripts", "tutorial-practice.sql")


def reset():
    """Drop and rebuild the practice database from its seed."""
    with open(PRACTICE) as seed:
        subprocess.run([CLIENT, "-S", SOCKET, "-u", USER], stdin=seed,
                       stdout=subprocess.DEVNULL, check=True)


def run(statement, cols=200, db=None):
    """Type a statement into the client under a pty and return the screen."""
    pid, fd = pty.fork()
    if pid == 0:
        os.environ["TERM"] = "dumb"
        os.execvp(CLIENT, [CLIENT, "-S", SOCKET, "-u", USER, db or DB])
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 60, cols, 0, 0))
    # Wait for the prompt rather than guessing how long the client takes to
    # start. Typing into it too early puts the terminal echo of the whole block
    # above the banner, and the results then have no prompt in front of them.
    banner = b""
    deadline = time.time() + 20
    while time.time() < deadline:
        ready, _, _ = select.select([fd], [], [], 0.2)
        if not ready:
            continue
        try:
            banner += os.read(fd, 65536)
        except OSError:
            break
        if banner.rstrip().endswith(b"mysql>"):
            break
    for line in statement.splitlines():
        os.write(fd, line.encode() + b"\n")
        time.sleep(0.25)
    time.sleep(2.5)
    os.write(fd, b"exit\n")
    time.sleep(0.6)
    buf = b""
    try:
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            buf += chunk
    except OSError:
        pass
    os.waitpid(pid, 0)
    # The client rings the terminal bell after an error, and that byte lands in
    # front of the next prompt, which would otherwise hide it from the prompt
    # filtering below.
    text = (banner + buf).decode(errors="replace").replace("\r\n", "\n")
    return text.replace("\x07", "")


def printed(raw, statement):
    """Everything the client printed after the last line of the statement."""
    lines = raw.split("\n")
    last = statement.splitlines()[-1].strip()
    start = max(i for i, l in enumerate(lines) if l.strip().endswith(last))
    out = lines[start + 1:]
    end = [i for i, l in enumerate(out) if l.startswith("mysql> exit")]
    return "\n".join(out[:end[0]] if end else out).strip("\n")


def is_multi(sql):
    """True when a block holds more than 1 statement.

    A statement ends in a semicolon, or in \\G when the client is being asked
    for vertical output.
    """
    ends = [l.rstrip() for l in sql.splitlines()]
    return len([l for l in ends if l.endswith(";") or l.endswith("\\G")]) > 1


def printed_session(raw, statement):
    """Every line the client printed for a block of several statements.

    The pty echoes what is typed, so the prompt lines are dropped and what is
    left is the run of results in the order the page shows them.
    """
    lines = raw.split("\n")
    first = statement.splitlines()[0].strip()
    start = min(i for i, l in enumerate(lines) if l.strip().endswith(first))
    out = lines[start + 1:]
    end = [i for i, l in enumerate(out) if l.startswith("mysql> exit")]
    out = out[:end[0]] if end else out
    kept = [l for l in out if not l.startswith("mysql> ") and not l.startswith("    -> ")]
    return "\n".join(kept).strip("\n")


def session_text(block):
    """A session transcript with the timings and the blank runs taken out."""
    lines = []
    for line in block.strip().split("\n"):
        line = re.sub(r"\(\d+\.\d+ sec\)", "", line).rstrip()
        if line or (lines and lines[-1]):
            lines.append(line)
    return "\n".join(lines).strip("\n")


def pairs(text):
    """Every ```sql block whose very next fenced block is its ```text output.

    Walking the fences beats one regex over the whole file: a non-greedy match
    will happily run past the prose between an unrelated pair of blocks and
    report an alignment that does not exist.
    """
    fences = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        if lines[i].startswith("```"):
            lang = lines[i][3:].strip()
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            fences.append((lang, "\n".join(lines[i + 1:j])))
            i = j + 1
        else:
            i += 1
    return [(a[1], b[1]) for a, b in zip(fences, fences[1:])
            if a[0] == "sql" and b[0] == "text"]


def significant(block):
    """The column header and the row-count or error line."""
    lines = [l for l in block.strip().split("\n") if l.strip() != "..."]
    header = next((l for l in lines if l.startswith("|")), None)
    footer = next((l for l in reversed(lines) if "row" in l or "ERROR" in l), None)
    if footer:
        footer = re.sub(r"\(\d+\.\d+ sec\)", "", footer).strip()
    return header, footer


def data_rows(block):
    """Every printed row except the header, as a sorted list.

    Sorted rather than positional because a query with no ORDER BY may come back
    in a different order on a different server, which is not a documentation
    defect. A wrong value still changes the list.
    """
    lines = [l.rstrip() for l in block.strip().split("\n")]
    body = [l for l in lines if l.startswith("|")]
    return sorted(body[1:])


def missing_rows(page_block, live_block):
    """Page rows that the server did not print. Elided rows are not required."""
    live = list(data_rows(live_block))
    gone = []
    for row in data_rows(page_block):
        if row in live:
            live.remove(row)
        else:
            gone.append(row)
    return gone


def main():
    ok = bad = skipped = 0
    for path in sorted(glob.glob(os.path.join(REPO, "tutorial", "*.mdx"))):
        name = os.path.basename(path)
        text = open(path).read()
        found_db = VERIFY_DB.search(text)
        db = found_db.group(1) if found_db else None
        if VERIFY_RESET.search(text):
            reset()
        for sql, shown in pairs(text):
            sql = sql.strip()
            found = set(PLACEHOLDER.findall(sql)) - REAL_KEYWORDS
            if found or sql.upper().startswith("USE "):
                skipped += 1
                continue
            raw = run(sql, db=db)
            if is_multi(sql):
                live = session_text(printed_session(raw, sql))
                if session_text(shown) == live:
                    ok += 1
                    continue
                bad += 1
                print(f"MISMATCH {name}: {sql.splitlines()[0][:60]}")
                print("   page:")
                print(session_text(shown))
                print("   live:")
                print(live)
                continue
            live = printed(raw, sql)
            want, got = significant(shown), significant(live)
            gone = missing_rows(shown, live)
            if want == got and not gone:
                ok += 1
            else:
                bad += 1
                print(f"MISMATCH {name}: {sql.splitlines()[0][:60]}")
                if want != got:
                    print(f"   page: {want}")
                    print(f"   live: {got}")
                for row in gone:
                    print(f"   page row not returned by the server: {row}")
    print(f"\nmatched {ok}, mismatched {bad}, skipped {skipped}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
