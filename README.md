# Videre

Simple Python GUI framework based on Pygame.

Still Work In Progress.

## Unicode

Videre targets **Unicode 16.0** as its single reference version (enforced at
import by `videre/core/textual/unicode_props.py`). The Unicode algorithms it implements —
UAX#29 grapheme/word segmentation and the UAX#9 bidirectional algorithm — are
16.0-conformant and validated against Unicode's official conformance suites.

See [docs/unicode-conformance.md](docs/unicode-conformance.md) for the full audit
(coverage, supported scripts, and known gaps).

## Origin of name

https://fr.wiktionary.org/wiki/videre#la
https://en.wiktionary.org/wiki/videre

## Development

To run unit tests with Pytest + Coverage:

```
uv run pytest --cov=videre --cov-report=term-missing --cov-report=html --cov-report=json tests -n auto
```

To format code with Ruff:

```
uv run ruff format

uv run ruff check

uv run ruff check --fix
```
