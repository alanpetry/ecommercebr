#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-../.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

"$PYTHON_BIN" scripts/sync_telegram.py
"$PYTHON_BIN" scripts/clean_content.py
"$PYTHON_BIN" scripts/ai_moderate.py
"$PYTHON_BIN" scripts/build_site.py

if git diff --quiet -- content docs config; then
  echo "Sem mudanças para publicar."
  exit 0
fi

git add config content docs
git commit -m "Atualiza conversas da comunidade"
git push
