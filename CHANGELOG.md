# Changelog

## 0.2.0

- **Try it with no personal data.** New `try-yapply` skill and `yapply demo` command build a fictional profile, validate it, and render a sample résumé PDF.
- **PDF résumés.** New `render-application` command renders validated résumés with ReportLab. The layout aligns every section to one text column.
- **Friendlier first run.** When ReportLab is missing, `demo` stops before creating any files and prints the exact install command for the Python that runs Yapply. The skills ask before installing anything.
- **Install from GitHub.** Added a Claude Code marketplace, so `/plugin marketplace add Faiz-k490/Yapply` works.
- **Open source.** Released under the MIT license, with contributing, security, and CI setup.
- **Checked README.** Tests verify the manifests agree on a version and that every figure in the README's metrics table matches the code.
- **Clean bundles.** `scripts/build_plugin.py` builds a plugin folder without tests, Git history, or private workspaces.

## 0.1.0

- First release: onboarding, job discovery, application preparation, and tracking skills, plus the provenance validator and opt-in telemetry.
