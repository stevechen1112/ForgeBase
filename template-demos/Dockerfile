# syntax=docker/dockerfile:1

FROM node:24-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM alpine:3.23 AS runner
RUN apk upgrade --no-cache \
    && apk add --no-cache nginx \
    && mkdir -p /var/cache/nginx \
    && chown -R nginx:nginx /var/cache/nginx /var/run /var/log/nginx /etc/nginx/http.d
COPY nginx.conf /etc/nginx/http.d/default.conf
COPY --from=builder --chown=nginx:nginx /app/out /usr/share/nginx/html
USER nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off; pid /tmp/nginx.pid;"]
