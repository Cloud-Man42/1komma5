FROM node:20-alpine AS builder

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
ARG NEXT_PUBLIC_API_BASE_URL=http://backend:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_EMIC_USER_AUTH_ENABLED=false
ENV NEXT_PUBLIC_EMIC_USER_AUTH_ENABLED=$NEXT_PUBLIC_EMIC_USER_AUTH_ENABLED
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app
RUN apk add --no-cache wget
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
