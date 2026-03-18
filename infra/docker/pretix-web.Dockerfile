#
# Repo-based Pretix web image for the live stack migration.
#
# Goal:
# Reproduce the now-validated live customization model from Git only.
#
# This image:
#   1. Starts from pretix/standalone:stable
#   2. Copies repo plugin sources into /pretix/src/<plugin>
#   3. Installs each custom plugin with editable pip installs
#   4. Copies repo-managed core overrides into Pretix core paths
#   5. Runs pretix rebuild from /pretix/src
#
# Notes:
# - Keep this file readable. The intention is operational clarity, not cleverness.
# - The build context for this Dockerfile is expected to be the Git repository root.
#
FROM pretix/standalone:stable

USER root

# Mirror the validated live customization flow by keeping repo-managed custom
# sources under /pretix/src before installing them.
RUN set -eux; \
    mkdir -p /pretix/src; \
    install -d /pretix/src/pretix/control/templates/pretixcontrol/auth; \
    install -d /pretix/src/pretix/control/static/pretixcontrol/css

COPY plugins/pretix_sslcommerz /pretix/src/pretix_sslcommerz
COPY plugins/pretix_admissions /pretix/src/pretix_admissions
COPY plugins/pretix_ecube_access /pretix/src/pretix_ecube_access
COPY plugins/pretix_exclusive_access /pretix/src/pretix_exclusive_access
COPY plugins/pretix_ecube_control_theme /pretix/src/pretix_ecube_control_theme
COPY plugins/pretix_event_themes /pretix/src/pretix_event_themes
COPY plugins/pretix_ecubefooter /pretix/src/pretix_ecubefooter

COPY core_overrides/pretix/control/templates/pretixcontrol/base.html /pretix/src/pretix/control/templates/pretixcontrol/base.html
COPY core_overrides/pretix/control/templates/pretixcontrol/auth/base.html /pretix/src/pretix/control/templates/pretixcontrol/auth/base.html
COPY core_overrides/pretix/control/static/pretixcontrol/css/ecube-dark.css /pretix/src/pretix/control/static/pretixcontrol/css/ecube-dark.css

WORKDIR /pretix/src

# Install each plugin exactly as in the validated live customization script.
RUN set -eux; \
    pip install -e /pretix/src/pretix_sslcommerz; \
    pip install -e /pretix/src/pretix_admissions; \
    pip install -e /pretix/src/pretix_ecube_access; \
    pip install -e /pretix/src/pretix_exclusive_access; \
    pip install -e /pretix/src/pretix_ecube_control_theme; \
    pip install -e /pretix/src/pretix_event_themes; \
    pip install -e /pretix/src/pretix_ecubefooter; \
    python -m pretix rebuild

# Return to the default Pretix working directory for consistency with the base image.
WORKDIR /pretix

USER pretixuser
