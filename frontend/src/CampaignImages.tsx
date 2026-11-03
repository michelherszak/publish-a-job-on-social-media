import { useEffect, useState } from 'react';
import { ImagePlus, Trash2 } from 'lucide-react';
import { API, secureFetch } from './api';
import { t } from './i18n';
import './campaign-images.css';

export type Crop = {x:number;y:number;zoom:number};
export type CampaignImage = {id:number;name:string;width:number;height:number;revision:number;selected:boolean;feed:Crop;story:Crop};
export type ImageDraft = {id:number;revision:number;feed:Crop;story:Crop};
export type ImageFormat = 'feed'|'story';
export function imageURL(campaignId:number,image:CampaignImage,format:'original'|ImageFormat){return `${API}/campaigns/${campaignId}/images/${image.id}/${format}?v=${image.revision}`;}
export function cropDraft(image:CampaignImage):ImageDraft{return {id:image.id,revision:image.revision,feed:{...image.feed},story:{...image.story}};}

async function imageRequest(path:string,options:RequestInit={}){
  const response=await secureFetch(path,options);
  const data=await response.json();
  if(!response.ok)throw new Error(typeof data.detail==='string'?t(data.detail):t('Bild konnte nicht gespeichert werden. Bitte erneut versuchen.'));
  return data;
}
export function useCampaignImages(campaignId:number,onCommitted?:()=>Promise<void>){
  const [images,setImages]=useState<CampaignImage[]>([]);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  useEffect(()=>{let active=true;setImages([]);setLoading(true);setError('');setNotice('');imageRequest(`/campaigns/${campaignId}/images`).then(data=>{if(active)setImages(data.images);}).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[campaignId]);
  async function reload(){const data=await imageRequest(`/campaigns/${campaignId}/images`);setImages(data.images);setError('');}
  async function retry(){setLoading(true);setError('');try{await reload();}catch(e){setError((e as Error).message);}finally{setLoading(false);}}
  async function perform(path:string,options:RequestInit,notice:string){setBusy(true);setError('');setNotice('');try{const data=await imageRequest(path,options);setImages(data.images);setNotice(notice);await onCommitted?.();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  return {images,loading,busy,error,notice,reload,retry,
    upload:(file:File)=>perform(`/campaigns/${campaignId}/images?name=${encodeURIComponent(file.name.slice(0,160))}`,{method:'POST',headers:{'Content-Type':file.type||'application/octet-stream'},body:file},t('Foto gespeichert. Prüfe jetzt die Ausschnitte.')),
    select:(id:number)=>perform(`/campaigns/${campaignId}/images/${id}/select`,{method:'POST'},t('Kampagnenmotiv ausgewählt.')),
    remove:(id:number)=>perform(`/campaigns/${campaignId}/images/${id}`,{method:'DELETE'},t('Foto entfernt.')),
  };
}

export function ImageCropPreview({campaignId,image,format,crop}:{campaignId:number;image:CampaignImage;format:ImageFormat;crop:Crop}){
  const ratio=format==='feed'?4/5:9/16;
  const aspect=image.width/image.height;
  const width=Math.max(1,aspect/ratio)*crop.zoom*100;
  const height=Math.max(1,ratio/aspect)*crop.zoom*100;
  return <div className={`ci-crop ci-${format}`}><img src={imageURL(campaignId,image,'original')} alt={image.name} style={{width:`${width}%`,height:`${height}%`,left:`${-(width-100)*crop.x}%`,top:`${-(height-100)*crop.y}%`}}/></div>;
}

type Props={campaignId:number;state:ReturnType<typeof useCampaignImages>;draft?:ImageDraft;onDraft:(draft:ImageDraft|null)=>void;format:ImageFormat;onFormat:(format:ImageFormat)=>void;canEdit:boolean;busy:boolean;dirty:boolean;onSave:()=>void;};
export function CampaignImages({campaignId,state,draft,onDraft,format,onFormat,canEdit,busy,dirty,onSave}:Props){
  const selected=state.images.find(image=>image.selected);
  const current=selected?(draft?.id===selected.id?draft:cropDraft(selected)):null;
  const blocked=busy||state.busy||state.loading;
  function change(key:keyof Crop,value:number){if(!current)return;const next={...current,[format]:{...current[format],[key]:value}};onDraft(selected&&JSON.stringify(next)===JSON.stringify(cropDraft(selected))?null:next);}
  return <section className="ci-panel" aria-label={t('Kampagnenbilder')}>
    <header className="ci-heading"><div><h2>{t('Kampagnenbilder')}</h2><p>{t('Ein Motiv für Instagram und Meta. Prüfe Feed und Story und gib Bild und Text gemeinsam frei.')}</p></div><small>{t('Eigene Fotos · ohne MH-Tokenverbrauch')}</small></header>
    {state.error&&<div role="alert" className="cs-error">{state.error} <button type="button" className="ghost" disabled={blocked} onClick={()=>void state.retry()}>{t("Bilder erneut laden")}</button></div>}
    {state.loading?<p role="status">{t('Bilder werden geladen …')}</p>:state.error?null:<>
      <div className="ci-library">{state.images.map(image=><div className={`ci-photo ${image.selected?'selected':''}`} key={image.id}><button type="button" className="ci-select" aria-pressed={image.selected} disabled={!canEdit||blocked||dirty} onClick={()=>void state.select(image.id)}><img src={imageURL(campaignId,image,'feed')} alt={image.name}/><span>{image.name}</span><small>{image.selected?t('Ausgewähltes Motiv'):t('Als Motiv auswählen')}</small></button>{canEdit&&<button type="button" className="ci-delete" disabled={blocked||dirty} aria-label={t('Foto entfernen: {name}',{name:image.name})} onClick={()=>{if(window.confirm(t('Dieses Foto aus der Kampagne entfernen?')))void state.remove(image.id);}}><Trash2 size={16}/></button>}</div>)}
        {canEdit&&state.images.length<6&&<label className={`ci-upload ${blocked||dirty?'disabled':''}`}><ImagePlus size={24}/><strong>{t('Foto hochladen')}</strong><span>{t('JPG, PNG oder WebP · bis 10 MiB · maximal sechs Fotos')}</span><input type="file" aria-label={t('Foto hochladen')} accept="image/jpeg,image/png,image/webp" disabled={blocked||dirty} onChange={e=>{const file=e.target.files?.[0];e.target.value='';if(file){if(file.size>10*1024*1024){window.alert(t('Bild zu groß oder leer (maximal 10 MiB).'));return;}void state.upload(file);}}}/></label>}
      </div>
      {!selected&&<p className="ci-empty">{t('Noch kein Kampagnenbild ausgewählt. Die Kampagne kann auch nur mit Text erstellt werden.')}</p>}
      {selected&&current&&<div className="ci-editor"><div><div className="ci-formats" role="group" aria-label={t('Bildformat')}><button type="button" aria-pressed={format==='feed'} onClick={()=>onFormat('feed')}>{t('Feed · 4:5')}</button><button type="button" aria-pressed={format==='story'} onClick={()=>onFormat('story')}>{t('Story · 9:16')}</button></div><ImageCropPreview campaignId={campaignId} image={selected} format={format} crop={current[format]}/></div><div className="ci-controls"><h3>{t('Bildausschnitt')}</h3><p>{t('Verschiebe das Motiv und vergrößere es bei Bedarf. Jeder Ausschnitt wird separat gespeichert.')}</p>{([['x',t('Horizontal')],['y',t('Vertikal')],['zoom',t('Vergrößerung')]] as const).map(([key,label])=><label key={key}>{label}<input type="range" min={key==='zoom'?1:0} max={key==='zoom'?3:1} step="0.01" value={current[format][key]} disabled={!canEdit||blocked} onChange={e=>change(key,Number(e.target.value))}/></label>)}{Math.min(selected.width,selected.height*(format==='feed'?4/5:9/16))/current[format].zoom<1080?<p className="ci-quality">{t('Das Original ist klein. Prüfe die Schärfe im exportierten Bild.')}</p>:null}<p>{t('Die JPG-Dateien für Feed und Story werden mit dem Kampagnenpaket exportiert. Die Vorschau zeigt Bild und Text, das Plattformlayout kann abweichen.')}</p>{canEdit&&<div className="ci-actions"><button type="button" className="ghost" disabled={blocked||!draft} onClick={()=>onDraft(null)}>{t('Ausschnitte zurücksetzen')}</button><button type="button" className="primary" disabled={blocked||!dirty} onClick={onSave}>{t('Bild und Text speichern')}</button></div>}</div></div>}
    </>}
    {dirty&&<p className="cs-dirty-label">{t('Speichere oder verwirf deine Änderungen, bevor du ein anderes Foto auswählst.')}</p>}
    <p className="ci-notice" role="status">{state.busy?t('Bild wird verarbeitet …'):state.notice}</p>
  </section>;
}
