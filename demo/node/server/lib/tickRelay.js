import { WebSocket, WebSocketServer } from "ws";

const STREAM_WS_URL = process.env.STREAM_WS_URL || "ws://localhost:8765";
const RECONNECT_DELAY_MS = 3000;

/**
 * Relays bdshare-stream's WebSocket broadcast to browser clients connected
 * to our own /ws/ticks endpoint, so the browser only ever talks to this
 * Node server (single origin) rather than connecting to bdshare-stream
 * directly.
 */
export function attachTickRelay(httpServer, path = "/ws/ticks") {
  const wss = new WebSocketServer({ server: httpServer, path });
  let latestMessage = null;

  wss.on("connection", (client) => {
    if (latestMessage) client.send(latestMessage);
  });

  function broadcast(message) {
    latestMessage = message;
    for (const client of wss.clients) {
      if (client.readyState === WebSocket.OPEN) client.send(message);
    }
  }

  function connectUpstream() {
    const upstream = new WebSocket(STREAM_WS_URL);
    upstream.on("message", (data) => broadcast(data.toString()));
    upstream.on("error", () => upstream.close());
    upstream.on("close", () => setTimeout(connectUpstream, RECONNECT_DELAY_MS));
  }

  connectUpstream();
  return wss;
}
