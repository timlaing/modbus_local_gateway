# Pull Request

<!-- Thank you for contributing to Modbus Local Gateway! Please fill out the
     template below to help us review your change. Every contribution is
     appreciated. -->

## Summary

<!-- Briefly describe the change and the problem it solves. -->

## Type of change

<!-- Check the box that applies. -->

- [ ] Feature (`feat:` / enhancement)
- [ ] Bug fix (`fix:`)
- [ ] New YAML device configuration
- [ ] Maintenance / refactor (`refactor:` / `chore:`)
- [ ] Dependencies (`build:` / `chore:`)
- [ ] Documentation (`docs:`)

## Related issues / PRs

<!-- Link any related issues or pull requests, e.g. Fixes #123. -->

## Changes

<!-- Describe the changes in detail. For new device support, include the device
     manufacturer/model, the YAML file name, and the register/coil sections it
     covers.

     Keep this PR focused: each PR should be a single, self-contained change.
     If your work spans multiple distinct fixes or features, split them into
     separate PRs so each can be reviewed and merged independently. -->

## Device configuration (if applicable)

<!-- For new YAML device configs in
     custom_components/modbus_local_gateway/device_configs/ -->

- YAML file name:
- Manufacturer / model:
- Data sections used (read_write_word / read_only_word / read_write_boolean / read_only_boolean):
- Tested against the physical device / a Modbus simulator?

> Do **not** include personal configuration (IP addresses, passwords, live
> device data) in device config files — that belongs in a user's
> `/config/modbus_local_gateway/` override directory.

## Documentation

<!-- Check the boxes that apply. -->

- [ ] Updated the README "Creating YAML Device Configurations" section (if the schema changed)
- [ ] Updated the README "Supported Devices" tested-slaves list (if adding a device)
- [ ] Updated `CONTRIBUTING.md` / other docs if the change affects them

## Verification

<!-- What did you do to verify the change?

     Changes will not be processed unless the verification checks below are
     completed. Ensure every box that applies to your change is ticked before
     requesting a review. -->

- [ ] This PR is a single, self-contained change (one fix or feature only)
- [ ] The PR is editable by maintainers (`maintainer_can_modify` / "Allow edits from maintainers")
- [ ] Ran `uv run prek run --files <changed paths>` — all hooks pass
- [ ] Ran `uv run prek run --all-files` — all hooks pass
- [ ] Ran `uv run pytest` — all tests pass
- [ ] Added or updated tests for any code changes (one test file per entity/platform in `tests/`)
- [ ] No new issues reported by static analysis (ruff, mypy in manual stage, SonarQube)
- [ ] CI (linting.yml, tests.yml) is passing on the PR

---

Thanks again for your contribution!
