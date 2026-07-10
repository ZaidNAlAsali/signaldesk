import type {
  Analysis,
  Analytics,
  AuditEvent,
  AuditVerification,
  DecisionInput,
  NewCaseInput,
  OpsCase,
} from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Request failed" }));
    const detail = body.detail;
    const message = typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail.map((item) => item?.msg ?? "Invalid input").join("; ")
        : `Request failed with HTTP ${response.status}`;
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export const api = {
  listCases: () => request<OpsCase[]>("/api/cases"),
  getAnalytics: () => request<Analytics>("/api/analytics"),
  getAudit: (id: string) => request<AuditEvent[]>(`/api/cases/${id}/audit`),
  verifyAudit: (id: string) => request<AuditVerification>(`/api/cases/${id}/audit/verify`),
  createCase: (input: NewCaseInput) =>
    request<OpsCase>("/api/cases", { method: "POST", body: JSON.stringify(input) }),
  analyzeCase: (caseId: string) =>
    request<Analysis>(`/api/cases/${caseId}/analyze`, { method: "POST" }),
  decideCase: (caseId: string, input: DecisionInput) =>
    request(`/api/cases/${caseId}/decision`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
};

export function websocketUrl(): string {
  const url = new URL(API_URL);
  const protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${url.host}/ws/events`;
}
