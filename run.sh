#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  echo "❌ .env not found. Copy .env.example to .env and add your GEMINI_API_KEY." >&2
  exit 1
fi

echo "🚀 Starting LegalEase Pro at http://localhost:8001"
echo "   Frontend: http://localhost:8001/"
echo "   API docs: http://localhost:8001/docs"

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
