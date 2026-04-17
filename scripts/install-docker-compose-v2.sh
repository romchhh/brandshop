#!/usr/bin/env sh
# Встановлення Docker Compose V2 без apt (коли репозиторії Ubuntu EOL / 404).
# Після виконання: docker compose version
#
# Використання:
#   curl -fsSL ... | sh   АБО
#   chmod +x scripts/install-docker-compose-v2.sh && sudo ./scripts/install-docker-compose-v2.sh

set -e

COMPOSE_VERSION="${COMPOSE_VERSION:-v2.32.4}"

case "$(uname -m)" in
  x86_64)  ARCH=x86_64 ;;
  aarch64) ARCH=aarch64 ;;
  arm64)   ARCH=aarch64 ;;
  *)
    echo "Непідтримана архітектура: $(uname -m)" >&2
    exit 1
    ;;
esac

URL="https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-${ARCH}"
PLUGIN_DIR="/usr/local/lib/docker/cli-plugins"
TMP="/tmp/docker-compose-$$"

echo "Завантаження Compose ${COMPOSE_VERSION} (${ARCH})..."
curl -fSL "$URL" -o "$TMP"
chmod +x "$TMP"

echo "Встановлення у ${PLUGIN_DIR}/docker-compose (потрібні права root)..."
sudo mkdir -p "$PLUGIN_DIR"
sudo mv "$TMP" "$PLUGIN_DIR/docker-compose"
sudo chmod 755 "$PLUGIN_DIR/docker-compose"

echo "Готово. Перевірка:"
docker compose version
