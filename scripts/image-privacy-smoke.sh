#!/usr/bin/env bash
# LL-020: run this repo's own image ALONE -- no compose file, no mount -- and prove it logs
# no visitor's address. (1) It answers a real page and a missing path; each status code is
# read straight from the client, which is what proves the requests actually arrived, before
# anything below ever looks at the container's own logs. (2) Its logs then hold neither the
# missing path nor any IPv4 address.
#
# LINKLING_WEB_SMOKE_PORT   host port to publish (default 18080)
# LINKLING_WEB_SMOKE_IMAGE  image tag to build and run (default linkling-web-smoke:<random>)
#
# Exit status: 0 pass, 1 fail: <step>, 2 blind: <what was absent>. Blind means the check
# could not look -- docker unreachable, the container never came up, or a request never got
# an HTTP response -- which is different from looking and finding a leak.
set -euo pipefail
cd "$(dirname "$0")/.."

fail() { echo "fail: $*" >&2; exit 1; }
blind() { echo "blind: $*" >&2; exit 2; }

command -v docker >/dev/null 2>&1 || blind "docker is not on PATH"
command -v curl >/dev/null 2>&1 || blind "curl is not on PATH"
docker info >/dev/null 2>&1 || blind "the docker daemon is not reachable"

rand() { od -An -N"$1" -tx1 /dev/urandom | tr -d ' \n'; }

image="${LINKLING_WEB_SMOKE_IMAGE:-linkling-web-smoke:$(rand 4)}"
container="linkling-web-smoke-$(rand 6)"
port="${LINKLING_WEB_SMOKE_PORT:-18080}"
base="http://127.0.0.1:$port"
missing="/no-such-page-$(rand 8)"

cleanup() { docker rm -f "$container" >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "image $image, container $container, on $base"

docker build -t "$image" . >/dev/null || fail "docker build failed"

if ! docker run -d --name "$container" -p "$port:80" "$image" >/dev/null; then
    blind "docker run never started a container"
fi

# Wait for nginx to actually be serving before requesting anything -- a connection refused
# because the server is not up yet is not evidence of anything this script checks.
up=""
for _ in $(seq 1 30); do
    if curl -s -o /dev/null "$base/"; then up=1; break; fi
    state="$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null || true)"
    case "$state" in exited|dead) blind "the container is $state before it ever answered" ;; esac
    sleep 0.5
done
[ -n "$up" ] || blind "the container never answered on $base"

# The proof that each request arrived: the status code the client itself received, read
# before any log is inspected. A "000" from curl means no HTTP response at all -- blind,
# not a request the server ever saw or could have logged.
ok_status="$(curl -s -o /dev/null -w '%{http_code}' "$base/")"
missing_status="$(curl -s -o /dev/null -w '%{http_code}' "$base$missing")"
echo "GET / -> $ok_status; GET $missing -> $missing_status"
[ "$ok_status" != "000" ] || blind "GET / got no HTTP response -- no request can be proven to have arrived"
[ "$missing_status" != "000" ] || blind "GET $missing got no HTTP response -- no request can be proven to have arrived"
[ "$ok_status" = 200 ] || fail "GET / answered $ok_status, not 200"
[ "$missing_status" = 404 ] || fail "GET $missing answered $missing_status, not 404"

logs="$(docker logs "$container" 2>&1)"
if grep -qF "$missing" <<<"$logs"; then
    fail "the container logs name the requested path: $(grep -F "$missing" <<<"$logs" | head -1)"
fi
addrs="$(grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' <<<"$logs" | grep -vx '0\.0\.0\.0' || true)"
[ -z "$addrs" ] || fail "the container logs hold an IPv4 address: $(head -1 <<<"$addrs")"

echo "pass"
