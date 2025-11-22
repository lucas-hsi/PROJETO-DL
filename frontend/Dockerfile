# ========== BUILDER ==========
FROM node:18-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# ========== RUNNER ==========
FROM node:18-alpine
WORKDIR /app

COPY --from=builder /app ./

EXPOSE 3000
ENV PORT=3000
ENV HOST=0.0.0.0

CMD ["npm", "start"]