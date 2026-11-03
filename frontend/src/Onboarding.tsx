import { t } from './i18n';
import { useEffect, useRef, useState } from 'react';
import { ArrowRight, Check, Building2, FileText, ShieldCheck, CreditCard } from 'lucide-react';
import { billingRequest, secureFetch } from './api';
import { Billing } from './Billing';
import { AuthUser, SecurityPanel } from './Auth';
import { CampaignWizard, type Briefing } from './CampaignWizard';
import { JobDescription } from './JobDescription';
import './billing.css';
import './onboarding.css';

type Profile = { industry: string; location: string; brand_description: string; benefits: string; tone: string };
type State = { done: boolean; deferred: boolean; required: boolean; paid: boolean; profile_done: boolean; company: Profile & { id: number; name: string }; campaign: { id: number; status: string; generated: string; generation_mode?: string } | null };
const steps = [
  { label: t('Konto absichern'), icon: ShieldCheck },
  { label: t('Tarif buchen'), icon: CreditCard },
  { label: t('Firmenprofil'), icon: Building2 },
  { label: t('Erster Entwurf'), icon: FileText },
];

export function Onboarding() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [state, setState] = useState<State | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [profile, setProfile] = useState<Profile>({ industry: '', location: '', brand_description: '', benefits: '', tone: t('Freundlich und direkt') });
  const [wizard, setWizard] = useState(false);
  const [briefing, setBriefing] = useState<Briefing>({ role: '', location: '', employment_type: t('Vollzeit'), tasks: '', requirements: '', benefits: '', salary: '', tone: t('Freundlich und direkt'), channels: ['Instagram', 'Meta'] });
  const [wallet, setWallet] = useState<{ managed: boolean; active: boolean; available: number; generation_mode?: string } | null>(null);
  const draftId = useRef<number | null>(null);
  const submitting = useRef(false);
  const key = useRef(crypto.randomUUID());
  const profileCompany = useRef<number | null>(null);
  const loadSequence = useRef(0);
  const stageHeading = useRef<HTMLHeadingElement>(null);

  async function load() {
    const sequence = ++loadSequence.current;
    try {
      const me = await billingRequest<AuthUser>('/auth/me');
      if (sequence !== loadSequence.current) return;
      setUser(me);
      if (me.security_pending) { setState(null); return; }
      const next = await billingRequest<State>('/onboarding');
      if (sequence !== loadSequence.current) return;
      if (!next.required) { window.location.assign('/app'); return; }
      setState(next);
      // Refreshing payment or a failed action must not overwrite unsaved profile input.
      if (profileCompany.current !== next.company.id) {
        profileCompany.current = next.company.id;
        setProfile({ industry: next.company.industry, location: next.company.location, brand_description: next.company.brand_description, benefits: next.company.benefits, tone: next.company.tone || t('Freundlich und direkt') });
      }
      setError('');
    } catch (e) {
      if (sequence === loadSequence.current) setError((e as Error).message);
    }
  }
  useEffect(() => { void load(); return () => { ++loadSequence.current; }; }, []);
  useEffect(() => {
    if (!state || state.paid || busy) return;
    const check = () => { if (document.visibilityState !== 'hidden' && !submitting.current) void load(); };
    const timer = window.setInterval(check, 5000);
    window.addEventListener('focus', check);
    return () => { clearInterval(timer); window.removeEventListener('focus', check); };
  }, [state?.paid, busy]);
  useEffect(() => {
    if (!wizard) return;
    let current = true;
    const update = () => {
      if (document.visibilityState !== 'hidden' && !submitting.current)
        void billingRequest<NonNullable<typeof wallet>>('/tokens/wallet').then(next => { if (current) setWallet(next); }).catch(() => {});
    };
    update();
    const timer = window.setInterval(update, 15000);
    window.addEventListener('focus', update);
    return () => { current = false; clearInterval(timer); window.removeEventListener('focus', update); };
  }, [wizard]);

  async function perform(action: () => Promise<void>) {
    if (submitting.current) return;
    submitting.current = true;
    ++loadSequence.current;
    setBusy(true); setError('');
    try { await action(); await load(); }
    catch (e) { setError((e as Error).message); }
    finally { submitting.current = false; setBusy(false); }
  }
  async function openWizard() {
    await perform(async () => {
      setWallet(await billingRequest<NonNullable<typeof wallet>>('/tokens/wallet'));
      draftId.current = state?.campaign?.id || null;
      if (draftId.current) {
        const campaign = await billingRequest<{ briefing: Briefing }>(`/campaigns/${draftId.current}`);
        setBriefing({ ...campaign.briefing, channels: campaign.briefing.channels.filter(channel => ['Instagram', 'Meta'].includes(channel)) });
      } else setBriefing(p => ({ ...p, location: profile.location, benefits: profile.benefits, tone: profile.tone }));
      setWizard(true);
    });
  }
  async function firstDraft(generate: boolean, testPackage = false) {
    await perform(async () => {
      let id = draftId.current;
      if (!id) {
        const created = await billingRequest<{ id: number }>('/campaigns', { organization_id: state!.company.id, briefing });
        id = created.id; draftId.current = id;
      } else {
        const response = await secureFetch(`/campaigns/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ briefing }) });
        if (!response.ok) throw new Error(t('Das Briefing konnte nicht gespeichert werden.'));
      }
      setState(s => s ? { ...s, campaign: { id: id!, status: 'Draft', generated: '{}' } } : s);
      if (generate) {
        const response = await secureFetch(`/campaigns/${id}/generate${testPackage ? '?test_package=true' : ''}`, { method: 'POST', headers: { 'Idempotency-Key': key.current } });
        if (!response.ok) { const data = await response.json(); throw new Error(data.detail); }
        key.current = crypto.randomUUID();
      } else {
        await billingRequest('/onboarding/defer', { campaign_id: id });
      }
      setWizard(false);
      if (!generate) window.location.assign('/app');
    });
  }
  let jobText = '';
  try { jobText = JSON.parse(state?.campaign?.generated || '{}').jobAd || ''; } catch { /* A malformed saved package remains resumable. */ }
  const activeStep = !user || user.security_pending ? 0 : !state?.paid ? 1 : !state.profile_done ? 2 : 3;
  useEffect(() => { stageHeading.current?.focus(); }, [activeStep, !!state, state?.done, !!jobText]);
  const updateProfile = (field: keyof Profile, value: string) => setProfile(p => ({ ...p, [field]: value }));

  return <main className="pay-registration onboarding">
    <a className="pay-back" href="/">{t('← MH Startseite')}</a>
    <header className="ob-heading"><span className="pay-kicker">{t('DEIN START MIT MH')}</span><h1>{t('In wenigen Schritten zum ersten Entwurf.')}</h1><p>{t('Ein Schritt nach dem anderen. Abgeschlossene Schritte bleiben gespeichert.')}</p></header>
    <ol className="onboarding-steps" aria-label={t('Einrichtungsschritte')}>
      {steps.map(({ label, icon: Icon }, index) => {
        const complete = !!state?.done || (!!user && index < activeStep);
        return <li key={label} className={complete ? 'is-complete' : ''} aria-current={!state?.done && index === activeStep ? 'step' : undefined}><span className="ob-step-icon" aria-hidden="true">{complete ? <Check size={20}/> : <Icon size={20}/>}</span><span><small>{index + 1}</small>{label}{complete && <span className="ob-sr-only"> · {t('Abgeschlossen')}</span>}</span></li>;
      })}
    </ol>
    {error && !wizard && <div className="pay-error" role="alert"><p>{t(error)}</p>{!state && <><button type="button" disabled={busy} onClick={() => perform(async () => {})}>{t('Erneut versuchen')}</button><a href="/app">{t('Zur Anmeldung')}</a></>}</div>}
    {!user && !error && <p role="status">{t('Dein Konto wird geladen …')}</p>}
    {user?.security_pending && <SecurityPanel user={user} onReady={() => { void load(); }}/>} 
    {user && !user.security_pending && !state && !error && <p role="status">{t('Einrichtung wird geladen …')}</p>}
    {user && !user.security_pending && state && <>
      {state.done ? <div className="pay-registration-card"><span className="ob-card-icon" aria-hidden="true"><Check/></span><h2 ref={stageHeading} tabIndex={-1}>{t('Dein Workspace ist eingerichtet.')}</h2><p>{t('Du kannst Entwürfe bearbeiten, prüfen und exportieren. Lade dein Team bei Bedarf unter Settings ein.')}</p><a className="pay-primary ob-link" href="/app">{t('Zum Workspace')} <ArrowRight size={18}/></a></div>
      : !state.paid ? <><div className="ob-stage-intro"><h2 ref={stageHeading} tabIndex={-1}>{t('Wähle deinen Tarif.')}</h2><p>{t('Dein Konto ist abgesichert. Nach bestätigter Zahlung geht es mit dem Firmenprofil weiter. Du kannst die Einrichtung später fortsetzen.')}</p></div><Billing onboarding onConfirmed={()=>{void load();}}/></>
      : !state.profile_done ? <section className="pay-registration-card" aria-labelledby="ob-profile-heading"><span className="pay-kicker">{state.company.name}</span><h2 id="ob-profile-heading" ref={stageHeading} tabIndex={-1}>{t('Firmenprofil')}</h2><p>{t('Drei kurze Angaben reichen für den Start. Alles Weitere kannst du später ergänzen.')}</p>
        <form onSubmit={e => { e.preventDefault(); if (!profile.industry.trim() || !profile.location.trim() || !profile.brand_description.trim()) { setError(t('Branche, Standort und Firmenbeschreibung sind erforderlich.')); return; } void perform(async () => { await billingRequest('/onboarding/profile', profile); }); }}>
          <fieldset disabled={busy} className="ob-fields"><div className="ob-profile-grid">
            <label>{t('Branche')}<input required maxLength={160} value={profile.industry} placeholder={t('Zum Beispiel: Elektrohandwerk oder Pflege')} onChange={e => updateProfile('industry', e.target.value)}/></label>
            <label>{t('Standort')}<input required maxLength={160} autoComplete="address-level2" value={profile.location} placeholder={t('Zum Beispiel: Hamburg')} onChange={e => updateProfile('location', e.target.value)}/></label>
          </div>
          <label>{t('Was zeichnet eure Firma aus?')}<span className="ob-hint">{t('Ein bis zwei Sätze zu eurem Betrieb und eurem Team reichen.')}</span><textarea required maxLength={2000} rows={3} value={profile.brand_description} onChange={e => updateProfile('brand_description', e.target.value)}/></label>
          <details className="ob-optional"><summary>{t('Vorteile & Ton ergänzen (optional)')}</summary><p className="ob-hint">{t('Diese Angaben werden ins Briefing übernommen. Bitte nur belegbare Vorteile nennen.')}</p>
            <label>{t('Vorteile für Bewerber')}<textarea maxLength={2000} rows={3} value={profile.benefits} onChange={e => updateProfile('benefits', e.target.value)}/></label>
            <label>{t('Gewünschter Ton')}<input maxLength={160} list="ob-tones" value={profile.tone} onChange={e => updateProfile('tone', e.target.value)}/><datalist id="ob-tones"><option>{t('Freundlich und direkt')}</option><option>{t('Professionell und sachlich, Sie-Ansprache')}</option><option>{t('Locker und persönlich, Du-Ansprache')}</option></datalist></label>
          </details>
          <button className="pay-primary" type="submit">{busy ? t('Wird gespeichert …') : t('Profil speichern & weiter')} <ArrowRight size={18}/></button></fieldset>
        </form>
      </section>
      : <section className="pay-registration-card" aria-labelledby="ob-draft-heading"><span className="ob-card-icon" aria-hidden="true"><FileText/></span><h2 id="ob-draft-heading" ref={stageHeading} tabIndex={-1}>{t('Dein erster Kampagnenentwurf')}</h2>
        {!jobText ? <><p>{t('Erstelle dein Briefing in vier Schritten. Speichere es ohne Tokenverbrauch und gehe zum Dashboard. Ein erfolgreiches Textpaket kostet 50 MH-Tokens.')}</p><div className="ob-package"><strong>{['Instagram', 'Meta', 'MH'].join(' · ')}</strong><span>{t('Zwei Kanäle und eine gemeinsame Stellenbeschreibung.')}</span></div><button className="pay-primary" disabled={busy} onClick={openWizard}>{state.campaign ? t('Gespeichertes Briefing fortsetzen') : t('Kampagne Schritt für Schritt erstellen')} <ArrowRight size={18}/></button></>
        : <>{state.campaign?.generation_mode === 'local_test' && <p role="status">{t('Testpaket aus lokalen Vorlagen · keine KI-Generierung.')}</p>}<p>{t('Prüfe den Text auf korrekte Angaben. Im Workspace kannst du ihn anschließend bearbeiten und exportieren.')}</p><div className="onboarding-copy"><JobDescription text={jobText}/></div><button className="pay-primary" disabled={busy} onClick={() => perform(async () => {
          const response = await secureFetch(`/campaigns/${state.campaign!.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: 'Review' }) });
          if (!response.ok) throw new Error(t('Entwurf konnte nicht zur Prüfung markiert werden.'));
          await billingRequest('/onboarding/complete', {});
        })}>{t('Entwurf gelesen · Einrichtung abschließen')} <Check size={18}/></button></>}
      </section>}
    </>}
    {wizard && state && <CampaignWizard mode="new" briefing={briefing} setBriefing={setBriefing} orgs={[state.company]} orgId={state.company.id} setOrgId={() => {}} isAgency={false} onClose={() => setWizard(false)} onSave={firstDraft} saveLaterLabel={t("Briefing speichern & zum Dashboard")} busy={busy} error={t(error)} saved={draftId.current !== null} wallet={wallet}/>}
  </main>;
}
