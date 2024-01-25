@default:
  @just --list

# Check formatting with ruff
@check:
  pipenv run ruff format --check

# Apply formatting with ruff
@format:
  pipenv run ruff format

# Run ruff linter
@lint:
  pipenv run ruff check
