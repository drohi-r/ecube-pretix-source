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

## TODO

- Record the exact upstream image digest used for the deployed build.
- Record the corresponding upstream pretix version or upstream source reference associated with that deployed image.
- Pin the upstream base image in the build configuration if reproducible provenance tracking is required.
