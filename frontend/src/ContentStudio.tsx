import { t, locale } from "./i18n";
import { useRef, useState } from 'react';
import { Check, Copy, FileText, Instagram, Megaphone, Save, Sparkles } from 'lucide-react';
import type { Briefing } from './CampaignWizard';
import './content-studio.css';
import { CampaignImages, cropDraft, useCampaignImages } from './CampaignImages';
import type { ImageDraft, ImageFormat } from './CampaignImages';
import { SocialPreview } from './SocialPreview';
export type StudioCampaign = {id:number;organization_id:number;role:string;location:string;status:'Draft'|'Review'|'Live';channels:string[];briefing:Partial<Briefing>;generated:Record<string,string>;change_request:string;updated_at:number;generation_mode?:string;briefing_stale?:boolean;briefing_fingerprint?:string};
const formats = [
  {id:'social',name:'Instagram',detail:t("Beiträge"),icon:Instagram,hint:t("Prüfe beide Varianten. Der Einstieg sollte die Stelle und ihren Vorteil verständlich machen.")},
  {id:'meta',name:'Meta',detail:t("Anzeigentexte"),icon:Megaphone,hint:t("Prüfe jede Variante mit Haupttext, Überschrift und Beschreibung. Werbebudget ist nicht enthalten.")},
];
type Props={onConfirmBriefing?:()=>void;campaign:StudioCampaign;orgName:(id:number)=>string;activeTab:string;onTab:(id:string)=>void;drafts:Record<string,string>;onChange:(id:string,value:string)=>void;imageDraft?:ImageDraft;onImageDraft?:(draft:ImageDraft|null)=>void;onImagesCommitted?:()=>Promise<void>;onSave:(imageEdit?:ImageDraft)=>Promise<boolean>;onDiscard:()=>void;onEdit:()=>void;onGenerate:()=>void;canEdit:boolean;busy:boolean;error:string;cost:string};
export function ContentStudio({onConfirmBriefing,campaign,orgName,activeTab,onTab,drafts,onChange,imageDraft,onImageDraft,onImagesCommitted,onSave,onDiscard,onEdit,onGenerate,canEdit,busy,error,cost}:Props){
  const [view,setView]=useState<'edit'|'preview'>('edit');
  const [copyState,setCopyState]=useState('');
  const [imageFormat,setImageFormat]=useState<ImageFormat>('feed');
  const [savingImages,setSavingImages]=useState(false);
  const [imageSaveError,setImageSaveError]=useState('');
  const images=useCampaignImages(campaign.id,onImagesCommitted);
  const photo=images.images.find(image=>image.selected);
  const photoCrop=photo?(imageDraft?.id===photo.id?imageDraft:cropDraft(photo)):null;
  const allBusy=busy||images.busy||images.loading||savingImages;
  async function saveAll(){
    setImageSaveError('');setSavingImages(true);
    try{if(await onSave(imageDraft)){onImageDraft?.(null);await images.reload();}}
    catch(e){setImageSaveError((e as Error).message);}
    finally{setSavingImages(false);}
  }
  function discardAll(){onImageDraft?.(null);onDiscard();}

  const tabRefs=useRef<(HTMLButtonElement|null)[]>([]);
  const format=formats.find(f=>f.id===activeTab)||formats[0];
  const content=drafts[format.id]??campaign.generated[format.id]??'';
  const dirty=Object.keys(drafts).filter(id=>drafts[id] !== (campaign.generated[id]||''));
  const unsaved=dirty.length+(imageDraft?1:0);
  const hasContent=Object.values(campaign.generated).some(text=>text.trim());
  const words=content.trim()?content.trim().split(/\s+/).length:0;
  const status={Draft:t("Entwurf"),Review:t("In Prüfung"),Live:t("Freigegeben")}[campaign.status];
  function selectTab(id:string){onTab(id);setCopyState('');}
  async function copy(){try{await navigator.clipboard.writeText(content);setCopyState(t("Text kopiert."));}catch{setCopyState(t("Kopieren nicht möglich. Markiere den Text und kopiere ihn manuell."));}}
  return <section className="content-studio" aria-label={t("Content Studio")}>
    <header className="cs-heading"><div><span className="mini">MH CONTENT STUDIO</span><h1>{t("Aus Entwürfen wird eure Kampagne.")}</h1><p>{t("Text für Text bearbeiten. Gemeinsam prüfen. Bereit für den Export.")}</p></div><span className={`status ${campaign.status.toLowerCase()}`}>{status}</span></header>
    <div className="cs-campaign"><div className="cs-campaign-title"><small>{t("Kampagne")}</small><strong>{campaign.role}</strong></div><div className="cs-campaign-meta"><strong>{orgName(campaign.organization_id)}</strong><span>{campaign.location} · {campaign.briefing.employment_type || t("Beschäftigung nicht angegeben")}</span></div><span className="cs-cost">{cost}</span></div>
    <div className="cs-workflow"><span className="cs-phase"><Check size={15}/> {t("Briefing")}</span><span className={campaign.status==='Draft'?'current':''}>{t("01 · Texte bearbeiten")}</span><span className={campaign.status==='Review'?'current':''}>{t("02 · Gemeinsam prüfen")}</span><span className={campaign.status==='Live'?'current':''}>{t("03 · Exportieren")}</span></div>
    {campaign.generation_mode === "local_test" && <p className="cs-notice" role="status">{t("Testpaket aus lokalen Vorlagen · keine KI-Generierung.")}</p>}
    {campaign.briefing_stale&&<div className="cs-notice"><strong>{t("Briefing und Texte erneut abgleichen")}</strong><p>{t("Diese Texte wurden noch nicht mit dem aktuellen Briefing abgeglichen. Prüfe alle Formate, bevor du die Fassung freigibst.")}</p>{canEdit&&onConfirmBriefing&&<button className="ghost" disabled={allBusy||unsaved>0} onClick={onConfirmBriefing}>{t("Alle gespeicherten Texte mit diesem Briefing geprüft")}</button>}</div>}
    {campaign.change_request&&<div className="cs-notice"><strong>{t("Feedback zur Überarbeitung")}</strong><p>{campaign.change_request}</p></div>}
    {error&&<div className="cs-error" role="alert">{t(error)} {t("Deine ungespeicherten Texte bleiben in dieser Sitzung erhalten.")}</div>}
    {imageSaveError&&<p className="cs-error" role="alert">{imageSaveError}</p>}
    <CampaignImages campaignId={campaign.id} state={images} draft={imageDraft} onDraft={draft=>onImageDraft?.(draft)} format={imageFormat} onFormat={setImageFormat} canEdit={canEdit} busy={allBusy} dirty={unsaved>0} onSave={()=>void saveAll()}/>
    <div className="cs-layout">
      <aside className="cs-rail"><div className="cs-rail-title"><span>{t("TEXTFORMATE")}</span><small>{formats.filter(f=>(drafts[f.id]??campaign.generated[f.id]??'').trim()).length} {t("/ 2 mit Inhalt")}</small></div>
        <div role="tablist" aria-label={t("Textformat")} aria-orientation="vertical" className="cs-tabs">{formats.map((f,index)=>{const Icon=f.icon;return <button ref={el=>{tabRefs.current[index]=el;}} key={f.id} id={`cs-tab-${f.id}`} role="tab" aria-selected={format.id===f.id} aria-controls="cs-text-panel" tabIndex={format.id===f.id?0:-1} onClick={()=>selectTab(f.id)} onKeyDown={e=>{let next=index;if(e.key==='ArrowDown')next=(index+1)%formats.length;else if(e.key==='ArrowUp')next=(index+formats.length-1)%formats.length;else if(e.key==='Home')next=0;else if(e.key==='End')next=formats.length-1;else return;e.preventDefault();selectTab(formats[next].id);tabRefs.current[next]?.focus();}}><Icon size={18}/><span><strong>{f.name}</strong><small>{f.detail}</small></span>{dirty.includes(f.id)?<span className="cs-unsaved" aria-label={t("Ungespeichert")}>●</span>:(campaign.generated[f.id]||'').trim()?<Check size={14} aria-label={t("Text vorhanden")}/>:null}</button>})}</div>
        <details className="cs-brief"><summary>{t("Briefing nachschlagen")}</summary><dl>{[[t("Aufgaben"),campaign.briefing.tasks],[t("Notwendige Voraussetzungen"),campaign.briefing.requirements],[t("Bei uns lernbar"),campaign.briefing.learnable_requirements],[t("Tatsächliche Arbeitszeiten"),campaign.briefing.working_hours],[t("Benefits"),campaign.briefing.benefits],[t("Gehalt"),campaign.briefing.salary],[t("Tonalität"),campaign.briefing.tone]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value||t("Nicht angegeben")}</dd></div>)}</dl>{canEdit&&<button className="ghost" disabled={allBusy} onClick={onEdit}>{t("Briefing bearbeiten")}</button>}</details>
        {canEdit&&<details className="cs-brief"><summary>{t("Neues Textpaket erstellen")}</summary><p>{t("Erstellt Instagram, Meta und die MH-Stellenbeschreibung neu. Frühere Versionen bleiben im Verlauf.")} {cost}</p><button className="ghost" disabled={allBusy||unsaved>0} onClick={onGenerate}><Sparkles size={15}/> {hasContent?t("Neu erstellen"):t("Texte erstellen")}</button>{unsaved>0&&<p>{t("Speichere oder verwirf zuerst deine Änderungen.")}</p>}</details>}
      </aside>
      <div className="cs-document" id="cs-text-panel" role="tabpanel" aria-labelledby={`cs-tab-${format.id}`}>
        <header className="cs-document-head"><div><h2>{format.name}</h2><p>{format.hint}</p></div><div className="cs-view" role="group" aria-label={t("Darstellung")}><button aria-pressed={view==='edit'} onClick={()=>setView('edit')}>Text</button><button aria-pressed={view==='preview'} onClick={()=>setView('preview')}>{t("Vorschau")}</button></div></header>
        {!hasContent&&!content&&<div className="cs-empty"><FileText size={28}/><h3>{t("Dein Briefing ist bereit.")}</h3><p>{canEdit?t("Erstelle Texte für Instagram und Meta oder beginne mit deinem eigenen Text."):t("Für dieses Format ist noch kein Text vorhanden.")}</p>{canEdit&&<button className="primary" disabled={allBusy||unsaved>0} onClick={onGenerate}><Sparkles size={16}/> {t("Textpaket erstellen")}</button>}</div>}
        {view==='edit'?<textarea className="cs-textarea" aria-label={`${format.name}${t(" bearbeiten")}`} value={content} readOnly={!canEdit} disabled={allBusy} onChange={e=>onChange(format.id,e.target.value)} placeholder={canEdit?t("Hier ist Platz für euren Text …"):t("Noch kein Text vorhanden.")} onKeyDown={e=>{if((e.metaKey||e.ctrlKey)&&e.key==='s'){e.preventDefault();if(canEdit&&!allBusy&&unsaved)void saveAll();}}}/>:<SocialPreview key={format.id} channel={format.id === "meta" ? "meta" : "social"} content={content} company={orgName(campaign.organization_id)} role={campaign.role} location={campaign.location} campaignId={campaign.id} photo={photo} crop={photoCrop} format={imageFormat} onFormat={setImageFormat}/>}
        <div className="cs-text-meta"><span>{content.length.toLocaleString(locale)} {t("Zeichen ·")} {words.toLocaleString(locale)} {t("Wörter")}</span><button className="text-btn" disabled={!content} onClick={copy}><Copy size={14}/> {t("Text kopieren")}</button></div><span className="cs-copy-status" role="status">{copyState}</span>
        <footer className="cs-savebar"><div role="status"><span className={unsaved?'cs-dirty-label':'cs-saved-label'}>{allBusy?t("Wird verarbeitet …"):unsaved?t(unsaved===1?'Eine Änderung ungespeichert':'{count} Änderungen ungespeichert',{count:unsaved.toLocaleString(locale)}):hasContent?t("Alle Änderungen gespeichert"):t("Noch keine Texte gespeichert")}</span><small>{canEdit?t("Änderungen bleiben beim Kanalwechsel erhalten. Speichere vor dem Verlassen der Sitzung."):t("Leseansicht · Änderungen sind hier nicht möglich.")}</small></div>{canEdit&&<div className="cs-actions">{unsaved>0&&<button className="text-btn" disabled={allBusy} onClick={()=>{if(window.confirm(t("Alle ungespeicherten Text- und Bildänderungen dieser Kampagne verwerfen?")))discardAll();}}>{t("Verwerfen")}</button>}<button className="primary" disabled={allBusy||!unsaved} onClick={()=>void saveAll()}><Save size={16}/> {t("Änderungen speichern")}</button></div>}</footer>
      </div>
    </div>
    <details className="cs-destination"><summary>{t("Stellenbeschreibung auf MH")}</summary><p>{t("Das ist die gemeinsame Zielseite für Bewerbungen aus Instagram und Meta. Sie wird erst nach Freigabe und ausdrücklicher Aktivierung öffentlich.")}</p><label>{t("Text der MH-Bewerbungsseite")}<textarea value={drafts.jobAd??campaign.generated.jobAd??''} readOnly={!canEdit} disabled={allBusy} onChange={e=>onChange('jobAd',e.target.value)} onKeyDown={e=>{if((e.metaKey||e.ctrlKey)&&e.key==='s'){e.preventDefault();if(canEdit&&!allBusy&&unsaved)void saveAll();}}}/></label>{canEdit&&<button className="ghost" disabled={allBusy||!unsaved} onClick={()=>void saveAll()}><Save size={16}/> {t("Änderungen speichern")}</button>}</details>
  </section>;
}
