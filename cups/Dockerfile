# ---- Build stage ----
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM} AS builder

RUN apk add --no-cache build-base cmake git cups-dev

# Build brlaser
RUN git clone https://github.com/pdewacht/brlaser.git /tmp/brlaser && \
    cd /tmp/brlaser && \
    cmake . && make && make install DESTDIR=/tmp/install

# ---- Runtime stage ----
FROM $BUILD_FROM

ENV LANG=C.UTF-8

# Redirect CUPS state directly into the persistent /data volume
ENV CUPS_DATADIR=/data/cups \
    CUPS_CACHEDIR=/data/cups/cache \
    CUPS_LOGDIR=/data/cups/logs \
    CUPS_STATEDIR=/data/cups/state \
    CUPS_SERVERROOT=/data/cups/config

RUN apk add --no-cache \
      cups \
      cups-filters \
      ghostscript \
      libjpeg-turbo \
      net-snmp \
      avahi \
      avahi-compat-libdns_sd \
      dbus

# Copy brlaser artifacts from builder
COPY --from=builder /tmp/install/ /

# Copy rootfs (init scripts, configs)
COPY rootfs /

# Expose IPP port
EXPOSE 631

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD /usr/bin/lpstat -r || exit 1
