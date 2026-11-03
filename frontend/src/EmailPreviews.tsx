import { t } from "./i18n";
import { useEffect, useState } from 'react';
import { Mail, Monitor, Smartphone, RefreshCw } from 'lucide-react';
import { billingRequest } from './api';
import './email-previews.css';
type Preview = {id:string;label:string;description:string;subject:string;sender:string;recipient:string;content_type:string;text:string};
const loadEmailPreviews = () => billingRequest<{previews:Preview[]}>('/admin/email-previews');
export function EmailPreviews({loadPreviews = loadEmailPreviews}:{loadPreviews?: typeof loadEmailPreviews} = {}){
  const [items,setItems]=useState<Preview[]>([]);
  const [selected,setSelected]=useState('registration');
  const [mode,setMode]=useState<'rendered'|'text'>('rendered');
  const [mobile,setMobile]=useState(false);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');
  const [retry,setRetry]=useState(0);
  useEffect(()=>{let active=true;setLoading(true);setError('');loadPreviews().then(data=>{if(active)setItems(data.previews);}).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[retry,loadPreviews]);
  const preview=items.find(item=>item.id===selected)||items[0];
  return <section className="email-previews page"><header className="ep-header"><span className="mini">{t("PLATFORM ADMIN · VORLAGEN")}</span><h1>{t("E-Mail-Vorschau")}</h1><p>{t("So sehen die automatischen Nachrichten von MH aus.")}</p></header>
    <div className="ep-notice"><Mail size={19}/><div><strong>{t("Beispieldaten · Kein Versand")}</strong><p>{t("Alle Ansichten verwenden dieselben Vorlagen wie der Versand. Absender, Empfänger und Links sind fiktiv; Links sind in der Vorschau nicht anklickbar.")}</p></div></div>
    {loading?<div role="status" className="panel ep-loading">{t("Vorlagen werden geladen …")}</div>:error?<div role="alert" className="error"><p>{t(error)}</p><button className="ghost" onClick={()=>setRetry(n=>n+1)}><RefreshCw size={16}/> {t("Erneut laden")}</button></div>:preview&&<>
      <nav aria-label={t("E-Mail-Vorlage")} className="ep-templates">{items.map((item,index)=><button key={item.id} aria-pressed={preview.id===item.id} onClick={()=>setSelected(item.id)}><span>0{index+1}</span><strong>{t(item.label)}</strong></button>)}</nav>
      <div className="ep-toolbar"><div><h2>{t(preview.label)}</h2><p>{t(preview.description)}</p></div><div className="ep-controls"><div role="group" aria-label={t("Ansicht")}><button aria-pressed={mode==='rendered'} onClick={()=>setMode('rendered')}>{t("Gerendert")}</button><button aria-pressed={mode==='text'} onClick={()=>setMode('text')}>{t("Klartext")}</button></div>{mode==='rendered'&&<div role="group" aria-label={t("Vorschaugröße")}><button aria-label={t("Desktop-Vorschau")} aria-pressed={!mobile} onClick={()=>setMobile(false)}><Monitor size={17}/></button><button aria-label={t("Mobile Vorschau")} aria-pressed={mobile} onClick={()=>setMobile(true)}><Smartphone size={17}/></button></div>}</div></div>
      <p className="ep-format">{t("Diese E-Mails werden als Klartext verschickt. Die Darstellung kann je nach E-Mail-Programm abweichen.")}</p>
      <div className="ep-stage"><article aria-label={`${t(preview.label)}${t(": Nachrichtenvorschau")}`} className={`ep-message ${mobile&&mode==='rendered'?'ep-mobile':''}`}><header><div className="ep-envelope"><Mail size={20}/><span>MH Recruiting Workspace</span></div><h3>{preview.subject}</h3><dl><div><dt>{t("Von")}</dt><dd>{preview.sender}</dd></div><div><dt>{t("An")}</dt><dd>{preview.recipient}</dd></div></dl></header>{mode==='text'?<pre className="ep-raw" aria-label={t("Unveränderter Nachrichtentext")}>{preview.text}</pre>:<div className="ep-body">{preview.text.trimEnd().split('\n\n').map((paragraph,index)=><p className={paragraph.startsWith('https://')?'ep-link':''} key={`${preview.id}-${index}`}>{paragraph}</p>)}</div>}<footer>{t("Vorschau mit Beispieldaten · Nicht versendet")}</footer></article></div>
    </>}
  </section>;
}
