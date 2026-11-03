import { t } from "./i18n";
import { useEffect, useRef, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { ArrowRight, Check, ChevronLeft, Sparkles, X } from "lucide-react";
import "./campaign-wizard.css";

export type Briefing = { role: string; location: string; employment_type: string; tasks: string; requirements: string; learnable_requirements?: string; working_hours?: string; benefits: string; salary: string; tone: string; channels: string[] };
type Props = {
  mode: "new" | "edit"; briefing: Briefing; setBriefing: Dispatch<SetStateAction<Briefing>>;
  orgs: { id: number; name: string }[]; orgId: number | null; setOrgId: (id: number) => void;
  isAgency: boolean; onClose: () => void; onSave: (generate: boolean, testPackage?: boolean) => void; saveLaterLabel?: string;
  busy: boolean; error: string; saved: boolean;
  wallet: { managed: boolean; active: boolean; available: number; generation_mode?: string } | null;
};
const steps = [t("Stelle"), t("Profil & Angebot"), t("Kanäle"), t("Prüfen")];
const channels = [
  ["Instagram", t("Kurze Texte für eure visuellen Social-Posts.")],
  ["Meta", t("Anzeigenvarianten für Facebook und Instagram.")],
];

export function CampaignWizard({ mode, briefing, setBriefing, orgs, orgId, setOrgId, isAgency, onClose, onSave, saveLaterLabel, busy, error, saved, wallet }: Props) {
  const [step, setStep] = useState(0);
  const [returnToReview, setReturnToReview] = useState(false);
  const [attempted, setAttempted] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [factsConfirmed, setFactsConfirmed] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const initialBriefing = useRef(JSON.stringify(briefing));
  function close() {
    if (busy) return;
    if (JSON.stringify(briefing) !== initialBriefing.current && !window.confirm(t("Fenster schließen? Nicht gespeicherte Änderungen gehen verloren. Mit „Briefing speichern“ kannst du später fortsetzen."))) return;
    onClose();
  }
  const heading = useRef<HTMLHeadingElement>(null);
  const validRole = briefing.role.trim().length >= 2;
  const validLocation = briefing.location.trim().length >= 2;
  const canSave = !!orgId && validRole;
  const valid = !!orgId && validRole && validLocation && briefing.channels.length > 0;
  const paidLabel = isAgency || wallet?.managed;
  const localTest = !isAgency && wallet?.generation_mode === 'local_test';
  const blocked = !isAgency && (!wallet || (wallet.managed && (!wallet.active || wallet.available < 50)));
  const field = (key: keyof Briefing, value: string) => { setBriefing(p => ({ ...p, [key]: value })); setConfirmed(false); setFactsConfirmed(false); };
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    dialog.current?.showModal();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = overflow; previous?.focus(); };
  }, []);
  useEffect(() => { heading.current?.focus(); }, [step]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, []);
  function advance() {
    setAttempted(true);
    if (step === 0 && (!validRole || !validLocation || !orgId)) return;
    if (step === 2 && !briefing.channels.length) return;
    setAttempted(false); setStep(n => returnToReview ? 3 : n + 1); setReturnToReview(false);
  }
  const missing = [!briefing.tasks.trim() && t("Aufgaben"), !briefing.requirements.trim() && t("Anforderungen"), !briefing.benefits.trim() && t("Benefits"), !briefing.salary.trim() && t("Gehalt")].filter(Boolean);
  return <dialog ref={dialog} className="campaign-wizard" aria-labelledby="campaign-heading" onCancel={e => { e.preventDefault(); if (!busy) close(); }}>
    <header className="cw-header"><div><span className="mini">{t("MH · KAMPAGNENBRIEFING")}</span><h2>{mode === "new" ? t("Die nächste passende Bewerbung beginnt hier.") : t("Ein gutes Briefing macht den Unterschied.")}</h2><p>{t("Beschreibe die Stelle. Prüfe dein Paket. Gib deinem Team einen guten Entwurf.")}</p></div><button type="button" className="ghost cw-close" aria-label={t("Briefing schließen")} disabled={busy} onClick={close}><X size={20}/></button></header>
    <nav aria-label={t("Fortschritt")}><ol className="cw-steps">{steps.map((label, index) => <li key={label} aria-current={step === index ? "step" : undefined}><span>{index < step ? <Check size={16}/> : index + 1}</span>{label}</li>)}</ol></nav>
    <form onSubmit={e => { e.preventDefault(); if (busy) return; if (step < 3) advance(); else if (valid && (mode === "edit" || (confirmed && factsConfirmed && !blocked))) onSave(mode === "new", localTest); }}>
      <fieldset disabled={busy} className="cw-fields">
        {wallet?.managed && !wallet.active && <p className="cw-feedback cw-error" role="status">{t("Für das Speichern und Erstellen ist ein aktives Abo erforderlich. Prüfe „Abo & Tokens“ im Workspace.")}</p>}
        <section className="cw-body">
          <div className="cw-intro"><span className="mini">{t("SCHRITT")} {step + 1} {t("VON 4")}</span><h2 id="campaign-heading" ref={heading} tabIndex={-1}>{[t("Wen möchtet ihr einstellen?"), t("Was macht die Stelle konkret?"), t("Wo möchtet ihr Menschen erreichen?"), t("Passt alles für euren Entwurf?")][step]}</h2><p>{[t("Zum Speichern reicht der Stellentitel. Vor der Texterstellung den tatsächlichen Arbeitsort ergänzen."), t("Konkrete, belegbare Angaben helfen der KI. Alle Felder auf dieser Seite sind optional."), t("Wähle mindestens einen geplanten Kanal. Du kannst die Texte anschließend selbst bearbeiten."), t("Prüfe die Fakten und den Verbrauch, bevor du das Paket erstellst.")][step]}</p></div>
          {step === 0 && <div className="form-grid">
            <label className="wide">{t("Unternehmen")}<select value={orgId || ""} disabled={!isAgency || mode === "edit" || saved} onChange={e => setOrgId(Number(e.target.value))}>{!orgId && <option value="">{t("Unternehmen auswählen")}</option>}{orgs.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}</select></label>
            <label className="wide">{t("Stellentitel")} <span className="cw-hint">{t("Zum Beispiel: Elektroniker für Betriebstechnik (m/w/d)")}</span><input autoComplete="off" maxLength={180} value={briefing.role} aria-invalid={attempted && !validRole} aria-describedby={attempted && !validRole ? "cw-role-error" : undefined} onChange={e => field("role", e.target.value)}/>{attempted && !validRole && <span role="alert" className="cw-error" id="cw-role-error">{t("Bitte einen Stellentitel mit mindestens 2 Zeichen eingeben.")}</span>}</label>
            <label>{t("Arbeitsort")}<span className="cw-hint">{t("Zum Beispiel: Hamburg · 2 Tage mobil")}</span><input maxLength={180} value={briefing.location} aria-invalid={attempted && !validLocation} aria-describedby={attempted && !validLocation ? "cw-location-error" : undefined} onChange={e => field("location", e.target.value)}/>{attempted && !validLocation && <span role="alert" className="cw-error" id="cw-location-error">{t("Bitte einen Arbeitsort mit mindestens 2 Zeichen eingeben.")}</span>}</label>
            <label>{t("Beschäftigung (optional)")}<span className="cw-hint">{t("Zum Beispiel: Vollzeit, 38 Std./Woche")}</span><input maxLength={180} value={briefing.employment_type} onChange={e => field("employment_type", e.target.value)}/></label>
            <aside className="cw-tip wide">{t("Tipp: Nutze einen verständlichen Stellentitel und beschreibe den tatsächlichen Arbeitsort. Firmenangaben werden aus eurem Profil übernommen, soweit vorhanden.")}</aside>
          </div>}
          {step === 1 && <div className="form-grid">
            <label className="wide">{t("Aufgaben")}<span className="cw-hint">{t("Was tut die Person im Alltag? Drei bis fünf konkrete Aufgaben reichen.")}</span><textarea maxLength={4000} placeholder={t("Zum Beispiel: Anlagen warten, Störungen analysieren, Reparaturen dokumentieren …")} value={briefing.tasks} onChange={e => field("tasks", e.target.value)}/></label>
            <label className="wide">{t("Notwendige Voraussetzungen")}<span className="cw-hint">{t("Trenne unverzichtbare Kenntnisse von dem, was man bei euch lernen kann.")}</span><textarea maxLength={4000} placeholder={t("Erforderlich: …\\nVon Vorteil: …")} value={briefing.requirements} onChange={e => field("requirements", e.target.value)}/></label>
            <label className="wide">{t("Bei uns lernbar")}<span className="cw-hint">{t("Diese Fähigkeiten sind keine Voraussetzung für eine Bewerbung.")}</span><textarea maxLength={4000} value={briefing.learnable_requirements||""} onChange={e=>field("learnable_requirements",e.target.value)}/></label>
            <label className="wide">{t("Tatsächliche Arbeitszeiten")}<input maxLength={500} value={briefing.working_hours||""} onChange={e=>field("working_hours",e.target.value)}/></label>
            <label className="wide">{t("Benefits & Arbeitsbedingungen")}<span className="cw-hint">{t("Was bietet ihr wirklich? Prüfe auch die Angaben aus eurem Firmenprofil.")}</span><textarea maxLength={4000} placeholder={t("Zum Beispiel: 30 Urlaubstage, feste Schichten, bezahlte Weiterbildung …")} value={briefing.benefits} onChange={e => field("benefits", e.target.value)}/></label>
            <label>{t("Gehalt (optional)")}<input maxLength={300} placeholder={t("Zum Beispiel: 45.000–55.000 € brutto/Jahr")} value={briefing.salary} onChange={e => field("salary", e.target.value)}/></label>
            <label>{t("Tonalität (optional)")}<input maxLength={300} list="cw-tones" value={briefing.tone} onChange={e => field("tone", e.target.value)}/><datalist id="cw-tones"><option>{t("Freundlich und direkt")}</option><option>{t("Professionell und sachlich, Sie-Ansprache")}</option><option>{t("Locker und persönlich, Du-Ansprache")}</option></datalist></label>
          </div>}
          {step === 2 && <><div className="cw-channels">{channels.map(([name, description]) => <label className={briefing.channels.includes(name) ? "is-selected" : ""} key={name}><input type="checkbox" checked={briefing.channels.includes(name)} onChange={() => { setBriefing(p => ({ ...p, channels: p.channels.includes(name) ? p.channels.filter(c => c !== name) : [...p.channels, name] })); setConfirmed(false); }}/><span><strong>{name}</strong><small>{description}</small></span></label>)}</div>{attempted && !briefing.channels.length && <p role="alert" className="cw-error">{t("Wähle mindestens einen Kanal aus.")}</p>}<aside className="cw-tip">{t("Das Paket enthält Texte für Instagram und Meta sowie die gemeinsame Stellenbeschreibung auf MH. Deine Auswahl markiert die geplanten Kanäle und ändert den Paketpreis nicht. Eigene Bilder kannst du im Studio hinzufügen. KI-Bilder, Videos und Werbebudget sind nicht enthalten.")}</aside></>}
          {step === 3 && <>
            <div className="cw-summary">{[
              [t("Stelle"), `${orgs.find(o => o.id === orgId)?.name || "—"} · ${briefing.role}`, `${briefing.location} · ${briefing.employment_type || t("Beschäftigung nicht angegeben")}`, 0],
              [t("Profil & Angebot"), `${t("Aufgaben: ")}${briefing.tasks || t("Nicht angegeben")}${t("\nAnforderungen: ")}${briefing.requirements || t("Nicht angegeben")}\n${t("Bei uns lernbar")}: ${briefing.learnable_requirements || t("Nicht angegeben")}\n${t("Tatsächliche Arbeitszeiten")}: ${briefing.working_hours || t("Nicht angegeben")}`, `${t("Benefits: ")}${briefing.benefits || t("Nicht angegeben")}${t("\nGehalt: ")}${briefing.salary || t("Nicht angegeben")}${t("\nTonalität: ")}${briefing.tone || t("Nicht angegeben")}`, 1],
              [t("Geplante Kanäle"), briefing.channels.join(" · "), t("Instagram, Meta und die MH-Bewerbungsseite im Paket enthalten"), 2],
            ].map(([title, text, detail, target]) => <section key={title}><div><h3>{title}</h3><p>{text}</p><p>{detail}</p></div><button type="button" className="text-btn" aria-label={`${title}${t(" ändern")}`} onClick={() => { setStep(Number(target)); setReturnToReview(true); setConfirmed(false); }}>{t("Ändern")}</button></section>)}</div>
            {!!missing.length && <p className="cw-tip">{t("Noch offen:")} {missing.join(", ")}{t(". Du kannst fortfahren und diese Angaben später ergänzen. Prüfe, ob der Entwurf dadurch zu allgemein bleibt.")}</p>}
            {mode === "new" && <label className="cw-consent"><input type="checkbox" checked={factsConfirmed} onChange={e=>setFactsConfirmed(e.target.checked)}/><span>{t("Ich habe die Angaben und übernommenen Vorteile geprüft. Unbekannte Fakten bleiben offen; unzutreffende Aussagen habe ich entfernt.")}</span></label>}
            {mode === "new" ? <div className="cw-cost"><Sparkles size={23}/><div><h3>{isAgency ? t("50 MH-Tokens bei verwalteten Firmenkonten") : wallet ? wallet.managed ? localTest ? t("50 Test-Tokens für ein Testpaket") : t("50 MH-Tokens für ein Kampagnenpaket") : t("Kostenloses Demo-Paket") : t("Guthaben wird geladen")}</h3><p>{isAgency ? t("Verwaltete Firmenkonten benötigen ein aktives Abo und 50 Tokens. Demo-Firmen verwenden kostenlose lokale Vorlagen. Das Guthaben prüft der Server vor der Erstellung.") : wallet?.managed ? `${t("Verfügbar: ")}${wallet.available} Tokens${!blocked ? `${t(" · Nach erfolgreicher Erstellung: ")}${wallet.available - 50}` : ""}${t(". Bei technischen Fehlern wird kein Guthaben abgezogen.")}` : wallet ? t("Demo-Konten erstellen lokale Vorlagentexte ohne KI-Aufruf und ohne Tokenverbrauch.") : t("Vor der Erstellung wird dein Guthaben geprüft.")}</p>{paidLabel && <p>{localTest ? t("Lokaler Test: Das Paket wird aus Vorlagen erstellt. Es werden keine Daten an OpenAI gesendet. 50 Test-Tokens werden nur bei Erfolg abgezogen.") : t("Firmenname und Briefing werden zur Texterstellung an OpenAI übermittelt. Bitte keine Bewerberdaten oder vertraulichen Informationen eingeben.")}</p>}{blocked && <p className="cw-error">{!wallet ? t("Bitte warte auf die Guthabenprüfung.") : !wallet.active ? t("Ein aktives bezahltes Abo ist für das Speichern und die Erstellung erforderlich. Prüfe „Abo & Tokens“ im Workspace.") : t("Es fehlen Tokens. Lade unter „Abo & Tokens“ Guthaben auf oder speichere zunächst das Briefing.")}</p>}<label className="cw-consent"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/><span>{localTest ? t("Ich möchte das lokale Testpaket für 50 Test-Tokens erstellen und die Texte anschließend prüfen.") : paidLabel ? t("Ich möchte das Paket für 50 MH-Tokens erstellen und die Texte anschließend prüfen.") : t("Ich möchte kostenlose Demo-Texte erstellen und anschließend prüfen.")}</span></label></div></div> : <aside className="cw-tip">{t("Das Speichern ändert nur das Briefing und verbraucht keine Tokens. Bereits erstellte Texte bleiben erhalten. Neue Texte kannst du danach separat erstellen.")}</aside>}
            <p className="cw-hint">{t("Danach: Texte prüfen und bearbeiten → zur Freigabe geben → exportieren. Es wird nichts automatisch veröffentlicht.")}</p>
          </>}
        </section>
        <footer className="cw-footer"><div>{step > 0 && <button type="button" className="ghost" onClick={() => { setStep(n => n - 1); setReturnToReview(false); setAttempted(false); }}><ChevronLeft size={16}/> {t("Zurück")}</button>}</div><div>{canSave && <button type="button" className="ghost" disabled={!!wallet?.managed && !wallet.active} onClick={() => onSave(false)}>{mode === "new" ? saveLaterLabel || t("Briefing speichern & später fortsetzen") : t("Briefing speichern")}</button>}{step < 3 ? <button className="primary">{returnToReview ? t("Zur Prüfung") : t("Weiter")} <ArrowRight size={16}/></button> : mode === "new" ? <button className="primary" disabled={!valid || !confirmed || !factsConfirmed || blocked}><Sparkles size={16}/>{localTest ? t("Testpaket für 50 Tokens erstellen") : paidLabel ? t("Paket für 50 Tokens erstellen") : t("Demo-Paket erstellen")}</button> : null}</div></footer>
      </fieldset>
      {busy && <div className="cw-feedback" role="status"><span className="cw-pulse"/>{t("Dein Briefing wird verarbeitet. Bei der Texterstellung kann das einen Moment dauern. Bitte lass dieses Fenster geöffnet.")}</div>}
      {error && <div className="cw-feedback cw-error" role="alert"><strong>{t("Das hat noch nicht geklappt.")}</strong><p>{error}</p>{saved && <p>{t("Dein Briefing ist gespeichert. Versuche die Erstellung erneut oder schließe das Fenster und kehre später zur Kampagne zurück.")}</p>}</div>}
    </form>
  </dialog>;
}
