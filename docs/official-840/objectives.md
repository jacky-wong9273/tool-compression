# Objectives

Prepare the official 840-case U/S/X/SX sample so a later off-peak flight can be audited and then flown. The flight itself is a separate authorization. This package stops at the plan, the converted catalogues, a partial editorial seal, and a no-API gate.

## In scope

- A fresh conversion of all 840 pinned BFCL records into OpenAI-completions tools. That conversion is U. It is contemporaneous with this package. It does not copy a historical official U file.
- S and X written independently from that U, for a counted tranche, then SX composed from those two frozen bases.
- A runner that plans thinking off and then thinking on over the same catalogues, shares one observation only inside one cell, and stops on a peak clock.
- A Stage A gate with `provider_called: false` and `spend_cny: "0"`.
- Counts of cued and uncued sealed cases, and of the identities S=U, X=U, SX=S, SX=X, and SX=U.
- A remaining-work manifest for every case that does not yet have a sealed S and X.

## Out of scope

- A paid call, a provider socket, and `--live` as an executed command.
- Official settlement. `official_settlement` stays false until Jacky separately says otherwise.
- The closed 10% target and the official U/L/E scores. Protocol v1.1 keeps `target_provider_input_reduction` at `1/10` and `official_accuracy_in_scope` false.
- Rewriting the 12-case first pilot, its cue revision, or its systems-test flight. Those trees stay byte-stable. The first-pilot commit remains `61329baeba8e40fb3ed6c62fbbc8cae71ded1ac3`.
- A peak-continuation switch. `--authorize-peak` belongs to the 12-case systems test. This command does not accept it.
- Inventing an S edit or an X cue for a case that was not read. Unsealed cases stay in [remaining-work.json](remaining-work.json).

## What a later flight would answer

Once every case is sealed and a live run is separately authorized, the question is official full-call accuracy under five contrasts: S−U, X−U, SX−S, SX−X, and SX−U. Each contrast is computed twice, once for thinking off and once for thinking on. Local token length is not that accuracy. The 12-case systems-test results are not a stand-in for this sample.
