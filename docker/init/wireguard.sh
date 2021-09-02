#!/bin/bash

if [ "${UNPRIVILEGED}" == "yes" ]; then
	echo "$(date +'%Y-%m-%d %H:%M:%S') [INFO] Unprivileged mode enabled"
	/bin/bash /init/unprivileged.sh
elif [ "${UNPRIVILEGED}" != "no" ]; then
	echo "$(date +'%Y-%m-%d %H:%M:%S') [INFO] Unprivileged not set or invalid value, defaulting to privileged mode."
	export UNPRIVILEGED=false
fi

export VPN_CONFIG=$(find /config/wireguard -maxdepth 1 -name "*.conf" -print -quit 2>/dev/null)

if [[ -z "${VPN_CONFIG}" ]]; then
	echo "$(date +'%Y-%m-%d %H:%M:%S') [Warning] VPN disabled. No WireGuard config file found in /config/wireguard/. Download one from your VPN provider and restart this container. Make sure the file extension is '.conf'"
else
	cp "$VPN_CONFIG" /etc/wireguard/wg0.conf

	public_ip="$(dig +short myip.opendns.com @resolver1.opendns.com)"
	echo "$(date +'%Y-%m-%d %H:%M:%S') [Info] Your public IP is: $public_ip"

	echo "$(date +'%Y-%m-%d %H:%M:%S') [Info] Starting Wireguard"
	echo "--------------------"
	wg-quick up wg0
	echo "--------------------"

	vpn_ip="$(dig +short myip.opendns.com @resolver1.opendns.com)"
	if [[ "$public_ip" != "$vpn_ip" ]]; then
		echo "$(date +'%Y-%m-%d %H:%M:%S') [Info] Your public IP changed to: $vpn_ip"
	else
		echo "$(date +'%Y-%m-%d %H:%M:%S') [Warning] Your public IP did not change."
	fi
fi