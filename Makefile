.PHONY: app check clean format format-check install-hooks lint typecheck

format:
	uv run --extra all ruff format apps battlesim tests
	uv run --extra all ruff check --fix apps battlesim tests

lint:
	uv run --extra all ruff check apps battlesim tests

format-check:
	uv run --extra all ruff format --check apps battlesim tests

typecheck:
	uv run --extra all ty check apps battlesim tests
	uv run --extra all mypy

check:
	uv run --extra all pre-commit validate-config .pre-commit-config.yaml
	uv run --extra all ruff check apps battlesim tests
	uv run --extra all ruff format --check apps battlesim tests
	uv run --extra all ty check apps battlesim tests
	uv run --extra all mypy
	uv run --extra all pytest -v

install-hooks:
	uv run --extra all pre-commit install --hook-type pre-commit --overwrite

app:
	uv run --extra app streamlit run apps/battle_viewer.py

clean:
	rm -rf __pycache__ .ipynb_checkpoints .pytest_cache .ruff_cache battlesim.egg-info build dist
