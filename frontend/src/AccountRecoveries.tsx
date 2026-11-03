import { useEffect, useRef, useState, FormEvent } from 'react';
import { billingRequest } from './api';
import { t, locale } from './i18n';
import { AuthUser, renderCodeDigits, SecurityPanel } from './Auth';
import './account-recovery.css';

type Recovery = {id:string;email:string;name:string;company:string|null;state:string;created_at:number;expires_at:number;review_reference:string};
export function AccountRecoveries({user,onSecurityReady}:{user:AuthUser;onSecurityReady:()=>void}) {
  const [items,setItems]=useState<Recovery[]>([]);
  const [selectedId,setSelectedId]=useState('');
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const [retry,setRetry]=useState(0);
  const [reference,setReference]=useState('');
  const [email,setEmail]=useState('');
  const [verified,setVerified]=useState(false);
  const [code,setCode]=useState('');
  const [busy,setBusy]=useState(false);
  const pending=useRef(false);
  const digitInputs=useRef<(HTMLInputElement|null)[]>([]);
  const selected=items.find(item=>item.id===selectedId);
  useEffect(()=>{
    let active=true;setLoading(true);setError('');
    billingRequest<{requests:Recovery[]}>('/admin/account-recoveries').then(result=>{
      if(active){setItems(result.requests);setSelectedId(previous=>result.requests.some(item=>item.id===previous)?previous:result.requests[0]?.id||'');}
    }).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[retry]);
  function choose(id:string) {setSelectedId(id);setReference('');setEmail('');setVerified(false);setCode('');setError('');setNotice('');}
  async function review(decision:'approve'|'reject') {
    if(pending.current||!selected||!reference.trim()||email.trim().toLowerCase()!==selected.email||!/^[0-9]{6}$/.test(code)||(decision==='approve'&&!verified))return;
    pending.current=true;setBusy(true);setError('');setNotice('');
    try {
      await billingRequest(`/admin/account-recoveries/${encodeURIComponent(selected.id)}/review`,{decision,reference,email,ownership_verified:verified,code});
      setCode('');setReference('');setEmail('');setVerified(false);
      setNotice(decision==='approve'?t("Freigabe gespeichert. Der einmalige Wiederherstellungslink wurde an das bestätigte Konto gesendet."):t("Wiederherstellung abgelehnt. Das Konto bleibt unverändert."));setRetry(n=>n+1);
    } catch(e){setError((e as Error).message);setCode('');}
    finally{pending.current=false;setBusy(false);}
  }
  function submit(e:FormEvent) {e.preventDefault();void review('approve');}
  const canReview=!!selected&&reference.trim().length>=3&&email.trim().toLowerCase()===selected.email&&/^[0-9]{6}$/.test(code)&&!busy;
  return <section className="page account-recoveries"><header><h1>{t("Kontowiederherstellung")}</h1><p>{t("Anfragen mit bestätigtem Postfach. Prüfe die Kontoinhaberschaft über einen unabhängig bekannten Kontakt oder bestehende Firmenunterlagen. Eine E-Mail allein reicht nicht.")}</p></header>
    {notice&&<p className="pay-notice" role="status">{notice}</p>}
    {error&&<p className="pay-error" role="alert">{t(error)}</p>}
    <button className="ghost" disabled={busy||loading} onClick={()=>setRetry(n=>n+1)}>{t("Erneut laden")}</button>
    {loading?<p role="status">{t("Anfragen werden geladen …")}</p>:!items.length?<p>{t("Keine offenen Wiederherstellungsanfragen.")}</p>:<div className="account-recovery-layout">
      <nav aria-label={t("Wiederherstellungsanfragen")}>{items.map(item=><button disabled={busy} className="panel" key={item.id} aria-pressed={selectedId===item.id} onClick={()=>choose(item.id)}><strong>{item.email}</strong><span>{item.company||item.name}</span><small>{item.state==='approved'?t("Freigegeben · Link erneut senden möglich"):t("Prüfung erforderlich")}</small></button>)}</nav>
      {selected&&<div className="pay-registration">
        {!user.mfa_enabled?<><p>{t("Richte zuerst deinen eigenen Authenticator ein. Jede Freigabe verlangt einen aktuellen Code des Platform Admin.")}</p><SecurityPanel user={user} onReady={onSecurityReady}/></>:<article className="pay-registration-card auth-card">
          <h2>{selected.email}</h2><p>{selected.name} · {selected.company}</p><p>{t("Prüfungsnummer:")} {selected.id}</p><p>{t("Angefordert:")} {new Date(selected.created_at*1000).toLocaleString(locale)}</p>
          <p>{t("Freigabe sendet einen 30 Minuten gültigen Link. Erst dessen Verwendung ändert Passwort und MFA und beendet alle bisherigen Sitzungen.")}</p>
          <form onSubmit={submit}>
            <label>{t("Bestätigte Konto-E-Mail erneut eingeben")}<input type="email" autoComplete="off" required maxLength={320} disabled={busy} value={email} onChange={e=>setEmail(e.target.value)}/></label>
            <label>{t("Referenz der unabhängigen Prüfung")}<input required minLength={3} maxLength={240} disabled={busy} value={reference} onChange={e=>setReference(e.target.value)}/></label>
            <p>{t("Nur die Vorgangsnummer speichern, keine Ausweiskopien oder vertraulichen Nachweise.")}</p>
            <label className="pay-check"><input type="checkbox" disabled={busy} checked={verified} onChange={e=>setVerified(e.target.checked)}/><span>{t("Ich habe die Kontoinhaberschaft unabhängig vom angefragten Postfach geprüft.")}</span></label>
            <p>{t("Bestätige die Entscheidung mit einem neuen Code aus deinem eigenen Authenticator.")}</p>
            {renderCodeDigits(code,setCode,digitInputs,busy)}
            <button className="pay-primary" disabled={!canReview||!verified}>{selected.state==='approved'?t("Neuen Wiederherstellungslink senden"):t("Freigeben und Wiederherstellungslink senden")}</button>
            <button type="button" disabled={!canReview} onClick={()=>void review('reject')}>{t("Anfrage ablehnen")}</button>
          </form>
        </article>}
      </div>}
    </div>}
  </section>;
}
