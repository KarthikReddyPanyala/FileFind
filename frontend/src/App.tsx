import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

interface Source {
  name: string;
  path: string;
  date_modified: string;
}

interface Message {
  role: "user" | "agent";
  content: string;
  sources?: Source[];
}

function App() {
  const [savedFolders, setSavedFolders] = useState<string[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [folderPath, setFolderPath] = useState("");
  const [indexStatus, setIndexStatus] = useState("");
  const [view, setView] = useState<"chat" | "scope">("chat");
  const [controller, setController] = useState<AbortController | null>(null);

  useEffect(() => {
    loadFolders();
  }, []);

  async function loadFolders() {
    const response = await fetch("http://127.0.0.1:8000/folders");
    const data = await response.json();
    setSavedFolders(data.folders);
  }

  async function removeFolder(folder: string) {
    await fetch("http://127.0.0.1:8000/folders/remove", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder_path: folder }),
    });
    loadFolders();
  }

  async function handleAsk() {
    if (!question.trim() || loading) return;
    const userMessage = question;
    setQuestion("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    const abortController = new AbortController();
    setController(abortController);

    try {
      const response = await fetch("http://127.0.0.1:8000/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: userMessage,
          history: messages.map(m => ({
            role: m.role === "agent" ? "assistant" : "user",
            content: m.content
          }))
        }),
        signal: abortController.signal,
      });

      const data = await response.json();
      const fullAnswer = data.answer;
      const words = fullAnswer.split(" ");

      setMessages(prev => [...prev, { role: "agent", content: "", sources: data.sources }]);

      for (let i = 0; i < words.length; i++) {
        if (abortController.signal.aborted) break;
        await new Promise(res => setTimeout(res, 40));
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: words.slice(0, i + 1).join(" ")
          };
          return updated;
        });
      }
    } catch (e: any) {
      if (e.name === "AbortError") {
        setMessages(prev => [...prev, { role: "agent", content: "Stopped.", sources: [] }]);
      }
    }

    setLoading(false);
    setController(null);
  }

  function handleStop() {
    if (controller) controller.abort();
  }

  async function handleIndex() {
    if (!folderPath.trim()) return;
    setIndexStatus("Indexing...");
    const response = await fetch("http://127.0.0.1:8000/index", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder_path: folderPath }),
    });
    const data = await response.json();
    setIndexStatus(`✓ Indexed ${data.indexed} of ${data.total} files`);
  }

  async function openFile(path: string) {
    await invoke("open_file", { path });
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="logo">
          <span className="logo-text">FileFind</span>
          <span className="logo-dot">.</span>
        </div>
        <nav>
          <button
            className={`nav-btn ${view === "chat" ? "active" : ""}`}
            onClick={() => setView("chat")}
          >
            ⌬ Agent
          </button>
          <button
            className={`nav-btn ${view === "scope" ? "active" : ""}`}
            onClick={() => setView("scope")}
          >
            ◈ Scope
          </button>
        </nav>
        <div className="sidebar-footer">
          <span className="status-dot"></span>
          <span className="status-text">Local · Private</span>
        </div>
      </aside>

      <main className="main">
        {view === "chat" && (
          <div className="chat-view">
            <div className="messages">
              {messages.length === 0 && (
                <div className="empty-state">
                  <div className="empty-icon">⌬</div>
                  <div className="empty-title">Ask anything about your files</div>
                  <div className="empty-sub">The agent reads and reasons over your documents locally</div>
                  <div className="suggestions">
                    <div className="suggestion" onClick={() => setQuestion("Which resume is best for a data science role?")}>Which resume is best for a data science role?</div>
                    <div className="suggestion" onClick={() => setQuestion("Summarize my most recent document")}>Summarize my most recent document</div>
                    <div className="suggestion" onClick={() => setQuestion("What skills do I have across all my files?")}>What skills do I have across all my files?</div>
                  </div>
                </div>
              )}
              {messages.map((msg, i) => (
                <div key={i} className={`message ${msg.role}`}>
                  <div className="message-label">{msg.role === "user" ? "YOU" : "AGENT"}</div>
                  <div className="message-content">{msg.content}</div>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="sources">
                      <div className="sources-label">Best Match</div>
                      <div className="source-chip best" onClick={() => openFile(msg.sources![0].path)}>
                        ↗ {msg.sources[0].name}
                      </div>
                      {msg.sources.length > 1 && (
                        <>
                          <div className="sources-label" style={{ marginTop: "12px" }}>Other Sources</div>
                          {msg.sources.slice(1).map((src, j) => (
                            <div key={j} className="source-chip" onClick={() => openFile(src.path)}>
                              ↗ {src.name}
                            </div>
                          ))}
                        </>
                      )}
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="message agent">
                  <div className="message-label">AGENT</div>
                  <div className="thinking">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              )}
            </div>
            <div className="input-area">
              <input
                type="text"
                placeholder="Ask anything about your files..."
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAsk()}
                disabled={loading}
              />
              {loading ? (
                <button onClick={handleStop} className="stop-btn">■ Stop</button>
              ) : (
                <button onClick={handleAsk}>→</button>
              )}
            </div>
          </div>
        )}

        {view === "scope" && (
          <div className="scope-view">
            <h2>Agent Scope</h2>
            <p className="scope-desc">Define which folders the agent is allowed to access and index.</p>
            <div className="scope-input-row">
              <input
                type="text"
                placeholder="Folder path e.g. C:\Users\karth\Documents"
                value={folderPath}
                onChange={(e) => setFolderPath(e.target.value)}
              />
              <button onClick={async () => { await handleIndex(); loadFolders(); }}>Add & Index</button>
            </div>
            {indexStatus && <div className="status">{indexStatus}</div>}

            {savedFolders.length > 0 && (
              <div className="folder-list">
                <div className="sources-label" style={{ marginBottom: "12px" }}>Indexed Folders</div>
                {savedFolders.map((folder, i) => (
                  <div key={i} className="folder-item">
                    <span className="folder-path">{folder}</span>
                    <button className="remove-btn" onClick={() => removeFolder(folder)}>✕</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;