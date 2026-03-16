# Videre

Simple Python GUI framework based on Pygame.

Still Work In Progress.

## Origin of name

https://fr.wiktionary.org/wiki/videre#la
https://en.wiktionary.org/wiki/videre

## Development

To run unit tests with Pytest + Coverage:

```
uv run pytest --cov=videre --cov-report=term-missing --cov-report=html --cov-report=json videre_tests
```

To format code with Ruff:

```
uv run ruff format

uv run ruff check

uv run ruff check --fix
```
