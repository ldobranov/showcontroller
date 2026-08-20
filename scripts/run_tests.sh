#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

python3 -m compileall -q \
    app.py auth.py config.py engine.py gpio.py logger.py paths.py \
    service.py state.py udp.py routes services modules
python3 -m unittest discover -s tests -p 'test_*.py' -v
bash -n install.sh update.sh scripts/run_tests.sh scripts/safe_update.sh
