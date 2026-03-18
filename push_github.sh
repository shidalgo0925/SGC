#!/usr/bin/env bash
# Ejecutar en Git Bash en tu PC (no desde Cursor sin tus llaves).
set -e
mkdir -p ~/.ssh
ssh-keyscan -t ed25519 github.com >> ~/.ssh/known_hosts 2>/dev/null || true
cd "$(dirname "$0")"
eval "$(ssh-agent -s)" >/dev/null
ssh-add ~/.ssh/id_ed25519_github
export GIT_SSH_COMMAND='ssh -i ~/.ssh/id_ed25519_github -o IdentitiesOnly=yes'
git push -u origin main
echo "OK — revisa github.com/shidalgo0925/SGC"
