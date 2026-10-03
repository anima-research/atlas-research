#!/bin/sh
# Publish site/ as the Cloudflare Worker "atlas-names" (static assets, no code).
# Needs a logged-in wrangler (npx wrangler whoami).  Live at:
#   https://atlas-names.lari-0c7.workers.dev
set -eu
cd "$(dirname "$0")/site"
npx --yes wrangler deploy --name atlas-names --compatibility-date 2026-08-06 --assets .
