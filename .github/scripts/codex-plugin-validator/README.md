# Codex plugin validator

These unmodified Python files are vendored from the `plugin-creator` system skill
bundled with `codex-cli 0.158.0-alpha.2.1`, extracted in an isolated Codex home on
2026-10-01. They validate the Codex plugin manifest and skill metadata without
login, API credentials, or network access. The CLI has no `codex plugin validate`
subcommand.

Source paths inside the Codex home:

- `skills/.system/plugin-creator/scripts/validate_plugin.py`
- `skills/.system/plugin-creator/scripts/identifier_validation.py`

SHA-256 checksums:

```text
f4eeadb733b28b0c3e714de263a76d6542866a672f3e99bdffcf4dbcdf85e944  validate_plugin.py
a6d51ce4a9a7e8f85626ff5808a467a67574e7f8cdf1167ffb467c5f67e57223  identifier_validation.py
```

The validator is kept here because CI runners do not ship with Codex system
skills. PyYAML is a CI dependency only; it is not a Yapply runtime dependency or
included in the clean plugin bundle.

Upstream: [OpenAI Codex](https://github.com/openai/codex), licensed under
[Apache-2.0](LICENSE). The license text is copied from upstream commit
`60947e234156ac12bdb7fba2477d3965f166bd34`. The validator snapshot comes from the
CLI bundle, not that source commit.

To update, extract both scripts from the same Codex release, replace them without
local modifications, update the recorded release and checksums, and rerun:

```text
python -m pip install PyYAML==6.0.3
python .github/scripts/codex-plugin-validator/validate_plugin.py .
```
