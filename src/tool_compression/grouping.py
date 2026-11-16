"""Exact-request groups within one case and one replicate.

P, I, and C keep their own hashes. When those hashes coincide, the comparison
condition is the reporting label L. U and E join that group when their request
hashes match. The same hash in another case or replicate is a different group.
"""

from dataclasses import dataclass

REPORTING_LABEL = "L"
CONDITION_ORDER = ("U", "P", "I", "C", "L", "E")


@dataclass(frozen=True)
class RequestGroup:
    category: str
    case_id: str
    replicate: int
    request_hash: str
    members: tuple[str, ...]
    shared_response_id: str

    def as_dict(self) -> dict:
        return {
            "category": self.category,
            "case_id": self.case_id,
            "replicate": self.replicate,
            "request_hash": self.request_hash,
            "members": list(self.members),
            "shared_response_id": self.shared_response_id,
            "group_is_one_independent_response": True,
            "extra_members_are_reused": len(self.members) > 1,
            "logical_members": len(self.members),
        }


def local_reporting_label(hashes: dict[str, str]) -> dict:
    """L when the P, I, and C request hashes are equal. Otherwise no label."""
    present = all(name in hashes for name in ("P", "I", "C"))
    coincide = present and hashes["P"] == hashes["I"] == hashes["C"]
    return {
        "coincide": coincide,
        "label": REPORTING_LABEL if coincide else None,
        "request_hash": hashes["P"] if coincide else None,
        "traces": ("P", "I", "C"),
        "label_is_compressor": False,
        "label_is_selected_winner": False,
    }


def comparison_condition_hashes(local_hashes: dict[str, str], e_hash: str | None) -> dict[str, str]:
    """Conditions that can share a response: U, L or the separate local arms, and E."""
    if "U" not in local_hashes:
        raise ValueError("U is required")
    conditions = {"U": local_hashes["U"]}
    label = local_reporting_label(local_hashes)
    if label["coincide"]:
        conditions[REPORTING_LABEL] = label["request_hash"]
    else:
        for name in ("P", "I", "C"):
            if name in local_hashes:
                conditions[name] = local_hashes[name]
    if e_hash is not None:
        conditions["E"] = e_hash
    return conditions


def group_exact_requests(
    category: str,
    case_id: str,
    replicate: int,
    condition_hashes: dict[str, str],
) -> list[RequestGroup]:
    if replicate < 0:
        raise ValueError("replicate index is non-negative")
    buckets: dict[str, list[str]] = {}
    for name in _ordered(condition_hashes):
        buckets.setdefault(condition_hashes[name], []).append(name)
    groups = []
    for digest, members in buckets.items():
        ordered = tuple(members)
        groups.append(
            RequestGroup(
                category=category,
                case_id=case_id,
                replicate=replicate,
                request_hash=digest,
                members=ordered,
                shared_response_id=f"{category}/{case_id}/r{replicate}/{digest}",
            )
        )
    return groups


def _ordered(condition_hashes: dict[str, str]) -> list[str]:
    return sorted(
        condition_hashes,
        key=lambda name: (
            CONDITION_ORDER.index(name) if name in CONDITION_ORDER else len(CONDITION_ORDER),
            name,
        ),
    )
