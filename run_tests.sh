#!/usr/bin/env bash
# ==============================================================================
# Helper script to run test automation without worrying about python vs python3
# ==============================================================================
cd "$(dirname "$0")"

if [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python 3 was not found."
    exit 1
fi

$PYTHON_CMD test_automation_runner.py "$@"
