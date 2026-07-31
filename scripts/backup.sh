#!/bin/sh
# Backs up the Postgres database, the Chroma vector store, and the JWT
# signing keypair into a single timestamped tarball under ./backups.
#
# Run from anywhere:
#   ./scripts/backup.sh
#
# Suggested cron entry (daily at 3am, keeping backups on the same host -
# copy the resulting tarball offsite yourself if you want redundancy
# beyond this VM's disk):
#   0 3 * * * /path/to/reverse-file-search/scripts/backup.sh
set -eu

repo_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo_root"

timestamp=$(date +%Y%m%d-%H%M%S)
out_dir="$repo_root/backups"
work_dir="$out_dir/tmp-$timestamp"
archive="$out_dir/backup-$timestamp.tar.gz"

mkdir -p "$work_dir"

docker compose exec -T db pg_dump -U postgres reverse_file_search > "$work_dir/db.sql"

tar czf "$archive" \
    -C "$work_dir" db.sql \
    -C "$repo_root" backend/storage backend/keys

rm -rf "$work_dir"

echo "Backup written to $archive"
