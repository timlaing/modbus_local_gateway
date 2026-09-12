# AGENTS.md

Home Assistant custom integration ("Modbus Local Gateway") that talks to
Modbus TCP gateways via YAML device configs in `device_configs/`. Entities:
sensor, binary_sensor, switch, number, select, text.

## Commands

- Install deps: `uv sync` (uses `uv.lock`; dev deps via `requirements_dev.txt`)
- Tests: `pytest` or `pytest --cov=. --cov-report xml:coverage.xml` (asyncio auto-mode, `tests/`)
- Lint/format: `ruff check .`, `ruff format .`, `isort --check-only --diff .`
- Full check set: `prek run --files <paths>` (yamllint, check-yaml, cspell, prettier, EOF)
- Pre-commit: `pre-commit run --all-files` (ruff, ruff-format, isort, misc)
- Type checks handled via ruff; mypy config absent (mypy cache present, use care)

## Structure

- `custom_components/modbus_local_gateway/` — integration (config_flow, coordinator, entities)
  - `device_configs/` — YAML register/coil definitions (one per device model)
  - `entity_management/` — entity base classes
  - `sensor_types/` — data conversion/value types
- `tests/` — pytest suite (one test file per entity/platform)
- `docs/`, `devices/`, `scripts/` — supporting material
- `.opencode/plans/` — active plans (delete when done)

## Conventions

- Python 3.14, black-compatible (88-char lines, ruff + isort with `profile = "black"`)
- Config additions belong in `device_configs/` as YAML; keep them minimal, use unique entity keys
- Run `prek` before pushing; verify files via sonarqube, then push (ask first)
- Conventional commits (`fix:`, `feat:`, `chore:`, `docs:`) with a body of bullet points
