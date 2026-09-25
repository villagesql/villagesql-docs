#!/usr/bin/env python3
"""Re-run every SQL example in tutorial/ and compare it with what is published.

Each lesson pairs a ```sql block with the ```text block holding its output. This
runs each of those statements against a live server and compares the two lines
that carry the meaning: the column header, and the footer reporting how many
rows came back. Those are what go stale when a query or the data changes, and
they are what a reader compares their own screen against.

The client is driven through a pseudo-terminal on purpose. The mysql client
drops the +---+ borders and the "(0.00 sec)" timing when its output is not a
terminal, so a capture taken any other way does not match what a reader sees.

Blocks using UPPER_SNAKE placeholders are syntax skeletons and are skipped, as
is anything that is not a query. Examples shown as shell commands are not
covered here and have to be run by hand.

    VSQL_CLIENT=/path/to/mysql VSQL_SOCKET=/tmp/mysql.sock \
        python3 scripts/verify-tutorial-examples.py

Exits non-zero when any example disagrees with the page.
"""

import fcntl, glob, os, pty, re, struct, sys, termios, time

CLIENT = os.environ.get("VSQL_CLIENT", "mysql")
SOCKET = os.environ.get("VSQL_SOCKET", "/tmp/mysql.sock")
USER = os.environ.get("VSQL_USER", "root")
DB = os.environ.get("VSQL_DB", "sakila")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PLACEHOLDER = re.compile(r"\b[A-Z][A-Z_]{3,}\b")
KEYWORDS = r"\b(SELECT|FROM|INNER|JOIN|CROSS|ON|USING|AS|USE|COUNT)\b"


def run(statement, cols=200):
    """Type a statement into the client under a pty and return the screen."""
    pid, fd = pty.fork()
    if pid == 0:
        os.environ["TERM"] = "dumb"
        os.execv(CLIENT, [CLIENT, "-S", SOCKET, "-u", USER, DB])
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 60, cols, 0, 0))
    time.sleep(1.5)
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
    return buf.decode(errors="replace").replace("\r\n", "\n")


def printed(raw, statement):
    """Everything the client printed after the last line of the statement."""
    lines = raw.split("\n")
    last = statement.splitlines()[-1].strip()
    start = max(i for i, l in enumerate(lines) if l.strip().endswith(last))
    out = lines[start + 1:]
    end = [i for i, l in enumerate(out) if l.startswith("mysql> exit")]
    return "\n".join(out[:end[0]] if end else out).strip("\n")


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
    lines = [l for l in block.strip().split("\n") if l != "..."]
    header = next((l for l in lines if l.startswith("|")), None)
    footer = next((l for l in reversed(lines) if "row" in l or "ERROR" in l), None)
    if footer:
        footer = re.sub(r"\(\d+\.\d+ sec\)", "", footer).strip()
    return header, footer


def main():
    ok = bad = skipped = 0
    for path in sorted(glob.glob(os.path.join(REPO, "tutorial", "*.mdx"))):
        name = os.path.basename(path)
        for sql, shown in pairs(open(path).read()):
            sql = sql.strip()
            if PLACEHOLDER.search(re.sub(KEYWORDS, "", sql)) or sql.upper().startswith("USE "):
                skipped += 1
                continue
            want = significant(shown)
            got = significant(printed(run(sql), sql))
            if want == got:
                ok += 1
            else:
                bad += 1
                print(f"MISMATCH {name}: {sql.splitlines()[0][:60]}")
                print(f"   page: {want}")
                print(f"   live: {got}")
    print(f"\nmatched {ok}, mismatched {bad}, skipped {skipped}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
