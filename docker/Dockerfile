FROM alpine:3.14

RUN \
    apk update; \
    apk add --no-cache bash python3 py-pip ffmpeg wireguard-tools bind-tools; \
    pip3 install youtube-dl PyYAML PrettyTable bs4; \
    mkdir -p /downloads /init /etc/wireguard

COPY docker/init/ init/
COPY main.py /usr/local/bin/run

RUN \
    chmod +x /init/*.sh; \
    chmod +x /usr/local/bin/run

ENTRYPOINT ["/init/init.sh"]