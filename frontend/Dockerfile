# Frontend Docker image for Narrative.Rx — multi-stage build
# Stage 1: build React app
FROM node:20-alpine AS builder

WORKDIR /app

# Enable corepack so we can use yarn out of the box
RUN corepack enable

# Install deps first for better layer caching.
# The workflow guarantees yarn.lock exists before build (creating an empty
# placeholder if the repo push omitted it), so a plain COPY is safe here.
COPY package.json yarn.lock ./
RUN yarn install --network-timeout 600000

# Copy source
COPY . .

# Empty backend URL — nginx proxies /api to backend on the same origin,
# so the React bundle uses relative /api paths.
ENV REACT_APP_BACKEND_URL=""
RUN yarn build

# Stage 2: serve with nginx + reverse-proxy /api -> backend
FROM nginx:alpine

# nginx config with reverse proxy + SPA fallback
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/build /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
