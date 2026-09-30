---
name: try-yapply
description: Run Yapply's fully synthetic local demo and show the resulting resume PDF. Use when the user wants to test, preview, smoke-test, or see how Yapply works without supplying personal career data. Do not use when the user wants to begin with their real resume.
---

# Try Yapply safely

Demonstrate the complete local data, validation, tracking, and rendering path with synthetic content.

1. Resolve the plugin root from this installed `SKILL.md` path. Invoke `python3 <plugin-root>/scripts/yapply.py`; do not assume the current directory is the plugin root.
2. Use a `yapply-demo` directory under the user's current workspace. If that directory already contains `.yapply`, preserve it and choose a new numbered directory rather than deleting or overwriting anything.
3. Run `demo` with the chosen directory as `--root`. This creates a synthetic profile and role, validates source-fact provenance, marks the application ready, and renders a PDF.
4. Open or display the generated PDF when the host supports local-file previews. Otherwise return its absolute path.
5. Explain that every name, employer, posting, metric, and contact value in the demo is fictional. Mention that telemetry remains disabled.
6. Offer to start onboarding with the user's real résumé, but do not read or import personal files until the user asks.

## If ReportLab is missing

The `demo` command checks for ReportLab before creating any files, so a failed first run leaves nothing behind.

1. Tell the user that PDF rendering needs the ReportLab Python package and ask before installing anything.
2. With their approval, run the exact install command from the error message. It targets the same Python interpreter that runs Yapply.
3. If pip refuses because the environment is externally managed (common with Homebrew Python), explain the choices and let the user pick one. Do not add `--break-system-packages` without their approval.
4. Rerun `demo` with the same `--root`.
