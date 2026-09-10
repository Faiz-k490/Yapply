# Yapply workspace data contract

All user-owned data lives under `.yapply/` in the selected workspace.

## Verified profile facts

`profile.json` contains identity, preferences, and a list of facts. Each fact needs a stable ID, category, factual statement, and evidence note. Application content must cite one or more fact IDs.

```json
{
  "schema_version": 1,
  "identity": {
    "name": "Example Person",
    "email": "person@example.com",
    "phone": "",
    "location": "Example City",
    "links": []
  },
  "preferences": {
    "target_roles": ["Software Engineer"],
    "target_locations": ["Remote"],
    "work_authorization": "",
    "remote_preference": "any"
  },
  "facts": [
    {
      "id": "fact-project-compiler",
      "category": "project",
      "statement": "Built a compiler project in Rust.",
      "evidence": "Repository and course submission",
      "keywords": ["Rust", "compilers"]
    }
  ]
}
```

The example above is synthetic and is not copied into new workspaces.

## Application directory

Each application lives in `.yapply/applications/<slug>/` and contains `job.json` plus `resume.json`.

Every generated résumé statement uses this shape:

```json
{
  "text": "Built a compiler project in Rust.",
  "source_fact_ids": ["fact-project-compiler"]
}
```

`yapply validate-application <slug>` rejects empty statements, missing provenance, unknown fact IDs, duplicate fact IDs, unsupported status values, and malformed workspace records.

## Tracker states

The supported states are `saved`, `preparing`, `ready`, `applied`, `interviewing`, `offer`, `rejected`, and `withdrawn`.
