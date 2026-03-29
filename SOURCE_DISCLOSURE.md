# Source Disclosure

This repository is a public source-disclosure mirror for an Ecube-maintained customized pretix deployment.

## Included Material

This mirror contains:

- Ecube-maintained custom plugins under `plugins/`
- selected Ecube-maintained override files under `core_overrides/`
- custom presale and error page templates under `templates/`
- the Docker image assembly file at `infra/docker/pretix-web.Dockerfile`
- top-level documentation describing the disclosure scope and provenance of the public mirror

The modified image is assembled using `infra/docker/pretix-web.Dockerfile`.

That Dockerfile currently builds from `pretix/standalone:stable`, then layers the disclosed Ecube-maintained plugins and selected override files into the resulting image.

Because the Dockerfile references `pretix/standalone:stable`, the exact resolved upstream image version or digest may vary at build time unless it is pinned separately and recorded.

## Excluded Material

This mirror does not contain:

- the full upstream pretix source tree
- the full private Ecube operations repository
- operational secrets or secret values
- `.env` files or similar environment-specific configuration files
- host-specific deployment paths or host-specific operational state
- private automation used only for internal deployment workflows
- internal infrastructure details, credentials, inventories, or backup roots

## Relationship To The Running Deployment

This mirror is intended to publish the Ecube-maintained source modifications relevant to the customized deployment layer. It does not by itself identify a fully pinned upstream pretix version or digest for every historical deployment.

For provenance and build-mapping notes about the current disclosed build path, see `UPSTREAM_VERSION.md`.

## Sync History

- **2026-03-29**: Full sync of all plugins, core overrides, templates, and Dockerfile. Added `templates/` directory (error pages and presale template overrides). Removed stale `core_overrides/pretix/control/static/pretixcontrol/css/ecube-dark.css`. Updated upstream version reference to pretix 2026.2.0.
