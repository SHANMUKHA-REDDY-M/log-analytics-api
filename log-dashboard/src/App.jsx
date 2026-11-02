import { useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, Info, XCircle } from "lucide-react";

const API_KEY = import.meta.env.VITE_API_KEY || "service-auth-xyz";
const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/api/v1/logs/ws/stats";

const colors = {
  DEBUG: "#94a3b8",
  INFO: "#3b82f6",
  WARN: "#f59e0b",
  ERROR: "#ef4444",
  FATAL: "#991b1b",
};

function App() {
  const [stats, setStats] = useState([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let socket;
    let retryTimer;
    let stopped = false;

    const connect = () => {
      socket = new WebSocket(`${WS_URL}?api_key=${encodeURIComponent(API_KEY)}`);
      socket.onopen = () => {
        setConnected(true);
        setError("");
      };
      socket.onmessage = (event) => setStats(JSON.parse(event.data));
      socket.onerror = () => setError("Live feed unavailable; retrying...");
      socket.onclose = () => {
        setConnected(false);
        if (!stopped) retryTimer = setTimeout(connect, 3000);
      };
    };

    connect();
    return () => {
      stopped = true;
      clearTimeout(retryTimer);
      socket?.close();
    };
  }, []);

  const totals = useMemo(
    () => Object.fromEntries(stats.map((item) => [item.severity, item.count])),
    [stats],
  );

  return (
    <main>
      <header>
        <div>
          <h1><Activity color="#60a5fa" /> Live Log Analytics</h1>
          <p>Redis Pub/Sub updates from the FastAPI ingestion pipeline</p>
        </div>
        <span className={connected ? "status connected" : "status"}>
          {connected ? "● Connected" : "○ Reconnecting"}
        </span>
      </header>
      {error && <div className="error">{error}</div>}
      <section className="cards">
        {[
          ["INFO", Info],
          ["WARN", AlertTriangle],
          ["ERROR", XCircle],
          ["FATAL", Activity],
        ].map(([severity, Icon]) => (
          <article key={severity} style={{ borderColor: colors[severity] }}>
            <Icon color={colors[severity]} />
            <span>{severity}</span>
            <strong>{(totals[severity] || 0).toLocaleString()}</strong>
          </article>
        ))}
      </section>
      <section className="table-card">
        <h2>Severity distribution</h2>
        {stats.length === 0 ? (
          <p>No logs have been ingested yet.</p>
        ) : (
          stats.map((item) => (
            <div className="bar-row" key={item.severity}>
              <span>{item.severity}</span>
              <div><i style={{ width: `${Math.min(item.count / Math.max(...stats.map((s) => s.count)) * 100, 100)}%`, background: colors[item.severity] }} /></div>
              <b>{item.count.toLocaleString()}</b>
            </div>
          ))
        )}
      </section>
    </main>
  );
}

export default App;
