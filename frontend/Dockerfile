FROM node:20-alpine

WORKDIR /app

COPY package.json /app/package.json
RUN npm install --legacy-peer-deps

COPY src /app/src
COPY tsconfig.json /app/tsconfig.json
COPY next.config.mjs /app/next.config.mjs

EXPOSE 3000
CMD ["npm", "run", "dev"]