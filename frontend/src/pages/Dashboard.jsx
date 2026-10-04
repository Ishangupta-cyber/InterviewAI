import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";

const Stat = ({ label, value }) => <div className="stat"><b>{value ?? "—"}</b><span>{label}</span></div>;

export default function Dashboard() {
  const [d, setD] = useState(null);
  const [history, setHistory] = useState([]);
  const [err, setErr] = useState("");
  useEffect(() => {
    api("/dashboard/").then(setD).catch((e) => setErr(e.message));
    api("/sessions/").then(setHistory).catch(() => {});
  }, []);

  if (err) return <div className="error">{err}</div>;
  if (!d) return <p className="muted">Loading…</p>;

  return (
    <div className="stack">
      <div className="row between">
        <h2>Your progress</h2>
        <Link className="btn" to="/interview">Start interview</Link>
      </div>
      <div className="stats">
        <Stat label="Interviews" value={d.total_interviews} />
        <Stat label="Completed" value={d.completed} />
        <Stat label="Average score" value={d.completed ? d.avg_score : null} />
        <Stat label="Best score" value={d.completed ? d.best_score : null} />
        <Stat label="Resume ATS" value={d.resume_ats} />
      </div>

      {d.completed === 0 ? (
        <div className="card"><p>No completed interviews yet. <Link to="/resume">Upload your resume</Link>, then start a mock interview to see your analytics here.</p></div>
      ) : (
        <div className="grid2">
          <div className="card">
            <h4>Score trend</h4>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={d.trend.map((t, i) => ({ ...t, n: `#${i + 1}` }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" /><XAxis dataKey="n" /><YAxis domain={[0, 100]} /><Tooltip />
                <Line type="monotone" dataKey="score" stroke="#4f46e5" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="card">
            <h4>Performance by area</h4>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={d.topics} layout="vertical" margin={{ left: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" /><XAxis type="number" domain={[0, 100]} /><YAxis type="category" dataKey="name" width={130} /><Tooltip />
                <Bar dataKey="score" fill="#4f46e5" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {history.length > 0 && (
        <div className="card">
          <h4>History</h4>
          <table>
            <thead><tr><th>Date</th><th>Role</th><th>Type</th><th>Answered</th><th>Score</th><th /></tr></thead>
            <tbody>
              {history.map((s) => (
                <tr key={s.id}>
                  <td>{new Date(s.start_time).toLocaleDateString()}</td><td>{s.role}</td><td>{s.interview_type}</td>
                  <td>{s.answered}/{s.total_questions}</td><td>{s.total_score ?? "—"}</td>
                  <td><Link to={s.status === "completed" ? `/report/${s.id}` : `/interview/${s.id}`}>{s.status === "completed" ? "Report" : "Resume"}</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
