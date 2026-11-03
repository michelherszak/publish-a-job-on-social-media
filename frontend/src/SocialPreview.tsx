import { useState } from 'react';
import { Bookmark, ChevronRight, Globe2, Heart, Image, MessageCircle, MoreHorizontal, Send, Share2, ThumbsUp, X } from 'lucide-react';
import { t } from './i18n';
import { ImageCropPreview } from './CampaignImages';
import type { CampaignImage, ImageDraft, ImageFormat } from './CampaignImages';
import './social-preview.css';

type Variant = { text: string; name: string };
export function previewVariants(content: string): Variant[] {
  const matches = [...content.matchAll(/^(?:Variante|Variant)\s+([A-Z])(?:\s*[·:–—-][^\n]*)?\s*$/gm)];
  // Only interpret explicit variant headings; custom copy remains intact.
  if (matches.length < 2 || content.slice(0, matches[0].index).trim()) return [{ text: content, name: '' }];
  return matches.map((match, i) => ({ name: match[1], text: content.slice(match.index! + match[0].length, matches[i + 1]?.index ?? content.length).trim() }));
}
export function metaPreviewCopy(text: string) {
  const fields = [...text.matchAll(/^(Primary Text|Haupttext|Headline|Überschrift|Description|Beschreibung):[ \t]*/gim)];
  const fallback = { body: text, headline: '', description: '' };
  if (!fields.length || text.slice(0, fields[0].index).trim()) return fallback;
  const copy = { body: '', headline: '', description: '' }, seen = new Set<string>();
  for (let i = 0; i < fields.length; i++) {
    const match = fields[i], label = match[1].toLowerCase();
    const key = /primary text|haupttext/.test(label) ? 'body' : /headline|überschrift/.test(label) ? 'headline' : 'description';
    if (seen.has(key)) return fallback;
    seen.add(key); copy[key] = text.slice(match.index! + match[0].length, fields[i + 1]?.index ?? text.length).trim();
  }
  return seen.has('body') ? copy : fallback;
}

type Props = { channel: 'social' | 'meta'; content: string; company: string; role: string; location: string; campaignId: number; photo?: CampaignImage; crop: ImageDraft | null; format: ImageFormat; onFormat: (format: ImageFormat) => void };
export function SocialPreview({ channel, content, company, role, location, campaignId, photo, crop, format, onFormat }: Props) {
  const [variant, setVariant] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const variants = previewVariants(content), current = variants[Math.min(variant, variants.length - 1)];
  const isInstagram = channel === 'social', story = format === 'story';
  const copy = isInstagram ? { body: current.text, headline: '', description: '' } : metaPreviewCopy(current.text);
  const initials = company.trim().split(/\s+/).slice(0, 2).map(word => word[0]).join('');
  const body = copy.body || t('Deine Textvorschau erscheint hier.');
  const collapsible = body.length > 180 || body.split('\n').length > 4;
  const media = photo && crop ? <ImageCropPreview campaignId={campaignId} image={photo} format={format} crop={crop[format]}/> : <div className={`sp-placeholder ${story ? 'sp-placeholder-story' : ''}`}><Image size={30}/><span>{t('Kein Kampagnenbild ausgewählt')}</span></div>;
  const brand = <><span className="sp-avatar" aria-hidden="true">{initials}</span><div className="sp-identity"><strong>{company}</strong><small>{isInstagram ? location : <>{t('Gesponsert')} · <Globe2 size={10} aria-hidden="true"/></>}</small></div></>;
  const caption = <div className="sp-caption"><div className={`sp-copy ${collapsible && !expanded ? 'sp-copy-short' : ''}`}>{isInstagram && !story && <strong>{company} </strong>}{body}</div>{collapsible && <button type="button" className="sp-more" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}>{expanded ? t('Weniger anzeigen') : t('Mehr anzeigen')}</button>}</div>;
  return <section className={`social-preview sp-${isInstagram ? 'instagram' : 'facebook'}`} aria-label={isInstagram ? t('Instagram-Vorschau') : t('Meta-Vorschau')}>
    <div className="sp-toolbar"><span>{isInstagram ? 'Instagram' : 'Meta · Facebook'} · {story ? t('Story') : t('Feed')}</span><div role="group" aria-label={t('Vorschauformat')}><button type="button" aria-pressed={!story} onClick={() => onFormat('feed')}>{t('Feed')}</button><button type="button" aria-pressed={story} onClick={() => onFormat('story')}>{t('Story')}</button></div></div>
    {variants.length > 1 && <div className="sp-variants" role="group" aria-label={t('Textvariante')}>{variants.map((item, i) => <button key={i} type="button" aria-pressed={Math.min(variant, variants.length - 1) === i} onClick={() => { setVariant(i); setExpanded(false); }}>{t('Variante {name}', { name: item.name })}</button>)}</div>}
    {story ? <>
      <article className="sp-story" aria-label={t('Story-Vorschau')}>
        {media}<div className="sp-story-top"><div className="sp-progress" aria-hidden="true"/><header>{brand}<X size={20} aria-hidden="true"/></header></div>
        <div className="sp-story-bottom"><span className="sp-story-cta">{t('Jetzt bewerben')} <ChevronRight size={17} aria-hidden="true"/></span><div className="sp-story-reply" aria-hidden="true"><span>{t('Nachricht senden')}</span><Heart size={23}/><Send size={22}/></div></div>
      </article><div className="sp-story-caption">{caption}</div>
    </> : <article className="sp-post" aria-label={isInstagram ? t('Instagram-Beitragsvorschau') : t('Facebook-Anzeigenvorschau')}>
      <header className="sp-post-header">{brand}<MoreHorizontal size={22} aria-hidden="true"/></header>
      {!isInstagram && caption}
      {(photo || isInstagram) && media}
      {isInstagram ? <><div className="sp-instagram-actions" aria-hidden="true"><Heart/><MessageCircle/><Send/><Bookmark className="sp-bookmark"/></div>{caption}</> : <>
        <div className="sp-link-card"><div><small>{t('MH · Stellenangebot')}</small><strong>{copy.headline || role}</strong>{copy.description && <p>{copy.description}</p>}</div><span className="sp-apply">{t('Jetzt bewerben')}</span></div>
        <div className="sp-facebook-actions" aria-hidden="true"><span><ThumbsUp size={18}/>{t('Gefällt mir')}</span><span><MessageCircle size={18}/>{t('Kommentieren')}</span><span><Share2 size={18}/>{t('Teilen')}</span></div>
      </>}
    </article>}
    <p className="sp-note">{t('Kampagnenvorschau · Das Layout auf der Zielplattform kann abweichen. Es wurde nichts veröffentlicht.')}</p>
  </section>;
}
