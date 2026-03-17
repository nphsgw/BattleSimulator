format:
	uv run --extra all ruff format battlesim tests
	uv run --extra all ruff check --fix battlesim tests

lint:
	uv run --extra all ruff check battlesim tests

format-check:
	uv run --extra all ruff format --check battlesim tests

typecheck:
	uv run --extra all ty check battlesim tests/test_battle.py tests/test_composite.py tests/test_terrain.py

check:
	uv run --extra all ruff check battlesim tests
	uv run --extra all ruff format --check battlesim tests
	uv run --extra all ty check battlesim tests/test_battle.py tests/test_composite.py tests/test_terrain.py
	uv run pytest -v

clean:
	rm -rf __pycache__ .ipynb_checkpoints .pytest_cache .ruff_cache battlesim.egg-info build dist
