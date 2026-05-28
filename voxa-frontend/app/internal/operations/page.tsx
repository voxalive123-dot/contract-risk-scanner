import Link from "next/link";

type ServiceState = {
  status?: string;
  generated_at?: string;
  runtime?: Record<string, unknown>;
  startup_checks?: Record<string, string>;
  failure_discipline?: {
    frontend_backend_connectivity?: string;
    retry_safe_flows?: string[];
    graceful_degradation?: string[];
  };
  environment?: Record<string, unknown>;
};

type GovernanceSpine = {
  status?: string;
  generated_at?: string;
  objective?: string;
  control_plane?: Record<string, string[]>;
  destructive_action_registry?: Record<string, {
    label?: string;
    requires_confirmation?: boolean;
    requires_reason?: boolean;
    rollback_action?: string;
    risk?: string;
  }>;
  operator_safety_rules?: string[];
  rollback_doctrine?: Record<string, {
    action?: string;
    rollback?: string;
    risk?: string;
  }>;
};

async function fetchJson<T>(path: string): Promise<{ ok: boolean; data?: T; error?: string }> {
  const baseUrl = process.env.VOXA_API_BASE_URL || "http://127.0.0.1:8000";

  try {
    const response = await fetch(`${baseUrl}${path}`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return { ok: false, error: `${response.status} ${response.statusText}` };
    }

    return { ok: true, data: (await response.json()) as T };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : "Unknown service-state fetch failure",
    };
  }
}

function Panel({
  title,
  eyebrow,
  children,
}: {
  title: string;
  eyebrow?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[28px] border border-[#dac7a6] bg-[#fffaf0] p-6 shadow-[0_16px_36px_rgba(75,55,25,0.08)]">
      {eyebrow && (
        <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">
          {eyebrow}
        </div>
      )}
      <h2 className="mt-2 text-2xl font-semibold tracking-tight text-neutral-950">{title}</h2>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function StatusPill({ ok }: { ok: boolean }) {
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
      ok
        ? "border border-emerald-200 bg-emerald-50 text-emerald-800"
        : "border border-red-200 bg-red-50 text-red-800"
    }`}>
      {ok ? "Observable" : "Needs attention"}
    </span>
  );
}

export default async function InternalOperationsPage() {
  const [serviceState, governanceSpine, auditEvents, warnings] = await Promise.all([
    fetchJson<ServiceState>("/internal/ops/service-state"),
    fetchJson<GovernanceSpine>("/internal/ops/governance-spine"),
    fetchJson<{ event_count?: number; events?: Array<Record<string, string>> }>("/internal/ops/audit-events"),
    fetchJson<{ warning_count?: number; warnings?: Array<{ severity: string; code: string; message: string }> }>("/internal/ops/warnings"),
  ]);

  const controlPlane = governanceSpine.data?.control_plane ?? {};
  const destructiveRegistry = governanceSpine.data?.destructive_action_registry ?? {};

  return (
    <main className="min-h-screen bg-[#f6efe1] text-neutral-950">
      <div className="mx-auto max-w-[1500px] px-6 py-8 md:px-8">
        <div className="mb-6 flex flex-col gap-4 rounded-[30px] border border-[#dac7a6] bg-[#1e1712] p-6 text-[#f5efe4] shadow-[0_24px_70px_rgba(30,23,18,0.22)] md:flex-row md:items-end md:justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#d5bd88]">
              VoxaRisk internal operations
            </div>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
              Operational maturity control plane
            </h1>
            <p className="mt-3 max-w-4xl text-sm leading-6 text-[#d8cec2]">
              Owner-facing visibility for governance control, destructive-action safety, service state, and failure discipline.
            </p>
          </div>
          <div className="flex gap-2">
            <StatusPill ok={serviceState.ok} />
            <StatusPill ok={governanceSpine.ok} />
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="space-y-6">
            <Panel title="Governance spine" eyebrow="Phase 1">
              {!governanceSpine.ok ? (
                <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
                  Governance spine unavailable: {governanceSpine.error}
                </div>
              ) : (
                <div className="space-y-5">
                  <p className="text-sm leading-6 text-neutral-700">{governanceSpine.data?.objective}</p>
                  <div className="grid gap-4 md:grid-cols-2">
                    {Object.entries(controlPlane).map(([section, items]) => (
                      <div key={section} className="rounded-2xl border border-[#e1cfad] bg-[#fffdf8] p-4">
                        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8a6a34]">
                          {section.replaceAll("_", " ")}
                        </div>
                        <ul className="mt-3 space-y-2 text-sm leading-6 text-neutral-700">
                          {items.map((item) => (
                            <li key={item} className="flex gap-2">
                              <span className="mt-2 h-1.5 w-1.5 rounded-full bg-[#8a6a34]" />
                              <span>{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Panel>

            <Panel title="Destructive-action safety registry" eyebrow="Action safety">
              <div className="grid gap-4">
                {Object.entries(destructiveRegistry).map(([key, action]) => (
                  <div key={key} className="rounded-2xl border border-[#e1cfad] bg-[#fffdf8] p-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <div className="text-sm font-semibold text-neutral-950">{action.label ?? key}</div>
                        <p className="mt-1 text-sm leading-6 text-neutral-700">{action.risk}</p>
                      </div>
                      <div className="flex flex-wrap gap-2 text-xs">
                        <span className="rounded-full border border-[#d7c3a0] bg-[#fcf2df] px-3 py-1 font-semibold text-[#6f552d]">
                          reason required
                        </span>
                        <span className="rounded-full border border-[#d7c3a0] bg-[#fcf2df] px-3 py-1 font-semibold text-[#6f552d]">
                          confirm required
                        </span>
                      </div>
                    </div>
                    <div className="mt-3 text-xs leading-5 text-[#8a6a34]">
                      Rollback doctrine: {action.rollback_action ?? "manual owner review"}
                    </div>
                  </div>
                ))}
              </div>
            </Panel>

            <Panel title="Failure discipline" eyebrow="Phase 2">
              {!serviceState.ok ? (
                <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
                  Service state unavailable: {serviceState.error}
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="rounded-2xl border border-[#e1cfad] bg-[#fffdf8] p-4">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8a6a34]">
                      Frontend/backend diagnostic rule
                    </div>
                    <p className="mt-2 text-sm leading-6 text-neutral-700">
                      {serviceState.data?.failure_discipline?.frontend_backend_connectivity}
                    </p>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-2xl border border-[#e1cfad] bg-[#fffdf8] p-4">
                      <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8a6a34]">
                        Retry-safe flows
                      </div>
                      <ul className="mt-3 space-y-2 text-sm leading-6 text-neutral-700">
                        {(serviceState.data?.failure_discipline?.retry_safe_flows ?? []).map((item) => (
                          <li key={item}>• {item}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="rounded-2xl border border-[#e1cfad] bg-[#fffdf8] p-4">
                      <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8a6a34]">
                        Graceful degradation
                      </div>
                      <ul className="mt-3 space-y-2 text-sm leading-6 text-neutral-700">
                        {(serviceState.data?.failure_discipline?.graceful_degradation ?? []).map((item) => (
                          <li key={item}>• {item}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </Panel>
          </div>

          <aside className="space-y-6">
            <Panel title="Service state" eyebrow="Runtime">
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between gap-4 border-b border-[#eadcc4] pb-3">
                  <span className="text-neutral-600">API service</span>
                  <span className="font-semibold text-neutral-950">{serviceState.ok ? "reachable" : "unavailable"}</span>
                </div>
                <div className="flex items-center justify-between gap-4 border-b border-[#eadcc4] pb-3">
                  <span className="text-neutral-600">Generated</span>
                  <span className="text-right font-semibold text-neutral-950">{serviceState.data?.generated_at ?? "not available"}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-neutral-600">Governance</span>
                  <span className="font-semibold text-neutral-950">{governanceSpine.ok ? "defined" : "unavailable"}</span>
                </div>
              </div>
            </Panel>

            <Panel title="Startup checks" eyebrow="Readiness">
              <div className="space-y-3">
                {Object.entries(serviceState.data?.startup_checks ?? {}).map(([key, value]) => (
                  <div key={key} className="rounded-2xl border border-[#e1cfad] bg-[#fffdf8] p-3">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#8a6a34]">
                      {key.replaceAll("_", " ")}
                    </div>
                    <p className="mt-1 text-xs leading-5 text-neutral-700">{value}</p>
                  </div>
                ))}
              </div>
            </Panel>

            <Panel title="Operational warnings" eyebrow="Failure visibility">
              <div className="space-y-3">
                {(warnings.data?.warnings ?? []).length === 0 ? (
                  <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-800">
                    No operational warnings detected.
                  </div>
                ) : (
                  (warnings.data?.warnings ?? []).map((warning) => (
                    <div key={warning.code} className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
                      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-800">
                        {warning.severity} · {warning.code}
                      </div>
                      <p className="mt-2 text-sm leading-6 text-amber-900">{warning.message}</p>
                    </div>
                  ))
                )}
              </div>
            </Panel>

            <Panel title="Audit visibility" eyebrow="Governance evidence">
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between gap-4 border-b border-[#eadcc4] pb-3">
                  <span className="text-neutral-600">Recorded events</span>
                  <span className="font-semibold text-neutral-950">{auditEvents.data?.event_count ?? 0}</span>
                </div>
                {(auditEvents.data?.events ?? []).slice(0, 5).map((event) => (
                  <div key={event.id} className="rounded-2xl border border-[#e1cfad] bg-[#fffdf8] p-3">
                    <div className="font-semibold text-neutral-950">{event.action}</div>
                    <div className="mt-1 text-xs leading-5 text-neutral-600">
                      {event.target} · {event.reason}
                    </div>
                  </div>
                ))}
                {(auditEvents.data?.events ?? []).length === 0 && (
                  <p className="text-sm leading-6 text-neutral-600">
                    No operational actions recorded in this runtime yet.
                  </p>
                )}
              </div>
            </Panel>

            <Panel title="Owner navigation" eyebrow="Control routes">
              <div className="grid gap-2 text-sm">
                {[
                  ["/internal/command-centre", "Command centre"],
                  ["/internal/users", "Users"],
                  ["/internal/orgs", "Organizations"],
                  ["/internal/audit", "Audit"],
                  ["/internal/revenue", "Revenue"],
                  ["/dashboard", "Dashboard"],
                  ["/account", "Account"],
                ].map(([href, label]) => (
                  <Link key={href} href={href} className="rounded-xl border border-[#e1cfad] bg-[#fffdf8] px-4 py-3 font-semibold text-neutral-800 transition hover:bg-[#fcf2df]">
                    {label}
                  </Link>
                ))}
              </div>
            </Panel>
          </aside>
        </div>
      </div>
    </main>
  );
}
