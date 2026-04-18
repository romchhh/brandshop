# Base image
FROM node:18-alpine

ARG NEXT_PUBLIC_API_HOST=http://localhost:8000
# У Docker (docker-compose) — http://server:8000, щоб image optimizer діставав медіа з Django
ARG NEXT_PUBLIC_IMAGE_UPSTREAM=
# 1 = фото з /media/... на хості Next (volume server/media → public/media), без префікса API до URL
ARG NEXT_PUBLIC_MEDIA_SAME_ORIGIN=0
ARG NEXT_PUBLIC_DEV=0
ENV NEXT_PUBLIC_API_HOST=$NEXT_PUBLIC_API_HOST
ENV NEXT_PUBLIC_IMAGE_UPSTREAM=$NEXT_PUBLIC_IMAGE_UPSTREAM
ENV NEXT_PUBLIC_MEDIA_SAME_ORIGIN=$NEXT_PUBLIC_MEDIA_SAME_ORIGIN
ENV NEXT_PUBLIC_DEV=$NEXT_PUBLIC_DEV

WORKDIR /app

# Кеш шару залежностей (менше повторних записів на диск при перезбірці)
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile --network-timeout 120000

COPY . .
RUN mkdir -p public/media
RUN yarn build

# Expose the port for the React dev server
EXPOSE 3001

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]

# Start the React app
CMD ["yarn", "start"]
