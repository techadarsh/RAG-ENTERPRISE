# Dockerfile for Next.js frontend (ui)
# - Multi-stage build for minimal image size
# - Uses Node 20 official image
# - NODE_ENV=production for runtime

FROM node:20 AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM deps AS build
COPY . .
RUN npm run build

FROM node:20 AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app .
EXPOSE 3000
CMD ["npx", "next", "start"]
