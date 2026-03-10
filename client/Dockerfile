FROM node:20-slim AS base

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

FROM base AS build

# 1. Copy only lockfile first to fetch dependencies incrementally
COPY pnpm-lock.yaml /app/
WORKDIR /app
RUN pnpm fetch

# 2. Copy source code and install offline (using fetched packages in the pnpm store)
COPY . /app/
RUN pnpm install -r --offline

# 3. Build the frontend
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN pnpm run build

# 4. Serve static files
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80