// Derives the WebSocket URL for the chat tutor from the REST API base.
const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

export function chatWsUrl(): string {
  return BASE.replace(/^http/, "ws") + "/chat/ws";
}
