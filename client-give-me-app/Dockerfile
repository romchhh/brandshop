# Base image
FROM node:18-alpine

ARG NEXT_PUBLIC_API_HOST=http://localhost:8000
# У Docker (docker-compose) — http://server:8000, щоб image optimizer діставав медіа з Django
ARG NEXT_PUBLIC_IMAGE_UPSTREAM=
ARG NEXT_PUBLIC_DEV=0
ENV NEXT_PUBLIC_API_HOST=$NEXT_PUBLIC_API_HOST
ENV NEXT_PUBLIC_IMAGE_UPSTREAM=$NEXT_PUBLIC_IMAGE_UPSTREAM
ENV NEXT_PUBLIC_DEV=$NEXT_PUBLIC_DEV

WORKDIR /app

# Кеш шару залежностей (менше повторних записів на диск при перезбірці)
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile --network-timeout 120000

COPY . .
RUN yarn build

# Expose the port for the React dev server
EXPOSE 3001

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]

# Start the React app
CMD ["yarn", "start"]
