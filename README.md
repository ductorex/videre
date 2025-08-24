Pytest + Coverage:

```
uv run pytest --cov=videre --cov-report=term-missing --cov-report=html --cov-report=json videre_tests
```

Ruff:

```
uv run ruff format

uv run ruff check

uv run ruff check --fix
```
