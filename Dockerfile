# See docs/adr/0002-site-container-base-image.md for why nginx:alpine.
FROM nginx:1.27-alpine

# See docs/adr/0003-bake-privacy-directives-into-image.md: this makes the image private on
# its own, with no compose mount required (LL-020).
COPY deploy/nginx-privacy.conf /etc/nginx/conf.d/00-privacy.conf
COPY site/ /usr/share/nginx/html/
