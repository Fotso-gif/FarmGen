#!/usr/bin/env bash
# Simple end-to-end curl test:
# - GET health (stores cookies)
# - POST add item to session cart (JSON)
# - GET cart
# - POST checkout (creates PaymentIntent)
#
# Usage: ./scripts/test_checkout.sh [BASE_URL]
# Example: ./scripts/test_checkout.sh http://127.0.0.1:8000

BASE="${1:-http://127.0.0.1:8000}"
COOKIEJAR="$(mktemp /tmp/curl-cookiejar.XXXXXX)"
JQ="${JQ:-jq}"   # install jq for pretty JSON (optional)

echo "Using base URL: $BASE"
echo "Cookie jar: $COOKIEJAR"
echo

# 1) fetch health (and any cookies)
echo "1) GET /payments/api/health/ ..."
curl -s -c "$COOKIEJAR" "$BASE/payments/api/health/" | ( command -v $JQ >/dev/null 2>&1 && $JQ || cat )
echo
# try to extract CSRF token from cookiejar (if set by server)
CSRF_TOKEN=$(grep -i 'csrftoken' "$COOKIEJAR" | awk '{print $7}' | tail -n1 || true)
CSRF_HEADER=""
if [ -n "$CSRF_TOKEN" ]; then
  CSRF_HEADER=(-H "X-CSRFToken: $CSRF_TOKEN")
  echo "Found CSRF token in cookies, will send X-CSRFToken header."
else
  echo "No CSRF token found in cookiejar — proceeding without CSRF header."
fi
echo

# helper to show responses nicely
do_curl() {
  local method=$1; shift
  local url=$1; shift
  local data=$1
  if [ -n "$data" ]; then
    resp=$(curl -s -b "$COOKIEJAR" -c "$COOKIEJAR" -H "Content-Type: application/json" "${CSRF_HEADER[@]}" -X "$method" -d "$data" "$url")
  else
    resp=$(curl -s -b "$COOKIEJAR" -c "$COOKIEJAR" "${CSRF_HEADER[@]}" -X "$method" "$url")
  fi
  if command -v $JQ >/dev/null 2>&1; then
    echo "$resp" | $JQ
  else
    echo "$resp"
  fi
}

# 2) Add item to cart
echo "2) POST add item to cart (/payments/api/cart/)"
ITEM_JSON='{"product_id":"sku123","name":"Tomate","price":500,"quantity":2}'
do_curl "POST" "$BASE/payments/api/cart/" "$ITEM_JSON"
echo

# 3) GET cart
echo "3) GET cart (/payments/api/cart/)"
do_curl "GET" "$BASE/payments/api/cart/"
echo

# 4) POST checkout (omit amount to use session cart total)
echo "4) POST checkout (/payments/api/checkout/)"
CHECKOUT_JSON='{"currency":"usd"}'
do_curl "POST" "$BASE/payments/api/checkout/" "$CHECKOUT_JSON"
echo

echo "Done. Cookiejar file: $COOKIEJAR (remove when done)."
