# Ecube Pretix Source Mirror

This repository is a public source-disclosure mirror for the modified pretix deployment used by Ecube.

[`pretix`](https://pretix.eu/about/en/) is the upstream project. This mirror contains Ecube-maintained modifications and plugins, selected core template/static override files, and the repo-built Dockerfile used to assemble the modified pretix web image.

This repository does not contain the full upstream pretix source tree. It publishes the Ecube-maintained source components and override files that are relevant to source disclosure for the deployed customization layer.

Operational deployment on Ecube private infrastructure may include additional private environment configuration, deployment automation, and host-specific settings that are intentionally not published here.

## Repository Structure

- `plugins/` - Ecube custom pretix plugins included in the deployed image
- `core_overrides/` - Selected pretix core template/static overrides maintained in source control
- `infra/docker/pretix-web.Dockerfile` - Dockerfile used to assemble the modified pretix web image from this repository source
- `SOURCE_DISCLOSURE.md` - Scope summary of the disclosed customizations and exclusions
- `LICENSE_NOTES.md` - Short attribution and source-disclosure notes

## Upstream / Attribution

pretix is the upstream ticketing and event management software project. This repository does not replace the upstream project; it publishes Ecube-specific source modifications and custom plugin code maintained around that upstream base.

## Provenance / Build Mapping

This mirror is exported from the private Ecube development repository for public source-disclosure purposes.

The modified web image is assembled using `infra/docker/pretix-web.Dockerfile`. That Dockerfile currently starts from `pretix/standalone:stable`, then layers the disclosed Ecube plugins and selected override files into the resulting image.

Because the Dockerfile references the `stable` upstream image tag, the exact resolved upstream base image may vary depending on build time unless it is pinned separately.

## Public Source Disclosure Scope

This mirror is intended to disclose the relevant source code for Ecube-maintained pretix customizations used in deployment. Private operational material such as secrets, environment files, internal infrastructure details, host-specific paths, backup artifacts, and private deployment documentation is excluded.
