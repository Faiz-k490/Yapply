# Yapply privacy contract

Yapply is local-first. Career documents and application records stay inside the user's chosen workspace unless the user explicitly moves or shares them.

## Data that stays local

- identity and contact details;
- master-profile facts and evidence;
- job descriptions, employers, titles, and URLs;
- generated résumé and cover-letter content;
- application notes and tracker entries;
- file paths and filenames.

## Optional anonymous telemetry

Telemetry is disabled by default. A user must enable it and choose an HTTPS endpoint. Before sending, the CLI builds events from an allow-list; arbitrary properties are rejected.

Allowed fields are limited to:

- one-time event ID, event name, schema version, plugin version, and UTC calendar date;
- success or failure outcome;
- application status transitions;
- coarse count buckets such as `0`, `1`, `2-5`, `6-20`, or `21+`.

No career content is hashed and sent as a substitute for raw content. Hashing predictable values such as an employer or email address would not make them safely anonymous.

Events contain no stable installation or session identifier, so the collector cannot reconstruct an individual user's journey from the payload. A production collector must also discard source IP addresses and request logs rather than treating transport metadata as anonymous.

Users can inspect the exact queue with `yapply telemetry preview`, clear it with `yapply telemetry clear`, disable collection with `yapply telemetry disable`, or set `DISABLE_TELEMETRY=1` / `DO_NOT_TRACK=1` for an immediate override.

## Network behavior

The core workflow makes no provider API calls. `yapply telemetry flush` is the only CLI command that sends data, and it only sends previously previewable allow-listed events to the configured HTTPS endpoint.

## Who reads your files

Yapply has no server. The AI agent you run it in, such as Claude Code or Codex, reads and writes the workspace to do what you ask, under that provider's own privacy terms. When you ask for job leads, the agent searches the web with its own tools, and the skills tell it to leave your identity and contact details out of searches.

## Retention

Yapply keeps nothing off your computer. Workspace files stay until you delete them, and deleting the `.yapply` folder removes everything Yapply created. Queued telemetry events are removed from the queue once `yapply telemetry flush` sends them, or when you run `yapply telemetry clear`. How long a telemetry collector keeps events is up to whoever runs the endpoint you chose.

## Contact

Ask privacy questions in [GitHub issues](https://github.com/Faiz-k490/Yapply/issues). Report privacy bugs privately, as described in [SECURITY.md](SECURITY.md).
