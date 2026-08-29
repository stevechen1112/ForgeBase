# syntax=docker/dockerfile:1

FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:24-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_TENANT_SLUG
ARG NEXT_PUBLIC_SITE_URL
ARG NEXT_PUBLIC_SITE_NAME
ARG NEXT_PUBLIC_BASE_PATH
ARG NEXT_PUBLIC_ASSET_BASE
ARG NEXT_PUBLIC_TURNSTILE_SITE_KEY
ARG FORGEBASE_TENANT_HOST_OVERRIDE
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_TENANT_SLUG=${NEXT_PUBLIC_TENANT_SLUG} \
    NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL} \
    NEXT_PUBLIC_SITE_NAME=${NEXT_PUBLIC_SITE_NAME} \
    NEXT_PUBLIC_BASE_PATH=${NEXT_PUBLIC_BASE_PATH} \
    NEXT_PUBLIC_ASSET_BASE=${NEXT_PUBLIC_ASSET_BASE} \
    NEXT_PUBLIC_TURNSTILE_SITE_KEY=${NEXT_PUBLIC_TURNSTILE_SITE_KEY} \
    FORGEBASE_TENANT_HOST_OVERRIDE=${FORGEBASE_TENANT_HOST_OVERRIDE}
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# 非 strict 模式建置：API 尚未上線時 SSG 頁面會降級，上線後由 ISR/revalidate 補資料
RUN mkdir -p public && npx next build

FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
RUN apk upgrade --no-cache \
    && rm -rf /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/corepack \
    && rm -f /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack \
    && addgroup -S nodejs \
    && adduser -S nextjs -G nodejs
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
