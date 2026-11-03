import {useEffect,useState} from 'react';
import {billingRequest,secureFetch} from './api';
import {t,locale} from './i18n';
import './social-publishing.css';

type Connection={page_id:string;page_name:string;instagram_id:string;instagram_name:string;expired:boolean;connected_at:number};
type MetaStatus={ready:boolean;missing:string[];connection:Connection|null;pages:{id:string;name:string;instagram_id:string;instagram_name:string}[]};
type Publication={id:string;platform:string;page_name:string;message:string;link_url:string;state:'preview'|'publishing'|'published'|'unknown'|'failed';post_id:string;post_url:string;updated_at:number};
type Link={id:string;channel:string;variant:string;active:boolean;url:string};
type Campaign={id:number;status:string;generated:Record<string,string>};

async function disconnect(){
 const response=await secureFetch('/social/meta/connection',{method:'DELETE'});
 if(!response.ok)throw new Error(t('Verbindung konnte nicht entfernt werden.'));
}

export function MetaConnection(){
 const [status,setStatus]=useState<MetaStatus|null>(null);
 const [instagram,setInstagram]=useState(false);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState(()=>({select:t('Wähle jetzt die Unternehmensseite aus.'),cancelled:t('Facebook-Anmeldung wurde abgebrochen.'),failed:t('Facebook-Verbindung fehlgeschlagen. Bitte Seitenrechte und App-Einrichtung prüfen.')}[new URLSearchParams(window.location.search).get('social')||'']||''));
 async function load(){setStatus(await billingRequest<MetaStatus>('/social/meta/status'));}
 useEffect(()=>{let active=true;billingRequest<MetaStatus>('/social/meta/status').then(r=>{if(active)setStatus(r);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[]);
 async function perform(action:()=>Promise<void>){setBusy(true);setError('');try{await action();await load();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 return <section className="panel settings-card social-panel"><span className="mini">FACEBOOK & INSTAGRAM</span><h2>{t('Eigene Unternehmensseite verbinden')}</h2><p>{t('Jede Firma verbindet ihre eigene Seite. MH veröffentlicht dort erst nach ausdrücklicher Bestätigung. Eine Verbindung veröffentlicht noch keinen Beitrag.')}</p>
 {error&&<p className="error" role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}
 {!status&&!error&&<p role="status">{t('Wird geladen …')}</p>}
 {status&&<>
 {!status.ready&&<div className="social-notice"><strong>{t('Meta-Einrichtung noch offen')}</strong><p>{t('Der Betreiber richtet zuerst die öffentliche MH-Adresse und die Meta-App ein. Danach meldest du dich bei Facebook an und wählst deine Seite aus.')}</p></div>}
 {status.connection&&<div className="social-target"><strong>{status.connection.page_name}</strong><span>{status.connection.expired?t('Verbindung abgelaufen · bitte erneut verbinden'):t('Facebook-Seite verbunden')}</span><span>{status.connection.instagram_id?`${t('Instagram-Verbindung vorbereitet:')} ${status.connection.instagram_name||status.connection.instagram_id}`:t('Instagram noch nicht verbunden')}</span></div>}
 {status.pages.length>0&&<div className="social-pages"><h3>{t('Deine freigegebenen Facebook-Seiten')}</h3>{status.pages.map(page=><div key={page.id}><strong>{page.name}</strong>{page.instagram_id&&<span>Instagram: {page.instagram_name||page.instagram_id}</span>}<button className="primary small" disabled={busy} onClick={()=>perform(async()=>{await billingRequest('/social/meta/page',{page_id:page.id});setNotice(t('Unternehmensseite verbunden.'));})}>{t('Diese Seite verwenden')}</button></div>)}</div>}
 <label className="social-check"><input type="checkbox" checked={instagram} onChange={e=>setInstagram(e.target.checked)} disabled={busy}/>{t('Instagram-Firmenkonto ebenfalls verbinden')}</label><p>{t('Für diesen Instagram-Anschluss muss ein professionelles Instagram-Konto mit der gewählten Facebook-Seite verknüpft sein. Die Veröffentlichung auf Instagram folgt im nächsten Schritt.')}</p>
 <div className="social-actions"><button className="primary" disabled={busy||!status.ready} onClick={()=>perform(async()=>{const result=await billingRequest<{url:string}>('/social/meta/connect',{instagram});window.location.assign(result.url);})}>{t('Über Facebook anmelden')}</button>{status.connection&&<button className="ghost" disabled={busy} onClick={()=>perform(async()=>{await disconnect();setNotice(t('Verbindung aus MH entfernt. Bereits veröffentlichte Beiträge bleiben auf Facebook.'));})}>{t('Verbindung entfernen')}</button>}</div>
 </>}
 </section>;
}

export function FacebookPublishing({campaign,dirty,admin}:{campaign:Campaign;dirty:boolean;admin:boolean}){
 const [status,setStatus]=useState<MetaStatus|null>(null);
 const [links,setLinks]=useState<Link[]>([]);
 const [publication,setPublication]=useState<Publication|null>(null);
 const [loaded,setLoaded]=useState(false);
 const [message,setMessage]=useState(campaign.generated.social||'');
 const [linkId,setLinkId]=useState('');
 const [confirmed,setConfirmed]=useState(false);
 const [postId,setPostId]=useState('');
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 async function load(){const [a,b,c]=await Promise.all([billingRequest<MetaStatus>('/social/meta/status'),billingRequest<{links:Link[]}>(`/campaigns/${campaign.id}/tracking/links`),billingRequest<{publication:Publication|null}>(`/campaigns/${campaign.id}/social/publication`)]);setStatus(a);setLinks(b.links.filter(l=>['Facebook','Meta'].includes(l.channel)&&l.active));setPublication(c.publication);setLoaded(true);}
 useEffect(()=>{let active=true;Promise.all([billingRequest<MetaStatus>('/social/meta/status'),billingRequest<{links:Link[]}>(`/campaigns/${campaign.id}/tracking/links`),billingRequest<{publication:Publication|null}>(`/campaigns/${campaign.id}/social/publication`)]).then(([a,b,c])=>{if(active){setStatus(a);const fb=b.links.filter(l=>['Facebook','Meta'].includes(l.channel)&&l.active);setLinks(fb);setLinkId(fb[0]?.id||'');setPublication(c.publication);if(c.publication){setMessage(c.publication.message.replace('\n\n'+c.publication.link_url,''));}setLoaded(true);}}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[campaign.id]);
 async function perform(action:()=>Promise<void>){setBusy(true);setError('');try{await action();}catch(e){setError((e as Error).message);try{await load();}catch{/* Keep the last known state visible when the network is unavailable. */}}finally{setBusy(false);}}
 const ready=loaded&&status?.ready&&status.connection&&!status.connection.expired&&campaign.status==='Live'&&!dirty;
 const locked=publication&&['publishing','unknown','published'].includes(publication.state);
 const previewCurrent=publication?.state==='preview'&&publication.message===message.trim()+'\n\n'+publication.link_url&&links.some(l=>l.id===linkId&&l.url===publication.link_url);
 return <section className="panel social-panel"><span className="mini">FACEBOOK</span><h2>{t('Auf der Unternehmensseite veröffentlichen')}</h2><p>{t('Veröffentlicht einen normalen Facebook-Beitrag mit Text und Bewerbungslink. Es wird keine bezahlte Werbung gebucht.')}</p><p className="social-notice">{t('Kampagnenbilder werden hier noch nicht an Facebook übertragen. Exportiere die JPG-Dateien und verwende sie beim manuellen Veröffentlichen.')}</p>
 {error&&<p className="error" role="alert">{error}</p>}
 {!loaded&&!error&&<p role="status">{t('Wird geladen …')}</p>}
 {loaded&&<>
 {!status?.ready&&<p className="social-notice">{t('Die Meta-App und öffentliche MH-Adresse müssen zuerst eingerichtet werden.')}</p>}
 {(!status?.connection||status.connection.expired)&&<p>{t('Bitte die eigene Facebook-Seite unter Settings verbinden.')}</p>}
 {campaign.status!=='Live'&&<p>{t('Die Kampagne muss zuerst intern freigegeben werden.')}</p>}
 {dirty&&<p>{t('Speichere oder verwirf zuerst deine Änderungen.')}</p>}
 {!links.length&&<p>{t('Erstelle oben einen aktiven Facebook-Anzeigenlink und aktiviere die Bewerbungsseite. Danach aktualisieren.')}</p>}
 {!locked&&<form onSubmit={e=>{e.preventDefault();void perform(async()=>{setPublication(await billingRequest<Publication>(`/campaigns/${campaign.id}/social/facebook/preview`,{message,link_id:linkId}));setConfirmed(false);});}}>
 <label>{t('Facebook-Beitragstext')}<textarea required maxLength={10000} rows={8} value={message} onChange={e=>{setMessage(e.target.value);setConfirmed(false);}} disabled={busy}/></label><p>{t('Wähle eine Textvariante und prüfe den vollständigen Beitrag. Der Bewerbungslink wird ergänzt.')}</p>
 <label>{t('Facebook-Bewerbungslink')}<select required value={linkId} disabled={busy} onChange={e=>{setLinkId(e.target.value);setConfirmed(false);}}><option value="">{t('Bitte auswählen')}</option>{links.map(l=><option key={l.id} value={l.id}>{l.variant}</option>)}</select></label>
 <button className="ghost" disabled={busy||!ready||!message.trim()||!linkId}>{t('Veröffentlichung prüfen')}</button></form>}
 {publication&&<div className="social-preview"><h3>{publication.page_name}</h3><pre>{publication.message}</pre>
 {publication.state==='preview'&&<><p>{t('Vorschau · noch nicht veröffentlicht')}</p><label className="social-check"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)} disabled={busy||!previewCurrent}/>{t('Ich habe den Beitrag geprüft und möchte ihn jetzt öffentlich auf dieser Unternehmensseite veröffentlichen.')}</label><button className="primary" disabled={busy||!ready||!previewCurrent||!confirmed} onClick={()=>perform(async()=>{setPublication(await billingRequest<Publication>(`/campaigns/${campaign.id}/social/facebook/publish`,{preview_id:publication.id,confirmed:true}));setConfirmed(false);})}>{busy?t('Wird verarbeitet …'):t('Jetzt auf Facebook veröffentlichen')}</button></>}
 {publication.state==='published'&&<p role="status">{t('Facebook hat die Veröffentlichung bestätigt.')} <a href={publication.post_url} target="_blank" rel="noopener noreferrer">{t('Beitrag öffnen')}</a> · {new Date(publication.updated_at*1000).toLocaleString(locale)}</p>}
 {publication.state==='failed'&&<p role="alert">{t('Facebook hat den Beitrag abgewiesen. Prüfe die Verbindung und erstelle anschließend eine neue Vorschau.')}</p>}
 {['publishing','unknown'].includes(publication.state)&&<><p role="status">{t('Ergebnis noch nicht eindeutig bestätigt. Prüfe die Unternehmensseite auf Facebook. MH sendet diesen Beitrag nicht automatisch erneut.')}</p>{admin&&<details><summary>{t('Vorhandenen Facebook-Beitrag nachträglich bestätigen')}</summary><p>{t('Nach zwei Minuten kannst du die Beitrags-ID der ursprünglichen Seite prüfen lassen. MH vergleicht den veröffentlichten Text mit dieser Vorschau.')}</p><label>{t('Beitrags-ID (Seiten-ID_Beitrags-ID)')}<input value={postId} onChange={e=>setPostId(e.target.value)}/></label><button className="ghost" disabled={busy||!/^\d+_\d+$/.test(postId)} onClick={()=>perform(async()=>{setPublication(await billingRequest<Publication>(`/campaigns/${campaign.id}/social/facebook/verify`,{post_id:postId}));})}>{t('Beitrag auf Facebook überprüfen')}</button></details>}</>}
 </div>}
 <button className="text-btn" disabled={busy} onClick={()=>perform(load)}>{t('Verbindungsstatus und Links aktualisieren')}</button>
 <details><summary>{t('Instagram · nächster Schritt')}</summary><p>{status?.connection?.instagram_id?`${t('Instagram-Verbindung vorbereitet:')} ${status.connection.instagram_name||status.connection.instagram_id}`:t('Verbinde das professionelle Instagram-Konto unter Settings.')}</p><p>{t('Instagram benötigt zusätzlich ein geeignetes Bild oder Video. Der bisherige SVG-Export ist dafür kein fertiges Upload-Format. Bildveröffentlichung und Medienbereitstellung sind noch offen.')}</p></details>
 </>}
 </section>;
}
