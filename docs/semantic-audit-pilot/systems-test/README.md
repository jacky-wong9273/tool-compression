# USX systems test

A scored flight path for the same 12 catalogues as the [first pilot](../README.md) and the [cue revision](../cue-revision/README.md). It is a systems test: the machinery can build the four arms, share identical payloads, reserve against a supplied ceiling, and name the official scorer. It is not Evaluation Protocol v1.1 settlement, and it does not move the 10% target.

No provider was called to produce this directory. The gate in [dry-run/gate.json](dry-run/gate.json) records spend ¥0.

| Section | File |
| --- | --- |
| What this flight asks | [objectives.md](objectives.md) |
| Arms, model, sharing, rate card, ceiling | [methodology.md](methodology.md) |
| Accuracy, the multiple split, irrelevance, contrasts | [quality.md](quality.md) |
| The dry-run that was executed, and the later live command | [operator.md](operator.md) |
| Stage A gate | [dry-run/gate.json](dry-run/gate.json) |

```bash
python -m tool_compression usx-flight --no-api --bfcl-root /path/to/bfcl --out /tmp/usx-gate
pytest -q
```

`EXPLORATORY_CEILING_CNY` has to be set in the environment for that command. The value used for the committed gate is a proof figure. Jacky supplies the real ceiling before anyone starts the paid call.
