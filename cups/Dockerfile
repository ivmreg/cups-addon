# ARG BUILD_FROM
# FROM $BUILD_FROM as builder

# RUN apk add --no-cache build-base cmake git cups-dev

# # Build brlaser
# RUN git clone https://github.com/pdewacht/brlaser.git /tmp/brlaser && \
#     cd /tmp/brlaser && \
#     cmake . && make && make install DESTDIR=/tmp/install

# # Final runtime image
# FROM $BUILD_FROM

ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG=C.UTF-8
ENV CUPS_DATADIR=/data/cups
ENV CUPS_CACHEDIR=/data/cups/cache
ENV CUPS_LOGDIR=/data/cups/logs
ENV CUPS_STATEDIR=/data/cups/state
ENV CUPS_SERVERROOT=/data/cups/config

RUN apk add --no-cache \
      cups \
      cups-filters \
      ghostscript \
      libjpeg-turbo \
      net-snmp \
      avahi \
      avahi-compat-libdns_sd \
      dbus

# # Copy brlaser artifacts from builder
# COPY --from=builder /tmp/install/ /

# Copy rootfs (scripts and configs)
COPY rootfs /

EXPOSE 631

HEALTHCHECK CMD lpstat -r || exit 1
