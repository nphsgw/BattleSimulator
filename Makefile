format:
	uv run --extra all black .
	uv run --extra all ruff check --fix

clean:
	rm -rf __pycache__ .ipynb_checkpoints .pytest_cache .ruff_cache battlesim.egg-info build dist
