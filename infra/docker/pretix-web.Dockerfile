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
#   6. Runs collectstatic explicitly so custom assets are always collected
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
    install -d /pretix/src/pretix/control/static/pretixcontrol/css; \
    install -d /pretix/src/pretix/multidomain

COPY plugins/pretix_sslcommerz /pretix/src/pretix_sslcommerz
COPY plugins/pretix_admissions /pretix/src/pretix_admissions
COPY plugins/pretix_ecube_access /pretix/src/pretix_ecube_access
COPY plugins/pretix_exclusive_access /pretix/src/pretix_exclusive_access
COPY plugins/pretix_ticketing_portal /pretix/src/pretix_ticketing_portal
COPY plugins/pretix_ecube_control_theme /pretix/src/pretix_ecube_control_theme
COPY plugins/pretix_event_themes /pretix/src/pretix_event_themes
COPY plugins/pretix_ecubemail /pretix/src/pretix_ecubemail
COPY plugins/pretix_ecubetickets /pretix/src/pretix_ecubetickets
COPY plugins/pretix_ecubefooter /pretix/src/pretix_ecubefooter
COPY templates /pretix/src/templates

COPY core_overrides/pretix/control/templates/pretixcontrol/base.html /pretix/src/pretix/control/templates/pretixcontrol/base.html
COPY core_overrides/pretix/control/templates/pretixcontrol/auth/base.html /pretix/src/pretix/control/templates/pretixcontrol/auth/base.html
COPY core_overrides/pretix/multidomain/maindomain_urlconf.py /pretix/src/pretix/multidomain/maindomain_urlconf.py

RUN chmod -R a+rX /pretix/src/templates

WORKDIR /pretix/src

# Install each plugin exactly as in the validated live customization script.
RUN set -eux; \
    pip install --no-cache-dir -e /pretix/src/pretix_sslcommerz; \
    pip install --no-cache-dir -e /pretix/src/pretix_admissions; \
    pip install --no-cache-dir -e /pretix/src/pretix_ecube_access; \
    pip install --no-cache-dir -e /pretix/src/pretix_exclusive_access; \
    pip install --no-cache-dir -e /pretix/src/pretix_ticketing_portal; \
    pip install --no-cache-dir -e /pretix/src/pretix_ecube_control_theme; \
    pip install --no-cache-dir -e /pretix/src/pretix_event_themes; \
    pip install --no-cache-dir -e /pretix/src/pretix_ecubemail; \
    pip install --no-cache-dir -e /pretix/src/pretix_ecubetickets; \
    pip install --no-cache-dir -e /pretix/src/pretix_ecubefooter; \
    pip install --no-cache-dir pretix-oidc; \
    python -m pretix rebuild; \
    chmod -R u+w /pretix/src/pretix/static.dist; \
    python -m pretix collectstatic --noinput; \
    # Manual copy for plugins whose app.path doesn't match the static dir \
    # (editable installs resolve to outer package, not inner Python package) \
    for plugin in pretix_exclusive_access pretix_admissions pretix_ecube_access \
                  pretix_ticketing_portal pretix_ecube_control_theme pretix_event_themes \
                  pretix_ecubemail pretix_ecubetickets pretix_ecubefooter pretix_sslcommerz; do \
        src="/pretix/src/$plugin/$plugin/static/$plugin"; \
        if [ -d "$src" ]; then \
            mkdir -p "/pretix/src/pretix/static.dist/$plugin"; \
            cp -a "$src"/* "/pretix/src/pretix/static.dist/$plugin/"; \
        fi; \
    done; \
    chmod -R a+rX /pretix/src/pretix/static.dist

# Return to the default Pretix working directory for consistency with the base image.
WORKDIR /pretix

USER pretixuser
