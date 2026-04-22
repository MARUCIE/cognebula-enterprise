#!/usr/bin/env bash
# Deploy web/out/ to VPS with snapshot/rollback.
#
# Usage:
#   scripts/deploy_web.sh [tag]     # tag = short label written into snapshot filename
#   scripts/deploy_web.sh rollback  # revert to newest snapshot
#
# Contract:
#   1. Snapshot current prod state BEFORE touching it (so the last-known-good
#      build is always one ssh-untar away)
#   2. Build is assumed already done (web/out/ exists); script does not
#      trigger `next build` to keep build and deploy auditable as separate
#      steps
#   3. Post-rsync, verify a content signal (keyword grep on the deployed
#      HTML). If the signal is missing the rsync reverted something; fail
#      loud so the caller can roll back manually
#
# Conventions mirror HANDOFF.md 2026-04-20 deploy ritual:
#   rsync -az --delete web/out/ contabo:/home/kg/cognebula-web/
#   chown www-data:www-data + chmod o+rX

set -euo pipefail

readonly REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
readonly OUT_DIR="${REPO_DIR}/web/out"
readonly SSH_HOST="contabo"
readonly SSH_OPTS=(-T -o RemoteCommand=none -o BatchMode=yes)
readonly REMOTE_DIR="/home/kg/cognebula-web"
readonly REMOTE_PARENT="/home/kg"
readonly CONTENT_SIGNAL_FILE="expert/data-quality/index.html"
readonly CONTENT_SIGNAL_KEYWORD="条款语义审核"

log() { printf '[deploy] %s\n' "$*" >&2; }
die() { printf '[deploy][ERROR] %s\n' "$*" >&2; exit 1; }

snapshot_current() {
  local tag="${1:-prev}"
  local ts
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  local name="cognebula-web-snapshot-${ts}-${tag}.tgz"
  log "snapshotting current prod → ${name}"
  ssh "${SSH_OPTS[@]}" "$SSH_HOST" \
    "cd ${REMOTE_PARENT} && tar -czf ${name} cognebula-web/ && ls -lh ${name}" \
    | tail -1
  printf '%s\n' "$name"
}

rsync_out() {
  [[ -d "$OUT_DIR" ]] || die "missing ${OUT_DIR}; run 'cd web && next build' first"
  log "rsync ${OUT_DIR}/ → ${SSH_HOST}:${REMOTE_DIR}/"
  rsync -az --delete -e "ssh -o RemoteCommand=none" \
    "${OUT_DIR}/" "${SSH_HOST}:${REMOTE_DIR}/"
}

fix_perms() {
  log "chown + chmod on ${REMOTE_DIR}"
  ssh "${SSH_OPTS[@]}" "$SSH_HOST" \
    "chown -R www-data:www-data ${REMOTE_DIR}/ && chmod -R o+rX ${REMOTE_DIR}/"
}

verify_signal() {
  log "verifying content signal '${CONTENT_SIGNAL_KEYWORD}' in ${CONTENT_SIGNAL_FILE}"
  local count
  count="$(ssh "${SSH_OPTS[@]}" "$SSH_HOST" \
    "grep -c '${CONTENT_SIGNAL_KEYWORD}' ${REMOTE_DIR}/${CONTENT_SIGNAL_FILE} 2>/dev/null || echo 0")"
  if [[ "$count" -lt 1 ]]; then
    die "content signal missing from deployed ${CONTENT_SIGNAL_FILE}; deployment corrupt — run 'scripts/deploy_web.sh rollback' immediately"
  fi
  log "content signal present (${count} match)"
}

rollback() {
  log "listing snapshots on VPS"
  local latest
  latest="$(ssh "${SSH_OPTS[@]}" "$SSH_HOST" \
    "ls -1t ${REMOTE_PARENT}/cognebula-web-snapshot-*.tgz 2>/dev/null | head -1" \
    | tr -d '\r')"
  [[ -n "$latest" ]] || die "no snapshots found on VPS"
  log "rolling back to ${latest}"
  ssh "${SSH_OPTS[@]}" "$SSH_HOST" \
    "cd ${REMOTE_PARENT} && rm -rf cognebula-web.rollback && mv cognebula-web cognebula-web.rollback && tar -xzf ${latest} && chown -R www-data:www-data cognebula-web/ && chmod -R o+rX cognebula-web/ && echo restored from ${latest}"
  log "rollback complete; old tree preserved at ${REMOTE_PARENT}/cognebula-web.rollback until next deploy"
}

case "${1:-deploy}" in
  rollback)
    rollback
    ;;
  deploy|*)
    tag="${1:-prev}"
    snapshot_current "$tag"
    rsync_out
    fix_perms
    verify_signal
    log "deploy OK"
    ;;
esac
