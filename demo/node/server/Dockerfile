# Self-contained — the Node app never imports bdshare itself, only talks to
# the other services over HTTP/WebSocket, so this context is just this
# directory (not the repo root like the Python service Dockerfiles).
#   docker build -f demo/node/server/Dockerfile -t bdshare-node-demo demo/node/server
FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm install --omit=dev

COPY . .

EXPOSE 3000

CMD ["node", "server.js"]
