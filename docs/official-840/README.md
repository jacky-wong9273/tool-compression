# Official 840-case U/S/X/SX package

Preparation for a later off-peak flight of the official sample: `multiple` 200, `simple_python` 400, `irrelevance` 240. This directory converts a fresh U for all 840 cases, seals a reviewed partial S/X tranche, and dry-runs the flight plan. It does not call a provider, and it does not settle official scores.

The formative 12-case pilot under `docs/semantic-audit-pilot/` stays frozen. Its systems-test scores are a different sample.

| Section | File |
| --- | --- |
| What this package is for | [objectives.md](objectives.md) |
| Pin, four-way design, thinking passes, sharing, off-peak stop | [methodology.md](methodology.md) |
| The sealed tranche, case by case | [reading.md](reading.md) |
| How a later scored run would be read | [quality.md](quality.md) |
| The dry-run that was executed, and the later live command | [operator.md](operator.md) |
| Cases still without an S or an X | [remaining-work.md](remaining-work.md) |
| Counts, identities, and dry-run status | [handover.md](handover.md) |
| Stage A gate | [dry-run/gate.json](dry-run/gate.json) |

```bash
EXPLORATORY_CEILING_CNY='0.01' \
  python -m tool_compression usx-840 --no-api \
  --bfcl-root /path/to/gorilla/berkeley-function-call-leaderboard \
  --out /tmp/official-840-gate
pytest -q
```

`EXPLORATORY_CEILING_CNY` has to be set. The value in the committed gate is a proof figure. It does not authorize a later process to spend. `--live` on this package stops while any case remains unsealed.
