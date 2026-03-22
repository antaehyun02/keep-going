FROM node:20-slim

WORKDIR /app

COPY backend/package.json /app/package.json
RUN npm install --production

COPY backend/ /app/
COPY frontend/ /app/frontend/

ENV NODE_ENV=production \
    PORT=3000

EXPOSE 3000

CMD ["node", "src/server.js"]
