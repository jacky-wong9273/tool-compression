"""Population summary of one editor revision, and the diff between two summaries.

``population_summary`` takes the renderer and helpers as arguments and imports
no editor itself, so ``scripts/clean_start_sent_digest.py population`` can run
this same code against the editors of an earlier commit (a ``git worktree`` on
``PYTHONPATH``) and the package can run it against the current ones. Only
initial catalogues of in-scope questions are summarised; questions and gold
answers are never editor inputs. Token counts are local o200k_base counts.
"""

from __future__ import annotations

from collections import Counter
import json

ARMS = ("U", "S", "X", "SX")
EXAMPLES = 12


def population_summary(categories, questions, facing, render, counter, dump) -> dict:
    cache: dict[str, dict] = {}
    tools_tokens = {"all": Counter(), "by_category": {}}
    changed = Counter()
    s_occurrences = Counter()
    cue_rows: dict[tuple, dict] = {}
    s_edits: dict[tuple, dict] = {}
    rules = None
    total = 0
    for category in categories:
        per_category = Counter()
        for case in questions(category):
            tools = facing(case["function"], case["category"])
            key = dump(tools)
            if key not in cache:
                rendered = render(tools)
                rules = rendered["rules"]
                cache[key] = {
                    "rendered": rendered,
                    "tokens": {arm: counter.count(dump(rendered["arms"][arm])) for arm in ARMS},
                    "catalogue": len(cache),
                }
            record = cache[key]
            rendered = record["rendered"]
            total += 1
            for arm in ARMS:
                per_category[arm] += record["tokens"][arm]
                tools_tokens["all"][arm] += record["tokens"][arm]
                if arm != "U" and rendered["arms"][arm] != rendered["arms"]["U"]:
                    changed[arm] += 1
            for change in rendered["changes"]:
                if change["arm"] == "S":
                    s_occurrences[change["change_class"]] += 1
                    edit_key = (change["function"], change["pointer"], change["before"])
                    s_edits.setdefault(edit_key, {
                        "function": change["function"],
                        "pointer": change["pointer"],
                        "before": change["before"],
                        "after": change["after"],
                        "change_class": change["change_class"],
                    })
                    continue
                cue_key = (change["function"], change["rival"], change["cue"])
                row = cue_rows.setdefault(cue_key, {
                    "target": change["function"],
                    "rival": change["rival"],
                    "cue": change["cue"],
                    "axis": change["axis"],
                    "questions": 0,
                    "catalogues": set(),
                })
                row["questions"] += 1
                row["catalogues"].add(record["catalogue"])
        tools_tokens["by_category"][category] = {arm: per_category[arm] for arm in ARMS}
    cues = []
    for key in sorted(cue_rows):
        row = dict(cue_rows[key])
        row["catalogues"] = len(row["catalogues"])
        cues.append(row)
    distinct_by_class = Counter(row["change_class"] for row in s_edits.values())
    return {
        "rules": rules,
        "questions": total,
        "unique_catalogues": len(cache),
        "tools_tokens": {
            "all": {arm: tools_tokens["all"][arm] for arm in ARMS},
            "by_category": tools_tokens["by_category"],
        },
        "questions_changed": {arm: changed[arm] for arm in ARMS if arm != "U"},
        "s_edit_occurrences_by_class": dict(sorted(s_occurrences.items())),
        "s_distinct_edits_by_class": dict(sorted(distinct_by_class.items())),
        "s_distinct_edits": [s_edits[key] for key in sorted(s_edits)],
        "cues": cues,
    }


def _percent(part: int, whole: int) -> float | None:
    return round(100 * part / whole, 3) if whole else None


def _token_view(tokens: dict) -> dict:
    u = tokens["U"]
    return {
        **tokens,
        "S-U_percent": _percent(tokens["S"] - u, u),
        "X-U_percent": _percent(tokens["X"] - u, u),
        "SX-U_percent": _percent(tokens["SX"] - u, u),
    }


def revision_diff(before: dict, after: dict) -> dict:
    """What changed between two population summaries, with counts and examples."""
    old_cues = {(row["target"], row["rival"], row["cue"]): row for row in before["cues"]}
    new_cues = {(row["target"], row["rival"], row["cue"]): row for row in after["cues"]}
    old_pairs = {(row["target"], row["rival"]): row for row in before["cues"]}
    new_pairs = {(row["target"], row["rival"]): row for row in after["cues"]}
    reworded = sorted(
        pair for pair in set(old_pairs) & set(new_pairs) if old_pairs[pair]["cue"] != new_pairs[pair]["cue"]
    )
    removed = sorted(key for key in old_cues if (key[0], key[1]) not in new_pairs)
    added = sorted(key for key in new_cues if (key[0], key[1]) not in old_pairs)
    old_edits = {(row["function"], row["pointer"], row["before"]): row for row in before["s_distinct_edits"]}
    new_edits = {(row["function"], row["pointer"], row["before"]): row for row in after["s_distinct_edits"]}
    dropped = sorted(key for key in old_edits if key not in new_edits)
    gained = sorted(key for key in new_edits if key not in old_edits)
    rewritten = sorted(
        key for key in set(old_edits) & set(new_edits) if old_edits[key]["after"] != new_edits[key]["after"]
    )

    def by_class(keys, table) -> dict:
        return dict(sorted(Counter(table[key]["change_class"] for key in keys).items()))

    return {
        "rules": {"before": before["rules"], "after": after["rules"]},
        "questions": {"before": before["questions"], "after": after["questions"]},
        "tools_tokens_all": {
            "before": _token_view(before["tools_tokens"]["all"]),
            "after": _token_view(after["tools_tokens"]["all"]),
        },
        "tools_tokens_by_category": {
            category: {
                "before": _token_view(before["tools_tokens"]["by_category"][category]),
                "after": _token_view(after["tools_tokens"]["by_category"][category]),
            }
            for category in after["tools_tokens"]["by_category"]
        },
        "questions_changed": {"before": before["questions_changed"], "after": after["questions_changed"]},
        "s_edit_occurrences_by_class": {
            "before": before["s_edit_occurrences_by_class"],
            "after": after["s_edit_occurrences_by_class"],
        },
        "s_distinct_edits": {
            "no_longer_made": {"count": len(dropped), "by_class": by_class(dropped, old_edits),
                               "examples": [old_edits[key] for key in dropped[:EXAMPLES]]},
            "new": {"count": len(gained), "by_class": by_class(gained, new_edits),
                    "examples": [new_edits[key] for key in gained[:EXAMPLES]]},
            "rewritten": {
                "count": len(rewritten),
                "examples": [
                    {**new_edits[key], "before_rules_after": old_edits[key]["after"]} for key in rewritten[:EXAMPLES]
                ],
            },
        },
        "cues": {
            "distinct": {"before": len(before["cues"]), "after": len(after["cues"])},
            "cued_question_occurrences": {
                "before": sum(row["questions"] for row in before["cues"]),
                "after": sum(row["questions"] for row in after["cues"]),
            },
            "removed": [old_cues[key] for key in removed],
            "added": [new_cues[key] for key in added],
            "reworded": [
                {"target": pair[0], "rival": pair[1], "before": old_pairs[pair]["cue"], "after": new_pairs[pair]["cue"],
                 "questions": new_pairs[pair]["questions"]}
                for pair in reworded
            ],
        },
    }


def dumps(payload: dict) -> str:
    return json.dumps(payload, indent=1, ensure_ascii=False) + "\n"
