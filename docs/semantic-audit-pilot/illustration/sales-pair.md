# Worked illustration: an invented sales pair

This pair is invented. It is not a BFCL catalogue, it is not one of the 12 selected cases, and it is outside the pilot denominator. The wording is local to this note. No design-discussion table is treated as a locked script.

The same renderer builds U, S, X, and SX. Input and token totals are in `sales-pair.json`.

## U

`record_completed_sale`: "Records a completed retail sale for one stock-keeping unit. The amount is in US dollars, and the stored result is a completed sale."

- `sku`: "Stock-keeping unit of the product sold."
- `amount`: "Completed-sale amount in US dollars."

`prepare_price_quote`: "Prepares a price quote for one stock-keeping unit. The amount is in US dollars, and the stored result is a quote rather than a completed sale."

- `sku`: "Stock-keeping unit of the product being quoted."
- `amount`: "Quoted amount in US dollars."

Read alone, the quote tool already says it stores a quote rather than a completed sale. S keeps that clause. Deleting it would hide the tool's own distinction in order to make the later cue look more necessary.

## S, each tool alone

`record_completed_sale`: "Record a completed sale of one stock-keeping unit, in US dollars."

The second U sentence repeats "completed sale." US dollars stay. `sku` becomes "Stock-keeping unit sold." The amount line is already the unit and the completed-sale role, so it stays.

`prepare_price_quote`: "Prepare a price quote for one stock-keeping unit, in US dollars, stored as a quote rather than a completed sale."

`sku` becomes "Stock-keeping unit quoted." The amount line stays.

## X, from the original sentences

One space, then the cue, on the function description only.

`record_completed_sale` cue: "Unlike prepare_price_quote, which prepares a price quote and stores a quote rather than a completed sale, this records a completed sale and stores that completed sale."

`prepare_price_quote` cue: "Unlike record_completed_sale, which records a completed sale and stores that completed sale, this prepares a price quote and stores a quote rather than a completed sale."

The "rather than a completed sale" half is in the quote tool's own original description. It is not inferred from the sale tool being silent.

Rejected cue: "Only record_completed_sale uses US dollars." Both originals state US dollars. A shared fact is not a contrast.

## SX

SX appends the same cue strings to the S descriptions. The sale tool's cue still says the result is stored as a completed sale, even though S had shortened that repeated clause. The cue is not rewritten to match S.

Local `o200k_base` field tokens for this illustration: U 92, S 65, X 154, SX 127. Those numbers are not part of the 12-case tables.
