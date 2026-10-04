import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, auth } from "../api.js";

export default function Login() {
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ name: "", email: "", phone: "", password: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      const data = await api(mode === "login" ? "/auth/login/" : "/auth/register/", { method: "POST", body: f });
      auth.set(data);
      nav("/dashboard");
    } catch (x) { setErr(x.message); } finally { setBusy(false); }
  }

  return (
    <div className="auth">
      <form className="card" onSubmit={submit}>
        <h1 className="brand big">Interview<b>AI</b></h1>
        <p className="muted">AI-based interview preparation &amp; assessment</p>
        {mode === "register" && (
          <>
            <label>Name<input value={f.name} onChange={set("name")} required /></label>
            <label>Phone<input value={f.phone} onChange={set("phone")} /></label>
          </>
        )}
        <label>Email<input type="email" value={f.email} onChange={set("email")} required /></label>
        <label>Password<input type="password" value={f.password} onChange={set("password")} minLength={8} required /></label>
        {err && <div className="error">{err}</div>}
        <button className="btn" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}</button>
        <button type="button" className="link" onClick={() => { setMode(mode === "login" ? "register" : "login"); setErr(""); }}>
          {mode === "login" ? "New here? Create an account" : "Have an account? Log in"}
        </button>
      </form>
    </div>
  );
}
