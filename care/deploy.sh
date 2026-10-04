#!/bin/sh
# Publish site/ as the Cloudflare Worker "atlas-care" (worker/wrangler.toml).
# Live at https://atlas.lari-island.ai/research/care/ and atlas-care.lari-0c7.workers.dev.
# Needs a logged-in wrangler (npx wrangler whoami). Unchanged files are not re-uploaded.
set -eu
cd "$(dirname "$0")/worker"
npx --yes wrangler deploy
