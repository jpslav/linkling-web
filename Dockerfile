# See docs/adr/0001-site-container-base-image.md for why nginx:alpine.
FROM nginx:1.27-alpine

COPY site/ /usr/share/nginx/html/
