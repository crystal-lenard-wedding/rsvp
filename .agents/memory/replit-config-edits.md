---
name: Replit config edits
description: Safe editing and whitespace behavior for workspace .replit configuration.
---

Direct patch edits to .replit are blocked. Prepare a complete temporary TOML file in the workspace and use the validated replacement callback instead. If preserving a final newline matters for a clean diff, end the temporary file with an extra blank line.

**Why:** A direct patch was rejected, and the first validated replacement normalized away the trailing newline, leaving an unrelated one-line diff. The extra blank line produced a clean file.

**How to apply:** When a future change genuinely requires editing .replit, use the validated replacement route and check the resulting diff. Prefer dedicated workflow tools for run configuration.

Running `node` for one-off browser QA can automatically add the Node.js runtime module to `.replit`, even when a static site has no Node dependency.

**Why:** A temporary QA script changed tracked Replit configuration despite no deliberate project setup change.

**How to apply:** After one-off Node checks, inspect the `.replit` diff and remove the unused runtime through the package-management skill's uninstall callback. Avoid leaving unrelated module changes in the site's source diff.