#!/usr/bin/with-contenv bashio

# This script performs one-time initialization.

set -e

CONFIG_PATH="/data/cups"
CONFIG_FILE="${CONFIG_PATH}/config/cupsd.conf"

bashio::log.info "Initializing CUPS configuration..."

# 1. Create persistent directory structure if it doesn't exist.
mkdir -p "${CONFIG_PATH}/cache" \
           "${CONFIG_PATH}/config/ppd" \
           "${CONFIG_PATH}/logs" \
           "${CONFIG_PATH}/state"

# 2. Copy the default cupsd.conf if one doesn't exist in /data.
if ! bashio::fs.file_exists "${CONFIG_FILE}"; then
    bashio::log.info "No cupsd.conf found. Copying default configuration."
    cp /etc/cups/cupsd.conf "${CONFIG_FILE}"
fi

bashio::log.info "Initialization complete."