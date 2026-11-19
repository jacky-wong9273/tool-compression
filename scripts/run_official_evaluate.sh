#!/usr/bin/env bash
# Evaluate saved BFCL result files. Does not call a model provider.
# Refuses generate. The scoring alias's registry model_name is deepseek-chat.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

for arg in "$@"; do
  if [[ "$arg" == "generate" ]]; then
    python3 -m tool_compression official-guard --action generate --model DeepSeek-V3.2-Exp-FC
    exit $?
  fi
done

BFCL=""
PROJECT_ROOT=""
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
Usage: run_official_evaluate.sh --bfcl PATH --project-root PATH

Runs `bfcl evaluate` for arms u, l, and e on result files already written under
PROJECT_ROOT/result_{u,l,e}/DeepSeek-V3.2-Exp-FC/. Dummy keys are exported.
Generate is refused. Historical machine paths are not defaults.
EOF
  exit 0
fi

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
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$BFCL" || -z "$PROJECT_ROOT" ]]; then
  echo "both --bfcl and --project-root are required" >&2
  exit 2
fi
if [[ ! -x "$BFCL" ]]; then
  echo "bfcl executable not found: $BFCL" >&2
  exit 2
fi

python3 -m tool_compression official-guard \
  --action evaluate \
  --model DeepSeek-V3.2-Exp-FC \
  --bfcl "$BFCL" >/dev/null

export BFCL_PROJECT_ROOT="$PROJECT_ROOT"
export OPENAI_API_KEY='UNUSED_OFFICIAL_EVAL_NO_PROVIDER_CALL'
export DEEPSEEK_API_KEY='UNUSED_OFFICIAL_EVAL_NO_PROVIDER_CALL'
unset ANTHROPIC_API_KEY GOOGLE_API_KEY MISTRAL_API_KEY COHERE_API_KEY \
  WANDB_BFCL_PROJECT WANDB_API_KEY AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY || true

mkdir -p "$PROJECT_ROOT/logs"
for arm in u l e; do
  echo "===== evaluate arm=$arm ====="
  "$BFCL" evaluate \
    --model DeepSeek-V3.2-Exp-FC \
    --test-category simple_python,multiple,irrelevance \
    --result-dir "result_${arm}" \
    --score-dir "score_${arm}" \
    | tee "$PROJECT_ROOT/logs/bfcl_evaluate_${arm}.log"
done
