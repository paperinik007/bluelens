FROM ubuntu:24.04

# NOTE (deviation from task brief, discovered during Step 4 verification): Ubuntu
# 24.04's plain `squid` apt package is linked against GnuTLS and does not implement
# ssl-bump/ssl_bump at all ("FATAL: Unknown http_port option 'ssl-bump'" at
# startup) — SNI-peek-and-splice is an OpenSSL-only Squid feature. `squid-openssl`
# is the same Squid 6.14 build linked against OpenSSL instead; same binary path,
# same config syntax, same version, just the TLS backend the brief's design
# actually requires.
RUN apt-get update \
    && apt-get install -y --no-install-recommends squid-openssl openssl \
    && rm -rf /var/lib/apt/lists/*

# ssl_bump's config parser requires a cert/key pair on the listening port even
# though "peek" + "splice" (used below) never terminates TLS or uses this key to
# decrypt anything — self-signed and disposable, satisfies startup validation only.
RUN openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 \
    -keyout /etc/squid/squid.key -out /etc/squid/squid.crt \
    -subj "/CN=egress-proxy-placeholder"

COPY squid.conf /etc/squid/squid.conf
EXPOSE 3128
CMD ["squid", "-N", "-d", "1"]
