# Source Disclosure

This repository is intended to disclose the source modifications and custom plugins used in the Ecube pretix deployment, while excluding private operational material that is not required for source disclosure.

## Disclosure Scope

This repository publishes Ecube-maintained modifications, plugins, and selected override files that are relevant to the deployed customization layer. The upstream pretix application remains an upstream project and is not republished here as a full source tree.

## Customizations Included

### Custom plugins

- `pretix_admissions`
- `pretix_ecube_access`
- `pretix_ecube_control_theme`
- `pretix_ecubefooter`
- `pretix_event_themes`
- `pretix_exclusive_access`
- `pretix_sslcommerz`

### Core override areas

- `pretix/control/templates/pretixcontrol/base.html`
- `pretix/control/templates/pretixcontrol/auth/base.html`
- `pretix/control/static/pretixcontrol/css/ecube-dark.css`

### Image build overview

The modified web image is assembled from `infra/docker/pretix-web.Dockerfile`.

At a high level, the Dockerfile:

- starts from the upstream `pretix/standalone:stable` image
- copies the Ecube plugin source directories into the image build context
- copies the selected core override files into pretix core paths inside the image
- installs each custom plugin with editable `pip install -e` steps
- runs `python -m pretix rebuild` to rebuild static/application assets

Secret environment values and private deployment configuration are intentionally excluded from this repository.

## Excluded Private Operational Material

The public mirror excludes material that is not required to disclose source modifications, including:

- `.env` files and secret configuration values
- private infrastructure and host-specific deployment files
- internal backup/export locations and backup artifacts
- internal operations and handover documentation
- private automation related only to internal deployment environments
- live or staging environment values that are not necessary to disclose source code changes
