ARG BUILD_FROM
FROM $BUILD_FROM

# Env
ENV LANG=C.UTF-8
ENV CUPS_DATADIR=/data/cups
ENV CUPS_CACHEDIR=/data/cups/cache
ENV CUPS_LOGDIR=/data/cups/logs
ENV CUPS_STATEDIR=/data/cups/state
ENV CUPS_SERVERROOT=/data/cups/config

# Setup base (Alpine)
RUN \
    echo "http://dl-cdn.alpinelinux.org/alpine/v$(cat /etc/alpine-release | cut -d'.' -f1,2)/main" > /etc/apk/repositories && \
    echo "http://dl-cdn.alpinelinux.org/alpine/v$(cat /etc/alpine-release | cut -d'.' -f1,2)/community" >> /etc/apk/repositories && \
    apk update && \
    apk add --no-cache \
      build-base \
      cmake \
      git \
      cups \
      cups-filters \
      ghostscript \
      libjpeg-turbo \
      net-snmp \
      avahi \
      avahi-compat-libdns_sd \
      avahi-tools \
      dbus

# Build and install brlaser
RUN git clone https://github.com/pdewacht/brlaser.git /tmp/brlaser && \
    cd /tmp/brlaser && \
    cmake . && make && make install && \
    rm -rf /tmp/brlaser

# Copy rootfs (scripts and configs)
COPY rootfs /

# Expose CUPS web interface port (host_network renders this optional)
EXPOSE 631

HEALTHCHECK \
    CMD lpstat -r || exit 1
