@default:
  @just --list

# Check formatting with ruff
@check:
  uv run ruff format --check

# Apply formatting with ruff
@format:
  uv run ruff format

# Run ruff linter
@lint:
  uv run ruff check
