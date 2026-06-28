#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

source .venv/bin/activate
python run_portfolio.py -c "configs/portfolios_hhhl_ml1_200.yaml"
