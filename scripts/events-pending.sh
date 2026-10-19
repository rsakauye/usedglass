#!/usr/bin/env bash
# Review event submissions waiting in Cloudflare KV (namespace UG_EVENTS). Nothing is published automatically.
# Needs wrangler logged in to Russell's Cloudflare account (`npx wrangler login`) or CLOUDFLARE_API_TOKEN with KV read/edit.
#   scripts/events-pending.sh            list pending submissions (full JSON)
#   scripts/events-pending.sh delete KEY  delete one (after copying it into data/events.json, or to reject it)
set -euo pipefail
NS=7d5892c3771945248468786b5f5049e3   # UG_EVENTS
W="npx --yes wrangler@4"
if [[ "${1:-}" == "delete" ]]; then
  $W kv key delete --remote --namespace-id "$NS" "$2"; exit
fi
keys=$($W kv key list --remote --namespace-id "$NS" --prefix pending: | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>JSON.parse(s).forEach(k=>console.log(k.name)))')
[[ -z "$keys" ]] && { echo "No pending event submissions."; exit; }
for k in $keys; do echo "== $k"; $W kv key get --remote --namespace-id "$NS" "$k"; echo; done
