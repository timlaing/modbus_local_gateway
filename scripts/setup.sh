#!/usr/bin/zsh
set -ex

cd "$(dirname "$0")/.."

export UV_LINK_MODE=copy

if [ ! -n "$VIRTUAL_ENV" ]; then
  rm -rf .venv || true
  if [ -x "$(command -v uv)" ]; then
    uv venv .venv
  else
    python3 -m venv .venv
  fi
  source .venv/bin/activate
fi

if ! [ -x "$(command -v uv)" ]; then
  python3 -m pip install uv
fi

scripts/startup.sh

prek install -f

if ! [ -e /opt/sonarqube-mcp/sonarqube-mcp-server.jar ]; then
  MCP_LISTING="https://binaries.sonarsource.com/s3api?delimiter=/&prefix=Distribution/sonarqube-mcp-server/"
  JAR=$(curl -fsSL --proto "=https" "${MCP_LISTING}" | grep -oP '<Key>.*?</Key>' | awk -F '[<>]' '/>.*\.jar</ { print $3 }' | tail -n 1)
  sudo mkdir -p /opt/sonarqube-mcp
  set -x
  sudo curl --proto "=https" -L -o /opt/sonarqube-mcp/sonarqube-mcp-server.jar "https://binaries.sonarsource.com/${JAR}"
fi
