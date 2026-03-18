#!/usr/bin/env bash
# seed_royalty_docs.sh
# Copies the generated royaltyBase knowledge base files into the Docker
# uploads volume so AnythingLLM can read them via the hotdir mount.
#
# Usage: bash seed_royalty_docs.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROYALTY_BASE="$SCRIPT_DIR/../baseDocs/royaltyBase"
CONTAINER="royalties-backend-1"
UPLOAD_DIR="/app/uploads"

if [ ! -d "$ROYALTY_BASE" ]; then
  echo "❌ $ROYALTY_BASE not found. Run generate_royalty_base.py first."
  exit 1
fi

FILE_COUNT=$(find "$ROYALTY_BASE" -type f | wc -l)
echo "📁 Found $FILE_COUNT files in royaltyBase"

# Create target directory in the container
echo "📤 Copying files to $CONTAINER:$UPLOAD_DIR/royalty-knowledge-base/ ..."

MSYS_NO_PATHCONV=1 docker exec "$CONTAINER" mkdir -p "$UPLOAD_DIR/royalty-knowledge-base"

# Copy using docker cp (works reliably on Windows/Mac/Linux)
docker cp "$ROYALTY_BASE/." "$CONTAINER:$UPLOAD_DIR/royalty-knowledge-base/"

# Verify
COPIED=$(MSYS_NO_PATHCONV=1 docker exec "$CONTAINER" find "$UPLOAD_DIR/royalty-knowledge-base" -type f | wc -l)
echo ""
echo "✅ Done! $COPIED files copied to the uploads volume."
echo ""
echo "AnythingLLM can now access these at:"
echo "  /app/server/storage/hotdir/royalty-docs/royalty-knowledge-base/"
echo ""
echo "Next steps:"
echo "  1. Open http://localhost:3001"
echo "  2. Create a workspace (e.g. 'Royalty Settlements')"
echo "  3. Upload documents from the hotdir or use the API"
echo "  4. Start chatting with your royalty data!"
