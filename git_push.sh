#!/bin/bash
cd "C:/Users/ei/Projects/royaltyStatementValidator"

echo "=== GIT LOG ==="
git log --oneline -5

echo ""
echo "=== GIT STATUS ==="
git status --short

echo ""
echo "=== FORCE PUSH ==="
git push --force-with-lease origin main 2>&1

echo ""
echo "=== RESULT: $? ==="
