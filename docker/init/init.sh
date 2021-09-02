#!/bin/bash --init-file

if [ "${VPN_ENABLED}" != "no" ]; then
    /bin/bash /init/wireguard.sh
fi