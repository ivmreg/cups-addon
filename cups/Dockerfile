# Build arguments
ARG BUILD_FROM

# ---- Build stage ----
FROM ${BUILD_FROM} AS builder

RUN apk add --no-cache build-base cmake git cups-dev

# Build brlaser
RUN git clone https://github.com/pdewacht/brlaser.git /tmp/brlaser \
 && cd /tmp/brlaser \
 && cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 . \
 && make \
 && make install DESTDIR=/tmp/install

# ---- Runtime stage ----
FROM ${BUILD_FROM}

ENV LANG=C.UTF-8

# Redirect CUPS state directly into the persistent /data volume
ENV CUPS_DATADIR=/data/cups \
    CUPS_CACHEDIR=/data/cups/cache \
    CUPS_LOGDIR=/data/cups/logs \
    CUPS_STATEDIR=/data/cups/state \
    CUPS_SERVERROOT=/data/cups/config

# runtime packages
RUN apk add --no-cache \
      cups \
      cups-filters \
      ghostscript \
      libjpeg-turbo \
      net-snmp \
      avahi \
      avahi-compat-libdns_sd \
      dbus \
      # AirPrint service generation dependencies
      inotify-tools \
      python3 \
      py3-pycups

# Copy brlaser artifacts from builder
COPY --from=builder /tmp/install/ /

# Copy rootfs
COPY rootfs /

# Fix permissions for s6-overlay scripts
RUN chmod -R 755 /etc/services.d && \
    chmod -R 755 /etc/cont-init.d

# Expose IPP port
EXPOSE 631

# Healthcheck: verify scheduler is alive (full path to lpstat)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD /usr/bin/lpstat -r || exit 1

# S6 will be PID 1 through Home Assistant
