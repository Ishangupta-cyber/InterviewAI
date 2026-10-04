import { Navigate, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { auth } from "./api.js";
import Login from "./pages/Login.jsx";
import Resume from "./pages/Resume.jsx";
import Interview from "./pages/Interview.jsx";
import Report from "./pages/Report.jsx";
import Dashboard from "./pages/Dashboard.jsx";

function Protected({ children }) {
  const a = auth.get();
  const nav = useNavigate();
  if (!a?.access) return <Navigate to="/login" replace />;
  const logout = () => { auth.clear(); nav("/login"); };
  return (
    <>
      <header className="nav">
        <span className="brand">Interview<b>AI</b></span>
        <nav>
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/resume">Resume</NavLink>
          <NavLink to="/interview">Interview</NavLink>
        </nav>
        <span className="who">{a.user?.name}<button className="link" onClick={logout}>Log out</button></span>
      </header>
      <main>{children}</main>
    </>
  );
}

export default function App() {
  const p = (el) => <Protected>{el}</Protected>;
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={p(<Dashboard />)} />
      <Route path="/resume" element={p(<Resume />)} />
      <Route path="/interview" element={p(<Interview />)} />
      <Route path="/interview/:id" element={p(<Interview />)} />
      <Route path="/report/:id" element={p(<Report />)} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
