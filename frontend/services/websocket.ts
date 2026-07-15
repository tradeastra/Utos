type EventHandler = (data: Record<string, unknown>) => void;

export class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: Map<string, Set<EventHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnect = 5;
  private reconnectDelay = 1000;

  constructor(url: string = 'ws://localhost:8000/ws') {
    this.url = url;
  }

  connect(token?: string) {
    const wsUrl = token ? `${this.url}?token=${token}` : this.url;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      console.log('[WS] Connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const handlers = this.handlers.get(msg.event_type);
        if (handlers) {
          handlers.forEach((h) => h(msg.data || msg));
        }
      } catch {
        console.error('[WS] Failed to parse message');
      }
    };

    this.ws.onclose = () => {
      console.log('[WS] Disconnected');
      if (this.reconnectAttempts < this.maxReconnect) {
        this.reconnectAttempts++;
        setTimeout(() => this.connect(token), this.reconnectDelay * this.reconnectAttempts);
      }
    };

    this.ws.onerror = () => {
      console.error('[WS] Error');
    };
  }

  subscribe(eventType: string, handler: EventHandler): () => void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set());
    }
    this.handlers.get(eventType)!.add(handler);
    return () => this.unsubscribe(eventType, handler);
  }

  unsubscribe(eventType: string, handler: EventHandler) {
    this.handlers.get(eventType)?.delete(handler);
  }

  send(data: unknown) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
  }
}

export const ws = new WebSocketService();
