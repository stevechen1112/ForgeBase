#!/usr/bin/env sh

set -eu

APP_DIR="${1:-.}"

cd "$APP_DIR"

mkdir -p .next/standalone/.next
rm -rf .next/standalone/public
ln -s "$PWD/public" .next/standalone/public

rm -rf .next/standalone/.next/static
ln -s "$PWD/.next/static" .next/standalone/.next/static
