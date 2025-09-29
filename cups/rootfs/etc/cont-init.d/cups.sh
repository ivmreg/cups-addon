#!/usr/bin/with-contenv bash
set -euo pipefail

# Persistent dirs
mkdir -p /data/cups/cache /data/cups/logs /data/cups/state /data/cups/config
chown -R root:lp /data/cups
chmod -R 775 /data/cups

# Ensure system dirs
mkdir -p /etc/cups /etc/avahi/services /run/cups /run/dbus
chown root:lp /run/cups
chmod 775 /run/cups

# Write CUPS config
cat > /data/cups/config/cupsd.conf <<'EOL'
Port 631
ServerAlias *

WebInterface Yes

DefaultAuthType None
DefaultEncryption Never
JobSheets none,none
PreserveJobHistory No

BrowseLocalProtocols dnssd
DefaultShared Yes

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

# Create a symlink from the default config location to our persistent location
ln -sf /data/cups/config/cupsd.conf /etc/cups/cupsd.conf
ln -sf /data/cups/config/printers.conf /etc/cups/printers.conf

# Start DBus (for Avahi) and Avahi daemon first
dbus-daemon --system --nopidfile
avahi-daemon -D

# Give daemons a moment to settle
sleep 2

# # Enforce encryption policy (modern syntax)
# cupsctl DefaultEncryption=Never || true

# Finally, start cupsd in foreground for s6 supervision
exec /usr/sbin/cupsd -f
