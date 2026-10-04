// Tiny fetch wrapper: attaches the JWT, refreshes it once on 401, throws Error(message) on failure.
const KEY = "interviewai.auth";

export const auth = {
  get: () => { try { return JSON.parse(localStorage.getItem(KEY)); } catch { return null; } },
  set: (v) => localStorage.setItem(KEY, JSON.stringify(v)),
  clear: () => localStorage.removeItem(KEY),
};

async function refresh() {
  const a = auth.get();
  if (!a?.refresh) return false;
  const r = await fetch("/api/auth/refresh/", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: a.refresh }),
  });
  if (!r.ok) return false;
  auth.set({ ...a, access: (await r.json()).access });
  return true;
}

export async function api(path, { method = "GET", body, form } = {}, retried = false) {
  const headers = {};
  const a = auth.get();
  if (a?.access) headers.Authorization = `Bearer ${a.access}`;
  if (body) headers["Content-Type"] = "application/json";
  const r = await fetch("/api" + path, { method, headers, body: form || (body ? JSON.stringify(body) : undefined) });
  if (r.status === 401 && a && !retried && path !== "/auth/login/") {
    if (await refresh()) return api(path, { method, body, form }, true);
    auth.clear();
    window.location.href = "/login";
    throw new Error("Session expired");
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || data.detail || `Request failed (${r.status})`);
  return data;
}
