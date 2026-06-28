#!/bin/bash
# Retry upload valuation.json to PA with exponential backoff
# Run: bash scripts/retry_upload_valuation.sh

PA_TOKEN="244b83030445a6656bb513af59fe9c2bb4aec61d"
LOCAL_FILE="/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/v2_deploy_pkg/valuation.json"
PA_URL="https://www.pythonanywhere.com/api/v0/user/froza/files/path/home/froza/etf-tool-mvp/valuation.json"
RELOAD_URL="https://www.pythonanywhere.com/api/v0/user/froza/webapps/froza.pythonanywhere.com/reload/"

MAX_ATTEMPTS=10

for i in $(seq 1 $MAX_ATTEMPTS); do
    code=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Token ${PA_TOKEN}" \
        "${PA_URL}" \
        -F "content=@${LOCAL_FILE}")

    echo "[$(date '+%H:%M:%S')] Attempt $i: HTTP $code"

    if [ "$code" = "200" ] || [ "$code" = "201" ]; then
        echo "✅ Upload succeeded! Reloading..."
        curl -s -o /dev/null -w "Reload: HTTP %{http_code}\n" \
            -H "Authorization: Token ${PA_TOKEN}" \
            "${RELOAD_URL}" -X POST
        echo "Done."
        exit 0
    fi

    if [ $i -lt $MAX_ATTEMPTS ]; then
        wait=$((2**i))
        echo "  Waiting ${wait}s..."
        sleep $wait
    fi
done

echo "❌ Upload failed after ${MAX_ATTEMPTS} attempts. PA may still be down."
exit 1
