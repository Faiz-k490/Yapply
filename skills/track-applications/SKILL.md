---
name: track-applications
description: Review or update the local Yapply application tracker. Use when the user asks what they applied to, wants pipeline totals, changes an application status, records an interview or offer, or asks for follow-up priorities. Do not use for discovering roles or drafting application content.
---

# Track Yapply applications

Keep the local application pipeline accurate without leaking employer or career data.

## Workflow

1. Resolve the plugin root from this skill's installed `SKILL.md` path and call `python3 <plugin-root>/scripts/yapply.py --root <workspace> ...`.
2. Run `status --json` to inspect totals. Read `.yapply/tracker.json` only when the user needs application-level detail.
3. Use `track <slug> <status>` for updates. Supported states are `saved`, `preparing`, `ready`, `applied`, `interviewing`, `offer`, `rejected`, and `withdrawn`.
4. Treat `applied`, `interviewing`, `offer`, `rejected`, and `withdrawn` as real-world assertions. Update them only from the user's statement or direct evidence in scope.
5. Report the new state and any obvious next action. Do not invent deadlines or contact history.

## Telemetry

Status events contain only the previous and new state plus anonymous event metadata. They never contain an application slug, company, role, note, or timestamp copied from the tracker. Honor `DISABLE_TELEMETRY=1` and `DO_NOT_TRACK=1` even when local configuration is enabled.
