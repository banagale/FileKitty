lint:
	poetry run ruff check .

format:
	poetry run ruff format .

test:
	poetry run pytest
