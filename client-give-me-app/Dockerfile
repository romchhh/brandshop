# syntax=docker/dockerfile:1
# Multi-stage: менший фінальний образ, швидший deploy після build

FROM node:18-alpine AS deps
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile --network-timeout 120000

FROM node:18-alpine AS builder
WORKDIR /app

ARG NEXT_PUBLIC_API_HOST=http://localhost:8000
ARG NEXT_PUBLIC_IMAGE_UPSTREAM=
ARG NEXT_PUBLIC_MEDIA_SAME_ORIGIN=0
ARG NEXT_PUBLIC_DEV=0
ENV NEXT_PUBLIC_API_HOST=$NEXT_PUBLIC_API_HOST \
    NEXT_PUBLIC_IMAGE_UPSTREAM=$NEXT_PUBLIC_IMAGE_UPSTREAM \
    NEXT_PUBLIC_MEDIA_SAME_ORIGIN=$NEXT_PUBLIC_MEDIA_SAME_ORIGIN \
    NEXT_PUBLIC_DEV=$NEXT_PUBLIC_DEV \
    NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN mkdir -p public/media && yarn build

FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3001

# standalone + static + public (медіа volume монтується в public/media)
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh && mkdir -p /app/public/media

EXPOSE 3001

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["node", "server.js"]
