FROM node:20-alpine

WORKDIR /app

RUN npm install -g pnpm

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install

# Copy source code
COPY . .

# Expose Vite's default port
EXPOSE 5173

# Run in dev mode with host binding
CMD ["pnpm", "dev", "--host"]
