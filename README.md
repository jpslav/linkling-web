# linkling-web

The Linkling public website: the landing page and the privacy page.

Part of **Linkling**, a small self-hosted link shortener built by the Tinyworks program.
This repository starts empty on purpose: everything else here is built through that program.

The Docker image logs no visitor's address on its own, with no compose file or mount
required: `docker run` of `linkling-web` alone still keeps `linkling-api`'s ADR-0004
promise that Linkling keeps no IP addresses (see
`docs/adr/0003-bake-privacy-directives-into-image.md`, `deploy/nginx-privacy.conf`,
`scripts/image-privacy-smoke.sh`).

The site loads nothing from a third party, and CI checks it on every pull request and every push
to `main`. The `no-third-party-site` job (`.github/workflows/ci.yml`) runs `linkling-api`'s
`scripts/no-third-party-check.sh` against this checkout: it checks out `linkling-api` at its `main`
(both repositories are public, so with no deploy key or secret), builds this Dockerfile into that
repository's compose stack, and fails if the site sends a packet to anyone but the visitor or serves
an absolute URL, a `<script>` or an inline event handler. A missing checkout is red, never green.
The check is `linkling-api`'s, so a change there to the script or to what it builds reaches this job
when it merges. Every job runs on `ubuntu-24.04`, not the `ubuntu-latest` alias, which moves to Ubuntu 26
from 2026-10-19.
