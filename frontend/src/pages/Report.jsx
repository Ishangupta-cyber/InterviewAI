import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";

export default function Report() {
  const { id } = useParams();
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    api(`/sessions/${id}/`).then(async (x) => {
      if (!x.report && x.session.answered) await api(`/sessions/${id}/finish/`, { method: "POST" }).then(async () => setD(await api(`/sessions/${id}/`)));
      else setD(x);
    }).catch((e) => setErr(e.message));
  }, [id]);

  if (err) return <div className="error">{err}</div>;
  if (!d) return <p className="muted">Loading…</p>;
  const r = d.report;
  if (!r) return <p className="muted">No answers recorded for this interview. <Link to="/interview">Start another</Link></p>;

  return (
    <div className="stack">
      <div className="row between">
        <h2>Interview report</h2>
        <Link className="btn alt" to="/interview">New interview</Link>
      </div>
      <div className="card">
        <div className="row between">
          <div><h3>{d.session.role}</h3><span className="muted">{d.session.interview_type} · {d.session.answered} answers</span></div>
          <div className={"score " + (r.total_score >= 70 ? "good" : r.total_score >= 50 ? "mid" : "bad")}>{r.total_score}<small>overall</small></div>
        </div>
        <div className="grid2">
          <div className="block"><h4>Strengths</h4><ul>{r.strengths.length ? r.strengths.map((s) => <li key={s}>{s}</li>) : <li className="muted">None above 70 yet</li>}</ul></div>
          <div className="block"><h4>Needs work</h4><ul>{r.weaknesses.length ? r.weaknesses.map((s) => <li key={s}>{s}</li>) : <li className="muted">Nothing below 60</li>}</ul></div>
        </div>
        <div className="block"><h4>Suggestions</h4><ul>{r.suggestions.map((s, i) => <li key={i}>{s}</li>)}</ul></div>
      </div>

      {r.roadmap?.focus_areas?.length > 0 && (
        <div className="card">
          <div className="row between">
            <h3>Your improvement roadmap</h3>
            <span className="muted small">{r.roadmap.source === "llm" ? "Written by Gemini from your scores" : "Rule-based plan from your scores"}</span>
          </div>
          {r.roadmap.summary && <p>{r.roadmap.summary}</p>}
          <div className="grid2">
            {r.roadmap.focus_areas.map((a, i) => (
              <div key={i} className="block">
                <h4>{a.area}</h4>
                {a.why && <p className="muted small">{a.why}</p>}
                <ul>{a.actions.map((x, j) => <li key={j}>{x}</li>)}</ul>
                {a.practice_resources?.length > 0 && <p className="muted small">Practise with: {a.practice_resources.join(", ")}</p>}
              </div>
            ))}
          </div>
          {r.roadmap.next_session_goal && <p className="note">Goal for your next session: {r.roadmap.next_session_goal}</p>}
        </div>
      )}

      <h3>Question by question</h3>
      {d.answers.map((a, i) => (
        <div key={i} className="card">
          <div className="row between">
            <b>{i + 1}. {a.question.text}</b>
            <span className="score small-score">{a.result.fusion.overall_score}</span>
          </div>
          <p className="muted">{a.transcript}</p>
        </div>
      ))}
    </div>
  );
}
