# ADR-0002 — Static site container: base image and pinning

- Status: Proposed
- Approver: (pending)
- Date: 2026-09-22

## Context

`linkling-api`'s ADR-0007 (Accepted, 2026-09-22) puts the public site in "a static
container in your own compose". `linkling-api`'s ADR-0009 (Accepted, 2026-09-22) requires
that container to be software the team runs itself — no third party in the build or the
click path — and that the served pages carry no third-party fonts, scripts or embeds.
`linkling-web`'s own conventions (`linkling-api`'s ADR-0008) fix the site itself as
hand-written HTML and CSS with no build step. `products/linkling/decision-policy.md`
marks "Docker base images and how they are pinned" as Claude's to decide, with an ADR.

## Decision

**Proposed: `nginx:1.27-alpine` as the site container's base image, pinned by tag rather
than by digest.**

Nginx serving static files needs no application code and no build step — the Dockerfile
only copies `site/` into `/usr/share/nginx/html/`. The default config already serves
`index.html` at `/` and any other file at its own path, which is all two flat HTML pages
need; nothing about it makes an outbound call at request time, so it satisfies
ADR-0009's "software you run, not a third party."

Pinned by tag (`1.27-alpine`), not by digest: a tag is legible in a diff and in this
Dockerfile, and rebuilding against it picks up that minor version's security patches. The
cost is that two builds of the same tag are not guaranteed byte-identical. Digest pinning
would fix that, but nothing in this repo yet automates bumping a pinned digest, and an
image frozen at a stale digest is its own kind of risk — revisit if a dependency-update
bot is added later.

Alternatives considered:
- `python:3.12-slim` running `python -m http.server` — keeps one language across both
  repos, but `http.server`'s own docs say it is not hardened for anything beyond local
  testing, and nothing else in this container needs Python (tests run against the served
  site from outside it, not inside the image).
- BusyBox `httpd` — smaller than `nginx:alpine`, rejected for now as less commonly
  operated, with a less-documented config surface for a two-page site that gains nothing
  from the extra minimalism.

## Consequences

- Rebuilding the image later can pick up a different `nginx` patch release under the same
  tag; that is deliberate, not an oversight.
- No build toolchain enters the image or the repo — `site/` is copied in verbatim, so the
  "no build toolchain unless you can say why one is needed" convention still holds.
- If the site ever needs server-side logic (unlikely for a two-page static shell), this
  ADR's base-image choice would need revisiting alongside that change.
