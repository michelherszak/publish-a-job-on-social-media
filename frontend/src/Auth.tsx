import { t } from "./i18n";
import { FormEvent, Dispatch, SetStateAction, RefObject, useEffect, useRef, useState } from 'react';
import { billingRequest } from './api';
import { authenticatorQr } from './authenticatorQr';
import { ArrowRight, KeyRound, Mail, ShieldCheck } from 'lucide-react';
import './billing.css';

export type AuthUser = {email:string; email_verified:boolean; mfa_enabled:boolean; mfa_required:boolean; mfa_ok:boolean; security_pending:boolean};
type AuthenticatorSetup = {secret:string;uri:string;website?:string};
export function renderCodeDigits(code:string,setCode:Dispatch<SetStateAction<string>>,digitInputs:RefObject<(HTMLInputElement|null)[]>,busy:boolean) {
  function focusDigit(index:number) {
    digitInputs.current?.[index]?.focus();
    digitInputs.current?.[index]?.select();
  }
  function enterDigits(index:number,value:string) {
    const digits=value.replace(/[^0-9]/g,'').slice(0,6);
    if(value&&!digits)return;
    const start=digits.length===6?0:index;
    setCode(previous=>{
      const next=previous.padEnd(6,' ').split('');
      if(!digits)next[start]=' ';
      else for(let offset=0;offset<digits.length&&start+offset<6;offset++)next[start+offset]=digits[offset];
      return next.join('').trimEnd();
    });
    if(digits)focusDigit(Math.min(start+digits.length,5));
  }
  return <fieldset className="auth-code" disabled={busy}>
          <legend>{t("Aktueller sechsstelliger Code")}</legend>
          <div className="auth-code-digits">{Array.from({length:6},(_,index)=><input key={index} ref={element=>{if(digitInputs.current)digitInputs.current[index]=element;}} aria-label={t("Ziffer {position} von 6",{position:index+1})} type="text" required autoComplete={index===0?"one-time-code":"off"} inputMode="numeric" maxLength={6} pattern="[0-9]" value={code[index]?.trim()||''} onFocus={e=>e.currentTarget.select()} onChange={e=>enterDigits(index,e.target.value)} onPaste={e=>{e.preventDefault();enterDigits(index,e.clipboardData.getData('text'));}} onKeyDown={e=>{
            if(e.key==='Backspace') {
              e.preventDefault();const target=code[index]?.trim()?index:Math.max(0,index-1);
              enterDigits(target,'');focusDigit(target);
            } else if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)) {
              e.preventDefault();focusDigit(e.key==='Home'?0:e.key==='End'?5:Math.max(0,Math.min(5,index+(e.key==='ArrowLeft'?-1:1))));
            }
          }}/> )}</div>
        </fieldset>;
}

export function SecurityPanel({user,onReady}:{user:AuthUser;onReady:()=>void}) {
  const [secret,setSecret]=useState('');
  const [qrCode,setQrCode]=useState('');
  const [qrError,setQrError]=useState(false);
  const [website,setWebsite]=useState('');
  const [code,setCode]=useState('');
  const [codes,setCodes]=useState<string[]>([]);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const [busy,setBusy]=useState(false);
  const [usingRecovery,setUsingRecovery]=useState(false);
  const [reconnecting,setReconnecting]=useState(false);
  const actionPending=useRef(false);
  const digitInputs=useRef<(HTMLInputElement|null)[]>([]);
  const reconnectProof=user.mfa_enabled&&reconnecting&&!secret;
  const recoveryInput=reconnectProof||usingRecovery;
  const Icon=!user.email_verified?Mail:codes.length?KeyRound:ShieldCheck;

  async function perform(action:()=>Promise<void>) {
    if(actionPending.current)return;
    actionPending.current=true;setBusy(true);setError('');
    try{await action();}catch(e){setError((e as Error).message);}
    finally{actionPending.current=false;setBusy(false);}
  }
  async function showSetup(setup:AuthenticatorSetup) {
    setSecret(setup.secret);setWebsite(setup.website||'');setQrCode('');setQrError(false);
    try{setQrCode(await authenticatorQr(setup.uri,setup.secret,user.email,setup.website));}
    catch{setQrError(true);}
  }
  function changeMode(reconnect:boolean,recovery:boolean) {
    setReconnecting(reconnect);setUsingRecovery(recovery);setCode('');setError('');setNotice('');
    setSecret('');setWebsite('');setQrCode('');setQrError(false);
  }
  async function submit(e:FormEvent) {
    e.preventDefault();
    if(!recoveryInput&&!/^[0-9]{6}$/.test(code)) {
      digitInputs.current?.[Array.from({length:6},(_,index)=>index).find(index=>!/[0-9]/.test(code[index]||''))??0]?.focus();
      return;
    }
    await perform(async()=>{
      if(reconnectProof) {
        const setup=await billingRequest<AuthenticatorSetup>('/auth/mfa/reconnect',{code});
        await showSetup(setup);setCode('');setUsingRecovery(false);
        setNotice(t("Der verwendete Wiederherstellungscode ist jetzt verbraucht."));
        return;
      }
      const result=await billingRequest<{recovery_codes:string[]}>('/auth/mfa/'+(user.mfa_enabled?'challenge':'confirm'),{code});
      setCode('');setSecret('');setWebsite('');setQrCode('');setQrError(false);setNotice('');
      if(result.recovery_codes.length)setCodes(result.recovery_codes);else onReady();
    });
  }
  const heading=!user.email_verified?t("E-Mail bestätigen"):codes.length?t("Wiederherstellungscodes sichern"):reconnecting?t("Authenticator-App verbinden"):user.mfa_enabled?t("Anmeldung bestätigen"):t("Authenticator einrichten");
  const qrSetup=<>
    <p>{t("Öffne deine Authenticator-App und füge ein neues Konto hinzu. Scanne anschließend den QR-Code.")}</p>
    {!secret?<button className="pay-primary" disabled={busy} onClick={()=>perform(async()=>showSetup(await billingRequest<AuthenticatorSetup>('/auth/mfa/setup',{})))}>{t("Authenticator einrichten")}</button>:<>
      {qrCode&&<div className="auth-qr"><img src={qrCode} alt={t("QR-Code für deine Authenticator-App")} width={240} height={240}/><p>{t("Scanne diesen Code nur mit deiner Authenticator-App.")}</p></div>}
      {qrError&&<p className="pay-notice" role="status">{t("Der QR-Code konnte nicht angezeigt werden. Du kannst den Schlüssel manuell in deiner Authenticator-App eingeben.")}</p>}
      <div className="auth-setup-identity">
        {website&&<p><strong>{t("Website")}</strong><br/>{website}</p>}
        <p><strong>{t("Benutzerkonto")}</strong><br/>{user.email}</p>
        <p>{t("Zeitbasiert, 6 Stellen, 30 Sekunden.")}</p>
      </div>
      <details className="auth-manual" open={qrError||undefined}><summary>{t("Einrichtung ohne Kamera")}</summary><label>{t("Einrichtungsschlüssel (nur in deiner Authenticator-App verwenden)")}<input readOnly autoComplete="off" spellCheck={false} value={secret}/></label></details>
    </>}
  </>;
  return <section className="pay-registration-card auth-card" aria-labelledby="auth-security-heading">
    <span className="auth-icon" aria-hidden="true"><Icon size={24}/></span><h1 id="auth-security-heading">{heading}</h1>
    {!user.email_verified?<>
      <p>{t("Bestätige die Nachricht an")} {user.email}{t(". Der Link gilt eine Stunde. Danach geht es mit der Absicherung und Tarifbuchung weiter.")}</p>
      <button className="pay-primary" disabled={busy} onClick={onReady}>{t("Bestätigung prüfen")} <ArrowRight size={18} aria-hidden="true"/></button>
      <button disabled={busy} onClick={()=>perform(async()=>{const r=await billingRequest<{message:string;local_mail:boolean}>('/auth/resend',{email:user.email});setNotice(r.local_mail?t("Lokaler Test: Die E-Mail liegt geschützt im Ordner backend/mail_outbox."):t(r.message));})}>{t("Bestätigungs-E-Mail erneut anfordern")}</button>
    </>:codes.length?<>
      <p>{t("Diese Codes werden nur jetzt angezeigt. Jeder Code kann einmal verwendet werden, wenn deine Authenticator-App nicht verfügbar ist. Bewahre sie in deinem Passwortmanager auf.")}</p>
      <pre className="auth-secret">{codes.join('\n')}</pre>
      <button className="pay-primary" onClick={onReady}>{t("Codes gesichert · weiter")} <ArrowRight size={18} aria-hidden="true"/></button>
    </>:<>
      {reconnectProof?<>
        <p>{t("Gib einen unbenutzten MH-Wiederherstellungscode ein. Danach zeigen wir den QR-Code für dein Konto, damit du die Authenticator-App verbinden kannst.")}</p>
        <p>{t("Ohne Wiederherstellungscode ist eine geprüfte Kontowiederherstellung erforderlich.")}</p>
      </>:!user.mfa_enabled||reconnecting?qrSetup:<p>{usingRecovery?t("Gib einen unbenutzten Wiederherstellungscode ein."):t("Öffne deine Authenticator-App und gib den aktuellen sechsstelligen Code ein.")}</p>}
      {(secret||user.mfa_enabled)&&<form onSubmit={submit}>
        {recoveryInput?<label>{t("Wiederherstellungscode")}<input required disabled={busy} autoComplete="off" inputMode="text" minLength={6} maxLength={100} value={code} onChange={e=>setCode(e.target.value.trim())}/></label>:renderCodeDigits(code,setCode,digitInputs,busy)}
        <button className="pay-primary" disabled={busy||(!recoveryInput&&!/^[0-9]{6}$/.test(code))}>{reconnectProof?t("QR-Code anzeigen"):t("Code bestätigen")} <ArrowRight size={18} aria-hidden="true"/></button>
      </form>}
      {user.mfa_enabled&&(reconnecting?<button className="auth-alternative" type="button" disabled={busy} onClick={()=>changeMode(false,false)}>{t("Zur Code-Eingabe")}</button>:<>
        <button className="auth-alternative" type="button" disabled={busy} onClick={()=>changeMode(false,!usingRecovery)}>{usingRecovery?t("Authenticator-App verwenden"):t("Wiederherstellungscode verwenden")}</button>
        <p className="auth-connect-hint">{t("Noch keinen MH-Eintrag in deiner Authenticator-App?")}</p>
        <button className="auth-alternative" type="button" disabled={busy} onClick={()=>changeMode(true,false)}>{t("Authenticator-App verbinden")}</button>
      </>)}
      {user.mfa_enabled&&<p><a href="/auth?action=recover">{t("Authenticator und Wiederherstellungscodes verloren?")}</a></p>}
    </>}
    {notice&&<p role="status" className="pay-notice">{notice}</p>}{error&&<p role="alert" className="pay-error">{t(error)}</p>}
    <p className="auth-footer"><button disabled={busy} onClick={()=>perform(async()=>{await billingRequest('/auth/logout',{});window.location.assign('/app');})}>{t("Abmelden")}</button></p>
  </section>;
}

export function AuthPage(){
  const [params]=useState(()=>new URLSearchParams(window.location.hash.slice(1)||window.location.search));
  useEffect(()=>{if(window.location.hash)history.replaceState(null,'',window.location.pathname);},[]);
  const action=params.get('action')||'forgot';const token=params.get('token')||'';
  const [email,setEmail]=useState('');const [password,setPassword]=useState('');const [name,setName]=useState('');const [recoveryCode,setRecoveryCode]=useState('');
  const [notice,setNotice]=useState('');const [error,setError]=useState('');const [busy,setBusy]=useState(false);const [done,setDone]=useState(false);
  const [confirmPassword,setConfirmPassword]=useState('');const [caseId,setCaseId]=useState('');
  const requestPending=useRef(false);
  const isRecovery=['recover','recover-verify','recover-reset'].includes(action);
  const verificationStarted=useRef(false);
  useEffect(()=>{
    if(action!=='verify'||verificationStarted.current)return;
    verificationStarted.current=true;
    if(!token){setError(t("Der Bestätigungslink ist unvollständig. Fordere einen neuen Link an."));return;}
    setBusy(true);
    void billingRequest('/auth/verify-email',{token})
      .then(()=>{setNotice(t("E-Mail bestätigt. Melde dich an, um dein Konto einzurichten."));setDone(true);})
      .catch(e=>setError((e as Error).message))
      .finally(()=>setBusy(false));
  },[action,token]);
  const title=isRecovery?t("Kontozugang wiederherstellen"):action==='verify'?t("E-Mail bestätigen"):action==='invite'?t("Einladung annehmen"):action==='resend'?t("Bestätigung erneut anfordern"):action==='reset'?t("Neues Passwort setzen"):t("Passwort vergessen");
  async function submit(e:FormEvent){e.preventDefault();if(requestPending.current)return;requestPending.current=true;setBusy(true);setError('');try{
    if(action==='recover-verify') {
      if(!token)throw new Error(t("Wiederherstellungsanfrage ist ungültig oder abgelaufen."));
      const result=await billingRequest<{case_id:string}>('/auth/recovery/verify',{token});setCaseId(result.case_id);setDone(true);
      setNotice(t("Postfach bestätigt. Dein MH-Betreiber muss nun die Kontoinhaberschaft unabhängig prüfen. Nach Freigabe erhältst du einen weiteren Link per E-Mail."));
    } else if(action==='recover-reset') {
      if(!token)throw new Error(t("Wiederherstellungsanfrage ist ungültig oder abgelaufen."));
      if(password!==confirmPassword)throw new Error(t("Die Passwörter stimmen nicht überein."));
      await billingRequest('/auth/recovery/reset',{token,password});setPassword('');setConfirmPassword('');setDone(true);
      setNotice(t("Kontozugang wiederhergestellt. Melde dich mit deinem neuen Passwort an und richte einen neuen Authenticator ein. Alle bisherigen Sitzungen und Codes sind ungültig."));
    } else if(action==='reset'){await billingRequest('/auth/reset-password',{token,password,recovery_code:recoveryCode});setNotice(t("Passwort geändert. Alle bisherigen Sitzungen wurden beendet. Bitte neu anmelden."));setDone(true);}
    else if(action==='invite'){await billingRequest('/auth/accept-invite',{token,password,name});setNotice(t("Einladung angenommen. Dein Konto gehört zum eingeladenen Firmen-Workspace. Bitte anmelden."));setDone(true);}
    else{const r=await billingRequest<{message:string;local_mail:boolean}>('/auth/'+(action==='recover'?'recovery/request':action==='resend'?'resend':'forgot'),{email});setNotice(r.local_mail?t(r.message)+' ' + t('Lokaler Test: Nachricht in backend/mail_outbox öffnen.'):t(r.message));}
  }catch(e){setError((e as Error).message);}finally{requestPending.current=false;setBusy(false);}}
  async function cancelRecovery() {
    if(requestPending.current)return;requestPending.current=true;setBusy(true);setError('');
    try{await billingRequest('/auth/recovery/cancel',{token});setDone(true);setNotice(t("Wiederherstellungsanfrage abgebrochen. Dein Passwort und Authenticator bleiben unverändert."));}
    catch(e){setError((e as Error).message);}finally{requestPending.current=false;setBusy(false);}
  }
  return <main className="pay-registration"><a className="pay-back" href="/app">{t("← Zur Anmeldung")}</a><div className={`pay-registration-card${isRecovery?' auth-card':''}`}>{isRecovery&&<span className="auth-icon" aria-hidden="true"><ShieldCheck size={24}/></span>}<h1>{title}</h1>
    {isRecovery&&!done&&<p>{action==='recover'?t("Authenticator und Codes verloren? Bestätige zuerst dein Postfach. Dein MH-Betreiber prüft anschließend die Kontoinhaberschaft unabhängig, bevor ein neuer Authenticator eingerichtet werden kann."):action==='recover-verify'?t("Bestätige diese Anfrage nur, wenn du sie selbst gestellt hast. Das bestätigt dein Postfach und startet die unabhängige Prüfung; dein Authenticator bleibt zunächst unverändert."):t("Die Wiederherstellung wurde freigegeben. Setze ein neues Passwort. Alle bisherigen Sitzungen, Authenticator- und Recovery-Codes werden ungültig. Nach der Anmeldung musst du einen neuen QR-Code scannen und neue Recovery-Codes sichern.")}</p>}
    {action==='verify'&&!done&&<p role="status">{busy?t("Der Bestätigungslink wird geprüft …"):error?t("Fordere bei Bedarf einen neuen Link an."):t("Bestätigung wird vorbereitet …")}</p>}{!done&&action!=='verify'&&<form onSubmit={submit}>
    {['forgot','resend','recover'].includes(action)&&<label>{t("Geschäftliche E-Mail")}<input type="email" required autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)}/></label>}
    {action==='invite'&&<label>{t("Dein Name")}<input required minLength={2} value={name} onChange={e=>setName(e.target.value)}/></label>}
    {['reset','invite','recover-reset'].includes(action)&&<label>{t("Neues Passwort (mindestens 15 Zeichen)")}<input type="password" minLength={15} maxLength={128} autoComplete="new-password" required value={password} onChange={e=>setPassword(e.target.value)}/></label>}
    {action==='recover-reset'&&<label>{t("Neues Passwort wiederholen")}<input type="password" required autoComplete="new-password" minLength={15} maxLength={128} value={confirmPassword} onChange={e=>setConfirmPassword(e.target.value)}/></label>}
    {action==='reset'&&<label>{t("Wiederherstellungscode (bei aktivierter Zwei-Faktor-Anmeldung erforderlich)")}<input autoComplete="off" value={recoveryCode} onChange={e=>setRecoveryCode(e.target.value)}/></label>}
    <button className="pay-primary" disabled={busy}>{busy?t("Wird geprüft …"):action==='recover'?t("Wiederherstellung anfordern"):action==='recover-verify'?t("Postfach bestätigen und Prüfung anfordern"):action==='recover-reset'?t("Passwort ändern und Authenticator neu einrichten"):title}</button></form>}
    {isRecovery&&!done&&token&&<button type="button" disabled={busy} onClick={cancelRecovery}>{t("Diese Anfrage abbrechen")}</button>}
    {notice&&<p className="pay-notice" role="status">{notice}</p>}{caseId&&<p>{t("Prüfungsnummer:")} <strong>{caseId}</strong></p>}{error&&<p className="pay-error" role="alert">{t(error)}</p>}<p><a href="/app">{t("Zur Anmeldung")}</a> · <a href={isRecovery?'/auth?action=recover':'/auth?action=resend'}>{isRecovery?t("Neue Wiederherstellungsanfrage"):t("Neue Bestätigung anfordern")}</a></p>{!isRecovery&&<p><a href="/auth?action=recover">{t("Authenticator und Wiederherstellungscodes verloren?")}</a></p>}</div></main>;
}
