#!/bin/sh
# Publish site/ as the Cloudflare Worker "atlas-care" (worker/wrangler.toml).
# Live at https://atlas.lari-island.ai/research/care/ and atlas-care.lari-0c7.workers.dev.
# Needs a logged-in wrangler (npx wrangler whoami). Unchanged files are not re-uploaded.
set -eu
# On a machine without `wrangler login`, the token comes from the environment (CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID).
[ -f "$HOME/.config/atlas-research/.env" ] && set -a && . "$HOME/.config/atlas-research/.env" && set +a
cd "$(dirname "$0")/worker"
npx --yes wrangler deploy
