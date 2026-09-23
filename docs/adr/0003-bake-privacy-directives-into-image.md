# ADR-0003 — Bake the visitor-privacy nginx directives into this image, not just linkling-api's compose mount

- Status: Proposed
- Approver: (pending)
- Date: 2026-09-23

## Context

ADR-0004 in `linkling-api` promises that Linkling keeps no visitor IP addresses. Stock
`nginx` breaks that promise on day one: it writes every visitor's address to its access log,
and adds `client: <address>` to request-level errors (404, 413, 403, ...) in its error log.
Today the only thing turning that off is `linkling-api`'s `compose.yaml`, which bind-mounts
`deploy/nginx-privacy.conf` (its own copy, written for api #8) into the site container at
`/etc/nginx/conf.d/00-privacy.conf`. That makes the promise true of the *pair* of repos run
together, but false of `linkling-web`'s own image run by itself: anyone who pulls or runs it
alone, with no compose file in sight, inherits the leak, and the (not-yet-written) privacy
page would be false for them (register item LL-020, found by `w-LL-005`).

The directives themselves are not this ADR's decision -- they are already written and tested
in `linkling-api` (`w-LL-005`'s report, `deploy/nginx-privacy.conf`), including the finding
that the error log must be off outright (`error_log /dev/null;`), not merely re-targeted,
because nginx attaches the client address to a request-level error at every severity,
including `crit`.

## Decision

**Proposed: carry `linkling-api`'s tested `access_log off; log_not_found off; error_log
/dev/null;` into `linkling-web`'s own `deploy/nginx-privacy.conf`, and `COPY` it into the
image at build time** at the exact path `linkling-api`'s compose mount already uses,
`/etc/nginx/conf.d/00-privacy.conf` (Dockerfile, this PR).

Same path, on purpose: nginx's `conf.d/*.conf` files are read in filename order and a later
file of the same name replaces an earlier one on disk rather than appending to it, so
`linkling-api`'s bind mount (`ro`) simply overlays this image's own copy with an identical
file at container start. Nothing about the two conflicts, and nothing in `linkling-api`
needs to change for that to keep being true. The mount becomes redundant the moment this
image ships, but removing it is `linkling-api`'s call, not this repo's (LL-020's scope
excludes it) -- until it is removed, `linkling-web` still works if `linkling-api` is rolled
back to an image predating this change, which the mount alone could not guarantee for the
reverse case (an old `linkling-api` compose file against a new, mount-free `linkling-web`
image run standalone).

Alternatives considered:
- **Do nothing here; require every deployment to remember the mount.** This is the status
  quo LL-020 exists to close: it works only for `linkling-api`'s own compose file, and
  silently reopens for anyone else.
- **A `docker-entrypoint.d/` script that rewrites `nginx.conf` at container start.** Stock
  `nginx:alpine`'s entrypoint already runs `.sh` scripts from that directory before starting
  nginx, so this was a real option. Rejected: it would run on every container start for a
  file that never needs to vary by environment, trading a build-time `COPY` (visible in the
  Dockerfile, no runtime cost, easy to read in `docker history`) for a runtime step that
  does the same thing less legibly.
- **A different path** (e.g. `/etc/nginx/conf.d/privacy.conf`, no `00-` prefix). Rejected
  because it would make the compose mount overlay a *different* filename, meaning both this
  image's file and `linkling-api`'s file would load, redundantly but still harmlessly -- the
  same path was simpler to reason about and to state as a guarantee here.

## Consequences

- `linkling-web`'s own image is private by default; running it with no compose file, no
  mount and no other configuration still meets ADR-0004's promise.
- `linkling-api`'s `compose.yaml` mount at `deploy/nginx-privacy.conf:/etc/nginx/conf.d/00-privacy.conf`
  is now redundant. It is left in place (out of scope for this item); a future item in
  `linkling-api` can remove it once someone there decides the duplication is worth cutting.
- Any future nginx config file added to this image must not reuse the `00-` prefix, or it
  will load out of the order this ADR assumes.
- The two repos' `deploy/nginx-privacy.conf` files are now independent copies of the same
  three directives, not a shared file -- a future change to the tested directives (e.g. a
  new request-level error found to leak an address) has to be carried into both by hand.
  Small and stable enough today that a shared package would cost more than it saves; revisit
  if the directives start changing often.
