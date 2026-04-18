const API_BASE = "http://localhost:8000";
const SESSION_KEY = "foodbridge_session_id";

export const getSessionId = (): string | null => localStorage.getItem(SESSION_KEY);
export const setSessionId = (id: string) => localStorage.setItem(SESSION_KEY, id);
export const clearSessionId = () => localStorage.removeItem(SESSION_KEY);

export interface ChatResponse {
  session_id: string;
  response: string;
}

export async function chat(message: string): Promise<ChatResponse> {
  const session_id = getSessionId();
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id }),
  });
  if (!res.ok) throw new Error(`Chat request failed (${res.status})`);
  const data = (await res.json()) as ChatResponse;
  if (data.session_id) setSessionId(data.session_id);
  return data;
}

export async function resetSession(): Promise<void> {
  const session_id = getSessionId();
  if (!session_id) return;
  try {
    await fetch(`${API_BASE}/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id }),
    });
  } finally {
    clearSessionId();
  }
}
