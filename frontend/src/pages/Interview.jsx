import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";

function Setup() {
  const nav = useNavigate();
  const [resumes, setResumes] = useState([]);
  const [f, setF] = useState({ resume_id: "", interview_type: "mixed", role: "Software Engineer", num_questions: 6 });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => {
    api("/resumes/").then((r) => { setResumes(r); if (r[0]) setF((x) => ({ ...x, resume_id: r[0].id })); });
  }, []);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function start(e) {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      const d = await api("/sessions/", { method: "POST", body: { ...f, resume_id: f.resume_id || null } });
      nav(`/interview/${d.session.id}`);
    } catch (x) { setErr(x.message); setBusy(false); }
  }

  return (
    <div className="stack">
      <h2>New interview</h2>
      <form className="card" onSubmit={start}>
        <label>Resume
          <select value={f.resume_id} onChange={set("resume_id")}>
            <option value="">None (generic questions)</option>
            {resumes.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </label>
        {!resumes.length && <p className="muted">No resume yet — <Link to="/resume">upload one</Link> for personalised questions.</p>}
        <label>Target role<input value={f.role} onChange={set("role")} /></label>
        <label>Type
          <select value={f.interview_type} onChange={set("interview_type")}>
            <option value="mixed">Technical + HR</option><option value="technical">Technical</option><option value="hr">HR</option>
          </select>
        </label>
        <label>Number of questions<input type="number" min="3" max="10" value={f.num_questions} onChange={set("num_questions")} /></label>
        {err && <div className="error">{err}</div>}
        <button className="btn" disabled={busy}>{busy ? "Generating questions…" : "Start interview"}</button>
      </form>
    </div>
  );
}

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;

function Room({ id }) {
  const nav = useNavigate();
  const [q, setQ] = useState(null);
  const [text, setText] = useState("");
  const [feedback, setFeedback] = useState(null);
  const [listening, setListening] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(0);
  const started = useRef(Date.now());
  const rec = useRef(null);

  useEffect(() => {
    api(`/sessions/${id}/`).then((d) => {
      if (d.session.status === "completed") return nav(`/report/${id}`, { replace: true });
      setQ(d.current_question); setDone(d.session.answered);
    }).catch((e) => setErr(e.message));
    return () => { window.speechSynthesis?.cancel(); rec.current?.stop(); };
  }, [id]);

  useEffect(() => {  // read each new question aloud
    if (!q || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(q.text));
    started.current = Date.now();
  }, [q?.id]);

  function toggleMic() {
    if (listening) { rec.current?.stop(); return; }
    const r = new SR();
    r.continuous = true; r.interimResults = false; r.lang = "en-US";
    const base = text ? text + " " : "";
    r.onresult = (e) => setText(base + Array.from(e.results).map((x) => x[0].transcript).join(" "));
    r.onend = () => setListening(false);
    r.onerror = () => setListening(false);
    rec.current = r; r.start(); setListening(true);
  }

  async function submit() {
    rec.current?.stop();
    setErr(""); setBusy(true);
    try {
      const d = await api(`/sessions/${id}/answer/`, {
        method: "POST", body: { transcript: text, duration_sec: Math.round((Date.now() - started.current) / 1000) },
      });
      setFeedback(d); setDone(d.answered); setText("");
    } catch (x) { setErr(x.message); } finally { setBusy(false); }
  }

  function next() {
    if (!feedback.next_question) return nav(`/report/${id}`);
    setQ(feedback.next_question); setFeedback(null);
  }

  async function endEarly() {
    try { await api(`/sessions/${id}/finish/`, { method: "POST" }); nav(`/report/${id}`); }
    catch (x) { setErr(x.message); }
  }

  if (err && !q) return <div className="error">{err}</div>;
  if (!q) return <p className="muted">Loading…</p>;

  if (feedback) {
    const f = feedback.result.fusion;
    return (
      <div className="stack">
        <div className="card">
          <div className="row between">
            <h3>Feedback</h3>
            <div className={"score " + (f.overall_score >= 70 ? "good" : f.overall_score >= 50 ? "mid" : "bad")}>{f.overall_score}<small>{f.verdict}</small></div>
          </div>
          <p>{f.summary}</p>
          {feedback.result.modules.map((m) => (
            <div key={m.module_id} className="block">
              <div className="row between"><b>{m.name}</b><span>{m.score}</span></div>
              <div className="bar"><i style={{ width: m.score + "%" }} /></div>
              {m.notes.map((n, i) => <p key={i} className="muted small">{n}</p>)}
            </div>
          ))}
          {!feedback.result.guard.passed && feedback.result.guard.flags.map((x, i) => <div key={i} className="error">{x}</div>)}
          {feedback.next_question?.kind === "follow-up probe" && <p className="note">Next is a follow-up: {feedback.next_question.reason}</p>}
          <button className="btn" onClick={next}>{feedback.next_question ? "Next question →" : "View report →"}</button>
        </div>
      </div>
    );
  }

  return (
    <div className="stack">
      <div className="row between">
        <h2>Interview</h2>
        <span className="muted">{done} answered · <button className="link" onClick={endEarly}>End &amp; get report</button></span>
      </div>
      <div className="card">
        <div className="chips">
          <span className="chip">{q.category}</span><span className="chip">{q.difficulty}</span>
          {q.kind === "follow-up probe" && <span className="chip warn">follow-up</span>}
        </div>
        <p className="question">{q.text}</p>
        <button className="link" onClick={() => { window.speechSynthesis?.cancel(); window.speechSynthesis?.speak(new SpeechSynthesisUtterance(q.text)); }}>🔊 Replay question</button>
        <textarea rows={7} placeholder={SR ? "Click the mic and speak, or type your answer…" : "Type your answer (voice input needs Chrome/Edge)…"}
          value={text} onChange={(e) => setText(e.target.value)} />
        {err && <div className="error">{err}</div>}
        <div className="row">
          {SR && <button className={"btn alt" + (listening ? " rec" : "")} onClick={toggleMic}>{listening ? "■ Stop recording" : "🎤 Speak answer"}</button>}
          <button className="btn" disabled={busy || !text.trim()} onClick={submit}>{busy ? "Evaluating…" : "Submit answer"}</button>
        </div>
      </div>
    </div>
  );
}

export default function Interview() {
  const { id } = useParams();
  return id ? <Room id={id} key={id} /> : <Setup />;
}
