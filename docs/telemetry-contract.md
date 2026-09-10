# Telemetry contract

Telemetry is off by default and follows four rules:

1. Event names and properties are allow-listed in code.
2. Free-form strings from career data are never accepted as event properties.
3. Events remain inspectable in `.yapply/telemetry/events.jsonl` until explicitly flushed.
4. `DISABLE_TELEMETRY=1` and `DO_NOT_TRACK=1` always win.

Events use a one-time random ID for delivery deduplication and a UTC calendar date for aggregation. They contain no stable installation ID or session ID. The future production collector must discard source IP addresses and avoid request logging.

Supported events:

| Event | Allowed properties |
| --- | --- |
| `workspace_initialized` | `outcome` |
| `profile_validated` | `outcome`, `fact_count_bucket`, `error_count_bucket` |
| `application_created` | `outcome` |
| `application_validated` | `outcome`, `statement_count_bucket`, `error_count_bucket` |
| `application_status_changed` | `outcome`, `from_status`, `to_status` |

The configured collector must use HTTPS. The CLI sends a JSON object containing an `events` array and deletes queued events only after a successful 2xx response.
