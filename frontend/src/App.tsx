import { t, locale, roleLabel, systemText } from "./i18n";
import "./styles.css";
import { CampaignWizard, type Briefing } from "./CampaignWizard";
import { Billing } from "./Billing";
import "./workspace-theme.css";
import { EmailPreviews } from "./EmailPreviews";
import { AccountRecoveries } from "./AccountRecoveries";
import { JobEngagement } from "./JobCampaign";
import { TrackingAnalytics } from "./Tracking";
import { MetaConnection } from "./SocialPublishing";
import { RecruitingWorkspace } from "./RecruitingWorkspace";
import type { ImageDraft } from "./CampaignImages";
import { ContentStudio } from "./ContentStudio";
import { NextSteps } from "./NextSteps";
import { secureFetch, billingRequest } from "./api";
import { AuthUser, SecurityPanel } from "./Auth";
import { Invitations } from "./Invitations";
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  LayoutDashboard, Users, Megaphone, Sparkles, CheckCircle2, BarChart3,
  Settings, Search, Bell, Plus, ArrowUpRight, ChevronRight,
  CircleCheck, Building2, MapPin, BriefcaseBusiness, Instagram,
  Linkedin, Globe2, LogOut, Trash2, Mail
} from "lucide-react";

type Screen = "recruiting" | "overview" | "customers" | "campaigns" | "studio" | "approvals" | "analytics" | "settings" | "billing" | "emails" | "recovery";
type User = { id: number; email: string; name: string; role: string; base_role: string; organization_id: number | null; security_required:boolean; view_role?:string } & AuthUser;
type ProfileFields = { industry: string; location: string; brand_description: string; benefits: string; tone: string; contact_name: string; contact_email: string; website: string };
type Org = { id: number; name: string } & ProfileFields;
const emptyProfile: ProfileFields = { industry: "", location: "", brand_description: "", benefits: "", tone: "", contact_name: "", contact_email: "", website: "" };
const profileOf = (org: Org): ProfileFields => ({ industry: org.industry, location: org.location, brand_description: org.brand_description, benefits: org.benefits, tone: org.tone, contact_name: org.contact_name, contact_email: org.contact_email, website: org.website });
type Campaign = { id: number; organization_id: number; role: string; location: string; status: "Draft" | "Review" | "Live"; channels: string[]; briefing: Partial<Briefing>; generated: Record<string,string>; change_request: string; updated_at: number; generation_mode?: string; image_revision?:number; briefing_stale?:boolean; briefing_fingerprint?:string };
type ActivityItem = { id: number; organization_id: number; project_id: number; actor: string | null; message: string; created_at: number };
type MetricRow = { project_id: number; channel: string; impressions: number; clicks: number; applications: number; source: string };
type IntegrationStatus = { provider: string; label: string; configured: boolean; model: string };
type AnalyticsData = { campaigns: number; draft: number; review: number; live: number; impressions: number; clicks: number; applications: number; metrics: MetricRow[] };
type DeletionPreview = {
  id: number; name: string; billing_blocked: boolean;
  counts: { users:number; campaigns:number; history:number; metrics:number; invitations:number; credentials:number };
  billing_records: { billing_accounts:number; billing_orders:number; token_ledger:number; invoice_deliveries:number };
};
const emptyBriefing: Briefing = { role: "", location: "", employment_type: t("Vollzeit"), tasks: "", requirements: "", benefits: "", salary: "", tone: t("Freundlich und direkt"), channels: ["Instagram", "Meta"] };
const nav = [
  ["overview", t("Overview"), LayoutDashboard], ["customers", t("Customers"), Users],
  ["campaigns", t("Campaigns"), Megaphone], ["recruiting", t("Recruiting"), BriefcaseBusiness], ["studio", t("Content Studio"), Sparkles],
  ["approvals", t("Approvals"), CheckCircle2], ["analytics", t("Analytics"), BarChart3]
] as const;
const channelIcons: Record<string, React.ElementType> = { Instagram, Facebook: Instagram, LinkedIn: Linkedin, XING: BriefcaseBusiness, Meta: Megaphone, Website: Globe2, Landingpage: Globe2 };

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await secureFetch(path, { ...options, headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers } });
  if (!response.ok) {
    let detail = `${t("Request failed (")}${response.status})`;
    try { const data = await response.json(); detail = typeof data.detail === "string" ? data.detail : detail; } catch { /* Keep status. */ }
    throw new Error(detail);
  }
  return response.json();
}

export function App() {
  const pendingCampaignId = useRef<number | null>(null);
  const submittingBriefing = useRef(false);
  const generationKeys = useRef<Record<number, string>>({});
  const initialSession = useRef<Promise<{authenticated:boolean;user:User|null}>|null>(null);
  const [checkingSession,setCheckingSession] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [screen, setScreen] = useState<Screen>(() => new URLSearchParams(window.location.search).has("social") ? "settings" : new URLSearchParams(window.location.search).has("billing") ? "billing" : "overview");
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [demoOrgs, setDemoOrgs] = useState<Pick<Org, "id" | "name">[]>([]);
  const [studioDrafts,setStudioDrafts] = useState<Record<number,Record<string,string>>>({});
  const [imageDrafts,setImageDrafts] = useState<Record<number,ImageDraft>>({});
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [wallet,setWallet] = useState<{managed:boolean;generation_mode?:string;included:number;purchased:number;available:number;active:boolean;ledger:{included_delta:number;purchased_delta:number;description:string;created_at:number}[]}|null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsData>({ campaigns: 0, draft: 0, review: 0, live: 0, impressions: 0, clicks: 0, applications: 0, metrics: [] });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState("social");
  const [modal, setModal] = useState<"new" | "edit" | null>(null);
  const [formOrgId, setFormOrgId] = useState<number | null>(null);
  const [briefing, setBriefing] = useState<Briefing>(emptyBriefing);
  const [recruitingDirty,setRecruitingDirty] = useState(false);
  const [query, setQuery] = useState("");
  const [showActivity, setShowActivity] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [users, setUsers] = useState<User[]>([]);
  const [newUser, setNewUser] = useState({ email: "", name: "", password: "", role: "kunde", organization_id: 0 });
  const [newOrg, setNewOrg] = useState({ name: "", industry: "", location: "" });
  const [profileOrgId, setProfileOrgId] = useState<number | null>(null);
  const [profileDraft, setProfileDraft] = useState<ProfileFields>(emptyProfile);
  const [metricDraft, setMetricDraft] = useState({ project_id: 0, channel: "Website", impressions: 0, clicks: 0, applications: 0, source: "manual" });
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [integrationDraft, setIntegrationDraft] = useState<Record<string,string>>({});
  const [openAiModel, setOpenAiModel] = useState("");

  const isAgency = user?.role === "platform_admin";
  const canWrite = !!user && ["platform_admin", "firmen_admin", "user"].includes(user.role);
  const canApprove = !!user && ["firmen_admin", "user"].includes(user.role);
  const canRecruit = !!user && !user.view_role && ["firmen_admin","user"].includes(user.role) && !!user.organization_id;
  const canBill = !!user && user.role === "firmen_admin" && user.base_role === "firmen_admin" && !user.view_role && !!user.organization_id;
  useEffect(() => {
    if (user && !canBill && screen === "billing") setScreen("overview");
  }, [user, canBill, screen]);
  function goScreen(next:Screen){if(screen==="recruiting" && recruitingDirty && !window.confirm(t("Ungespeicherte Recruiting-Angaben verwerfen?")))return;setScreen(next);}
  useEffect(()=>{if(user&&!canRecruit&&screen==="recruiting")setScreen("overview");},[user,canRecruit,screen]);
  const canManageUsers = !!user && ["platform_admin", "firmen_admin"].includes(user.role);
  const canManageIntegrations = !!user && ["platform_admin", "firmen_admin"].includes(user.role);
  const selected = campaigns.find(c => c.id === selectedId) || null;
  const hasUnsaved = Object.keys(imageDrafts).length>0 || campaigns.some(c => Object.entries(studioDrafts[c.id] || {}).some(([id,text]) => text !== (c.generated[id] || "")));
  useEffect(() => {
    if (!hasUnsaved) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); };
    window.addEventListener("beforeunload",warn);
    return () => window.removeEventListener("beforeunload",warn);
  },[hasUnsaved]);
  function clearStudioDraft(id:number) { setStudioDrafts(current => {const next={...current};delete next[id];return next;}); }
  const orgName = (id: number) => orgs.find(o => o.id === id)?.name || t("Company");
  const filtered = useMemo(() => campaigns.filter(c => `${c.role} ${c.location} ${orgName(c.organization_id)}`.toLowerCase().includes(query.toLowerCase())), [campaigns, query, orgs]);

  async function refresh(knownUser?:User) {
    const me = knownUser || await request<User>("/auth/me");
    setUser(me);
    if(me.security_pending)return;
    if(me.security_required && me.role==='firmen_admin' && !me.view_role){const setup=await billingRequest<{done:boolean;deferred:boolean}>('/onboarding');if(!setup.done && !setup.deferred){const result=new URLSearchParams(window.location.search).get('billing');window.location.assign('/onboarding'+(['success','cancelled'].includes(result||'')?'?billing='+result:''));return;}}
    const [organizations, projects, events, stats, balance] = await Promise.all([
      request<Org[]>("/organizations"),
      request<Campaign[]>("/campaigns"), request<ActivityItem[]>("/activity"),
      request<AnalyticsData>("/analytics"), request<NonNullable<typeof wallet>>("/tokens/wallet")
    ]);
    setUser(me); setOrgs(organizations); setCampaigns(projects); setActivity(events); setAnalytics(stats); setWallet(balance);
    const profileOrg = organizations.find(org => org.id === profileOrgId) || organizations[0];
    setProfileOrgId(profileOrg?.id || null); setProfileDraft(profileOrg ? profileOf(profileOrg) : emptyProfile);
    if (me.base_role === "platform_admin") {
      const options = await request<{organizations:Pick<Org,"id"|"name">[]}>("/demo/options").catch(() => ({organizations:[]}));
      setDemoOrgs(options.organizations);
    } else setDemoOrgs([]);
    setSelectedId(current => current && projects.some(c => c.id === current) ? current : projects[0]?.id || null);
    setFormOrgId(current => current && organizations.some(o => o.id === current) ? current : organizations[0]?.id || null);
  }

  useEffect(() => {
    let active = true;
    initialSession.current ||= billingRequest<{authenticated:boolean;user:User|null}>('/auth/session');
    initialSession.current.then(async session => {
      if(!active)return;
      if(session.authenticated&&session.user){await refresh(session.user);}
    }).catch(e => {if(active)setError((e as Error).message);})
      .finally(()=>{if(active)setCheckingSession(false);});
    return ()=>{active=false;};
  }, []);
  useEffect(() => { if(!user || user.security_pending)return; const update=()=>request<NonNullable<typeof wallet>>("/tokens/wallet").then(setWallet).catch(()=>{}); const timer=window.setInterval(update,15000); window.addEventListener("focus",update); return ()=>{clearInterval(timer);window.removeEventListener("focus",update);}; },[user,user?.organization_id,user?.view_role,user?.security_pending]);
  useEffect(() => { if (screen === "settings" && canManageUsers && !user?.security_pending) request<User[]>("/users").then(setUsers).catch(e => setError(e.message)); }, [screen, user, canManageUsers]);
  useEffect(() => { if (screen === "customers" && !isAgency) setScreen("campaigns"); }, [screen, isAgency]);
  useEffect(() => { if (screen === "settings" && canManageIntegrations && user && !user.security_pending) request<IntegrationStatus[]>("/settings/integrations").then(items => { setIntegrations(items); setOpenAiModel(items.find(item => item.provider === "openai")?.model || ""); }).catch(e => setError((e as Error).message)); }, [screen, canManageIntegrations, user, user?.role, user?.organization_id]);

  async function login(e: React.FormEvent) {
    e.preventDefault(); setError(""); setBusy(true);
    try {
      await request("/auth/login", { method: "POST", body: JSON.stringify({ email: loginEmail, password: loginPassword }) });
      setStudioDrafts({});setImageDrafts({}); setLoginPassword("");await refresh();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function switchDemo(value: string) {
    if((hasUnsaved || recruitingDirty) && !window.confirm(t("Ungespeicherte Text- und Bildänderungen verwerfen und Demoansicht wechseln?")))return;
    setError(""); setBusy(true);
    const [role, id] = value.split(":");
    try {
      await request("/demo/context", { method: "POST", body: JSON.stringify({ role, organization_id: id ? Number(id) : null }) });
      setStudioDrafts({});setImageDrafts({}); setModal(null); setQuery(""); setShowActivity(false); setIntegrations([]); setIntegrationDraft({});
      await refresh();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function logout() {
    if((hasUnsaved || recruitingDirty) && !window.confirm(t("Ungespeicherte Text- und Bildänderungen verwerfen und abmelden?")))return;
    setStudioDrafts({});setImageDrafts({});
    try { await request("/auth/logout", { method: "POST" }); } catch { /* Local sign out still succeeds. */ }
    setUser(null); setCampaigns([]); setOrgs([]);
  }
  async function run(action: () => Promise<void>) {
    setError(""); setBusy(true);
    let success = false;
    try { await action(); success = true; } catch (e) { setError((e as Error).message); }
    finally {
      try { await refresh(); } catch (e) { setError((e as Error).message); }
      setBusy(false);
    }
    return success;
  }
  function openNew() {
    const org = orgs.find(o => o.id === (isAgency ? profileOrgId : user?.organization_id)) || orgs[0];
    pendingCampaignId.current = null;
    setError("");
    setFormOrgId(org?.id || null);
    setBriefing({ ...emptyBriefing, channels: [...emptyBriefing.channels], location: org?.location || "", benefits: org?.benefits || "", tone: org?.tone || emptyBriefing.tone });
    setModal("new");
  }
  function chooseBriefingOrg(id: number) {
    setFormOrgId(id);
    const org = orgs.find(o => o.id === id);
    if (org && modal === "new") setBriefing(current => ({ ...current, location: org.location, benefits: org.benefits, tone: org.tone || emptyBriefing.tone }));
  }
  async function saveProfile(e: React.FormEvent) {
    e.preventDefault();
    if (!profileOrgId) return;
    await run(async () => { await request(`/organizations/${profileOrgId}`, { method: "PATCH", body: JSON.stringify(profileDraft) }); });
  }
  function openEdit(c: Campaign) { pendingCampaignId.current = null; setError(""); setBriefing({ ...emptyBriefing, ...c.briefing, role: c.role, location: c.location, channels: c.channels.filter(channel=>["Instagram","Meta"].includes(channel)) }); setFormOrgId(c.organization_id); setSelectedId(c.id); setModal("edit"); }
  function openStudio(c: Campaign) { setSelectedId(c.id); setScreen("studio"); setActiveTab("social"); }
  async function requestGeneration(id: number, testPackage = !isAgency && wallet?.generation_mode === "local_test") {
    const key = generationKeys.current[id] || (generationKeys.current[id] = crypto.randomUUID());
    const result = await request<Campaign>(`/campaigns/${id}/generate${testPackage ? "?test_package=true" : ""}`, { method: "POST", headers: { "Idempotency-Key": key } });
    delete generationKeys.current[id];
    return result;
  }
  async function saveBriefing(shouldGenerate: boolean, testPackage = false) {
    if (submittingBriefing.current || !formOrgId) return;
    submittingBriefing.current = true;
    const success = await run(async () => {
      let id = modal === "new" ? pendingCampaignId.current : selected?.id;
      if (!id) {
        const created = await request<Campaign>("/campaigns", { method: "POST", body: JSON.stringify({ organization_id: formOrgId, briefing }) });
        id = created.id;
        pendingCampaignId.current = id;
      } else {
        await request(`/campaigns/${id}`, { method: "PATCH", body: JSON.stringify({ briefing }) });
      }
      setSelectedId(id); setScreen("studio"); setActiveTab("social");
      if (shouldGenerate) await requestGeneration(id, testPackage);
      setModal(null);
      setBriefing({ ...emptyBriefing, channels: [...emptyBriefing.channels] });
    });
    if (success) pendingCampaignId.current = null;
    submittingBriefing.current = false;
  }
  async function updateCampaign(id: number, patch: {status?:string;[key:string]:unknown}) { await run(async () => { await request(`/campaigns/${id}`, { method: "PATCH", body: JSON.stringify({...patch,...(patch.status?{image_revision:campaigns.find(c=>c.id===id)?.image_revision||0}:{})}) }); }); }
  async function generate(id: number) { if (!window.confirm(`${!isAgency && wallet?.generation_mode === "local_test" ? t("Lokaler Test: Das Paket wird aus Vorlagen erstellt. Es werden keine Daten an OpenAI gesendet. 50 Test-Tokens werden nur bei Erfolg abgezogen.") : isAgency || wallet?.managed ? t("Ein neues Textpaket kostet 50 MH-Tokens.") : t("Kostenloses Demo-Paket aus lokalen Vorlagen erstellen?")}${t(" Bestehende Texte werden ersetzt; gespeicherte Versionen bleiben im Verlauf verfügbar. Bitte prüfe anschließend alle Angaben. Bei technischen Fehlern wird kein Guthaben abgezogen.")}`)) return; const ok=await run(async () => { const updated=await requestGeneration(id); setCampaigns(current=>current.map(c=>c.id===id?updated:c)); }); if(ok)clearStudioDraft(id); }
  async function saveContent(c: Campaign, imageEdit?:ImageDraft) {
    const edits = studioDrafts[c.id] || {};
    const ok = await run(async () => {
      const updated = await request<Campaign>(`/campaigns/${c.id}`, {method:"PATCH",body:JSON.stringify({generated:{...c.generated,...edits},...(imageEdit?{image_edit:imageEdit}:{})})});
      setCampaigns(current => current.map(item => item.id === updated.id ? updated : item));
    });
    if(ok)clearStudioDraft(c.id);
    return ok;
  }
  async function createOrg(e: React.FormEvent) { e.preventDefault(); await run(async () => { await request("/organizations", { method: "POST", body: JSON.stringify(newOrg) }); setNewOrg({ name: "", industry: "", location: "" }); }); }
  async function removeCustomer(org: Org) {
    const owned = campaigns.filter(c => c.organization_id === org.id);
    setError("");
    let preview: DeletionPreview;
    try {
      preview = await request<DeletionPreview>(`/organizations/${org.id}/deletion-preview`);
    } catch (e) {
      setError((e as Error).message);
      return;
    }
    if (preview.billing_blocked) {
      window.alert(`${org.name}${t(" kann nicht gelöscht werden.\n\nEs existieren Abrechnungsdaten. Abos und gesetzlich relevante Nachweise müssen zuerst separat geprüft und aufbewahrt werden. Stripe wird durch diese Funktion nicht verändert.")}`);
      return;
    }
    const summary = `${preview.counts.users}${t(" Nutzer, ")}${preview.counts.campaigns}${t(" Kampagnen, ")}${preview.counts.history}${t(" Verlaufseinträge, ")}${preview.counts.metrics}${t(" Kennzahlensätze, ")}${preview.counts.invitations}${t(" Einladungen und ")}${preview.counts.credentials}${t(" Firmenschlüssel")}`;
    const confirmationName = window.prompt(`${org.name}${t(" dauerhaft löschen?\n\nBetroffen: ")}${summary}${t(".\n\nDiese lokalen Daten und das Firmenprofil werden unwiderruflich entfernt. Gib zur Bestätigung den exakten Firmennamen ein:")}`);
    if (confirmationName !== org.name) return;
    await run(async () => {
      await request(`/organizations/${org.id}`, { method: "DELETE", body: JSON.stringify({confirmation_name:confirmationName}) });
      setUsers(current=>current.filter(u=>u.organization_id!==org.id));
      setImageDrafts(current=>{const next={...current};for(const campaign of owned)delete next[campaign.id];return next;});
      setStudioDrafts(current => { const next = { ...current }; for (const campaign of owned) delete next[campaign.id]; return next; });
      if (owned.some(c => c.id === selectedId)) setSelectedId(null);
    });
  }
  function selectMetric(projectId: number, channel: string) {
    const existing = analytics.metrics.find(row => row.project_id === projectId && row.channel === channel);
    setMetricDraft({ project_id: projectId, channel, impressions: existing?.impressions || 0, clicks: existing?.clicks || 0, applications: existing?.applications || 0, source: existing?.source || "manual" });
  }
  async function saveMetric(e: React.FormEvent) {
    e.preventDefault();
    const projectId = metricDraft.project_id || campaigns[0]?.id;
    if (!projectId) return;
    await run(async () => { await request(`/campaigns/${projectId}/metrics`, { method: "PUT", body: JSON.stringify({ ...metricDraft, project_id: undefined }) }); });
  }
  async function saveIntegration(provider: string) {
    const apiKey = integrationDraft[provider]?.trim() || null;
    const saved = await run(async () => {
      await request(`/settings/integrations/${provider}`, { method: "PUT", body: JSON.stringify({ api_key: apiKey, model: provider === "openai" ? openAiModel : null }) });
      setIntegrations(await request<IntegrationStatus[]>("/settings/integrations"));
    });
    if (saved) setIntegrationDraft(current => ({ ...current, [provider]: "" }));
  }
  async function clearIntegration(provider: string) {
    const cleared = await run(async () => {
      await request(`/settings/integrations/${provider}`, { method: "DELETE" });
      setIntegrations(await request<IntegrationStatus[]>("/settings/integrations"));
    });
    if (cleared) setIntegrationDraft(current => ({ ...current, [provider]: "" }));
  }
  async function createUser(e: React.FormEvent) {
    e.preventDefault();
    await run(async () => {
      await request("/users", { method: "POST", body: JSON.stringify({ ...newUser, organization_id: newUser.organization_id || user?.organization_id || orgs[0]?.id }) });
      setUsers(await request<User[]>("/users"));
      setNewUser({ email: "", name: "", password: "", role: "kunde", organization_id: orgs[0]?.id || 0 });
    });
  }

  let plannedTier = "";
  try { plannedTier = sessionStorage.getItem("mh_plan_interest") || ""; } catch { /* Storage is optional. */ }
  if(checkingSession)return <main className="login-page"><div className="login-card panel" role="status">{t("Anmeldestatus wird geprüft …")}</div></main>;
  if(user?.security_pending)return <main className="pay-registration">{error&&<p className="pay-error" role="alert">{t(error)}</p>}<SecurityPanel user={user} onReady={()=>{setError('');void refresh().catch(e=>setError(e.message));}}/></main>;
  if (!user) return <div className="login-page"><form className="login-card panel" onSubmit={login}>
    <div className="brand"><div className="brand-mark">M</div><div><strong>MH</strong><span>{t("Recruiting Workspace")}</span></div></div>
    <a className="login-return" href="/#start">{t("← Zurück zu deiner Tarifplanung")}</a><h1>{t("Im Workspace anmelden")}</h1><p>{t("Melde dich an, um in deinem Firmen-Workspace weiterzuarbeiten. Noch kein Zugang? Erstelle ein Unternehmenskonto.")}</p>{["Starter", "Team", "Scale"].includes(plannedTier) && <div className="login-plan">{t("Deine unverbindliche Planung: MH")} {plannedTier}{t(". Buche deinen Tarif nach der Anmeldung unter „Abo & Tokens“.")}</div>}
    <label>{t("Email")}<input type="email" autoComplete="username" required value={loginEmail} onChange={e => setLoginEmail(e.target.value)} /></label>
    <label>{t("Password")}<input type="password" autoComplete="current-password" required value={loginPassword} onChange={e => setLoginPassword(e.target.value)} /></label>
    <small className="login-help">{t("Nutze die Zugangsdaten, die du für den Pilotbetrieb erhalten hast.")}</small>
    {error && <div className="error">{t(error)}</div>}<button className="primary" disabled={busy}>{t("Anmelden")}</button><p><a className="login-return" href="/auth?action=forgot">{t("Passwort vergessen?")}</a> · <a className="login-return" href="/register">{t("Unternehmenskonto erstellen")}</a></p>
  </form></div>;

  return <div className="shell">
    <aside className="sidebar glass-edge">
      <div className="brand"><div className="brand-mark">M</div><div><strong>MH</strong><span>{t("Recruiting Workspace")}</span></div></div>
      <div className="nav-label">{t("Workspace")}</div><nav>{nav.filter(([id]) => (id !== "customers" || isAgency) && (id !== "recruiting" || canRecruit)).map(([id, label, Icon]) => <button key={id} className={`nav-item ${screen === id ? "active" : ""}`} onClick={() => goScreen(id)}><Icon size={18}/><span>{label}</span>{id === "studio" && hasUnsaved && <em aria-label={t("Unsaved changes")}>●</em>}{id === "approvals" && analytics.review > 0 && <em>{analytics.review}</em>}</button>)}</nav>
      <div className="nav-label bottom-label">{t("System")}</div>{isAgency && !user.view_role && <button className={`nav-item ${screen === "recovery" ? "active" : ""}`} onClick={()=>goScreen("recovery")}><CircleCheck size={18}/><span>{t("Kontowiederherstellung")}</span></button>}{isAgency && !user.view_role && <button className={`nav-item ${screen === "emails" ? "active" : ""}`} onClick={()=>goScreen("emails")}><Mail size={18}/><span>{t("E-Mail-Vorschau")}</span></button>}{canBill && <button className={`nav-item ${screen === "billing" ? "active" : ""}`} onClick={() => goScreen("billing")}><BriefcaseBusiness size={18}/><span>{t("Abo & Tokens")}</span></button>}<button className={`nav-item ${screen === "settings" ? "active" : ""}`} onClick={() => goScreen("settings")}><Settings size={18}/><span>{t("Settings")}</span></button>
      {wallet?.managed && <section className="panel token-wallet" aria-label={t("MH-Token-Guthaben")}>
        <div className="token-wallet-head">
          <p className="token-wallet-balance" aria-live="polite" aria-atomic="true"><strong>{wallet.available.toLocaleString(locale)}</strong><span>{t("MH-Tokens verfügbar")}</span>{wallet.generation_mode === "local_test" && <span className="token-wallet-test">{t("Testumgebung")}</span>}</p>
          {canBill && <button className="text-btn" onClick={()=>goScreen("billing")}>{t("Tokens aufladen")}</button>}
        </div>
        {!wallet.active && <p className="token-wallet-warning" role="status">{t("Gekaufte Tokens bleiben gespeichert. Für die Nutzung ist ein aktives bezahltes Abo erforderlich.")}</p>}
        <details><summary>{t("Details & Verbrauch")}</summary><div className="token-wallet-detail">
          <p>{wallet.included.toLocaleString(locale)} {t("monatlich enthalten ·")} {wallet.purchased.toLocaleString(locale)} {t("gekauft · 50 pro Textpaket")}</p>
          {wallet.generation_mode === "local_test" && <p>{t("Lokale Testumgebung · Testpakete aus Vorlagen für 50 Test-Tokens.")}</p>}
          <p><strong>{t("Letzte Aufladungen und Verbräuche")}</strong></p>{wallet.ledger.map((entry,i)=><p key={i}>{new Date(entry.created_at*1000).toLocaleDateString(locale)} · {systemText(entry.description)} · {entry.included_delta+entry.purchased_delta>0?"+":""}{entry.included_delta+entry.purchased_delta} {t("MH-Tokens")}</p>)}
          <p>{t("Monatliches Guthaben wird zuerst genutzt. Aufladungen werden addiert. MH-Tokens sind Produktguthaben, keine technischen KI-Tokens.")}</p>
        </div></details>
      </section>}
      <div className="user-card"><div className="avatar">{user.name.slice(0,2).toUpperCase()}</div><div><strong>{user.name}</strong><span>{roleLabel(user.role)}</span></div><button className="icon-btn" title={t("Sign out")} onClick={logout}><LogOut size={15}/></button></div>
    </aside>
    <main>
      {(screen === "campaigns" || user.base_role === "platform_admin") && <header className="topbar">
        {screen === "campaigns" && <>
          <div className="search"><Search size={18}/><input placeholder={t("Search campaigns...")} value={query} onChange={e => setQuery(e.target.value)} /></div>
          <div className="top-actions"><button className="icon-btn" title={t("Recent activity")} onClick={() => setShowActivity(!showActivity)}><Bell size={18}/>{activity.length > 0 && <i/>}</button>{canWrite && <button className="primary" onClick={openNew}><Plus size={18}/> {t("New Campaign")}</button>}</div>
        </>}
        {user.base_role === "platform_admin" && <section className="demo-toolbar panel" aria-label={t("Demoansicht wechseln")}>
          <div className="demo-toolbar-intro"><span className="mini">{t("PLATFORM ADMIN · DEMOANSICHT")}</span><strong>{t("Rolle und Firma wechseln")}</strong><p>{t("Änderungen in dieser Ansicht bleiben in einer separaten Demo-Datenbank.")}</p></div>
          <div className="demo-toolbar-controls">
            <label>{t("Rolle")}<select aria-label={t("Rolle auswählen")} disabled={busy || demoOrgs.length === 0} value={user.role} onChange={e => switchDemo(e.target.value === "platform_admin" ? "platform_admin" : `${e.target.value}:${user.organization_id || demoOrgs[0].id}`)}><option value="platform_admin">{t("Platform Admin")}</option><option value="firmen_admin">{t("Firmen Admin")}</option><option value="user">{t("User")}</option><option value="kunde">{t("Kunde")}</option></select></label>
            <label>{t("Firma")}<select aria-label={t("Firma auswählen")} disabled={busy || user.role === "platform_admin" || demoOrgs.length === 0} value={user.role === "platform_admin" ? "" : user.organization_id || ""} onChange={e => switchDemo(`${user.role}:${e.target.value}`)}><option value="">{t("Alle Firmen")}</option>{demoOrgs.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}</select></label>
          </div>
        </section>}
      </header>}
      {error && (screen !== "studio" || !selected) && <div className="error inline" role="alert">{t(error)}<button onClick={() => setError("")}>×</button></div>}

      {screen === "campaigns" && showActivity && <div className="activity-popover panel"><strong>{t("Recent activity")}</strong>{activity.length ? activity.map(a => <Activity key={a.id} title={`${a.actor || "Team"}: ${systemText(a.message)}`} time={new Date(a.created_at * 1000).toLocaleString(locale)} />) : <p>{t("No activity yet.")}</p>}</div>}
      {screen === "overview" && <div className="page"><section className="hero"><div><span className="eyebrow">{t("Recruiting workspace")}</span><h1>{t("Good morning,")} {user.name.split(" ")[0]}.</h1><p>{t("Your campaigns and approvals in one place.")}</p></div><button className="ghost" onClick={() => setScreen("analytics")}>{t("View performance")} <ArrowUpRight size={16}/></button></section>
        <div className="stats"><Stat label={t("Campaigns")} value={analytics.campaigns}/><Stat label={t("Awaiting approval")} value={analytics.review}/><Stat label={t("Live")} value={analytics.live}/><Stat label={t("Drafts")} value={analytics.draft}/></div>
        <section className="two-col"><div className="panel"><div className="panel-head"><div><span className="mini">{t("CURRENT WORK")}</span><h2>{t("Campaigns")}</h2></div><button className="text-btn" onClick={() => setScreen("campaigns")}>{t("View all")} <ChevronRight size={15}/></button></div><div className="campaign-list">{campaigns.length ? campaigns.slice(0, 6).map(c => <CampaignRow key={c.id} campaign={c} customer={orgName(c.organization_id)} onClick={() => openStudio(c)}/>) : <p className="empty">{t("No campaigns yet.")}</p>}</div></div><div className="panel"><NextSteps campaigns={campaigns} canWrite={canWrite} canApprove={canApprove} orgName={orgName} onOpen={openStudio}/><details className="dashboard-activity"><summary>{t("Aktivitätsverlauf")}</summary>{activity.length ? activity.slice(0,5).map(a => <Activity key={a.id} title={`${a.actor || "Team"}: ${systemText(a.message)}`} time={new Date(a.created_at * 1000).toLocaleString(locale)}/>) : <p className="empty">{t("No activity yet.")}</p>}</details></div></section>
      </div>}
      {screen === "emails" && isAgency && !user.view_role && <EmailPreviews/>}
      {screen === "recovery" && isAgency && !user.view_role && <AccountRecoveries user={user} onSecurityReady={()=>void refresh().catch(e=>setError(e.message))}/>}
      {screen === "customers" && isAgency && <div className="page">
        <PageTitle eyebrow="CRM" title={t("Customers")} subtitle={t("Companies in the workspace.")}/>
        <div className="customer-grid">{orgs.map(o => <article className={`customer-card panel ${profileOrgId === o.id ? "selected" : ""}`} key={o.id}><button type="button" className="customer-open" onClick={() => { setProfileOrgId(o.id); setProfileDraft(profileOf(o)); }}><div className="customer-top"><div className="company-logo large">{o.name.slice(0,1)}</div><span className="soft-badge">{o.industry}</span></div><h3>{o.name}</h3><p><MapPin size={14}/>{o.location}</p><div className="divider"/><span>{campaigns.filter(c => c.organization_id === o.id).length} {t("campaigns")}</span></button><button type="button" className="ghost-small customer-delete" disabled={busy} aria-label={t("Kunde {name} löschen", {name:o.name})} onClick={() => removeCustomer(o)}><Trash2 size={14}/> {t("Kunde löschen")}</button></article>)}{!orgs.length && <p className="empty">{t("Noch keine Firmen.")}</p>}</div>
        {profileOrgId && <form className="panel simple-form" onSubmit={saveProfile}><h2>{orgs.find(o => o.id === profileOrgId)?.name} {t("· Profil")}</h2><div className="form-grid">
          <label>{t("Branche")}<input value={profileDraft.industry} onChange={e => setProfileDraft({...profileDraft, industry:e.target.value})}/></label>
          <label>{t("Standort")}<input value={profileDraft.location} onChange={e => setProfileDraft({...profileDraft, location:e.target.value})}/></label>
          <label>{t("Ansprechpartner")}<input value={profileDraft.contact_name} onChange={e => setProfileDraft({...profileDraft, contact_name:e.target.value})}/></label>
          <label>{t("Kontakt-E-Mail")}<input type="email" value={profileDraft.contact_email} onChange={e => setProfileDraft({...profileDraft, contact_email:e.target.value})}/></label>
          <label>Website<input type="url" value={profileDraft.website} onChange={e => setProfileDraft({...profileDraft, website:e.target.value})}/></label>
          <label>{t("Tonalität")}<input value={profileDraft.tone} onChange={e => setProfileDraft({...profileDraft, tone:e.target.value})}/></label>
          <label className="wide">{t("Arbeitgeberprofil")}<textarea value={profileDraft.brand_description} onChange={e => setProfileDraft({...profileDraft, brand_description:e.target.value})}/></label>
          <label className="wide">{t("Benefits")}<textarea value={profileDraft.benefits} onChange={e => setProfileDraft({...profileDraft, benefits:e.target.value})}/></label>
        </div><button className="primary" disabled={busy}>{t("Profil speichern")}</button></form>}
        <form className="panel simple-form" onSubmit={createOrg}><h2>{t("Add company")}</h2><div className="form-grid"><label>Name<input required minLength={2} value={newOrg.name} onChange={e => setNewOrg({...newOrg,name:e.target.value})}/></label><label>{t("Industry")}<input value={newOrg.industry} onChange={e => setNewOrg({...newOrg,industry:e.target.value})}/></label><label>{t("Location")}<input value={newOrg.location} onChange={e => setNewOrg({...newOrg,location:e.target.value})}/></label></div><button className="primary" disabled={busy}>{t("Add company")}</button></form>
      </div>}
      {screen === "campaigns" && <div className="page"><PageTitle eyebrow="PIPELINE" title={t("Campaigns")} subtitle={t("Every recruiting project from briefing to live campaign.")}/><div className="panel table-card"><div className="table-head"><span>{t("Campaign")}</span><span>{t("Channels")}</span><span>Status</span></div>{filtered.map(c => <button className="table-row table-button" key={c.id} onClick={() => openStudio(c)}><div><strong>{c.role}</strong><small>{orgName(c.organization_id)} · {c.location}</small></div><div className="chips">{c.channels.map(x => <i key={x}>{x}</i>)}</div><span className={`status ${c.status.toLowerCase()}`}>{t(c.status)}</span></button>)}{!filtered.length && <p className="empty">{t("No campaigns found.")}</p>}</div></div>}
      {screen === "recruiting" && canRecruit && <RecruitingWorkspace key={selectedId} campaign={selected} campaigns={campaigns} onCampaign={setSelectedId} onNew={openNew} onStudio={id=>{setSelectedId(id);setScreen("studio");}} onRefresh={()=>refresh()} canWrite={canWrite && (!wallet?.managed || wallet.active)} onDirty={setRecruitingDirty}/>}
      {screen === "studio" && <div className="page">{selected ? <><ContentStudio key={`${selected.id}:${user.id}:${user.role}:${user.organization_id}:${user.view_role||''}`} imageDraft={imageDrafts[selected.id]} onImageDraft={draft=>setImageDrafts(current=>{const next={...current};if(draft)next[selected.id]=draft;else delete next[selected.id];return next;})} onImagesCommitted={async()=>{await refresh();}} onConfirmBriefing={()=>updateCampaign(selected.id,{reviewed_briefing:selected.briefing_fingerprint})} campaign={selected} orgName={orgName} activeTab={activeTab} onTab={setActiveTab} drafts={studioDrafts[selected.id] || {}} onChange={(id,value)=>setStudioDrafts(current=>({...current,[selected.id]:{...current[selected.id],[id]:value}}))} onSave={imageEdit=>saveContent(selected,imageEdit)} onDiscard={()=>clearStudioDraft(selected.id)} onEdit={()=>openEdit(selected)} onGenerate={()=>generate(selected.id)} canEdit={canWrite && selected.status!=="Live"} busy={busy} error={t(error)} cost={wallet?.generation_mode === "local_test" && !isAgency ? t("Lokale Testumgebung · Testpakete aus Vorlagen für 50 Test-Tokens.") : isAgency ? t("50 Tokens bei verwalteten Firmenkonten · Demos kostenlos") : wallet?.managed ? `${wallet.available.toLocaleString(locale)}${t(" Tokens verfügbar · 50 pro Textpaket")}` : t("Demo-Vorlagen · kostenlos")}/></> : <section className="panel cs-empty"><span className="mini">MH CONTENT STUDIO</span><h1>{t("Deine nächste Kampagne beginnt mit einem Briefing.")}</h1><p>{t("Erstelle ein Briefing und bearbeite anschließend eure Texte für Instagram und Meta.")}</p>{canWrite && <button className="primary" onClick={openNew}>{t("Kampagne erstellen")}</button>}</section>}</div>}
      {screen === "approvals" && <div className="page"><PageTitle eyebrow="QUALITY CONTROL" title={t("Approvals")} subtitle="Review campaign content before it goes live."/><div className="approval-list">{campaigns.filter(c => c.status === "Review").map(c => <div className="panel approval-card" key={c.id}><div><span className="mini">{orgName(c.organization_id)}</span><h3>{c.role}</h3><p>{c.location} · {c.channels.join(" · ")}</p></div><div className="approval-actions"><button className="ghost-small" onClick={() => openStudio(c)}>{t("Review content")}</button>{canApprove && <button className="ghost-small" disabled={busy} onClick={() => { const reason = window.prompt(t("What should be changed?")); if (reason?.trim()) updateCampaign(c.id,{change_request:reason.trim()}); }}>{t("Request changes")}</button>}{canApprove && <button className="primary small" disabled={busy || !!imageDrafts[c.id] || Object.entries(studioDrafts[c.id] || {}).some(([id,text])=>text!==(c.generated[id] || ""))} onClick={() => updateCampaign(c.id,{status:"Live"})}><CheckCircle2 size={15}/> {t("Approve")}</button>}</div></div>)}{!campaigns.some(c => c.status === "Review") && <div className="panel empty">{t("No campaigns awaiting approval.")}</div>}</div></div>}
      {screen === "analytics" && <div className="page"><PageTitle eyebrow="PERFORMANCE" title={t("Analytics")} subtitle={t("Bestätigte Bewerbungseingänge und getrennte manuelle Kennzahlen.")}/><JobEngagement campaigns={campaigns}/><TrackingAnalytics campaigns={campaigns} canReadApplications={!user.view_role && ["firmen_admin","user"].includes(user.role)}/><details><summary>{t("Manuell erfasste Kennzahlen · ohne bestätigten Bewerbungseingang")}</summary>
        <div className="stats"><Stat label={t("Campaigns")} value={analytics.campaigns}/><Stat label={t("Impressionen")} value={analytics.impressions}/><Stat label={t("Klicks")} value={analytics.clicks}/><Stat label={t("Bewerbungen")} value={analytics.applications}/></div>
        <div className="panel pipeline"><h2>{t("Kampagnenstatus")}</h2><div className="pipeline-bar">{(["Draft","Review","Live"] as const).map(status => { const count = analytics[status.toLowerCase() as "draft"|"review"|"live"]; return count > 0 && <div key={status} className={status.toLowerCase()} style={{width:`${count / analytics.campaigns * 100}%`}} title={`${t(status)}: ${count.toLocaleString(locale)}`}/>; })}</div><div className="pipeline-legend">{t("Entwurf:")} {analytics.draft} {t("· Prüfung:")} {analytics.review} {t("· Live:")} {analytics.live}</div></div>
        {canWrite && campaigns.length > 0 && <form className="panel simple-form" onSubmit={saveMetric}><h2>{t("Kennzahlen erfassen")}</h2><p>{t("Gesamtwerte für eine Kampagne und einen Kanal eintragen. Bestehende Werte werden ersetzt.")}</p><div className="form-grid">
          <label>{t("Kampagne")}<select value={metricDraft.project_id || campaigns[0].id} onChange={e => selectMetric(Number(e.target.value), metricDraft.channel)}>{campaigns.map(c => <option key={c.id} value={c.id}>{c.role} · {orgName(c.organization_id)}</option>)}</select></label>
          <label>{t("Kanal")}<select value={metricDraft.channel} onChange={e => selectMetric(metricDraft.project_id || campaigns[0].id, e.target.value)}>{["Website","Instagram","Facebook","LinkedIn","XING","Meta"].map(channel => <option key={channel}>{channel}</option>)}</select></label>
          <label>{t("Impressionen")}<input type="number" min="0" value={metricDraft.impressions} onChange={e => setMetricDraft({...metricDraft, impressions:Number(e.target.value)})}/></label>
          <label>{t("Klicks")}<input type="number" min="0" value={metricDraft.clicks} onChange={e => setMetricDraft({...metricDraft, clicks:Number(e.target.value)})}/></label>
          <label>{t("Bewerbungen")}<input type="number" min="0" value={metricDraft.applications} onChange={e => setMetricDraft({...metricDraft, applications:Number(e.target.value)})}/></label>
          <label>{t("Quelle")}<input value={metricDraft.source} onChange={e => setMetricDraft({...metricDraft, source:e.target.value})}/></label>
        </div><button className="primary" disabled={busy}>{t("Kennzahlen speichern")}</button></form>}
        {analytics.metrics.length > 0 && <section className="panel metrics-table"><h2>{t("Erfasste Werte")}</h2>{analytics.metrics.map(row => <div key={`${row.project_id}:${row.channel}`} className="metric-row"><strong>{campaigns.find(c => c.id === row.project_id)?.role || `${t("Kampagne ")}${row.project_id}`} · {row.channel}</strong><span>{row.impressions} {t("Impressionen ·")} {row.clicks} {t("Klicks ·")} {row.applications} {t("Bewerbungen")}</span><small>{t("Quelle:")} {row.source}</small></div>)}</section>}
      </details></div>}
      {screen === "billing" && canBill && <Billing/>}
      {screen === "settings" && <div className="page"><PageTitle eyebrow="SYSTEM" title={t("Settings")} subtitle="Konto, Benutzer und Integrationen verwalten."/>
        <div className="panel settings-card"><h2>{t("Angemeldet als")}</h2><p>{user.name} · {user.email}</p><p>{t("Rolle:")} {roleLabel(user.role)}</p><p>{t("Firma:")} {user.organization_id ? orgName(user.organization_id) : t("FLH / alle Firmen")}</p><button className="ghost" onClick={logout}><LogOut size={15}/> {t("Abmelden")}</button></div>
        {canBill && <MetaConnection/>}
        {canManageIntegrations && <section className="panel settings-card"><h2>{t("Integrationen und API-Schlüssel")}</h2><p>{isAgency ? t("OpenAI wird zentral vom Platform Admin verwaltet.") : t("LinkedIn und XING werden nur für deine Firma verwaltet. Facebook wird über die eigene Unternehmensseite verbunden.")} {t("Bezahlte KI-Entwürfe senden Briefing und Firmenname an OpenAI. Demo-Konten nutzen Vorlagen. LinkedIn- und XING-Schlüssel werden noch nicht zur Veröffentlichung verwendet.")}</p><div className="integrations-grid">{integrations.filter(item => item.provider!=="meta").map(item => <div className="integration-row" key={item.provider}><div><strong>{item.label}</strong><span>{item.configured ? t("Schlüssel gespeichert") : t("Kein Schlüssel gespeichert")}</span></div><label>{t("Zugangsschlüssel")}<input type="password" autoComplete="off" value={integrationDraft[item.provider] || ""} placeholder={item.configured ? t("Neuen Schlüssel zum Ersetzen eingeben") : t("Schlüssel eingeben")} onChange={e => setIntegrationDraft({...integrationDraft,[item.provider]:e.target.value})}/></label>{item.provider === "openai" && <label>{t("Modell")}<input value={openAiModel} placeholder={t("z. B. gpt-4.1-mini")} onChange={e => setOpenAiModel(e.target.value)}/></label>}<div className="integration-actions"><button className="primary small" disabled={busy || (!integrationDraft[item.provider]?.trim() && !(item.provider === "openai" && openAiModel.trim()))} onClick={() => saveIntegration(item.provider)}>{t("Speichern")}</button>{item.configured && <button className="ghost-small" disabled={busy} onClick={() => clearIntegration(item.provider)}>{t("Entfernen")}</button>}</div></div>)}</div></section>}
        {canManageUsers && <div className="panel settings-card"><h2>{t("Users")}</h2><div className="user-list">{users.map(u => <div key={u.id}><strong>{u.name}</strong><span>{u.email} · {roleLabel(u.role)} · {u.organization_id ? orgName(u.organization_id) : "FLH"}</span></div>)}</div>{user.role==="firmen_admin"&&!user.view_role?<Invitations/>:<form onSubmit={createUser}><h3>{t("Add user")}</h3><div className="form-grid"><label>Name<input required value={newUser.name} onChange={e => setNewUser({...newUser,name:e.target.value})}/></label><label>{t("Email")}<input type="email" required value={newUser.email} onChange={e => setNewUser({...newUser,email:e.target.value})}/></label><label>{t("Password (15+ characters)")}<input type="password" required minLength={15} value={newUser.password} onChange={e => setNewUser({...newUser,password:e.target.value})}/></label><label>{t("Role")}<select value={newUser.role} onChange={e => setNewUser({...newUser,role:e.target.value})}><option value="firmen_admin">{t("Firmen Admin")}</option><option value="user">{t("User")}</option><option value="kunde">{t("Kunde")}</option></select></label><label>{t("Company")}<select value={newUser.organization_id || (user.organization_id || orgs[0]?.id || 0)} onChange={e => setNewUser({...newUser,organization_id:Number(e.target.value)})}>{orgs.map(o => <option value={o.id} key={o.id}>{o.name}</option>)}</select></label></div><button className="primary" disabled={busy}>{t("Add user")}</button></form>}</div>}
      </div>}
    </main>
    {modal && <CampaignWizard mode={modal} briefing={briefing} setBriefing={setBriefing} orgs={orgs} orgId={formOrgId} setOrgId={chooseBriefingOrg} isAgency={isAgency} onClose={() => setModal(null)} onSave={saveBriefing} busy={busy} error={t(error)} saved={pendingCampaignId.current !== null} wallet={wallet}/>}
  </div>;
}

function Stat({label,value}:{label:string,value:number}) { return <div className="stat-card panel"><span>{t(label)}</span><strong>{value.toLocaleString(locale)}</strong></div>; }
function PageTitle({eyebrow,title,subtitle}:{eyebrow:string,title:string,subtitle:string}) { return <section className="hero compact"><div><span className="eyebrow">{t(eyebrow)}</span><h1>{title}</h1><p>{t(subtitle)}</p></div></section>; }
function Activity({title,time}:{title:string,time:string}) { return <div className="activity"><div className="activity-icon"><CircleCheck size={15}/></div><div><strong>{title}</strong><span>{time}</span></div></div>; }
function CampaignRow({campaign,customer,onClick}:{campaign:Campaign,customer:string,onClick:()=>void}) { return <button className="campaign-row row-button" onClick={onClick}><div className="campaign-main"><div className="company-logo">{customer.slice(0,1)}</div><div><strong>{campaign.role}</strong><span><Building2 size={13}/>{customer} <b>•</b> <MapPin size={13}/>{campaign.location}</span><div className="chips">{campaign.channels.map(c => { const Icon = channelIcons[c] || Megaphone; return <i key={c}><Icon size={12}/>{c}</i>; })}</div></div></div><span className={`status ${campaign.status.toLowerCase()}`}>{t(campaign.status)}</span></button>; }
