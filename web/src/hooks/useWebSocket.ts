"use client";

import { getAccessToken } from "@/lib/auth/store";
import { useCallback, useEffect, useRef, useState } from "react";

export type WebSocketStatus = "connecting" | "open" | "closed" | "error";

export interface WebSocketMessage<T = unknown> {
  type: string;
  payload: T;
  ts: string;
}

export interface UseWebSocketOptions {
  url?: string;
  reconnect?: boolean;
  reconnectIntervalMs?: number;
  maxReconnectAttempts?: number;
  onMessage?: (message: WebSocketMessage) => void;
  onStatusChange?: (status: WebSocketStatus) => void;
  auth?: boolean;
}

const DEFAULT_WS = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/events";

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    url = DEFAULT_WS,
    reconnect = true,
    reconnectIntervalMs = 4000,
    maxReconnectAttempts = 10,
    onMessage,
    onStatusChange,
    auth = true,
  } = options;

  const [status, setStatus] = useState<WebSocketStatus>("connecting");
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const socketRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  const onStatusRef = useRef(onStatusChange);
  onMessageRef.current = onMessage;
  onStatusRef.current = onStatusChange;

  const setStatusSafe = useCallback((next: WebSocketStatus) => {
    setStatus(next);
    onStatusRef.current?.(next);
  }, []);

  const connect = useCallback(() => {
    if (typeof window === "undefined") return;
    setStatusSafe("connecting");

    let wsUrl = url;
    if (auth) {
      const token = getAccessToken();
      if (token) wsUrl = `${url}?token=${encodeURIComponent(token)}`;
    }

    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      setReconnectAttempt(0);
      setStatusSafe("open");
    };

    socket.onclose = () => {
      setStatusSafe("closed");
      if (reconnect && reconnectAttempt < maxReconnectAttempts) {
        window.setTimeout(() => {
          setReconnectAttempt((n) => n + 1);
          connect();
        }, reconnectIntervalMs);
      }
    };

    socket.onerror = () => setStatusSafe("error");

    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as WebSocketMessage;
        setLastMessage(parsed);
        onMessageRef.current?.(parsed);
      } catch {
        /* ignore malformed frames */
      }
    };
  }, [
    auth,
    maxReconnectAttempts,
    reconnect,
    reconnectAttempt,
    reconnectIntervalMs,
    setStatusSafe,
    url,
  ]);

  useEffect(() => {
    connect();
    return () => {
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [connect]);

  const send = useCallback((message: WebSocketMessage) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
    }
  }, []);

  return { status, lastMessage, send, reconnect: connect, reconnectAttempt };
}
