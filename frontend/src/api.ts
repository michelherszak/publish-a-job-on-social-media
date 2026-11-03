import { t, language } from "./i18n";
const configured = import.meta.env.VITE_API_URL?.replace(/\/$/, "");
export const API = configured || (typeof window !== 'undefined' && ['localhost', '127.0.0.1'].includes(window.location.hostname) ? `http://${window.location.hostname}:8011` : '/api');
function networkError(): never { throw new Error(t('Der Server ist nicht erreichbar. Bitte später erneut versuchen.')); }
export async function secureFetch(path: string, options: RequestInit = {}) {
  const method = options.method || 'GET';
  const headers = new Headers(options.headers);
  headers.set("Accept-Language", language);
  if (!['GET','HEAD','OPTIONS'].includes(method.toUpperCase())) {
    const result = await fetch(API + '/auth/csrf', {credentials:'include',cache:'no-store',keepalive:options.keepalive}).catch(networkError);
    if (!result.ok) throw new Error(t('Sicherheitsprüfung nicht erreichbar. Bitte erneut versuchen.'));
    headers.set('X-CSRF-Token', (await result.json()).csrf);
  }
  return fetch(API + path, {...options,headers,credentials:'include',cache:'no-store'}).catch(networkError);
}
export async function billingRequest<T>(path: string, body?: unknown): Promise<T> {
  const response = await secureFetch(path, { method: body === undefined ? 'GET' : 'POST', headers: { ...(body !== undefined ? {'Content-Type':'application/json'} : {}) }, ...(body !== undefined ? {body:JSON.stringify(body)} : {}) });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? t(data.detail) : t('Bitte prüfe deine Angaben und versuche es erneut.'));
  return data;
}
