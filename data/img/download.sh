#!/bin/bash
# Download from url and write to file.

set -euo pipefail
IFS=$'\n\t'

if (( $# < 1 )); then
	echo "usage: ${0##*/} <url> [file]"
	exit 1
fi

url=$1

curl_args=()
if (( $# >= 2 )); then
  curl_args+=(-o "$2")
else
  curl_args+=(-O)
fi

echo "curl_args=${curl_args[*]}"

# Extra options are required due to website
# Chrome > Developer Tools > Network > Copy as cURL

curl \
  "${curl_args[@]}" \
  -H 'Upgrade-Insecure-Requests: 1' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36' \
  -H 'sec-ch-ua: "Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Linux"' \
  "$url"
