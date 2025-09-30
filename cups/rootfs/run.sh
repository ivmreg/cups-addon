#!/usr/bin/with-contenv bashio

# This script runs the main CUPS service.

set -e

bashio::log.info "Starting CUPS daemon..."

# The ENV variables in the Dockerfile handle persistence.
# We just need to start the service in the foreground.
exec /usr/sbin/cupsd -f