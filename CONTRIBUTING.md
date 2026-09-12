# Contributing to Modbus Local Gateway

First off, thanks for taking the time to contribute! Contributions of all kinds are welcome: bug reports, feature requests, new device configurations, documentation, and code fixes.

Please take a moment to review this document so that your contributions get reviewed (and merged) quickly.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Help](#getting-help)
- [Ways to Contribute](#ways-to-contribute)
- [Development Setup](#development-setup)
- [Adding a New Device Configuration](#adding-a-new-device-configuration)
- [Code Style](#code-style)
- [Testing](#testing)
- [Commit Messages](#commit-messages)
- [Pull Requests](#pull-requests)
- [Release Process](#release-process)

## Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behaviour as described in that document.

## Getting Help

If you are unsure about anything, or just want to discuss an idea, open a discussion in the [GitHub Discussions](https://github.com/timlaing/modbus_local_gateway/discussions) or on our [Discord community](https://discord.gg/rQ2cZ6K5YY).

## Ways to Contribute

### Reporting Bugs

Before creating a bug report, please:

1. Check the [existing issues](https://github.com/timlaing/modbus_local_gateway/issues) — the issue may already have been reported.
2. If you find a _closed_ issue that seems to describe the same problem, open a new issue and link to it.

When you open a bug report, complete the [bug report template](https://github.com/timlaing/modbus_local_gateway/issues/new?template=bug.yml). A good report helps us fix the problem faster:

- A clear, descriptive title.
- Your environment: Home Assistant version, integration version, gateway hardware.
- Steps to reproduce the problem.
- The expected behaviour and what actually happened.
- Relevant logs (enable debug logging first — see the README's troubleshooting section).
- The device configuration you are using.

### Requesting Features

Feature requests are welcome. Before opening one:

1. Search [existing issues](https://github.com/timlaing/modbus_local_gateway/issues) and discussions to see if the feature has already been requested.
2. Use the [feature request template](https://github.com/timlaing/modbus_local_gateway/issues/new?template=feature_request.yml).
3. Explain _why_ the feature is useful, and include any relevant register maps or datasheets.

### Submitting Device Configurations

The most common contribution is a YAML device configuration. See [Adding a New Device Configuration](#adding-a-new-device-configuration) below.

### Contributing Code

Small fixes and improvements are always appreciated. For anything non-trivial, please open an issue or a discussion first so we can agree on the approach before you invest the time.

## Development Setup

### Dev Container

The repository includes a dev container (`.devcontainer/`). If you open the repo in VS Code with the Dev Containers extension, the environment is set up for you.

### Manual Setup

Prerequisites:

- Python 3.14 (see `.python-version`)
- [uv](https://docs.astral.sh/uv/)

```bash
# Install dependencies (uses uv.lock)
uv sync

# Optionally, install pre-commit hooks
uv run pre-commit install
```

The test and analysis tools (and their exact versions) are pinned in `requirements_dev.txt`.

## Adding a New Device Configuration

See the README's [Creating YAML Device Configurations](README.md#creating-yaml-device-configurations) section for the full reference. In short:

1. Create a YAML file for the device in `custom_components/modbus_local_gateway/device_configs/`. Name it after the model (e.g. `SDM230.yaml`).
2. Keep it minimal — only include registers/coils that are useful.
3. Use unique entity keys within the file (`read_write_word`, `read_only_word`, etc.).
4. Validate that the file is well-formed YAML and follows the documented schema.

A JSON and YAML schema may be defined for the integration. As a minimum, make sure the file:

- has a valid `device` section (`manufacturer` and `model`);
- is validated locally (see [Code Style](#code-style) for the validation commands);
- is covered by an example in the README if it introduces a new capability.

Do **not** include personal configuration (IP addresses, passwords, live device data) in device config files — that belongs in the user's `/config/modbus_local_gateway/` override directory.

## Code Style

The repository uses `ruff`, `isort`, `prettier`, and `prek`.

```bash
# Python lint (ruff)
uv run ruff check .

# Python formatting (black-compatible, 88-char lines)
uv run ruff format .

# Import ordering (isort, profile black)
uv run isort --check-only --diff .

# Full check set (yamllint, check-yaml, cspell, prettier, EOF) on changed files
uv run prek run --files <paths>

# Everything at once before pushing
uv run prek run --all-files
```

Code should be black-compatible (88-character lines) and pass `ruff`, `isort`, and the `prek` checks without issues. When you change code, also add or update tests.

## Testing

The test suite lives in `tests/` (one test file per entity/platform) and uses `pytest` with `pytest-asyncio` in auto mode.

```bash
# Run the full test suite
uv run pytest

# Run with coverage
uv run pytest --cov=. --cov-report xml:coverage.xml
```

Please add tests for any new code you contribute and make sure the existing suite still passes.

## Commit Messages

The repository uses [Conventional Commits](https://www.conventionalcommits.org/):

- `fix:` — bug fixes
- `feat:` — new features
- `chore:` — maintenance tasks
- `docs:` — documentation changes
- `build:`, `refactor:`, `test:`, `style:`, `perf:` — as appropriate

The subject line should summarise the primary theme of the change in one sentence, and the body should list the key behavioural changes as bullet points:

```text
feat: add support for the FooBar Baz-300

- Add YAML device config for the FooBar Baz-300
- Document register layout for temperature and power sensors
```

## Pull Requests

1. **Branch from `main`.** The base branch for all pull requests is `main`.
2. **Keep PRs small and focused.** A single PR should address a single concern — it is much easier to review and merge.
3. **Update documentation.** If you add user-facing behaviour, update the README to match.
4. **Run the full check set** (`uv run prek run --all-files`) and the test suite before asking for review.
5. **Write a good description.** Explain what the PR does and why, and reference any related issues.

Before your PR is merged it must:

- pass CI (tests and lint);
- have a clean `prek`/`pre-commit` run;
- not introduce new issues reported by static analysis (e.g. SonarQube).

## Release Process

Releases are cut from `main` using a [release drafter](.github/release-drafter.yml). Version numbers follow the integration's manifest. Contributors do not need to bump versions — maintainers handle tagging and releases.

## Attribution

This contributing guide is adapted from best practices of the Home Assistant developer community. Thank you for contributing!
