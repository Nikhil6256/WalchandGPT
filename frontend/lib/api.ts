/**
 * API client for WalchandGPT backend.
 * All calls are authenticated with Bearer JWT tokens.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

function getAuthHeader(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || 'Request failed');
  }

  return res.json();
}

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: {
    name: string;
    email: string;
    password: string;
    role?: string;
    department?: string;
    year?: number;
  }) => request<any>('/api/auth/register', { method: 'POST', body: JSON.stringify(data) }),

  login: (email: string, password: string) =>
    request<any>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<any>('/api/auth/me'),
};

// ── Conversations ─────────────────────────────────────────────────────────────
export const conversationApi = {
  list: () => request<any>('/api/conversations'),
  create: (title?: string) =>
    request<any>('/api/conversations', {
      method: 'POST',
      body: JSON.stringify({ title: title || 'New Conversation' }),
    }),
  get: (id: string) => request<any>(`/api/conversations/${id}`),
  delete: (id: string) =>
    fetch(`${API_BASE}/api/conversations/${id}`, {
      method: 'DELETE',
      headers: getAuthHeader(),
    }),
};

// ── Documents ─────────────────────────────────────────────────────────────────
export const documentApi = {
  list: () => request<any>('/api/documents'),
  upload: (formData: FormData) =>
    fetch(`${API_BASE}/api/documents`, {
      method: 'POST',
      headers: getAuthHeader(),
      body: formData,
    }).then((r) => {
      if (!r.ok) throw new ApiError(r.status, 'Upload failed');
      return r.json();
    }),
  delete: (id: string) =>
    fetch(`${API_BASE}/api/documents/${id}`, {
      method: 'DELETE',
      headers: getAuthHeader(),
    }),
  reindex: (id: string) =>
    request<any>(`/api/documents/${id}/reindex`, { method: 'POST' }),
};

// ── Feedback ──────────────────────────────────────────────────────────────────
export const feedbackApi = {
  submit: (messageId: string, rating: 1 | -1, comment?: string) =>
    request<any>('/api/feedback', {
      method: 'POST',
      body: JSON.stringify({ message_id: messageId, rating, comment }),
    }),
};

// ── Admin ─────────────────────────────────────────────────────────────────────
export const adminApi = {
  analytics: () => request<any>('/api/admin/analytics'),
  toolLogs: (limit = 50, offset = 0) =>
    request<any>(`/api/admin/tool-logs?limit=${limit}&offset=${offset}`),
};

// ── Streaming chat ─────────────────────────────────────────────────────────────
export function streamChat(
  message: string,
  conversationId: string | null,
  onEvent: (type: string, data: Record<string, any>) => void,
  onError: (err: Error) => void
): () => void {
  const token = localStorage.getItem('access_token');
  if (!token) {
    onError(new Error('Not authenticated'));
    return () => {};
  }

  const controller = new AbortController();

  fetch(`${API_BASE}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message, conversation_id: conversationId }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Parse SSE frames
        const frames = buffer.split('\n\n');
        buffer = frames.pop() || '';

        for (const frame of frames) {
          const lines = frame.split('\n');
          let eventType = 'message';
          let dataStr = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) eventType = line.slice(7).trim();
            else if (line.startsWith('data: ')) dataStr = line.slice(6).trim();
          }

          if (dataStr) {
            try {
              const data = JSON.parse(dataStr);
              onEvent(eventType, data);
            } catch {
              // skip malformed frame
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError(err);
    });

  return () => controller.abort();
}

export { ApiError };
