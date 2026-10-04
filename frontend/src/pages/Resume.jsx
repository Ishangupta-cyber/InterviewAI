import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";

const List = ({ title, items }) =>
  items?.length ? (
    <div className="block">
      <h4>{title}</h4>
      <ul>{items.map((x, i) => <li key={i}>{x}</li>)}</ul>
    </div>
  ) : null;

export default function Resume() {
  const [list, setList] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const load = () => api("/resumes/").then(setList).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  async function upload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setErr(""); setBusy(true);
    const form = new FormData();
    form.append("file", file);
    try { await api("/resumes/", { method: "POST", form }); await load(); }
    catch (x) { setErr(x.message); }
    finally { setBusy(false); e.target.value = ""; }
  }

  const r = list[0];
  return (
    <div className="stack">
      <h2>Resume analysis</h2>
      <div className="card">
        <p className="muted">Upload a text-based PDF or DOCX. We extract your skills and projects, score ATS-friendliness, and use it to personalise your interview questions.</p>
        <input type="file" accept=".pdf,.docx" onChange={upload} disabled={busy} />
        {busy && <p className="muted">Analysing…</p>}
        {err && <div className="error">{err}</div>}
      </div>

      {r && (
        <div className="card">
          <div className="row between">
            <div>
              <h3>{r.name}</h3>
              <span className="muted">Analysed by {r.analysed_by === "llm" ? "Gemini" : "offline rules (no API key)"}</span>
            </div>
            <div className={"score " + (r.ats_score >= 70 ? "good" : r.ats_score >= 50 ? "mid" : "bad")}>
              {r.ats_score}<small>ATS</small>
            </div>
          </div>
          <div className="chips">{r.skills.map((s) => <span key={s} className="chip">{s}</span>)}</div>
          <div className="grid2">
            <List title="Education" items={r.education} />
            <List title="Experience" items={r.experience} />
            <List title="Projects" items={r.projects} />
            <List title="How to improve" items={r.suggestions} />
          </div>
          <Link className="btn" to="/interview">Start an interview with this resume →</Link>
        </div>
      )}
    </div>
  );
}
