import messages from './translations.json';

export type Language = 'de' | 'en';
/** Follow the first supported browser preference; use English for other languages. */
export function detectLanguage(languages: readonly string[]): Language {
  for (const tag of languages) {
    const base = tag.trim().toLowerCase().split(/[-_]/)[0];
    if (base === 'de' || base === 'en') return base;
  }
  return 'en';
}
// Resolve once per page load so an OS preference change cannot discard an edited draft.
// The public prerender remains German; English clients mount instead of hydrating it.
export const language: Language = typeof window === 'undefined' || typeof navigator === 'undefined' ? 'de' : detectLanguage(navigator.languages?.length ? navigator.languages : [navigator.language]);
export const locale = language === 'de' ? 'de-DE' : 'en-GB';
const catalog: Record<string, {de:string;en:string}> = messages;
export function t(source: string, values: Record<string, string | number> = {}): string {
  const text = catalog[source]?.[language] ?? source;
  return text.replace(/\{(\w+)\}/g, (match, key: string) => Object.prototype.hasOwnProperty.call(values,key) ? String(values[key]) : match);
}
export function roleLabel(role: string): string {
  return ({platform_admin:t('Platform Admin'),firmen_admin:t('Firmen Admin'),user:t('User'),kunde:t('Kunde')} as Record<string,string>)[role] || role;
}

/** Translate only known machine-generated text; keep embedded customer text intact. */
export function systemText(source: string): string {
  const need = source.match(/^Personalbedarf: (open|paused|closed); Zuständigkeiten aktualisiert$/);
  if (need) return t('Personalbedarf: {state}; Zuständigkeiten aktualisiert', {state:t(({open:'Suche offen',paused:'Suche pausiert',closed:'Suche abgeschlossen'} as Record<string,string>)[need[1]])});
  const patterns: [RegExp, string, string][] = [
    [/^(.+): Veröffentlichung manuell dokumentiert; keine Anbieterbestätigung$/, '{value}: Veröffentlichung manuell dokumentiert; keine Anbieterbestätigung', 'value'],
    [/^Kampagnenentwurf #(\d+) · 50 Tokens$/, 'Kampagnenentwurf #{value} · 50 Tokens', 'value'],
    [/^(.+) Monatsguthaben \(Rest des Vormonats verfällt\)$/, '{value} Monatsguthaben (Rest des Vormonats verfällt)', 'value'],
    [/^(.+) gekauft$/, '{value} gekauft', 'value'],
    [/^Kennzahlen für (.+) aktualisiert$/, 'Kennzahlen für {value} aktualisiert', 'value'],
    [/^Was bedeutet „(.+)“ bei dieser Stelle konkret\? Bitte ein belegbares Beispiel ergänzen\.$/, 'Was bedeutet „{value}“ bei dieser Stelle konkret? Bitte ein belegbares Beispiel ergänzen.', 'value'],
  ];
  for (const [pattern, key, field] of patterns) {
    const match = source.match(pattern);
    if (match) return t(key, {[field]:key === '{value} gekauft' || key.startsWith('{value} Monatsguthaben') ? t(match[1]) : match[1]});
  }
  return t(source);
}
export function historyText(item: {action:string;message:string}): string {
  // Comments and requests for changes are written by people, even when they match a translation key.
  if (item.action === 'commented' || item.action === 'changes_requested') return item.message;
  return systemText(item.message || item.action);
}
