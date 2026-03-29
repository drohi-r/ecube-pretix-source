# Ecube Pretix Public Source-Disclosure Mirror

This repository is a public source-disclosure mirror for an Ecube-maintained customized pretix deployment.

It contains Ecube-maintained modifications, custom plugins, selected core override files, and the Docker build file used to assemble the customized pretix web image published from this mirror.

This repository does not contain the full upstream pretix source tree. pretix remains the upstream software project and should be obtained from the upstream project itself.

This repository is not the full private operations repository used to run Ecube infrastructure. Operational secrets, environment files, host-specific deployment paths, private automation, internal infrastructure details, and other internal-only operational material are intentionally excluded.

## What This Repository Contains

- `plugins/` - Ecube-maintained custom pretix plugins included in the customized deployment image
- `core_overrides/` - selected Ecube-maintained override files applied onto upstream pretix paths during image assembly
- `templates/` - custom presale and error page templates layered into the deployment image
- `infra/docker/pretix-web.Dockerfile` - Dockerfile used to assemble the customized pretix web image from the disclosed source in this repository
- `SOURCE_DISCLOSURE.md` - scope and exclusions for the public source disclosure
- `LICENSE_NOTES.md` - short factual attribution and disclosure note
- `UPSTREAM_VERSION.md` - provenance and build-mapping note for the upstream base image reference used by this mirror
- `LICENSE` - GNU Affero General Public License version 3 text

## Build Mapping

The customized web image is assembled using `infra/docker/pretix-web.Dockerfile`.

That Dockerfile currently starts from `pretix/standalone:stable` and then layers the Ecube-maintained plugins and selected override files contained in this repository into the resulting image.

Because the Dockerfile currently builds from `pretix/standalone:stable`, the exact resolved upstream pretix image version or digest may vary at build time unless it is pinned separately and recorded from the deployment environment.

## Scope

This mirror is intended to publish the Ecube-maintained source components relevant to the customized deployment layer. It is not intended to republish the full upstream pretix source tree or the full private repository used for internal operations.

For additional detail, see `SOURCE_DISCLOSURE.md`, `LICENSE_NOTES.md`, and `UPSTREAM_VERSION.md`.
