---
name: prepare-application
description: Prepare a tailored, truthful job application from a selected posting and a verified Yapply profile. Use for tailoring a resume, drafting a cover letter, creating an application record, or checking that claims are supported. Do not use for broad job discovery or for submitting an application without explicit user direction.
---

# Prepare a grounded application

Create tailored material while maintaining a machine-checkable link to the user's verified source facts.

## Workflow

1. Resolve the plugin root from this skill's installed `SKILL.md` path. Use `python3 <plugin-root>/scripts/yapply.py --root <workspace> ...` for all Yapply CLI calls.
2. Run `validate-profile`. Stop and repair unsupported or ambiguous profile facts before drafting from them.
3. Obtain the full posting from the user or its live primary-source page. Capture the employer, role, URL, location, description, and current UTC timestamp.
4. Choose a lowercase application slug that contains only letters, numbers, and hyphens. Run `create-application <slug>` unless that application already exists.
5. Write the posting to `.yapply/applications/<slug>/job.json`.
6. Draft `.yapply/applications/<slug>/resume.json` using the contract in `<plugin-root>/docs/data-contract.md`. Every summary, skill, item, and bullet must include one or more `source_fact_ids`. Tailoring may select and reorder facts or improve wording, but it must not introduce new dates, metrics, tools, titles, credentials, outcomes, or responsibilities.
7. Run `validate-application <slug>`. Fix every error. Then run `track <slug> ready`.
8. Show the user the resulting local files and a concise claim-to-source review. Keep the status at `ready` until the user confirms they actually applied.

## Guardrails

- Do not write a claim whose supporting fact is merely related; the fact must directly support it.
- Do not weaken provenance requirements to make validation pass.
- Do not submit forms, send messages, or mark an application `applied` without explicit user authorization.
- Never put posting or résumé content into telemetry.
