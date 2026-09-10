---
name: find-jobs
description: Find and assess current job or internship openings against a verified Yapply profile. Use when the user asks to discover roles, build a shortlist, compare openings, check eligibility, or refresh job leads. Do not use when the user already selected one role and wants application materials.
---

# Find jobs with Yapply

Build a current, evidence-backed shortlist grounded in the user's preferences and verified profile.

## Workflow

1. Resolve the plugin root from this skill's installed `SKILL.md` path and use `python3 <plugin-root>/scripts/yapply.py --root <workspace> ...` for CLI calls.
2. Run `status` and `validate-profile`. If the workspace does not exist, use the onboarding workflow first. If only minor preference fields are missing, continue with explicit assumptions and label them.
3. Read `.yapply/profile.json`, but avoid repeating identity or contact fields in searches or outputs.
4. Search current, primary job sources. Open each shortlisted posting and verify that it is live, its location, employment type, experience expectations, and any work-authorization constraint.
5. Rank roles using only stated preferences and source facts. Separate hard eligibility checks from softer fit signals.
6. Present a compact shortlist with role, employer, location, direct posting link, eligibility result, and the source-fact IDs supporting the fit assessment.
7. When the user asks to save the shortlist, append records to `.yapply/candidates.json`. Store the posting text or a faithful snapshot only in the local workspace; telemetry must never receive company names, titles, URLs, or descriptions.

## Guardrails

- Do not claim a role is open without checking the live source.
- Do not treat missing requirements as satisfied.
- Do not create an application or apply unless the user asks.
