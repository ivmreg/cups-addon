# ---- Build stage ----
ARG BUILD_FROM
FROM $BUILD_FROM as builder

RUN apk add --no-cache build-base cmake git cups-dev

# Build brlaser
RUN git clone https://github.com/pdewacht/brlaser.git /tmp/brlaser && \
    cd /tmp/brlaser && \
    cmake . && make && make install DESTDIR=/tmp/install

# ---- Runtime stage ----
FROM $BUILD_FROM

ENV LANG=C.UTF-8

# Redirect CUPS state into /data for persistence
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

# Ensure persistent directories exist at image build time
RUN mkdir -p /data/cups/config/ppd \
             /data/cups/cache \
             /data/cups/logs \
             /data/cups/state && \
    chown -R root:lp /data/cups && \
    chmod -R 775 /data/cups

# Expose IPP port
EXPOSE 631

# Healthcheck: verify scheduler is alive
HEALTHCHECK CMD lpstat -r || exit 1
