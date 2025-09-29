#!/usr/bin/with-contenv bash
set -euo pipefail

# Persistent dirs
mkdir -p /data/cups/cache /data/cups/logs /data/cups/state /data/cups/config
chown -R root:lp /data/cups
chmod -R 775 /data/cups

# Ensure system dirs
mkdir -p /etc/cups /etc/avahi/services

# Write CUPS config
cat > /data/cups/config/cupsd.conf << 'EOL'
# Listen and accept specific hostnames/IPs to avoid Bad Request
Port 631
ServerAlias localhost
ServerAlias 127.0.0.1
ServerAlias 192.168.1.158
ServerAlias homeassistant.lan

# Enable web UI
WebInterface Yes

# Defaults
DefaultAuthType None
JobSheets none,none
PreserveJobHistory No

# AirPrint: publish via DNS-SD (Bonjour/mDNS)
BrowseLocalProtocols dnssd

# Access control: only local host + main LAN
<Location />
  Order allow,deny
  Allow localhost
  Allow 192.168.1.0/24
</Location>

<Location /admin>
  Order allow,deny
  Allow localhost
  Allow 192.168.1.0/24
</Location>

<Location /jobs>
  Order allow,deny
  Allow localhost
  Allow 192.168.1.0/24
</Location>

<Limit Send-Document Send-URI Hold-Job Release-Job Restart-Job Purge-Jobs \
       Set-Job-Attributes Create-Job-Subscription Renew-Subscription \
       Cancel-Subscription Get-Notifications Reprocess-Job Cancel-Current-Job \
       Suspend-Current-Job Resume-Job Cancel-My-Jobs Close-Job CUPS-Move-Job \
       CUPS-Get-Document>
  Order allow,deny
  Allow localhost
  Allow 192.168.1.0/24
</Limit>
EOL

# Define your Brother raw queue if not present
if [ ! -f /data/cups/config/printers.conf ]; then
  cat > /data/cups/config/printers.conf << 'EOL'
<Printer BrotherHL1110>
  Info Brother HL-1110 (Raw)
  Location Network
  DeviceURI socket://192.168.52.167:9100
  State Idle
  Accepting Yes
  Shared Yes
</Printer>
EOL
fi

# Avahi AirPrint bridge service (minimal; CUPS dnssd will publish actual queues)
cat > /etc/avahi/services/airprint.service << 'EOL'
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">%h CUPS</name>
  <service>
    <type>_ipp._tcp</type>
    <port>631</port>
  </service>
</service-group>
EOL

# Link configs into system paths
ln -sf /data/cups/config/cupsd.conf /etc/cups/cupsd.conf
ln -sf /data/cups/config/printers.conf /etc/cups/printers.conf

# Start DBus (for Avahi) and Avahi daemon, then CUPS
mkdir -p /run/dbus
dbus-daemon --system --nopidfile
avahi-daemon -D

# Foreground CUPS for add-on lifecycle
exec /usr/sbin/cupsd -f
