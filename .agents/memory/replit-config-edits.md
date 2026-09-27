---
name: Replit config edits
description: Safe editing and whitespace behavior for workspace .replit configuration.
---

Direct patch edits to .replit are blocked. Prepare a complete temporary TOML file in the workspace and use the validated replacement callback instead. If preserving a final newline matters for a clean diff, end the temporary file with an extra blank line.

**Why:** A direct patch was rejected, and the first validated replacement normalized away the trailing newline, leaving an unrelated one-line diff. The extra blank line produced a clean file.

**How to apply:** When a future change genuinely requires editing .replit, use the validated replacement route and check the resulting diff. Prefer dedicated workflow tools for run configuration.

For one-off JavaScript checks in this static workspace, prefer browser-based verification when Node is absent. Adding Node just for QA can automatically add its runtime module to `.replit`, even though the site does not need it.

**Why:** Node was unavailable in a later static-site check; an earlier temporary Node QA script changed tracked Replit configuration despite no deliberate project setup change.

**How to apply:** Verify interactions and syntax in a browser rather than installing Node solely for a check. If a Node check does add the runtime, inspect the `.replit` diff and remove the unused module through the package-management skill's uninstall callback.