#!/usr/bin/env bash
# Score saved T1 or T2 outputs with bfcl evaluate. Does not generate.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

for arg in "$@"; do
  if [[ "$arg" == "generate" || "$arg" == "--live" ]]; then
    echo "refusing ${arg}; this script only evaluates saved outputs" >&2
    exit 2
  fi
done

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
Usage: run_followon_evaluate.sh --bfcl PATH --project-root PATH --arm T1|T2

Runs `bfcl evaluate` for one saved follow-on directory. Generate is refused.
The scoring alias is DeepSeek-V3.2-Exp-FC. The child key is a dummy.
EOF
  exit 0
fi

BFCL=""
PROJECT_ROOT=""
ARM=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --bfcl)
      BFCL="$2"
      shift 2
      ;;
    --project-root)
      PROJECT_ROOT="$2"
      shift 2
      ;;
    --arm)
      ARM="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$BFCL" || -z "$PROJECT_ROOT" || -z "$ARM" ]]; then
  echo "--bfcl, --project-root, and --arm are required" >&2
  exit 2
fi

python3 -m tool_compression followon-score \
  --bfcl "$BFCL" \
  --project-root "$PROJECT_ROOT" \
  --arm "$ARM"
