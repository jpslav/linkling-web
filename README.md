# linkling-web

The Linkling public website: the landing page and the privacy page.

Part of **Linkling**, a small self-hosted link shortener built by the Tinyworks program.
This repository starts empty on purpose: everything else here is built through that program.

The Docker image logs no visitor's address on its own, with no compose file or mount
required: `docker run` of `linkling-web` alone still keeps `linkling-api`'s ADR-0004
promise that Linkling keeps no IP addresses (see
`docs/adr/0003-bake-privacy-directives-into-image.md`, `deploy/nginx-privacy.conf`,
`scripts/image-privacy-smoke.sh`).
