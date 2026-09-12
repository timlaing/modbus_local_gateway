---
name: code-review
description: "Use when reviewing code changes, PRs, or commits in the Modbus Local Gateway Home Assistant integration. Covers architecture, typing, HA conventions, modbus conversion semantics, YAML device configs, test coverage, and SonarQube quality rules. Trigger keywords: review, pr, code review, linting, typing, coverage, sonarqube, prek."
---

# Code Review Skill — Modbus Local Gateway

Systematic review checklist for the `modbus_local_gateway` Home Assistant custom integration.

## Review Standard

- Establish the review target before inspecting code: working-tree changes, staged changes, a commit or commit range, or a PR against its merge base. State the selected target and base in the result.
- Review only changes in scope. Do not report pre-existing problems unless the change makes them materially worse; mention important out-of-scope risks separately without presenting them as findings.
- Report a finding only when the changed code introduces a demonstrable functional, security, reliability, compatibility, or maintainability defect. Explain the triggering conditions and impact, and cite the smallest useful `file:line` range.
- Do not report speculative problems, personal style preferences, or issues already caught reliably by required automated tooling. Do not invent findings when none qualify.
- Classify findings as:
  - **P0**: catastrophic or release-blocking in nearly all uses.
  - **P1**: likely functional, security, or data-integrity defect.
  - **P2**: real defect under plausible conditions.
  - **P3**: worthwhile, non-blocking correctness or maintainability improvement.
- Keep suggestions separate from defects. A suggestion must not be presented as a blocker.

## 1. Architecture & Boundaries

- `custom_components/modbus_local_gateway/` is the integration. Keep module concerns separated:
  - `coordinator.py` — `ModbusCoordinator` (a `TimestampDataUpdateCoordinator`) and the `ModbusCoordinatorEntity` base entity (read/write locking, per-entity polling timers, entity_id migration).
  - `tcp_client.py` — `AsyncModbusTcpClientGateway` (pymodbus client subclass) owns all wire I/O: batched reads via `read_data`, register/coil writes, connection pooling through the `_CLIENT` class dict.
  - `conversion.py` — `Conversion`; the only place register/bits <-> native value conversion happens.
  - `transaction.py` — `MyTransactionManager` suppresses protocol-exception log spam.
  - `helpers.py` — `get_gateway_key` and `async_setup_entities` (shared platform setup); platform files must not duplicate this logic.
  - `entity_management/` — description dataclasses (`base.py`), type/unit constants (`const.py`), and YAML parsing (`modbus_device_info.py`, `device_loader.py`).
  - `device_configs/` — YAML device definitions, one file per device model.
- `__init__.py` registers exactly one `ModbusCoordinator` per gateway key in `hass.data[DOMAIN]` and forwards the entity platforms from `const.PLATFORMS`.
- Entity platform files (`sensor.py`, `binary_sensor.py`, `switch.py`, `number.py`, `select.py`, `text.py`) follow a uniform pattern: `async_setup_entry` calls `async_setup_entities(..., control=ControlType.X, entity_class=...)` and each entity class subclasses `ModbusCoordinatorEntity` plus the HA platform base.
- Do not bypass `Conversion` for register/bits interpretation or encoding — reads and writes must round-trip through it.

## 2. Imports & Module Layout

- Tests and source import via `custom_components.modbus_local_gateway.*` (or relative `from .` inside the package). Never shrink-wrap platform logic into `coordinator.py`.
- Entity descriptions are built in `entity_management/base.py`. `ModbusDeviceInfo` returns the union type `DESCRIPTION_TYPE`; `desc.control_type` selects the platform.
- Keep conversion of _data_ (in `Conversion`) separate from conversion of _value semantics_ (multiplier/offset/swap are supported at read and write time; `conv_map`, `conv_flags`, bit fields, and `conv_sum_scale` are read-only — writing them must raise `NotSupportedError`).
- Circular imports: `helpers.py` imports from `coordinator`, `context`, `entity_management`, and `entity_management.const`; `context.py` imports `ModbusEntityDescription` from `entity_management.base`. Do not introduce import cycles through `__init__.py`.

## 3. Type Safety & Typing

- Use modern union syntax (`X | None`), consistent with the repo (ruff `UP007` is ignored repo-wide only because HA ships `Optional` in some signatures).
- Source `# type: ignore` is acceptable only in the known spots:
  - the HA platform entity class definitions (`ModbusSensorEntity`, `ModbusNumberEntity`, `ModbusSwitchEntity`, `ModbusSelectEntity`, `ModbusTextEntity`, `ModbusBinarySensorEntity`) — MRO/`self.hass` magic;
  - `update_method=self.async_update` in the coordinator constructor; the `native_value` property in `sensor.py`.
- Test fakes may carry narrowly scoped suppressions; require the specific error code and keep the suppression on the affected expression. Never add a bare or unexplained `# type: ignore`.
- mypy is configured strict in `pyproject.toml` but runs only at the manual pre-commit stage; ruff is the CI type/lint gate.
- `bool` is a subclass of `int` in Python; if you need to distinguish, check `type(x) is bool`.

## 4. Data Conversion & Value Semantics

- `Conversion.convert_from_response` dispatches on `desc.data_type`; the register path (`_convert_from_register_response`) applies, in order: byte/word swap, string, float, `conv_map`, `conv_flags`, then decimal. Any change to this order changes device values.
- Integer register data types derive from `register_count` (1=16-bit, 2=32-bit, 4=64-bit) combined with `is_signed`. Float needs `register_count` of 2 or 4. Strings are NUL-terminated on read (`split("\0")[0]`).
- `read_data` in `tcp_client.py` batches reads up to `max_read_size` per request and appends `registers`/`bits`; the response must be rejected when the returned count doesn't match. `_process_entity` raises on unknown data type or a non-positive register count.
- Write paths: single register via `write_register`, multiple via `write_registers` with per-register fallback to `write_register` on error. Write failures are logged, not swallowed silently.
- `conv_sum_scale` multiplies the read count (`register_count * max(1, len(conv_sum_scale))`); an empty list means no scaling. Never read zero registers.
- COIL writes require a `bool` value (`TypeError` otherwise); strings/constraints validated by `ModbusEntityDescription.validate()` gate entity creation at load time.

## 5. HA Entity Conventions

- `ModbusCoordinatorEntity` maintains a unique_id of `{prefix}-{device_id}-{key}` (backward compatible — do not change, or HA creates duplicate entities) and a suggested object_id of `<ipnodots>_<yaml_key>`; entity_id migration happens once in `async_added_to_hass`.
- Entities with a `scan_interval` set poll on their own timer (`async_run`, `async_track_time_interval`); `ModbusCoordinator.async_update` filters them out and only returns cached data when nothing is due.
- Register listener/startup in `async_added_to_hass`, not `__init__`. Tests must `await entity.async_added_to_hass()` before asserting coordinator-triggered updates.
- Sensor semantics: `SameValue` and `MaxChangeExceeded` are raised on no-change/over-limit values and handled in `_handle_coordinator_update`. `never_resets` guards `TOTAL_INCREASING` sensors against backwards resets; `hw_version`/`sw_version` keys update the device registry.
- Number/select/text/switch platforms implement the `async_*_set*` methods; their synchronous counterparts must raise `NotImplementedError`.
- `write_data` (base entity) sends the write through `coordinator.client.write_data`, then schedules a follow-up state refresh; `UpdateFailed` is raised on failure so HA marks the entity unavailable.
- Config-flow steps accept `user_input: dict[str, Any] | None`; the flow tests a real client connection (SOCKET/RTU via `FramerType`) before offering the device-type step.
- `manifest.json` must keep `pymodbus`/`getmac` requirements, `config_flow: true`, `integration_type: device`, `iot_class: local_polling`, and the `issue_tracker`.

## 6. Device Config YAML

- Device configs live in `custom_components/modbus_local_gateway/device_configs/`. Sections are Modbus data types: `read_write_word`, `read_only_word`, `read_write_boolean`, `read_only_boolean` (values of `ModbusDataType`).
- The `device:` block requires `manufacturer` and `model`. `max_register_read` (default 8) becomes `coordinator.max_read_size`.
- Every entity key must be unique; `address` is required. Per platform: `control` must be a legal `ControlType` for the section (see `ModbusDeviceInfo.allowed_control_types`); `number:` needs `min`/`max`, `options` for selects, `on`/`off` for switches/binary sensors.
- Keep minimal and additive; do not alter existing keys/addresses in a shipped config without a migration or explicit approval (existing users' entities would re-map).
- Non-ASCII entity names in configs must be quoted in YAML (see `Test.yaml` and the shipped device configs).

## 7. Test Conventions

- Tests use `pytest-homeassistant-custom-component`; fixtures in `conftest.py`: `mock_config_entry` (`MockConfigEntry`), `mock_client` (`AsyncMock(spec=AsyncModbusTcpClientGateway)`), `valid_entity_description`.
- pytest runs with `asyncio_mode = "auto"` and `--disable-socket` — no test may open a real socket; stub the TCP client and `conversion.Conversion` at the class level (e.g. patch `coordinator.ModbusCoordinator.async_contexts` and `.conversion.Conversion.convert_from_response`).
- `conftest.py` carries module-level `# pylint: disable=unexpected-keyword-arg` and `# pylint: disable=protected-access` — tests may touch protected members, production code must not.
- Write module-level pytest functions, not class-based tests. Use `await entity.async_added_to_hass()` and, where HA async internals are involved, patch `asyncio.create_task`/`sleep` with a `_close_task()` helper and the `RuntimeWarning` filter.
- No `assert True` placeholders. No test may depend on real network or a live Modbus device.
- There is one test file per platform/source module (see `tests/`); add tests to the matching file.

## 8. Coverage Requirements

Every Python file under `custom_components/modbus_local_gateway/` should meet:

- **Line coverage > 90%**
- Exercise every reachable branch (`if`/`elif`/`else`/`match` arms). Any uncovered branch needs a test or a documented reason it is unreachable.

Run after writing tests:

```sh
pytest --cov=custom_components.modbus_local_gateway --cov-branch --cov-report=term-missing
```

The pytest pre-commit hook enforces `--cov-fail-under=90` at aggregate level only — inspect the per-file table before claiming compliance; an aggregate pass does not prove every file exceeds 90%.

## 9. Linting & Formatting

- Format/lint: `ruff check .` (import ordering via ruff `I` rules), `ruff format .` (black profile, 88 cols, `preview = true`).
- Full default-stage set: `uv run prek run --all-files` — or `uv run prek run --files <paths>` for a subset. Prefer `prek` for regular runs; `pre-commit` is equivalent only when it executes the same default-stage hook set, so do not invoke it directly. mypy and pylint are manual-stage hooks only.
- Some hooks apply fixes. A review-only request does not authorize worktree edits: record `git status --short` first and use non-mutating modes where practical. If a required check modifies files, disclose exactly what changed.
- cspell words and `ignoreWords` in `.vscode/cspell.json` must be **lowercase and sorted alphabetically**; `device_configs/` is ignored by cspell. Only add a word when a legitimate identifier needs it.
- Inline pylint disables are accepted for `broad-exception-caught`/`broad-except` on handler boundaries this repo already uses; do not silence SonarQube issues that can be fixed with code changes.

## 10. SonarQube Rules

Project key `timlaing_modbus_local_gateway` (sources `./custom_components/modbus_local_gateway`, tests `./tests`). Verify changed files via SonarQube before pushing.

| Rule  | Meaning                            | Fix                                                     |
| ----- | ---------------------------------- | ------------------------------------------------------- |
| S8508 | Mutable default in `dict.fromkeys` | Use dict comprehension                                  |
| S1172 | Unused function parameter          | Remove or accept if HA interface requires it            |
| S5914 | Constant boolean expression        | Remove or replace with meaningful assertion             |
| S9081 | Lambda should use `return_value`   | Use `patch(..., return_value=x)` instead of `lambda: x` |
| S7502 | Untracked asyncio task             | Save `create_task()` return to prevent GC               |
| S3776 | Cognitive complexity               | Refactor into smaller functions                         |
| S7637 | Actions pinned by tag not SHA      | Pin reusable actions to full commit SHAs                |

Verify changed files with the SonarQube MCP before pushing. The project key lives in `sonar-project.properties`; PR decoration requires the SonarQube Cloud GitHub App to be installed on the repo.

## 11. CI & Workflows

- `linting.yml` — `prek run` (via `j178/prek-action@v2`) on push/PR.
- `tests.yml` — Python 3.14 matrix, venv + `uv` install of `requirements_all.txt`, pytest with coverage + junit.
- `sonar.yml` — trusted scan on push to `main` (generates its own coverage) and a `pull_request_target` scan for fork/bot PRs using `secrets.SONAR_TOKEN` with `persist-credentials: false`.
- `hacs-validate.yml`, `hassfest-validate.yml`, `codeql.yml`, `release-drafter.yml` — validate the custom-component packaging/security posture.
- SonarQube secrets must never be used in untrusted (fork-derived) contexts; keep the privileged scan out of PR-controlled steps.

## 12. Commit & PR Conventions

- Conventional commits: `fix:`, `chore:`, `feat:`, `refactor:`, `test:`, `docs:` with a `-m` body of bullet points covering the behavioral changes.
- A review-only request does not authorize edits, commits, pushes, or merges. A fix-review request may include those actions only when the user explicitly requests them.
- Run `prek` and the full test suite before pushing; verify changed files via SonarQube. Always ask before pushing unless the user has pre-approved pushes.
- Plans live in `.opencode/plans`, are updated as work progresses, and are deleted when the task completes. Back up `.opencode/` before any destructive git operation.

## 13. Common Pitfalls

- `ModbusDataType` and `ControlType` are `StrEnum`s whose _values_ are the YAML section keys / `control` values — do not rely on member names.
- `desc.register_address` is 1-based/absolute as written in YAML (often `0x`-prefixed hex); pymodbus is zero-relative internally only where the device expects it — don't "fix" addressing casually.
- A `prefix` config option changes `unique_id` and gateway key (`get_gateway_key`); changing its format breaks existing device/entity identity.
- FramerType: SOCKET = "Via Gateway Device", RTU = "Direct Connection". `FramerType(connection_type)` derives the framer; never mismatch.
- `AsyncModbusTcpClientGateway._CLIENT` caches one client per `host:port:connection_type`; a test reset it or stub before asserting connection counts.
- Strings read from Modbus may be shorter than `register_count` — NUL split is required; do not rely on trailing-pad trimming.
- `Conversion.convert_to_registers` must reject unsupported write features (`conv_map`, `conv_flags`, bit/shift/sum-scale) with `NotSupportedError`, not silently drop them.

## 14. Review Workflow

1. Resolve and state the review target and base. Read that diff and identify all changed files and their categories (source, tests, device config, CI).
2. Check each source file against architecture rules (Section 1) and module-layout/import rules (Section 2).
3. Check typing per Section 3. Verify no new `# type: ignore` without the known justification list.
4. Check data-conversion semantics (Section 4) for any `conversion.py` / `tcp_client.py`/value-path changes.
5. Verify HA entity conventions (Section 5) for entity platform changes and device-config YAML rules (Section 6) for config changes.
6. Check test conventions (Section 7) and coverage (Section 8) for test changes.
7. Record the initial worktree status. Run non-mutating checks; if running `prek run --all-files`, detect and disclose any files it changes.
8. Run the coverage command and inspect every file's line and branch results. Do not infer per-file compliance from the aggregate percentage.
9. Check for SonarQube-tractable issues (Section 10) and workflow/security concerns (Section 11).
10. Report findings in priority order with tight `file:line` references, triggering conditions, impact, and a concrete fix. Separate suggestions from defects. If there are no actionable findings, say so explicitly.
11. Add a verification summary listing each command run and its pass, fail, or not-run status. Include relevant failures and environmental limitations; never imply a check ran when it did not.
