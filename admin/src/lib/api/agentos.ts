/**
 * Typed API client for AgentOS runtime.
 * Connects to NEXT_PUBLIC_AGENTOS_URL (default: http://localhost:8000).
 */

function resolveAgentOSBase(): string {
  const raw = process.env.NEXT_PUBLIC_AGENTOS_URL ?? "http://localhost:8000";
  return raw.replace(/\/$/, "");
}

const AGENTOS_BASE = resolveAgentOSBase();

async function agentFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${AGENTOS_BASE}${path}`, options);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`自動任務服務 ${path} 連線失敗（HTTP ${res.status}）`);
  }
  return res.json() as Promise<T>;
}

// ── Model types mirroring AgentOS Pydantic models ────────────────────────────

export type RunStatus =
  | "created"
  | "running"
  | "waiting_approval"
  | "completed"
  | "failed"
  | "canceled";

export type ApprovalDecision =
  | "pending"
  | "approved"
  | "rejected"
  | "edited"
  | "timed_out";

export type AgentRun = {
  id: string;
  task_id: string;
  session_id: string;
  status: RunStatus;
  started_at: string;
  finished_at: string | null;
  current_step_id: string | null;
  parent_run_id: string | null;
};

export type RunState = {
  run_id: string;
  state_version: number;
  execution_pointer: string;
  summary: string;
  last_error: string | null;
  failure_mode: string | null;
};

export type Approval = {
  id: string;
  task_id: string;
  run_id: string;
  checkpoint: string;
  step_id: string;
  decision: ApprovalDecision;
  created_at: string;
  expires_at: string | null;
  actor_id: string | null;
  decided_at: string | null;
  edited_payload: Record<string, unknown> | null;
};

export type Checkpoint = {
  id: string;
  run_id: string;
  step_id: string | null;
  checkpoint_type: string;
  state_ref: string;
  created_at: string;
};

export type RunView = {
  run: AgentRun;
  run_state: RunState;
  approvals: Approval[];
  checkpoints: Checkpoint[];
};

export type TraceEvent = {
  id: string;
  run_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  occurred_at: string;
};

export type TraceView = {
  run_id: string;
  events: TraceEvent[];
};

// ── API functions ─────────────────────────────────────────────────────────────

export const agentosApi = {
  listRuns: (status?: RunStatus) => {
    const qs = status ? `?status=${status}` : "";
    return agentFetch<RunView[]>(`/runs${qs}`);
  },

  getRun: (runId: string) => agentFetch<RunView>(`/runs/${runId}`),

  listPendingApprovals: () => agentFetch<Approval[]>("/approvals"),

  decideApproval: (
    approvalId: string,
    decision: "approved" | "rejected",
    actorId: string,
    editedPayload?: Record<string, unknown>,
  ) =>
    agentFetch<RunView>(`/approvals/${approvalId}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, actor_id: actorId, edited_payload: editedPayload ?? null }),
    }),

  getTraces: (runId: string) => agentFetch<TraceView>(`/traces/${runId}`),
};
