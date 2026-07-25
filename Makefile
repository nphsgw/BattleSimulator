format:
	uv run --extra all ruff format apps battlesim tests
	uv run --extra all ruff check --fix apps battlesim tests

lint:
	uv run --extra all ruff check apps battlesim tests

format-check:
	uv run --extra all ruff format --check apps battlesim tests

typecheck:
	uv run --extra all ty check battlesim tests/test_battle.py tests/test_composite.py tests/test_terrain.py

check:
	uv run --extra all ruff check apps battlesim tests
	uv run --extra all ruff format --check apps battlesim tests
	uv run --extra all ty check battlesim tests/test_battle.py tests/test_composite.py tests/test_terrain.py
	uv run pytest -v

app:
	uv run --extra app streamlit run apps/battle_viewer.py

clean:
	rm -rf __pycache__ .ipynb_checkpoints .pytest_cache .ruff_cache battlesim.egg-info build dist
