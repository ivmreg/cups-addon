# sensible default so tooling doesn't warn; supervisor/build system can override this ARG
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest

# ---- Build stage ----
FROM ${BUILD_FROM} AS builder

RUN apk add --no-cache build-base cmake git cups-dev

# Build brlaser
RUN git clone https://github.com/pdewacht/brlaser.git /tmp/brlaser \
 && cd /tmp/brlaser \
 && cmake . \
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
      dbus

# Copy brlaser artifacts from builder
COPY --from=builder /tmp/install/ /

# Copy rootfs into a temporary dir to avoid Docker trying to overwrite system dirs
COPY rootfs /tmp/rootfs/

# Merge rootfs contents into /:
# - if both are directories, copy contents into existing dir
# - otherwise remove existing target and move source into place
RUN set -eux; \
    for src in /tmp/rootfs/*; do \
      name="$(basename "$src")"; \
      tgt="/${name}"; \
      if [ -d "$src" ] && [ -d "$tgt" ]; then \
        echo "Merging directory $src -> $tgt"; \
        cp -a "$src/." "$tgt/"; \
      else \
        echo "Replacing $tgt with $src"; \
        rm -rf "$tgt" || true; \
        mv "$src" "$tgt"; \
      fi; \
    done; \
    rm -rf /tmp/rootfs

# Expose IPP port
EXPOSE 631

# Healthcheck: verify scheduler is alive (full path to lpstat)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD /usr/bin/lpstat -r || exit 1
