# Built locally (`npm run build`) and shipped as static files — the
# devserver's network to the npm registry is badly throttled, so building
# node_modules there was timing out. This image only needs nginx.
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY dist /usr/share/nginx/html
EXPOSE 80
