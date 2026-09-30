# Contributing to Yapply

Thanks for helping. Yapply is small on purpose: a Python standard-library CLI, five Markdown skills, and two plugin manifests.

## Set up

```bash
git clone https://github.com/Faiz-k490/Yapply.git
cd Yapply
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
```

Try your changes in Claude Code without installing from GitHub:

```bash
python3 scripts/build_plugin.py --force
claude --plugin-dir dist/yapply
```

## Ground rules

- **No real personal data.** Tests, fixtures, screenshots, and issues use fictional people only. Use `example.test` addresses.
- **Provenance is not optional.** Don't loosen the validator to make a résumé pass. Fix the facts or the draft instead.
- **Telemetry stays allow-listed.** A new event or property needs a matching update to [docs/telemetry-contract.md](docs/telemetry-contract.md) and [PRIVACY.md](PRIVACY.md) in the same pull request.
- **No new runtime dependencies** without an issue discussing why the standard library can't do it.
- **Keep the numbers true.** `tests/test_yapply.py` checks the "By the numbers" table in the README. If you add a skill, stage, or telemetry event, update the table too.

## Pull requests

1. Open an issue first for anything larger than a bug fix.
2. Keep each pull request to one change, with tests.
3. Make sure `python3 -m unittest discover -s tests` and `claude plugin validate . --strict` both pass.
4. If you change the look of the README images, edit `.github/assets/src/card.html` and run `scripts/render_brand_assets.sh`.
