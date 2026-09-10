---
name: onboard
description: Set up or repair a private Yapply career workspace and turn user-provided resumes, profiles, or notes into verified source facts. Use when the user wants to start Yapply, import their background, create a master profile, check setup, or migrate existing career materials. Do not use for tailoring a specific application when a valid Yapply profile already exists.
---

# Onboard to Yapply

Create a local source of truth for later applications without requiring a provider API key.

## Workflow

1. Treat the user's current project as the workspace unless they name another directory. Do not search outside the directory or files they placed in scope.
2. Resolve the plugin root from this skill's installed `SKILL.md` path. Run the CLI as `python3 <plugin-root>/scripts/yapply.py --root <workspace> ...`; never assume the user's current directory is the plugin directory.
3. Run `init`. It is idempotent and does not overwrite existing files.
4. Read `.yapply/profile.json` and any résumé, portfolio, or notes the user explicitly supplied.
5. Populate identity and preferences. Convert career evidence into small, independently verifiable facts. Give every fact a stable lowercase ID beginning with `fact-`, a category, a factual statement, an evidence note, and keywords.
6. Preserve exact dates, metrics, technologies, titles, and organizations from the source. Never infer a credential, outcome, skill, or number. If a material fact is ambiguous, ask one focused question or omit it.
7. Run `validate-profile` and fix structural errors before declaring onboarding complete.
8. Summarize what was imported, what remains missing, and where the local profile lives. Do not display sensitive fields unless the user asks.

## Privacy

- Keep all career content inside the selected `.yapply/` workspace.
- Do not enable telemetry without the user's explicit opt-in and an HTTPS collector endpoint.
- If telemetry is discussed, read `<plugin-root>/docs/telemetry-contract.md` and explain that event payloads can be previewed before they are sent.
