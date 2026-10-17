FROM node:22.22.0-alpine
WORKDIR /app
COPY services/game-runtime/package*.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY services/game-runtime/src ./src
USER node
EXPOSE 2567
CMD ["node", "src/index.js"]
