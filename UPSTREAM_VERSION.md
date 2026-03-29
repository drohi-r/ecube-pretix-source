# Upstream Version And Build Mapping

This repository is a public source-disclosure mirror for the Ecube-maintained customization layer around an upstream pretix deployment.

## Current Build Mapping

The customized image disclosed by this repository is assembled using `infra/docker/pretix-web.Dockerfile`.

The current Docker build starts from:

- `pretix/standalone:stable`

The Dockerfile then layers the Ecube-maintained plugins and selected override files from this repository into that upstream base image.

## Upstream Provenance Note

Because the Dockerfile currently references the moving tag `pretix/standalone:stable`, the exact resolved upstream pretix version or image digest may vary at build time unless it is pinned separately.

The exact currently deployed upstream pretix version or image digest is not recorded in the files present in this repository.

## Current Upstream Version

The deployed environment is currently running **pretix 2026.2.0** (as of 2026-03-29).

## TODO

- Record the exact upstream image digest used for the deployed build.
- Pin the upstream base image in the build configuration if reproducible provenance tracking is required.
