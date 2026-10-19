#!/usr/bin/env bash

set -u

URL="${1:-http://localhost:8000/health}"
MAX_ATTEMPTS="${2:-12}"
WAIT_SECONDS="${3:-5}"

for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
    STATUS=$(curl --silent --output /dev/null \
        --write-out "%{http_code}" \
        --max-time 5 \
        "$URL" || true)

    if [ "$STATUS" = "200" ]; then
        echo "Health check successful: HTTP 200 (attempt $attempt/$MAX_ATTEMPTS)"
        exit 0
    fi

    echo "Attempt $attempt/$MAX_ATTEMPTS returned HTTP ${STATUS:-000}"

    if [ "$attempt" -lt "$MAX_ATTEMPTS" ]; then
        sleep "$WAIT_SECONDS"
    fi
done

echo "Health check failed after $MAX_ATTEMPTS attempts"
exit 1
