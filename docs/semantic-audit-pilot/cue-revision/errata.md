# Errata to the first-pilot explanations

These notes correct explanations in the first pilot. They do not replace the sealed strings. The rendered catalogues, token tables, selection manifest, S record, and X record under `docs/semantic-audit-pilot/` stay as sealed at `61329ba`. The corrected wording for the new cues is in this directory, not in those files.

## ROA's rival was right for the wrong order reason

In `edits/x-record.json`, the `financial_ratios_calculate_ROA` entry says ROE "is earlier than the growth-rate tool." It is not. Catalogue order in `multiple_12` is the year-over-year growth tool, then ROE, then ROA. ROE remains the rival of ROA because the two are the similar return ratios. Catalogue order is not needed for that choice. The sealed first-pilot cue string is unchanged.

## The growth tool assesses; it does not analyze

In `edits/s-record.json`, the species parameter of `wildlife_population_assess_growth` gives this reason: the verb "calculated" was not replaced with the function's verb "analyzes." The growth function's description assesses population growth. The sibling, `ecological_impact_analyze`, analyzes impact. The parameter's own verb is "calculated," and keeping that verb is still what the sealed replacement does. The attribution of "analyzes" to the growth function is the error. The sealed S text is unchanged.

## "No inventoried claim marked lost" is not "all information was preserved"

The first-pilot ledger says the editor marked no inventoried claim as lost or unsupported. That is a statement about the inventory and the marks. It is not a finding that all information was preserved.

In `simple_python_175`, the law-type description originally reads "The type of law case. eg. Bankruptcy". The sealed S replacement removes `eg. Bankruptcy`. The schema has no enum and no other example. The omission is marked illustrative. An example can guide an argument even when it is not a requirement. The same-sitting self-review in the first pilot, and the same-sitting reread in this pass, cannot settle whether that removal changes a later argument. S was not reopened here.
