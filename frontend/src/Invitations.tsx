import { t, locale, roleLabel } from "./i18n";
import { FormEvent, useEffect, useState } from 'react';
import { billingRequest } from './api';
type Invite={email:string;role:string;expires_at:number};
export function Invitations(){
  const [email,setEmail]=useState('');const [role,setRole]=useState('user');const [pending,setPending]=useState<Invite[]>([]);
  const [notice,setNotice]=useState('');const [error,setError]=useState('');const [busy,setBusy]=useState(false);
  async function refresh(){setPending(await billingRequest<Invite[]>('/auth/invitations'));}
  useEffect(()=>{void refresh().catch(e=>setError(e.message));},[]);
  async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError('');try{const r=await billingRequest<{local_mail:boolean}>('/auth/invitations',{email,role});setEmail('');setNotice(r.local_mail?t("Einladung vorbereitet. Im lokalen Test liegt sie geschützt in backend/mail_outbox."):t("Einladung versendet. Sie gilt 48 Stunden."));await refresh();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  async function revoke(email:string){setBusy(true);setError('');try{await billingRequest('/auth/invitations/revoke',{email});await refresh();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  return <section><h3>{t("Teammitglied einladen")}</h3><p>{t("Die eingeladene Person legt ihr Passwort selbst fest. Die Einladung gilt nur für diese Firma und die ausgewählte Rolle.")}</p><form onSubmit={submit}><div className="form-grid"><label>{t("Geschäftliche E-Mail")}<input type="email" required autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)}/></label><label>{t("Rolle")}<select value={role} onChange={e=>setRole(e.target.value)}><option value="user">{t("Bearbeiter")}</option><option value="kunde">{t("Kunde · nur lesen")}</option><option value="firmen_admin">{t("Firmen-Admin · Zwei-Faktor-Anmeldung erforderlich")}</option></select></label></div><button className="primary" disabled={busy}>{t("Einladung senden")}</button></form>{notice&&<p role="status">{notice}</p>}{error&&<p role="alert" className="error">{t(error)}</p>}{!!pending.length&&<><h3>{t("Offene Einladungen")}</h3>{pending.map(i=><div className="user-list" key={i.email}><p>{i.email} · {roleLabel(i.role)} {t("· gültig bis")} {new Date(i.expires_at*1000).toLocaleString(locale)}</p><button disabled={busy} onClick={()=>{void revoke(i.email);}}>{t("Einladung widerrufen")}</button></div>)}</>}</section>;
}
