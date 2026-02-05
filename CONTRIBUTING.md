# **Contributing to VillageSQL Documentation**

Welcome! We believe clear documentation is just as vital as the code itself. Since VillageSQL is a tracking fork of MySQL, our goal is to provide a seamless experience for users transitioning between the two.

* **Note on Upstream Consistency:** If a feature works exactly like upstream MySQL, **do not duplicate the text.** Instead, please reference the existing [MySQL Documentation](https://dev.mysql.com/doc/). We only write custom docs for VillageSQL-specific extensions, optimizations, or deviations.

---

## **How to Contribute**

### **1. Identify the Need**

Before you start writing, please check our [GitHub Issues](https://github.com/villagesql/villagesql-docs/issues).

* **For small fixes:** (Typos, broken links, formatting) Feel free to open a Pull Request (PR) directly.
* **For new guides or major rewrites:** **You must open an issue first.** This allows the VillageSQL team to review the proposed structure and ensure it aligns with our roadmap and "Upstream Consistency" policy before you invest significant time.

### **2. Local Setup & Editing (Mintlify)**

Our docs are powered by **Mintlify**. To ensure your formatting looks correct:

1. **Fork and Clone** the repository.
2. **Install the Mintlify CLI:** `npm i -g mintlify`
3. **Run Preview:** Run `mintlify dev` in your terminal. This provides a live preview at `localhost:3000`.
4. **Navigation:** If you add a new file, you **must** register it in `mint.json` or it will not appear in the sidebar.

### **3. Submission Process**

1. **Branch:** Create a branch for your changes: `git checkout -b docs/my-update`.
2. **Commit:** Use clear, descriptive messages (e.g., `docs: add guide for X-Protocol extensions`).
3. **PR:** Open a Pull Request and link it to the issue you opened in Step 1.

---

## **Style Guide**

* **Tone:** Helpful, professional, and welcoming.
* **Components:** Take advantage of Mintlify's [reusable components](https://mintlify.com/docs/components/alerts) like `<Info>`, `<Warning>`, and `<Note>` to highlight key points.
* **Code Blocks:** Always specify the language for syntax highlighting (e.g., ```sql).

**Thank you for helping build the village!**
