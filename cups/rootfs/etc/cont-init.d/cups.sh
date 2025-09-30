#!/usr/bin/with-contenv bashio

# This script performs one-time initialization.

set -e

CONFIG_PATH="/data/cups"
CONFIG_FILE="${CONFIG_PATH}/config/cupsd.conf"

bashio::log.info "Initializing CUPS configuration..."

# 1. Create persistent directory structure if it doesn't exist.
# This is moved from the Dockerfile.
mkdir -p "${CONFIG_PATH}/cache" \
           "${CONFIG_PATH}/config/ppd" \
           "${CONFIG_PATH}/logs" \
           "${CONFIG_PATH}/state"

# 2. Copy the default cupsd.conf if one doesn't exist in /data.
if ! bashio::fs.file_exists "${CONFIG_FILE}"; then
    bashio::log.info "No cupsd.conf found. Copying default configuration."
    cp /etc/cups/cupsd.conf "${CONFIG_FILE}"
fi

# 3. Get admin credentials from add-on options.
ADMIN_USER=$(bashio::config 'admin_username')
ADMIN_PASS=$(bashio::config 'admin_password')

# 4. Set the admin password for the CUPS 'root' user group.
# This makes the username/password from the config functional.
bashio::log.info "Setting CUPS admin password..."
lppasswd -g sys -a "${ADMIN_USER}" <<< "${ADMIN_PASS}"

bashio::log.info "Initialization complete."