#!/bin/bash
set -e

echo "Homeassistant Recorder Database Editor"

mkdir -p /etc/dropbear

for keytype in rsa ecdsa ed25519; do
  keyfile="/etc/dropbear/dropbear_${keytype}_host_key"
  if [ ! -f "$keyfile" ]; then
    echo "[INFO] Generating $keytype key..."
    dropbearkey -t "$keytype" -f "$keyfile"
  fi
done

ln -sf /config /home/debug/config
chown -h debug:debug /home/debug/config || true
chown -R debug:debug /home/debug/config || true

CONFIG_PATH="/data/options.json"
SSH_ENABLED=$(jq -r '.enable_debug_shell // false' "$CONFIG_PATH")
SSH_PORT="${HASSIO_HOST_NETWORK_2233_TCP_PORT:-2233}"

if [ "$SSH_ENABLED" = "true" ]; then
    echo "[INFO] SSH debug shell enabled"
    # Run dropbear as user debug in the background
    sudo -u debug /usr/sbin/dropbear -E -p "$SSH_PORT" &
else
    echo "[INFO] SSH debug shell is disabled"
fi

# Wait forever for the container not to end
while true; do
    sleep 3600
done
