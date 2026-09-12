#!/usr/bin/zsh
set -ex

cd "$(dirname "$0")/.."

export UV_LINK_MODE=copy

if [ ! -n "$VIRTUAL_ENV" ]; then
  source .venv/bin/activate
fi

echo "Installing development dependencies..."

uv pip install \
  -r requirements_all.txt \
  --upgrade \
  --config-settings editable_mode=compat

if command -v npm >/dev/null 2>&1; then
  if [ -f package-lock.json ]; then
    npm ci
  else
    npm install
  fi
fi
