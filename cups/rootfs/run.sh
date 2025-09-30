#!/usr/bin/with-contenv bashio
set -e

bashio::log.info "Starting DBus and Avahi..."
dbus-daemon --system --nopidfile
avahi-daemon -D
sleep 2

bashio::log.info "Starting CUPS scheduler..."
exec /usr/sbin/cupsd -f
