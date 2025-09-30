#!/usr/bin/with-contenv bashio
set -e

CONFIG_PATH="/data/cups"
CONFIG_CONF="${CONFIG_PATH}/config"
CONFIG_FILE="${CONFIG_CONF}/cupsd.conf"

bashio::log.info "Initializing persistent CUPS directories..."

# Persistent dirs
mkdir -p "${CONFIG_PATH}/cache" \
         "${CONFIG_PATH}/logs" \
         "${CONFIG_PATH}/state" \
         "${CONFIG_CONF}/ppd"

# Permissions
chown -R root:lp "${CONFIG_PATH}"
chmod -R 775 "${CONFIG_PATH}"
chmod 755 "${CONFIG_CONF}/ppd"

# Seed cupsd.conf if missing
if [ ! -s "${CONFIG_FILE}" ]; then
    bashio::log.info "No cupsd.conf found. Copying default configuration."
    cp /etc/cups/cupsd.conf "${CONFIG_FILE}"
fi

# Ensure printers.conf exists with correct perms
touch "${CONFIG_CONF}/printers.conf"
chown root:lp "${CONFIG_CONF}/printers.conf"
chmod 600 "${CONFIG_CONF}/printers.conf"

# Symlinks into /etc/cups (so cupsd always uses /data)
ln -sf "${CONFIG_FILE}" /etc/cups/cupsd.conf
ln -sf "${CONFIG_CONF}/printers.conf" /etc/cups/printers.conf
rm -rf /etc/cups/ppd
ln -s "${CONFIG_CONF}/ppd" /etc/cups/ppd

bashio::log.info "CUPS initialization complete."
