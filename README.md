# Yapply

Yapply is a local-first plugin for Codex and Claude Code. It uses the agent the user already has access to, so the plugin does not ask users for an OpenAI or Anthropic API key.

This first milestone provides:

- a shared `skills/` package for onboarding, job discovery, application preparation, and tracking;
- a deterministic, dependency-free Python CLI for workspace creation and validation;
- source-fact provenance checks that reject unsupported resume statements;
- opt-in, anonymous telemetry with a local preview and queue;
- manifests for both Codex and Claude Code.

## Local data model

Running `yapply init` in a career workspace creates a private `.yapply/` directory:

```text
.yapply/
├── config.json
├── profile.json
├── tracker.json
├── candidates.json
├── applications/
└── telemetry/
    └── events.jsonl
```

`.yapply/.gitignore` ignores the whole workspace by default. The plugin source never needs to contain a user's résumé, identity, job descriptions, or application records.

## CLI

The CLI uses only the Python standard library:

```bash
./bin/yapply init
./bin/yapply status
./bin/yapply validate-profile
./bin/yapply create-application acme-backend
./bin/yapply validate-application acme-backend
./bin/yapply track acme-backend applied
./bin/yapply telemetry status
```

Use `./bin/yapply --help` for the full command list. Commands use the current directory as the career workspace unless `--root PATH` is supplied before the subcommand.

## Local plugin testing

For Claude Code:

```bash
claude plugin validate . --strict
claude --plugin-dir .
```

For Codex, validate the package with the Codex plugin validator and load the repository as a development plugin. The same skills are used by both hosts.

## Telemetry

Telemetry is off by default. When enabled, Yapply records only allow-listed product events and coarse counts. It never includes names, email addresses, free-form text, company names, role titles, URLs, document contents, file paths, or filenames. `DISABLE_TELEMETRY=1` or `DO_NOT_TRACK=1` overrides local configuration.

See [PRIVACY.md](PRIVACY.md) and [docs/data-contract.md](docs/data-contract.md) for the exact contracts.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 scripts/yapply.py --help
```

The next milestone is deterministic résumé rendering and a hosted, aggregate-only telemetry collector. The local workflow is usable without either service.
