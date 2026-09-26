---
name: Replit config edits
description: Safe editing and whitespace behavior for workspace .replit configuration.
---

Direct patch edits to .replit are blocked. Prepare a complete temporary TOML file in the workspace and use the validated replacement callback instead. If preserving a final newline matters for a clean diff, end the temporary file with an extra blank line.

**Why:** A direct patch was rejected, and the first validated replacement normalized away the trailing newline, leaving an unrelated one-line diff. The extra blank line produced a clean file.

**How to apply:** When a future change genuinely requires editing .replit, use the validated replacement route and check the resulting diff. Prefer dedicated workflow tools for run configuration.