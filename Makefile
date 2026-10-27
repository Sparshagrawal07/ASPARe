.PHONY: install test lint typecheck check demo dashboard showcase package

install:
	python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev,dashboard]"

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check src tests dashboard scripts

typecheck:
	.venv/bin/mypy

check: lint typecheck test
	.venv/bin/python tests/check_docs.py

demo:
	.venv/bin/python -m aspare.cli --mode dataset

dashboard:
	.venv/bin/streamlit run dashboard/app.py

# Live demo against your AWS account (set ASPARE_REGION to an allowed region first).
showcase:
	.venv/bin/streamlit run dashboard/app.py

package:
	scripts/package_lambda.sh
