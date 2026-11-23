# Selection manifest

Selection used case ids only. Questions, gold calls, and descriptions were not opened to choose the sample.

The rule, source hashes, and the 12 selected rows are in `manifest.json`. The full 840-row ranking is `ranked-ids.tsv`. The 12-row extract is `selected-ids.tsv`.

Both TSV files are the pre-recorded lists. Their SHA-256 values are locked in `manifest.json` and in `tests/test_semantic_audit.py`.

| File | SHA-256 |
| --- | --- |
| `BFCL_v4_multiple.json` | `aef168155ebd74b7ac2401198b201343bc7d16d7a3d7e0d4e6d8ee82c6969b2a` |
| `BFCL_v4_simple_python.json` | `82dd63ba502eb2520c6b5d1d9a5c4b590e03ff261565175561f6228a367d1991` |
| `BFCL_v4_irrelevance.json` | `2b6ed4c2e992cdcf5f1678a701851f944bef7550ee026ed1ddb89efed5be01a6` |
| `ranked-ids.tsv` | `e56fb0e69e45868dc9d9f1f35492b06a1329e286ddbbd417c6c18d1d354f1bc3` |
| `selected-ids.tsv` | `b613f6d31b3e6ffea5520393bf6d9fa16082c84400274094d040b2a82e3b0360` |

Pinned gorilla commit: `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`.

Selected ids, in rank order: `multiple_35`, `multiple_0`, `multiple_11`, `multiple_12`, `multiple_7`, `multiple_92`, `multiple_153`, `multiple_100`, `simple_python_175`, `simple_python_34`, `irrelevance_59`, `irrelevance_50`.
