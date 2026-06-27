#!/usr/bin/env bash
set -euo pipefail

# netbox-ai-ingest :: Layer 1 deployment bootstrap
#
# Stands up a clean, reproducible NetBox by wrapping the official netbox-docker
# project and layering our port override on top — without forking it.

# --- Pinning -----------------------------------------------------------------
# 'release' = always the latest stable. Good for the very first run.
# For TRUE reproducibility, after your first successful boot run:
#     git -C deploy/.netbox-docker describe --tags
# then re-run pinned to that tag, e.g.:
#     NETBOX_DOCKER_REF=3.10.0-3.2.1 ./bootstrap.sh
NETBOX_DOCKER_REF="${NETBOX_DOCKER_REF:-release}"
# -----------------------------------------------------------------------------

HERE="$(cd "$(dirname "$0")" && pwd)"
VENDOR_DIR="$HERE/.netbox-docker"

echo ">> Vendoring netbox-docker (ref: $NETBOX_DOCKER_REF)"
if [ ! -d "$VENDOR_DIR/.git" ]; then
  git clone -b "$NETBOX_DOCKER_REF" \
    https://github.com/netbox-community/netbox-docker.git "$VENDOR_DIR"
else
  git -C "$VENDOR_DIR" fetch --all --tags --prune
  git -C "$VENDOR_DIR" checkout "$NETBOX_DOCKER_REF"
fi

echo ">> Applying netbox-ai-ingest override"
cp "$HERE/docker-compose.override.yml" "$VENDOR_DIR/docker-compose.override.yml"

echo ">> Pulling images"
( cd "$VENDOR_DIR" && docker compose pull )

echo ">> Starting NetBox"
( cd "$VENDOR_DIR" && docker compose up -d )

cat <<'EOF'

------------------------------------------------------------
NetBox is starting. First boot runs DB migrations — give it
about 1-2 minutes before the web UI responds.

  URL:  http://localhost:8000

Create your admin user:
  cd deploy/.netbox-docker
  docker compose exec netbox /opt/netbox/netbox/manage.py createsuperuser

Stop (keep data):
  cd deploy/.netbox-docker && docker compose down

Stop and wipe data:
  cd deploy/.netbox-docker && docker compose down -v
------------------------------------------------------------
EOF
