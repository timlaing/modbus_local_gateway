# Security Policy

The developers of the Modbus Local Gateway integration take security
seriously. This document describes how to report security issues and what is
covered by the project's security processes.

## Supported Versions

Security fixes are applied to the latest release on the `main` branch. Only
the most recent release is actively patched.

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |
| older   | :x:                |

We recommend always running the most recent version, available both directly
from Home Assistant and through HACS. Since this integration controls physical
devices, keeping up to date is especially important.

## Reporting a Vulnerability

Please **do not open a public issue** for security vulnerabilities. Instead,
report them privately so they can be fixed before disclosure.

### Preferred: GitHub Security Advisories

Use the repository's dedicated security advisory flow:

1. Go to https://github.com/timlaing/modbus_local_gateway/security/advisories/new
2. Fill in the details of the vulnerability (title, description, affected
   components, and any reproduction steps).

This keeps the report private and gives the maintainer a place to coordinate a
fix and a disclosure timeline.

### Alternative: Direct email

If you cannot use GitHub Security Advisories, contact the maintainers directly
via the email address listed on the maintainer's GitHub profile
(https://github.com/timlaing).

### What to include

Please include as much of the following as possible:

- The affected version(s) of the integration and Home Assistant.
- The type of vulnerability (e.g. denial of service, command injection,
  information disclosure).
- Steps to reproduce the issue.
- The impact you believe the issue could have.
- If you have a suggested mitigation, include it.

### What happens next

- You will receive an acknowledgement of your report within **3 business days**.
- The maintainer will confirm the vulnerability and determine affected versions.
- A fix will be developed and released as soon as possible.
- The issue will be disclosed publicly after the fix is released, crediting the
  reporter if they wish to be credited.

## Security Considerations for Users

### Network exposure

The integration communicates with Modbus TCP gateways over your local network.
Best practices:

- Do **not** expose your Home Assistant instance or Modbus gateway to the
  public internet.
- Use a firewall to restrict Modbus TCP (default port 502) access to trusted
  devices only.
- If remote access is required, use the Home Assistant remote access tools
  (e.g. Nabu Casa, a trusted reverse proxy with authentication) and never place
  raw Modbus TCP in the DMZ.

### YAML device configurations

Device configurations define the registers/coils that are read and written.
Only install/override configs you trust:

- Validate YAML configs from third parties before use.
- Configs in `/config/modbus_local_gateway/` override the bundled ones; be
  aware of what you place there.
- Do **not** commit device configs containing credentials, IP addresses of your
  own devices, or other sensitive data.

### Secrets and credentials

Keep credentials, tokens, and private configuration out of the repository and
out of device config files. Report any accidental exposure privately (see
[Reporting a Vulnerability](#reporting-a-vulnerability)).

## Automated Security Tooling

The repository uses several automated checks to keep the codebase secure:

- **Dependabot** keeps Python and GitHub Actions dependencies up to date
  (see `.github/dependabot.yml`).
- **GitHub CodeQL** analysis runs against the codebase on every push.
- **SonarQube** security analysis runs as part of CI
  (see the security badges in the README).
- **pre-commit** hooks detect private keys and other secrets before they are
  committed (see `.pre-commit-config.yaml`).

If any of these surface an issue relevant to you, please report it following the
process above.

## Disclosures

Once a fix is released, a security advisory detailing the vulnerability, impact,
and mitigation will be published via the GitHub repository's security advisory
feed. Opt in to GitHub advisories to be notified automatically.

## Contact

- GitHub: https://github.com/timlaing (maintainer)
- Discussions: https://github.com/timlaing/modbus_local_gateway/discussions
- Discord: https://discord.gg/rQ2cZ6K5YY
