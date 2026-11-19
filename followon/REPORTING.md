# Follow-on reporting shell

`followon/reporting_shell.json` has one offline row per category, arm (`U`, `T1`, `T2`), and an empty replicate. `status` is `offline_only`.

`f_new` is T2 versus T1 on the complete category: numerator, denominator, and unknown preparation failures. Request groups are the sum, over prepared cases, of the distinct complete U/T1/T2 requests in that case. Local token sums use `o200k_base` on the prepared request. They are not provider total input `T`.

`mean_T`, paired saving, official correct, paired gains and losses, name hits, and abstention counts are null. Those cells stay null until a later flight stores matched responses. This file does not invent them.

Historical U/L/E rows are a separate list. Their status is `historical_recorded`. They are the closed 18–19 November result, recomputed from the committed settlement, and they are not contemporaneous comparators for T1 or T2.

The primary funnel in `followon/audit_summary.json` has four cumulative rows. Denominators are all eligible primary fields and all 200 primary cases, not the edited subset. Stop reasons partition every original case.
