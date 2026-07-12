"use client";

import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bot,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleGauge,
  ClipboardCheck,

  FileLock2,
  FileText,
  Filter,
  Inbox,
  Languages,
  Plus,
  Radar,
  RefreshCw,
  Search,
  ServerCog,
  ShieldCheck,
  Sparkles,
  UserCheck,
  Wifi,
  WifiOff,
  X,
  XCircle,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { api, websocketUrl } from "@/lib/api";
import type {
  Analytics,
  AuditEvent,
  AuditVerification,
  Category,
  DecisionInput,
  NewCaseInput,
  OpsCase,
  Priority,
} from "@/lib/types";
import { categoryLabels, formatDate, priorityMeta, statusMeta, titleCase } from "@/lib/ui";

const EMPTY_ANALYTICS: Analytics = {
  total: 0,
  by_status: {},
  by_priority: {},
  by_category: {},
  high_risk_open: 0,
  average_confidence: 0,
};

const priorityOrder: Priority[] = ["critical", "high", "medium", "low"];
const categoryOrder: Category[] = ["incident", "access", "procurement", "compliance", "service", "other"];

type QueueFilter = "all" | "review" | "open" | "closed";

function SignalMark() {
  return (
    <span className="signal-mark" aria-hidden="true">
      <span />
      <span />
      <span />
    </span>
  );
}

function BriefStat({ index, icon, label, value, detail }: {
  index: string;
  icon: React.ReactNode;
  label: string;
  value: string | number;
  detail: string;
}) {
  return (
    <article className="brief-stat">
      <span className="brief-stat-index">{index}</span>
      <div className="brief-stat-icon">{icon}</div>
      <div><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>
    </article>
  );
}

function QueueRow({ item, selected, onSelect }: { item: OpsCase; selected: boolean; onSelect: () => void }) {
  const priority = item.priority ? priorityMeta[item.priority] : null;
  const status = statusMeta[item.status];

  return (
    <button aria-current={selected ? "true" : undefined} className={`queue-row ${selected ? "queue-row-selected" : ""}`} onClick={onSelect} type="button">
      <span className={`queue-priority-line priority-line-${item.priority ?? "none"}`} />
      <span className="queue-main">
        <span className="queue-topline">
          <code>{item.reference}</code>
          <span className={status.className}>{status.label}</span>
        </span>
        <strong dir={item.language === "ar" ? "rtl" : "ltr"}>{item.title}</strong>
        <span className="queue-meta">
          <span>{item.requester}</span>
          <span>{formatDate(item.updated_at)}</span>
        </span>
      </span>
      <span className="queue-trailing">
        {priority ? <span className={priority.className}>{priority.label}</span> : <span className="badge badge-untriaged">Untriaged</span>}
        <ChevronRight size={17} aria-hidden="true" />
      </span>
    </button>
  );
}

function AuditTimeline({ events }: { events: AuditEvent[] }) {
  if (!events.length) {
    return <p className="muted-copy">No decisions recorded yet.</p>;
  }

  return (
    <ol className="audit-list">
      {events.map((event) => (
        <li key={event.id}>
          <span className="audit-dot" />
          <div title={`SHA-256 ${event.event_hash}`}>
            <strong>#{event.sequence} · {titleCase(event.event_type)}</strong>
            <p>{event.actor}</p>
            <time>{formatDate(event.created_at)}</time>
          </div>
        </li>
      ))}
    </ol>
  );
}

function RiskMeter({ score }: { score: number }) {
  const band = score >= 85 ? "critical" : score >= 65 ? "high" : score >= 40 ? "medium" : "low";
  return (
    <div className={`risk-meter risk-meter-${band}`} aria-label={`Risk score ${score} out of 100`}>
      <span>Analysis risk</span>
      <div><strong>{score}</strong><small>/100</small></div>
    </div>
  );
}

function CaseWorkspace({
  item,
  audit,
  auditVerification,
  busy,
  onAnalyze,
  onDecide,
}: {
  item: OpsCase;
  audit: AuditEvent[];
  auditVerification: AuditVerification | null;
  busy: string | null;
  onAnalyze: () => Promise<void>;
  onDecide: (input: DecisionInput) => Promise<void>;
}) {
  const analysis = item.latest_analysis;
  const [note, setNote] = useState("");
  const [overridePriority, setOverridePriority] = useState<Priority>(item.priority ?? "medium");
  const [overrideCategory, setOverrideCategory] = useState<Category>(item.category ?? "other");
  const isPending = busy !== null;

  return (
    <section className="workspace-panel" aria-labelledby="case-title">
      <header className="workspace-header">
        <div>
          <div className="workspace-reference">
            <code>{item.reference}</code>
            <span className={statusMeta[item.status].className}>{statusMeta[item.status].label}</span>
          </div>
          <h2 id="case-title" dir={item.language === "ar" ? "rtl" : "ltr"}>{item.title}</h2>
          <p className="workspace-requester">
            Submitted by <strong>{item.requester}</strong> · {formatDate(item.created_at)}
          </p>
        </div>
        {analysis ? <RiskMeter score={analysis.risk_score} /> : <div className="untriaged-orb"><Radar size={24} /><span>Awaiting<br />analysis</span></div>}
      </header>

      <div className="workspace-scroll">
        <article className="request-card">
          <div className="section-heading compact-heading">
            <div>
              <span className="section-kicker">Original request</span>
              <h3>Submission context</h3>
            </div>
            <span className="language-pill"><Languages size={14} />{item.language.toUpperCase()}</span>
          </div>
          <p dir={item.language === "ar" ? "rtl" : "ltr"} className={item.language === "ar" ? "arabic-copy" : ""}>
            {item.description}
          </p>
        </article>

        {!analysis ? (
          <article className="analysis-empty">
            <div className="analysis-empty-icon"><Sparkles size={26} /></div>
            <div>
              <span className="section-kicker">Decision support</span>
              <h3>Turn the request into a reviewable decision</h3>
              <p>SignalDesk redacts common PII, retrieves relevant policy passages, and produces structured triage. It never approves its own recommendation.</p>
            </div>
            <button className="primary-button" disabled={isPending} onClick={() => void onAnalyze()} type="button">
              {busy === "analyze" ? <RefreshCw className="spin" size={17} /> : <Bot size={17} />}
              Analyze request
            </button>
          </article>
        ) : (
          <>
            <article className="analysis-card">
              <div className="analysis-banner">
                <div>
                  <span className="section-kicker">AI decision support</span>
                  <h3>Structured triage</h3>
                </div>
                <span className="provider-pill"><Bot size={14} />{analysis.provider}</span>
              </div>

              <div className="analysis-grid">
                <div>
                  <span className="field-label">Category</span>
                  <strong>{categoryLabels[analysis.category]}</strong>
                </div>
                <div>
                  <span className="field-label">Priority</span>
                  <span className={priorityMeta[analysis.priority].className}>{priorityMeta[analysis.priority].label}</span>
                </div>
                <div>
                  <span className="field-label">Confidence</span>
                  <strong>{Math.round(analysis.confidence * 100)}%</strong>
                </div>
              </div>

              <div className="analysis-copy">
                <span className="field-label">Summary</span>
                <p>{analysis.summary}</p>
              </div>
              <div className="analysis-copy">
                <span className="field-label">Rationale</span>
                <p>{analysis.rationale}</p>
              </div>
              <div className="recommended-action">
                <ArrowRight size={18} />
                <div><span className="field-label">Recommended next action</span><p>{analysis.recommended_action}</p></div>
              </div>

              {!!analysis.redactions.length && (
                <div className="redaction-note">
                  <FileLock2 size={17} />
                  <span>{analysis.redactions.length} sensitive value{analysis.redactions.length === 1 ? "" : "s"} redacted before analysis</span>
                </div>
              )}
            </article>

            <article className="policy-card" id="policies">
              <div className="section-heading compact-heading">
                <div><span className="section-kicker">Policy grounding</span><h3>Cited controls</h3></div>
                <ShieldCheck size={21} />
              </div>
              {analysis.citations.length ? (
                <div className="citation-list">
                  {analysis.citations.map((citation) => (
                    <div className="citation" key={citation.policy_slug}>
                      <FileText size={17} />
                      <div><strong>{citation.policy_title}</strong><p>{citation.excerpt}</p></div>
                      <span>{citation.score.toFixed(1)}</span>
                    </div>
                  ))}
                </div>
              ) : <p className="muted-copy">No policy passage cleared the relevance threshold.</p>}
            </article>

            {item.status === "analyzed" ? (
              <article className="decision-card">
                <div className="section-heading compact-heading">
                  <div><span className="section-kicker">Human control</span><h3>Review and decide</h3></div>
                  <UserCheck size={22} />
                </div>
                <label className="note-field">
                  <span>Decision note</span>
                  <textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Record what you verified or changed..." />
                </label>
                <div className="decision-actions">
                  <button className="approve-button" disabled={isPending} onClick={() => void onDecide({ action: "approve", actor: "Demo reviewer", note })} type="button">
                    <Check size={17} />Approve
                  </button>
                  <button className="reject-button" disabled={isPending} onClick={() => void onDecide({ action: "reject", actor: "Demo reviewer", note })} type="button">
                    <X size={17} />Reject
                  </button>
                </div>
                <div className="override-box">
                  <div><strong>Override recommendation</strong><p>Change the structured result while preserving the original analysis.</p></div>
                  <div className="override-controls">
                    <select aria-label="Override category" value={overrideCategory} onChange={(event) => setOverrideCategory(event.target.value as Category)}>
                      {categoryOrder.map((category) => <option value={category} key={category}>{categoryLabels[category]}</option>)}
                    </select>
                    <select aria-label="Override priority" value={overridePriority} onChange={(event) => setOverridePriority(event.target.value as Priority)}>
                      {priorityOrder.map((priority) => <option value={priority} key={priority}>{priorityMeta[priority].label}</option>)}
                    </select>
                    <button disabled={isPending} onClick={() => void onDecide({ action: "override", actor: "Demo reviewer", note, category: overrideCategory, priority: overridePriority })} type="button">
                      Apply override
                    </button>
                  </div>
                </div>
              </article>
            ) : (
              <div className="decision-complete">
                {item.status === "approved" ? <CheckCircle2 size={20} /> : <XCircle size={20} />}
                <div><strong>Human decision recorded</strong><p>This case is {statusMeta[item.status].label.toLowerCase()} and preserved in the audit trail.</p></div>
              </div>
            )}
          </>
        )}

        <article className="audit-card" id="audit">
          <div className="section-heading compact-heading">
            <div><span className="section-kicker">Tamper-evident history</span><h3>Audit trail</h3></div>
            {auditVerification && (
              <span className={`integrity-pill ${auditVerification.valid ? "integrity-valid" : "integrity-invalid"}`}>
                {auditVerification.valid ? <ShieldCheck size={14} /> : <AlertTriangle size={14} />}
                {auditVerification.valid ? `${auditVerification.event_count} events verified` : "Integrity check failed"}
              </span>
            )}
          </div>
          <AuditTimeline events={audit} />
        </article>
      </div>
    </section>
  );
}

function NewCaseModal({ onClose, onCreate, busy }: { onClose: () => void; onCreate: (input: NewCaseInput) => Promise<void>; busy: boolean }) {
  const [form, setForm] = useState<NewCaseInput>({ title: "", description: "", requester: "", language: "en" });

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [onClose]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onCreate(form);
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="new-case-title" onMouseDown={(event) => event.stopPropagation()}>
        <header><div><span className="section-kicker">Operations intake</span><h2 id="new-case-title">Create a request</h2></div><button className="icon-button" onClick={onClose} aria-label="Close dialog" type="button"><X size={19} /></button></header>
        <form onSubmit={(event) => void submit(event)}>
          <label><span>Title</span><input autoFocus dir={form.language === "ar" ? "rtl" : "ltr"} required minLength={4} maxLength={180} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="What needs attention?" /></label>
          <label><span>Description</span><textarea dir={form.language === "ar" ? "rtl" : "ltr"} required minLength={10} maxLength={6000} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="Include impact, timing, and the requested outcome." /></label>
          <div className="form-grid">
            <label><span>Requester</span><input dir={form.language === "ar" ? "rtl" : "ltr"} required minLength={2} value={form.requester} onChange={(event) => setForm({ ...form, requester: event.target.value })} placeholder="Team or person" /></label>
            <label><span>Language</span><select value={form.language} onChange={(event) => setForm({ ...form, language: event.target.value as "en" | "ar" })}><option value="en">English</option><option value="ar">Arabic</option></select></label>
          </div>
          <footer><button type="button" className="secondary-button" onClick={onClose}>Cancel</button><button type="submit" className="primary-button" disabled={busy}>{busy && <RefreshCw size={16} className="spin" />}Create request</button></footer>
        </form>
      </div>
    </div>
  );
}

export function Dashboard() {
  const [cases, setCases] = useState<OpsCase[]>([]);
  const [analytics, setAnalytics] = useState<Analytics>(EMPTY_ANALYTICS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [auditVerification, setAuditVerification] = useState<AuditVerification | null>(null);
  const [filter, setFilter] = useState<QueueFilter>("all");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);


  const loadDashboard = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const [nextCases, nextAnalytics] = await Promise.all([api.listCases(), api.getAnalytics()]);
      setCases(nextCases);
      setAnalytics(nextAnalytics);
      setSelectedId((current) => current && nextCases.some((item) => item.id === current) ? current : nextCases[0]?.id ?? null);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load SignalDesk");
    } finally {
      if (!quiet) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const initialLoad = window.setTimeout(() => void loadDashboard(), 0);
    return () => window.clearTimeout(initialLoad);
  }, [loadDashboard]);

  useEffect(() => {
    if (!selectedId) {
      return;
    }
    let cancelled = false;
    void Promise.all([api.getAudit(selectedId), api.verifyAudit(selectedId)])
      .then(([events, verification]) => {
        if (!cancelled) {
          setAudit(events);
          setAuditVerification(verification);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAudit([]);
          setAuditVerification(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId, cases]);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
    let closed = false;

    const connect = () => {
      socket = new WebSocket(websocketUrl());
      socket.onopen = () => {
        setConnected(true);
        heartbeatTimer = setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) socket.send("ping");
        }, 20000);
      };
      socket.onmessage = () => void loadDashboard(true);
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        setConnected(false);
        if (heartbeatTimer) clearInterval(heartbeatTimer);
        heartbeatTimer = null;
        if (!closed) reconnectTimer = setTimeout(connect, 3000);
      };
    };

    connect();
    return () => {
      closed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (heartbeatTimer) clearInterval(heartbeatTimer);
      socket?.close();
    };
  }, [loadDashboard]);

  const visibleCases = useMemo(() => cases.filter((item) => {
    const filterMatch = filter === "all"
      || (filter === "review" && item.status === "analyzed")
      || (filter === "open" && ["new", "analyzed"].includes(item.status))
      || (filter === "closed" && ["approved", "overridden", "rejected"].includes(item.status));
    const queryText = `${item.reference} ${item.title} ${item.requester}`.toLowerCase();
    return filterMatch && queryText.includes(query.toLowerCase().trim());
  }), [cases, filter, query]);

  const selected = cases.find((item) => item.id === selectedId) ?? null;

  async function perform(label: string, operation: () => Promise<unknown>) {
    setBusy(label);
    try {
      await operation();
      await loadDashboard(true);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The operation failed");
    } finally {
      setBusy(null);
    }
  }

  async function createCase(input: NewCaseInput) {
    await perform("create", async () => {
      const created = await api.createCase(input);
      setSelectedId(created.id);
      setModalOpen(false);
    });
  }

  return (
    <main className="app-shell">
      <header className="desk-masthead">
        <a className="brand" href="#queue" aria-label="SignalDesk decision room"><SignalMark /><div><strong>SignalDesk</strong><span>Human decision room</span></div></a>
        <nav className="desk-nav" aria-label="Primary navigation">
          <a className="nav-active" href="#queue"><Inbox size={16} />Queue</a>
          <a href="#policies"><FileLock2 size={16} />Evidence</a>
          <a href="#audit"><ClipboardCheck size={16} />History</a>
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer"><ServerCog size={16} />API</a>
        </nav>
        <div className="masthead-actions">
          <span className={`connection-pill ${connected ? "connected" : "disconnected"}`}>{connected ? <Wifi size={14} /> : <WifiOff size={14} />}{connected ? "Live" : "Reconnecting"}</span>
          <button className="primary-button" onClick={() => setModalOpen(true)} type="button"><Plus size={17} /><span>New request</span></button>
        </div>
      </header>

      <div className="dashboard-content">
          <section className="desk-intro" aria-labelledby="desk-title">
            <div className="intro-copy">
              <span className="edition-line"><i /> Bilingual operations review</span>
              <h1 id="desk-title">Context before conclusions.</h1>
              <p>Read the request, question the recommendation, and leave a trail another person can verify.</p>
            </div>
            <aside className="desk-note">
              <span><Bot size={15} /> Decision support mode</span>
              <strong>Demo rules</strong>
              <p>AI may recommend. It cannot approve.</p>
            </aside>
          </section>

          {error && <div className="error-banner" role="alert"><AlertTriangle size={18} /><span>{error}</span><button onClick={() => setError(null)} aria-label="Dismiss error" type="button"><X size={16} /></button></div>}

          <section className="brief-stats" aria-label="Queue analytics">
            <BriefStat index="01" icon={<Inbox size={19} />} label="In the room" value={analytics.total} detail={`${analytics.by_status.new ?? 0} awaiting analysis`} />
            <BriefStat index="02" icon={<UserCheck size={19} />} label="At your desk" value={analytics.by_status.analyzed ?? 0} detail="Human decision required" />
            <BriefStat index="03" icon={<AlertTriangle size={19} />} label="Needs care" value={analytics.high_risk_open} detail="Critical and high priority" />
            <BriefStat index="04" icon={<CircleGauge size={19} />} label="Model confidence" value={`${Math.round(analytics.average_confidence * 100)}%`} detail="Across latest analyses" />
          </section>

          <section className="decision-layout" id="queue">
            <div className="queue-panel">
              <div className="queue-toolbar">
                <div><span className="section-kicker">The dispatch ledger</span><h2>Incoming requests</h2></div>
                <button className="icon-button" onClick={() => void loadDashboard()} aria-label="Refresh queue" type="button"><RefreshCw size={18} className={loading ? "spin" : ""} /></button>
              </div>
              <div className="queue-controls">
                <label className="search-box"><Search size={16} /><input aria-label="Search requests" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search requests" /></label>
                <div className="filter-tabs" aria-label="Queue filters"><Filter size={15} />{(["all", "review", "open", "closed"] as QueueFilter[]).map((value) => <button aria-pressed={filter === value} key={value} className={filter === value ? "filter-active" : ""} onClick={() => setFilter(value)} type="button">{titleCase(value)}</button>)}</div>
              </div>
              <div className="queue-list" aria-busy={loading}>
                {loading ? Array.from({ length: 5 }).map((_, index) => <div className="queue-skeleton" key={index} />) : visibleCases.length ? visibleCases.map((item) => <QueueRow key={item.id} item={item} selected={item.id === selectedId} onSelect={() => setSelectedId(item.id)} />) : <div className="empty-queue"><Filter size={24} /><strong>No matching requests</strong><p>Try another filter or create a new request.</p></div>}
              </div>
              <footer className="queue-footer"><span>{visibleCases.length} visible</span><span><Activity size={14} />Updated in real time</span></footer>
            </div>

            {selected ? <CaseWorkspace key={selected.id} item={selected} audit={audit} auditVerification={auditVerification} busy={busy} onAnalyze={() => perform("analyze", () => api.analyzeCase(selected.id))} onDecide={(input) => perform(input.action, () => api.decideCase(selected.id, input))} /> : <section className="workspace-panel workspace-empty"><Radar size={32} /><h2>Select a request</h2><p>Choose an item from the queue to review its context, analysis, and audit history.</p></section>}
          </section>

          <footer className="product-footer"><span><SignalMark />SignalDesk</span><p>Context first · Evidence visible · People decide</p><code>v0.3.0</code></footer>
      </div>

      {modalOpen && <NewCaseModal onClose={() => setModalOpen(false)} onCreate={createCase} busy={busy === "create"} />}
    </main>
  );
}
