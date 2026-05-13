import type { Assistant, ChatEvent, ContactListItem } from "@/types/chat";

async function httpGet<T>(path: string): Promise<T> {
  const r = await fetch(path, { method: "GET", cache: "no-store" });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || `HTTP ${r.status}`);
  }
  return (await r.json()) as T;
}

async function httpPost<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || `HTTP ${r.status}`);
  }
  return (await r.json()) as T;
}

async function httpPut<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || `HTTP ${r.status}`);
  }
  return (await r.json()) as T;
}

export async function fetchContacts(params?: { q?: string; limit?: number }): Promise<ContactListItem[]> {
  const sp = new URLSearchParams();
  if (params?.q) sp.set("q", params.q);
  if (params?.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  const data = await httpGet<{ data: ContactListItem[] }>(`/api/contacts${qs ? `?${qs}` : ""}`);
  return data.data;
}

export async function fetchEvents(contactId: string, limit = 200): Promise<ChatEvent[]> {
  try {
    const data = await httpGet<{ data: ChatEvent[] }>(
      `/api/contacts/${encodeURIComponent(contactId)}/messages?limit=${limit}`
    );
    return data.data;
  } catch {
    const data = await httpGet<{ data: ChatEvent[] }>(
      `/api/contacts/${encodeURIComponent(contactId)}/events?limit=${limit}`
    );
    return data.data;
  }
}

export async function fetchCandidates(contactId: string, limit = 5): Promise<string[]> {
  const data = await httpGet<{ data: string[] }>(
    `/api/contacts/${encodeURIComponent(contactId)}/candidates?limit=${limit}`
  );
  return data.data;
}

export async function fetchAssistants(): Promise<Assistant[]> {
  const data = await httpGet<{ data: Assistant[] }>("/api/assistants");
  return data.data;
}

export async function createAssistant(input: Pick<Assistant, "name" | "system_prompt">): Promise<Assistant> {
  const data = await httpPost<{ data: Assistant }>("/api/assistants", {
    role_id: "",
    name: input.name,
    system_prompt: input.system_prompt,
  });
  return data.data;
}

export async function fetchSelectedAssistant(contactId: string): Promise<{ role_id: string | null; assistant: Assistant | null }> {
  const data = await httpGet<{ data: { role_id: string | null; assistant: Assistant | null } }>(
    `/api/contacts/${encodeURIComponent(contactId)}/assistant`
  );
  return data.data;
}

export async function setSelectedAssistant(contactId: string, roleId: string): Promise<void> {
  await httpPut(`/api/contacts/${encodeURIComponent(contactId)}/assistant`, { role_id: roleId });
}

export async function generateCandidates(contactId: string): Promise<string[]> {
  const data = await httpPost<{ data: string[] }>(`/api/contacts/${encodeURIComponent(contactId)}/candidates/generate`);
  return data.data;
}
