// Platform Admin API — superuser only
import { apiClient } from "./client";

export type PlatformDashboard = {
  total_tenants: number;
  active_tenants: number;
  total_users: number;
  active_users: number;
  total_products: number;
  total_rfqs: number;
  total_visitors: number;
  legacy_unassigned_rfqs: number;
  legacy_unassigned_visitors: number;
  published_sites: number;
  blocked_sites: number;
  tenants_needing_attention: number;
  failed_jobs: number;
  rfqs_30d: number;
  daily_rfqs: { date: string; count: number }[];
  top_tenants: { name: string; rfq_count: number }[];
  attention_tenants: {
    id: string;
    name: string;
    slug: string;
    reasons: string[];
  }[];
};

export type TenantSummary = {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  user_count: number;
  product_count: number;
  rfq_count: number;
  visitor_count: number;
  rfq_count_30d: number;
  failed_job_count: number;
  last_activity_at?: string;
  site_build_status?: string;
  primary_domain?: string;
  cms_connected: boolean;
  site_ready: boolean;
  attention_reasons: string[];
};

export type TenantDetail = TenantSummary & {
  feature_overrides: Record<string, boolean>;
  resolved_features: Record<string, boolean>;
  users: {
    id: string;
    email: string;
    full_name: string;
    role: string;
    is_active: boolean;
  }[];
  recent_rfqs: {
    id: string;
    contact_name: string;
    contact_email: string;
    status: string;
    submitted_at?: string;
  }[];
};

export type AdminUser = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_superuser: boolean;
  tenant_id?: string;
  tenant_name?: string;
  created_at?: string;
  last_login_at?: string;
};

export type SystemHealth = {
  status: string;
  database: string;
  uptime_seconds: number;
  python_version: string;
  external_test: {
    status: "ready" | "blocked";
    ready: boolean;
    checks: Record<string, { ok: boolean; label: string }>;
    blockers: string[];
  };
};

export type RetirementCandidate = {
  candidate_key: string;
  display_name: string;
  status: "observing" | "retained" | "approved_removal" | "removed";
  code_state: "active" | "disabled" | "removed";
  started_at: string;
  required_observation_days: number;
  observed_days: number;
  window_complete: boolean;
  technical_removal_ready: boolean;
  recent_usage_count: number;
  tenant_count: number;
  last_used_at?: string;
  removal_ready: boolean;
  blockers: string[];
  evidence: {
    signal: string;
    enabled_preferences?: number;
    telemetry_events: number;
    domain_records: number;
    stores_request_payload_or_pii: boolean;
  };
  decision: {
    reason?: string;
    decided_at?: string;
    decided_by?: string;
    telemetry_verified_at?: string;
    telemetry_verified_by?: string;
    telemetry_evidence_ref?: string;
    data_disposition?: "not_applicable" | "retained" | "exported" | "deleted";
    rollback_revision?: string;
    removal_plan_ref?: string;
  };
};

export type RetirementAuditReport = {
  generated_at: string;
  report_sha256: string;
  policy: string;
  candidates: RetirementCandidate[];
};

export type TenantUpdate = {
  name?: string;
  feature_overrides?: Record<string, boolean>;
  is_active?: boolean;
};

export type OperationalJobSummary = {
  counts: Record<string, number>;
  stale_processing: number;
  healthy: boolean;
};

export type OperationalJobItem = {
  id: string;
  job_type: string;
  attempts: number;
  max_attempts: number;
  available_at: string;
  last_error?: string;
  updated_at: string;
};

export type OperationalJobList = {
  status: string;
  items: OperationalJobItem[];
};

export type ServiceLevelMetric = {
  key: string;
  label: string;
  kind: "rate" | "zero_tolerance";
  window: string;
  target: number;
  actual: number | null;
  numerator: number | null;
  denominator: number | null;
  evaluable: boolean;
  compliant: boolean;
  error_budget_remaining: number | null;
};

export type ServiceLevelReport = {
  current: {
    status: "healthy" | "at_risk" | "breached";
    sampled_at: string;
    metrics: ServiceLevelMetric[];
    breached: string[];
    insufficient_evidence: string[];
    scope: string;
    external_uptime_claimed: false;
  };
  history: {
    id: string;
    status: "healthy" | "at_risk" | "breached";
    metrics: ServiceLevelMetric[];
    sampled_at: string;
  }[];
  scope: string;
  external_uptime_claimed: false;
};

export type OperationalIncidentEvent = {
  id: string;
  action: string;
  actor_user_id?: string;
  note?: string;
  detail: Record<string, unknown>;
  created_at: string;
};

export type OperationalIncident = {
  id: string;
  incident_key: string;
  incident_type: string;
  severity: "warning" | "critical";
  status: "open" | "acknowledged" | "resolved";
  title: string;
  summary: string;
  metrics: ServiceLevelMetric;
  occurrence_count: number;
  first_seen_at: string;
  last_seen_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
  last_notified_at?: string;
  notification_error?: string;
  events: OperationalIncidentEvent[];
};

export type OperationalIncidentList = {
  items: OperationalIncident[];
  total: number;
};

export type SiteTemplate = {
  key: string;
  name: string;
  industry: string;
  demo_url: string;
  cms_connected: boolean;
  publish_supported: boolean;
};

export type TenantProvision = {
  name: string;
  slug: string;
  owner_email: string;
  owner_full_name: string;
  temporary_password: string;
  template_key: string;
  brand_name: string;
  logo_mark: string;
  contact_email: string;
  contact_phone?: string;
  site_url: string;
  primary_domain?: string;
  default_locale: string;
  locales: string[];
  theme_key: string;
  layout_key: string;
};

export type TenantProvisionPreflight = {
  ready: boolean;
  checks: Record<string, boolean>;
  blockers: string[];
  normalized: {
    primary_domain?: string;
    site_url: string;
    owner_email: string;
  };
};

export type TenantProvisioningManifest = {
  run_id: string;
  created_at: string;
  status_code: number;
  manifest: {
    tenant_id: string;
    owner_id: string;
    site_build_id: string;
    provisioning_run_id: string;
    status: string;
    delivery_stage: DeliveryStage;
    readiness: { ready: boolean; checks: Record<string, boolean>; blockers: string[] };
    next_actions: string[];
  };
};

export type PrivacyRetentionInventory = {
  generated_at: string;
  analytics_retention_days: number;
  analytics_cutoff: string;
  expired: Record<string, number>;
  total_expired: number;
  retained_business_evidence: Record<string, number>;
  policy: Record<string, string>;
};

export type PrivacyOperation = {
  id: string;
  operation_type: "retention_run" | "visitor_export" | "visitor_erasure";
  tenant_id?: string;
  subject_hash_prefix?: string;
  reason?: string;
  status: string;
  result: Record<string, unknown>;
  created_at: string;
  completed_at: string;
};

export type VisitorPrivacyRequest = {
  tenant_id: string;
  visitor_id: string;
  reason: string;
};

export type FeatureCatalogItem = {
  key: string;
  label: string;
  group: string;
  description: string;
  configurable: boolean;
  status:
    "available" | "core_required" | "awaiting_provider" | "service_required" | "core_in_development" | "pilot" | "retirement_observation";
  default_enabled: boolean;
};

export type FeatureCatalog = {
  features: FeatureCatalogItem[];
};

export type SiteBuild = {
  id: string;
  tenant_id: string;
  template_key: string;
  template: Partial<SiteTemplate>;
  status: string;
  primary_domain?: string;
  locales: string[];
  customization: Record<string, unknown>;
  cms_connected: boolean;
  readiness: {
    ready?: boolean;
    checks?: Record<string, boolean>;
    blockers?: string[];
  };
  published_at?: string;
  last_error?: string;
  delivery_stage: DeliveryStage;
  delivery_owner_id?: string;
  target_launch_at?: string;
  handoff_at?: string;
  acceptance_status: AcceptanceStatus;
  internal_note?: string;
};

export type PlatformSiteProfile = {
  brand_name: string;
  logo_mark: string;
  logo_url?: string;
  favicon_url?: string;
  theme_key: string;
  layout_key: string;
  contact_email: string;
  contact_phone?: string;
  site_url: string;
  default_locale: string;
  asset_base?: string;
  demo_company_folder?: string;
  header_nav_json?: string;
  header_actions_json?: string;
  footer_sections_json?: string;
  footer_badges_json?: string;
  social_links_json?: string;
  footer_cta_title?: string;
  footer_cta_description?: string;
  footer_cta_label?: string;
  footer_cta_href?: string;
  asset_manifest_json?: string;
  site_copy_json?: string;
};

export type DeliveryStage =
  | "intake"
  | "content"
  | "build"
  | "qa"
  | "client_review"
  | "launch_ready"
  | "live"
  | "on_hold";
export type AcceptanceStatus = "pending" | "requested" | "accepted" | "waived";

export type PlatformWorkItem = {
  kind: string;
  severity: "urgent" | "high" | "normal";
  title: string;
  detail: string;
  tenant_id?: string;
  tenant_name?: string;
  href: string;
  created_at?: string;
};

export type PlatformWorkspace = {
  counts: Record<string, number>;
  work_items: PlatformWorkItem[];
};

export type DeliveryBoardItem = {
  id: string;
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  template_key: string;
  delivery_stage: DeliveryStage;
  acceptance_status: AcceptanceStatus;
  delivery_owner_id?: string;
  delivery_owner_name?: string;
  target_launch_at?: string;
  handoff_at?: string;
  technical_status: string;
  primary_domain?: string;
  cms_connected: boolean;
  readiness: { ready?: boolean; blockers?: string[] };
  last_error?: string;
  updated_at: string;
};

export type PlatformRFQItem = {
  id: string;
  tenant_id?: string;
  tenant_name: string;
  rfq_number: string;
  contact_name?: string;
  contact_email?: string;
  status: string;
  priority: string;
  quality_score: number;
  assigned_to?: string;
  assigned_name?: string;
  sla_due_at?: string;
  sla_breached: boolean;
  created_at: string;
  is_spam: boolean;
  is_test_data: boolean;
};

export type PlatformRFQList = { data: PlatformRFQItem[]; total: number };

export type PlatformResourceStatus = {
  external_test: SystemHealth["external_test"];
  forms: {
    signed_challenge_required: boolean;
    turnstile_configured: boolean;
    allowed_hostnames_configured: boolean;
  };
  email: {
    provider: string;
    provider_configured: boolean;
    webhook_configured: boolean;
    dry_run: boolean;
    external_delivery_enabled: boolean;
    internal_allowlist_configured: boolean;
    sales_notify_configured: boolean;
  };
  storage: {
    r2_configured: boolean;
    asset_count: number;
    asset_bytes: number;
    tenants_with_assets: number;
    latest_asset_at?: string;
  };
  backups: {
    offsite_configured: boolean;
    last_backup_at: string | null;
    last_restore_drill_at: string | null;
    evidence_status: "verified" | "backup_only" | "not_recorded";
  };
  monitoring: {
    incident_alert_configured: boolean;
    external_monitor_configured: boolean;
    external_monitor_name?: string;
  };
};

export type PlatformUsageSummary = {
  totals: Record<string, number>;
  tenants: {
    tenant_id: string;
    tenant_name: string;
    slug: string;
    product_count: number;
    asset_count: number;
    asset_bytes: number;
    rfq_count: number;
    visitor_count: number;
  }[];
};

export type PlatformAuditItem = {
  id: string;
  actor_email: string;
  action: string;
  target_type: string;
  target_id?: string;
  changes: Record<string, unknown>;
  created_at: string;
};

export type AdoptionApplication = {
  id: string;
  application_number: string;
  company_name: string;
  website_url?: string;
  contact_name: string;
  work_email: string;
  phone?: string;
  job_title?: string;
  industry: string;
  target_markets?: string;
  current_situation: string;
  requested_scope: string;
  preferred_language: string;
  status: "new" | "reviewing" | "invited" | "declined" | "archived";
  internal_note?: string;
  source_page?: string;
  is_test_data: boolean;
  created_at: string;
  reviewed_at?: string;
};

export type AdoptionApplicationList = {
  data: AdoptionApplication[];
  meta: { total: number; page: number; page_size: number; total_pages: number };
};

export type GrowthAutomationPolicy = {
  tenant_id: string;
  company_identification_mode: "off" | "shadow";
  provider_name: string;
  min_intent_score: number;
  observation_retention_days: number;
  daily_lookup_quota: number;
  daily_provider_cost_limit: number;
  medium_confidence_threshold: number;
  high_confidence_threshold: number;
  allowed_countries: string[];
  updated_by?: string;
  created_at: string;
  updated_at: string;
  persisted: boolean;
};

export type CompanyCandidate = {
  id: string;
  tenant_id: string;
  visitor_id: string;
  network_observation_id: string;
  company_name: string;
  domain: string;
  provider: string;
  provider_company_id: string;
  confidence: number;
  confidence_band: "low" | "medium" | "high";
  match_method: string;
  evidence: Record<string, unknown>;
  status:
    "shadow" | "candidate" | "confirmed" | "rejected" | "expired" | "conflict";
  source_freshness?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  review_note?: string;
  expires_at: string;
  created_at: string;
  updated_at: string;
};

export type CompanyCandidateList = {
  data: CompanyCandidate[];
  limit: number;
  offset: number;
};

export type CompanyIdentificationMetrics = {
  tenant_id: string;
  days: number;
  observations: Record<string, number>;
  candidates: Record<string, number>;
  lookup_attempts: number;
  matched_lookups: number;
  match_rate: number | null;
  high_confidence_rate: number | null;
  unknown_count: number;
  conflict_count: number;
  total_estimated_cost: number;
  high_confidence_reviewed: number;
  high_confidence_precision: number | null;
  precision_gate: number;
  precision_gate_passed: boolean;
  provider_usage: {
    provider: string;
    status: string;
    requests: number;
    units: number;
    estimated_cost: number;
    average_latency_ms: number;
  }[];
};

export type ContactPersonaPolicy = {
  tenant_id: string;
  mode: "off" | "review_only";
  contact_provider_name: string;
  verification_provider_name: string;
  target_departments: string[];
  target_titles: string[];
  target_seniorities: string[];
  target_locations: string[];
  excluded_title_terms: string[];
  min_relevance_score: number;
  candidate_retention_days: number;
  max_candidates_per_company: number;
  daily_lookup_quota: number;
  daily_provider_cost_limit: number;
  updated_by?: string;
  updated_at: string;
  persisted: boolean;
};

export type ContactCandidate = {
  id: string;
  tenant_id: string;
  company_identification_id: string;
  company_name?: string;
  company_domain?: string;
  identity_notice: string;
  full_name: string;
  job_title?: string;
  department?: string;
  seniority?: string;
  location?: string;
  email_masked: string;
  verification_status:
    "verified" | "risky" | "catch_all" | "unknown" | "invalid";
  verification_provider?: string;
  verified_at?: string;
  source_provider: string;
  source_url?: string;
  source_freshness?: string;
  relevance_score: number;
  relevance_reasons: string[];
  confidence: number;
  status:
    | "candidate"
    | "approved"
    | "rejected"
    | "converted"
    | "expired"
    | "do_not_contact";
  review_reason_code?: string;
  review_note?: string;
  converted_contact_id?: string;
  expires_at: string;
  created_at: string;
};

export type ContactCandidateList = {
  data: ContactCandidate[];
  limit: number;
  offset: number;
};

export type ContactEnrichmentMetrics = {
  tenant_id: string;
  days: number;
  statuses: Record<string, number>;
  verifications: Record<string, number>;
  candidate_count: number;
  reviewed_count: number;
  approval_rate: number | null;
  verified_rate: number | null;
  average_relevance: number;
  provider_usage: {
    provider: string;
    operation: string;
    requests: number;
    units: number;
    estimated_cost: number;
    average_latency_ms: number;
  }[];
};

export type OutreachDraftPolicy = {
  tenant_id: string;
  mode: "off" | "review_only";
  lookback_days: number;
  snapshot_retention_days: number;
  max_evidence_events: number;
  allowed_languages: string[];
  policy_version: string;
  updated_by?: string;
  updated_at: string;
  persisted: boolean;
};

export type JourneySnapshot = {
  id: string;
  intent_score: number;
  intent_stage: string;
  intent_facets: Record<string, number>;
  top_products: {
    id: string;
    title: string;
    locale: string;
    score: number;
    events: number;
  }[];
  top_pages: {
    id: string;
    title: string;
    locale: string;
    score: number;
    events: number;
  }[];
  downloads: { product_id: string; title: string; event_id: string }[];
  comparisons: {
    id: string;
    title: string;
    locale: string;
    score: number;
    events: number;
  }[];
  cta_signals: { event_name: string; count: number }[];
  summary: string;
  evidence_event_ids: string[];
  knowledge_references: {
    entity_type: string;
    entity_id: string;
    title: string;
    locale: string;
  }[];
  generated_at: string;
  expires_at: string;
};

export type OutreachMessage = {
  id: string;
  tenant_id: string;
  contact_candidate_id: string;
  revision_of_id?: string;
  revision_no: number;
  language: string;
  to_email_masked: string;
  identity_notice: string;
  subject: string;
  html: string;
  text: string;
  personalization_evidence: Record<string, unknown>;
  knowledge_version: string;
  prompt_version: string;
  policy_version: string;
  generation_model: string;
  content_hash: string;
  status:
    | "draft"
    | "pending_review"
    | "approved"
    | "rejected"
    | "cancelled"
    | "queued"
    | "sending"
    | "sent"
    | "delivered"
    | "opened"
    | "clicked"
    | "bounced"
    | "complained"
    | "unsubscribed"
    | "failed";
  review_note?: string;
  generated_at: string;
  created_at: string;
  updated_at: string;
  journey_snapshot?: JourneySnapshot;
  send_available: boolean;
  send_requested_at?: string;
  scheduled_for?: string;
  send_attempts: number;
  provider?: string;
  provider_message_id?: string;
  sent_at?: string;
  delivered_at?: string;
  opened_at?: string;
  clicked_at?: string;
  bounced_at?: string;
  complained_at?: string;
  unsubscribed_at?: string;
  last_error?: string;
};

export type OutreachDeliveryPolicy = {
  tenant_id: string;
  mode: "off" | "approval_send";
  provider_name: "resend";
  timezone: string;
  quiet_hours_enabled: boolean;
  quiet_start_hour: number;
  quiet_end_hour: number;
  daily_send_quota: number;
  frequency_cap_days: number;
  unsubscribe_scope: "tenant" | "global";
  controlled_auto_opt_in: boolean;
  controlled_auto_legal_approved: boolean;
  controlled_auto_allowed_regions: string[];
  controlled_auto_allowed_personas: string[];
  controlled_auto_allowed_templates: string[];
  controlled_auto_review_sample_pct: number;
  controlled_auto_reviewed_by?: string | null;
  controlled_auto_reviewed_at?: string | null;
  updated_by?: string;
  updated_at: string;
  persisted: boolean;
  readiness: {
    ready: boolean;
    external_delivery_enabled: boolean;
    outreach_send_enabled: boolean;
    provider_configured: boolean;
    public_url_configured: boolean;
    unsubscribe_signing_configured: boolean;
    webhook_signing_configured: boolean;
  };
};

export type OutreachDeliveryEvent = {
  id: string;
  event_type: string;
  reason_code?: string;
  provider: string;
  provider_event_id: string;
  occurred_at?: string;
  created_at: string;
};

export type OutreachMessageList = {
  data: OutreachMessage[];
  limit: number;
  offset: number;
};

export const platformAdminApi = {
  dashboard: (token: string) =>
    apiClient.get<PlatformDashboard>("/admin/dashboard", token),

  tenants: (
    token: string,
    params?: {
      search?: string;
      is_active?: boolean;
      site_status?: string;
      needs_attention?: boolean;
      skip?: number;
      limit?: number;
    },
  ) => {
    const qs = params
      ? "?" +
        new URLSearchParams(
          Object.fromEntries(
            Object.entries(params)
              .filter(([, v]) => v !== undefined)
              .map(([k, v]) => [k, String(v)]),
          ),
        ).toString()
      : "";
    return apiClient.get<TenantSummary[]>(`/admin/tenants${qs}`, token);
  },

  tenant: (token: string, id: string) =>
    apiClient.get<TenantDetail>(`/admin/tenants/${id}`, token),

  tenantProvisioningManifest: (token: string, id: string) =>
    apiClient.get<TenantProvisioningManifest>(
      `/admin/tenants/${id}/provisioning-manifest`,
      token,
    ),

  privacyRetention: (token: string) =>
    apiClient.get<PrivacyRetentionInventory>("/admin/privacy/retention", token),

  privacyOperations: (token: string) =>
    apiClient.get<PrivacyOperation[]>("/admin/privacy/operations", token),

  runPrivacyRetention: (
    token: string,
    body: { confirm: boolean; reason: string },
    idempotencyKey: string,
  ) => apiClient.post<Record<string, unknown>>(
    "/admin/privacy/retention/run",
    body,
    token,
    { "Idempotency-Key": idempotencyKey },
  ),

  exportVisitorPrivacyData: (token: string, body: VisitorPrivacyRequest) =>
    apiClient.post<{ operation_id: string; export: Record<string, unknown> }>(
      "/admin/privacy/visitors/export",
      body,
      token,
    ),

  eraseVisitorPrivacyData: (
    token: string,
    body: VisitorPrivacyRequest,
    idempotencyKey: string,
  ) => apiClient.post<Record<string, unknown>>(
    "/admin/privacy/visitors/erase",
    body,
    token,
    { "Idempotency-Key": idempotencyKey },
  ),

  updateTenant: (token: string, id: string, body: TenantUpdate) =>
    apiClient.put<TenantSummary>(`/admin/tenants/${id}`, body, token),

  featureCatalog: (token: string) =>
    apiClient.get<FeatureCatalog>("/admin/feature-catalog", token),

  siteTemplates: (token: string) =>
    apiClient.get<SiteTemplate[]>("/admin/site-templates", token),

  preflightTenant: (token: string, body: TenantProvision) =>
    apiClient.post<TenantProvisionPreflight>(
      "/admin/tenant-provisioning/preflight",
      body,
      token,
    ),

  provisionTenant: (token: string, body: TenantProvision, idempotencyKey: string) =>
    apiClient.post<{
      tenant_id: string;
      owner_id: string;
      site_build_id: string;
      provisioning_run_id: string;
      status: string;
      delivery_stage: DeliveryStage;
      readiness: { ready: boolean; checks: Record<string, boolean>; blockers: string[] };
      next_actions: string[];
    }>("/admin/tenants", body, token, { "Idempotency-Key": idempotencyKey }),

  siteBuild: (token: string, id: string) =>
    apiClient.get<SiteBuild>(`/admin/tenants/${id}/site-build`, token),

  siteProfile: (token: string, id: string) =>
    apiClient.get<PlatformSiteProfile>(
      `/admin/tenants/${id}/site-profile`,
      token,
    ),

  updateSiteProfile: (
    token: string,
    id: string,
    body: Partial<PlatformSiteProfile>,
  ) =>
    apiClient.put<PlatformSiteProfile>(
      `/admin/tenants/${id}/site-profile`,
      body,
      token,
    ),

  createSiteBuild: (
    token: string,
    id: string,
    body: { template_key: string; primary_domain?: string; locales: string[] },
  ) =>
    apiClient.post<SiteBuild>(`/admin/tenants/${id}/site-build`, body, token),

  updateSiteBuild: (
    token: string,
    id: string,
    body: Partial<{
      template_key: string;
      primary_domain: string;
      locales: string[];
      customization: Record<string, unknown>;
      cms_connected: boolean;
      delivery_stage: DeliveryStage;
      delivery_owner_id: string | null;
      target_launch_at: string | null;
      handoff_at: string | null;
      acceptance_status: AcceptanceStatus;
      internal_note: string | null;
    }>,
  ) => apiClient.put<SiteBuild>(`/admin/tenants/${id}/site-build`, body, token),

  workspace: (token: string) =>
    apiClient.get<PlatformWorkspace>("/admin/workspace", token),

  deliveryBoard: (
    token: string,
    params?: { stage?: DeliveryStage; include_live?: boolean },
  ) => {
    const qs = params
      ? "?" +
        new URLSearchParams(
          Object.entries(params)
            .filter(([, value]) => value !== undefined)
            .map(([key, value]) => [key, String(value)]),
        ).toString()
      : "";
    return apiClient.get<DeliveryBoardItem[]>(
      `/admin/delivery-board${qs}`,
      token,
    );
  },

  rfqs: (
    token: string,
    params?: {
      status?: string;
      needs_attention?: boolean;
      include_spam?: boolean;
      include_test?: boolean;
      search?: string;
      limit?: number;
    },
  ) => {
    const qs = params
      ? "?" +
        new URLSearchParams(
          Object.entries(params)
            .filter(([, value]) => value !== undefined && value !== "")
            .map(([key, value]) => [key, String(value)]),
        ).toString()
      : "";
    return apiClient.get<PlatformRFQList>(`/admin/rfqs${qs}`, token);
  },

  resourceStatus: (token: string) =>
    apiClient.get<PlatformResourceStatus>("/admin/resources/status", token),

  usage: (token: string) =>
    apiClient.get<PlatformUsageSummary>("/admin/usage", token),

  auditLog: (
    token: string,
    params?: { tenant_id?: string; limit?: number },
  ) => {
    const qs = params
      ? "?" +
        new URLSearchParams(
          Object.entries(params)
            .filter(([, value]) => value !== undefined)
            .map(([key, value]) => [key, String(value)]),
        ).toString()
      : "";
    return apiClient.get<PlatformAuditItem[]>(`/admin/audit-log${qs}`, token);
  },

  validateSiteBuild: (token: string, id: string) =>
    apiClient.post<SiteBuild>(
      `/admin/tenants/${id}/site-build/validate`,
      {},
      token,
    ),

  publishSiteBuild: (token: string, id: string) =>
    apiClient.post<SiteBuild>(
      `/admin/tenants/${id}/site-build/publish`,
      {},
      token,
    ),

  tenantAuditLog: (token: string, id: string, limit = 30) =>
    apiClient.get<PlatformAuditItem[]>(
      `/admin/tenants/${id}/audit-log?limit=${limit}`,
      token,
    ),

  users: (
    token: string,
    params?: {
      search?: string;
      tenant_id?: string;
      skip?: number;
      limit?: number;
    },
  ) => {
    const qs = params
      ? "?" +
        new URLSearchParams(
          Object.fromEntries(
            Object.entries(params)
              .filter(([, v]) => v !== undefined)
              .map(([k, v]) => [k, String(v)]),
          ),
        ).toString()
      : "";
    return apiClient.get<AdminUser[]>(`/admin/users${qs}`, token);
  },

  createPlatformOperator: (
    token: string,
    body: { email: string; full_name: string; temporary_password: string },
  ) => apiClient.post<AdminUser>("/admin/platform-users", body, token),

  updatePlatformOperator: (
    token: string,
    id: string,
    body: { is_active: boolean },
  ) => apiClient.patch<AdminUser>(`/admin/platform-users/${id}`, body, token),

  systemHealth: (token: string) =>
    apiClient.get<SystemHealth>("/admin/system/health", token),

  serviceLevels: (token: string, historyLimit = 24) =>
    apiClient.get<ServiceLevelReport>(
      `/admin/operations/slo?history_limit=${historyLimit}`,
      token,
    ),

  sampleServiceLevels: (token: string) =>
    apiClient.post<Record<string, unknown>>(
      "/admin/operations/slo/sample",
      {},
      token,
    ),

  operationalIncidents: (token: string, limit = 50) =>
    apiClient.get<OperationalIncidentList>(
      `/admin/operations/incidents?limit=${limit}`,
      token,
    ),

  actOnIncident: (
    token: string,
    id: string,
    body: { action: "acknowledge" | "resolve"; note: string },
  ) =>
    apiClient.post<OperationalIncident>(
      `/admin/operations/incidents/${id}/actions`,
      body,
      token,
    ),

  operationalJobSummary: (token: string) =>
    apiClient.get<OperationalJobSummary>(
      "/ops/operational-jobs/summary",
      token,
    ),

  operationalJobs: (token: string, status = "failed", limit = 20) =>
    apiClient.get<OperationalJobList>(
      `/ops/operational-jobs?status=${encodeURIComponent(status)}&limit=${limit}`,
      token,
    ),

  retryOperationalJob: (token: string, id: string) =>
    apiClient.post<{ id: string; status: string; available_at: string }>(
      `/ops/operational-jobs/${id}/retry`,
      {},
      token,
    ),

  adoptionApplications: (
    token: string,
    params?: {
      status?: string;
      search?: string;
      include_test?: boolean;
      page?: number;
      page_size?: number;
    },
  ) => {
    const qs = params
      ? "?" +
        new URLSearchParams(
          Object.fromEntries(
            Object.entries(params)
              .filter(([, v]) => v !== undefined)
              .map(([k, v]) => [k, String(v)]),
          ),
        ).toString()
      : "";
    return apiClient.get<AdoptionApplicationList>(
      `/admin/adoption-applications${qs}`,
      token,
    );
  },

  updateAdoptionApplication: (
    token: string,
    id: string,
    body: { status?: string; internal_note?: string },
  ) =>
    apiClient.patch<AdoptionApplication>(
      `/admin/adoption-applications/${id}`,
      body,
      token,
    ),

  growthAutomationPolicy: (token: string, tenantId: string) =>
    apiClient.get<GrowthAutomationPolicy>(
      `/admin/company-identification/policies/${tenantId}`,
      token,
    ),

  updateGrowthAutomationPolicy: (
    token: string,
    tenantId: string,
    body: Omit<
      GrowthAutomationPolicy,
      "tenant_id" | "updated_by" | "created_at" | "updated_at" | "persisted"
    >,
  ) =>
    apiClient.put<GrowthAutomationPolicy>(
      `/admin/company-identification/policies/${tenantId}`,
      body,
      token,
    ),

  companyIdentificationProviders: (token: string) =>
    apiClient.get<{
      data: { name: string; healthy: boolean; estimated_cost: number }[];
    }>("/admin/company-identification/providers", token),

  companyCandidates: (
    token: string,
    tenantId: string,
    params?: {
      status?: string;
      confidence_band?: string;
      limit?: number;
      offset?: number;
    },
  ) => {
    const values = { tenant_id: tenantId, ...params };
    const qs = new URLSearchParams(
      Object.entries(values)
        .filter(([, value]) => value !== undefined && value !== "")
        .map(([key, value]) => [key, String(value)]),
    ).toString();
    return apiClient.get<CompanyCandidateList>(
      `/admin/company-identification/candidates?${qs}`,
      token,
    );
  },

  reviewCompanyCandidate: (
    token: string,
    candidateId: string,
    body: {
      decision: "confirm" | "reject" | "correct";
      reason_code?: string;
      note?: string;
      corrected_company_name?: string;
      corrected_domain?: string;
    },
  ) =>
    apiClient.post<CompanyCandidate>(
      `/admin/company-identification/candidates/${candidateId}/review`,
      body,
      token,
    ),

  companyIdentificationMetrics: (token: string, tenantId: string, days = 30) =>
    apiClient.get<CompanyIdentificationMetrics>(
      `/admin/company-identification/metrics?tenant_id=${encodeURIComponent(tenantId)}&days=${days}`,
      token,
    ),

  contactEnrichmentProviders: (token: string) =>
    apiClient.get<{
      contact: { name: string; healthy: boolean; estimated_cost: number }[];
      verification: {
        name: string;
        healthy: boolean;
        estimated_cost: number;
      }[];
    }>("/admin/contact-enrichment/providers", token),

  contactPersonaPolicy: (token: string, tenantId: string) =>
    apiClient.get<ContactPersonaPolicy>(
      `/admin/contact-enrichment/policies/${tenantId}`,
      token,
    ),

  updateContactPersonaPolicy: (
    token: string,
    tenantId: string,
    body: Omit<
      ContactPersonaPolicy,
      "tenant_id" | "updated_by" | "updated_at" | "persisted"
    >,
  ) =>
    apiClient.put<ContactPersonaPolicy>(
      `/admin/contact-enrichment/policies/${tenantId}`,
      body,
      token,
    ),

  contactCandidates: (
    token: string,
    tenantId: string,
    params?: {
      company_identification_id?: string;
      status?: string;
      limit?: number;
      offset?: number;
    },
  ) => {
    const values = { tenant_id: tenantId, ...params };
    const qs = new URLSearchParams(
      Object.entries(values)
        .filter(([, value]) => value !== undefined && value !== "")
        .map(([key, value]) => [key, String(value)]),
    ).toString();
    return apiClient.get<ContactCandidateList>(
      `/admin/contact-enrichment/candidates?${qs}`,
      token,
    );
  },

  enqueueContactEnrichment: (token: string, companyId: string) =>
    apiClient.post<{ job_id: string; status: string }>(
      `/admin/contact-enrichment/companies/${companyId}/enqueue`,
      {},
      token,
    ),

  reviewContactCandidate: (
    token: string,
    candidateId: string,
    body: {
      decision: "approve" | "reject" | "do_not_contact";
      reason_code?: string;
      note?: string;
    },
  ) =>
    apiClient.post<ContactCandidate>(
      `/admin/contact-enrichment/candidates/${candidateId}/review`,
      body,
      token,
    ),

  verifyContactCandidate: (token: string, candidateId: string) =>
    apiClient.post<ContactCandidate>(
      `/admin/contact-enrichment/candidates/${candidateId}/verify-email`,
      {},
      token,
    ),

  convertContactCandidate: (
    token: string,
    candidateId: string,
    body: { note?: string } = {},
  ) =>
    apiClient.post<{ candidate: ContactCandidate; contact_id: string }>(
      `/admin/contact-enrichment/candidates/${candidateId}/convert-to-contact`,
      body,
      token,
    ),

  contactEnrichmentMetrics: (token: string, tenantId: string, days = 30) =>
    apiClient.get<ContactEnrichmentMetrics>(
      `/admin/contact-enrichment/metrics?tenant_id=${encodeURIComponent(tenantId)}&days=${days}`,
      token,
    ),

  outreachDraftPolicy: (token: string, tenantId: string) =>
    apiClient.get<OutreachDraftPolicy>(
      `/admin/outreach/policies/${tenantId}`,
      token,
    ),

  updateOutreachDraftPolicy: (
    token: string,
    tenantId: string,
    body: Omit<
      OutreachDraftPolicy,
      "tenant_id" | "updated_by" | "updated_at" | "persisted"
    >,
  ) =>
    apiClient.put<OutreachDraftPolicy>(
      `/admin/outreach/policies/${tenantId}`,
      body,
      token,
    ),

  outreachDeliveryPolicy: (token: string, tenantId: string) =>
    apiClient.get<OutreachDeliveryPolicy>(
      `/admin/outreach/delivery-policies/${tenantId}`,
      token,
    ),

  updateOutreachDeliveryPolicy: (
    token: string,
    tenantId: string,
    body: Omit<
      OutreachDeliveryPolicy,
      "tenant_id" | "updated_by" | "updated_at" | "persisted" | "readiness"
    >,
  ) =>
    apiClient.put<OutreachDeliveryPolicy>(
      `/admin/outreach/delivery-policies/${tenantId}`,
      body,
      token,
    ),

  outreachMessages: (
    token: string,
    tenantId: string,
    status?: OutreachMessage["status"],
  ) => {
    const qs = new URLSearchParams({ tenant_id: tenantId });
    if (status) qs.set("status", status);
    return apiClient.get<OutreachMessageList>(
      `/admin/outreach/messages?${qs.toString()}`,
      token,
    );
  },

  enqueueOutreachDraft: (token: string, candidateId: string) =>
    apiClient.post<{ job_id: string; status: string }>(
      `/admin/outreach/candidates/${candidateId}/enqueue`,
      {},
      token,
    ),

  reviseOutreachMessage: (
    token: string,
    messageId: string,
    body: { subject: string; body_without_cta: string; note: string },
  ) =>
    apiClient.post<OutreachMessage>(
      `/admin/outreach/messages/${messageId}/revisions`,
      body,
      token,
    ),

  reviewOutreachMessage: (
    token: string,
    messageId: string,
    body: {
      decision: "approve" | "reject";
      reason_code?: string;
      note?: string;
    },
  ) =>
    apiClient.post<OutreachMessage>(
      `/admin/outreach/messages/${messageId}/review`,
      body,
      token,
    ),

  sendOutreachMessage: (
    token: string,
    messageId: string,
    body: { note?: string } = {},
  ) =>
    apiClient.post<{
      message: OutreachMessage;
      job_id?: string;
      duplicate: boolean;
    }>(`/admin/outreach/messages/${messageId}/send`, body, token),

  cancelOutreachMessage: (
    token: string,
    messageId: string,
    body: { note?: string } = {},
  ) =>
    apiClient.post<OutreachMessage>(
      `/admin/outreach/messages/${messageId}/cancel`,
      body,
      token,
    ),

  retryOutreachMessage: (
    token: string,
    messageId: string,
    body: { note?: string } = {},
  ) =>
    apiClient.post<{ message: OutreachMessage; job_id: string }>(
      `/admin/outreach/messages/${messageId}/retry`,
      body,
      token,
    ),

  outreachMessageEvents: (token: string, messageId: string) =>
    apiClient.get<{ data: OutreachDeliveryEvent[] }>(
      `/admin/outreach/messages/${messageId}/events`,
      token,
    ),

  retirementAudit: (token: string) =>
    apiClient.get<RetirementAuditReport>("/admin/retirement-audit", token),

  decideRetirementCandidate: (
    token: string,
    candidateKey: string,
    body: {
      status: "retained" | "approved_removal";
      reason: string;
      telemetry_evidence_ref?: string;
      data_disposition?: "not_applicable" | "retained" | "exported" | "deleted";
      rollback_revision?: string;
      removal_plan_ref?: string;
    },
  ) =>
    apiClient.put<RetirementCandidate>(
      `/admin/retirement-audit/${encodeURIComponent(candidateKey)}/decision`,
      body,
      token,
    ),
};
