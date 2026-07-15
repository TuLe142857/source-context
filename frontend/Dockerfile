FROM node:24.18 AS base

FROM base AS dev
WORKDIR /app
COPY package*.json .
RUN npm install
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

