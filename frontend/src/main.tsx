import { t, language } from "./i18n";
import React, { lazy, Suspense } from "react";
import { createRoot, hydrateRoot } from "react-dom/client";
const Landing = lazy(() => import("./Landing").then(module=>({default:module.Landing})));
const JobPortal = lazy(() => import("./JobPortal").then(module => ({default:module.JobPortal})));
const ApplyPage = lazy(() => import("./Apply").then(module => ({default:module.ApplyPage})));
const AdRedirect = lazy(() => import("./Apply").then(module => ({default:module.AdRedirect})));
const Registration = lazy(() => import("./Billing").then(module => ({ default: module.Registration })));
const App = lazy(() => import("./App").then(module => ({ default: module.App })));
const AuthPage = lazy(() => import("./Auth").then(module => ({ default: module.AuthPage })));
const Onboarding = lazy(() => import("./Onboarding").then(module => ({ default: module.Onboarding })));
document.documentElement.lang = language;
const path = window.location.pathname.replace(/\/$/, "") || "/";
const workspace = path === "/app";
if (path === "/") {
  document.title = t("Recruiting-Software & Kampagnen ab 19 € | MH");
  document.querySelector('meta[name="description"]')?.setAttribute("content", t("Recruiting-Kampagnen gemeinsam planen, Texte abstimmen und Inhalte exportieren. Entdecke die drei MH-Pilottarife ab 19 € mit flexiblen Tokens."));
  for (const selector of ['meta[property="og:title"]', 'meta[property="og:description"]', 'meta[name="twitter:title"]', 'meta[name="twitter:description"]']) {
    const meta = document.querySelector(selector);
    if (meta) meta.setAttribute('content', t(meta.getAttribute('content') || ''));
  }
  document.querySelector('meta[property="og:locale"]')?.setAttribute('content', language === 'de' ? 'de_DE' : 'en_GB');

}
const jobRoute=path === "/jobs" || /^\/jobs\/\d+$/.test(path);
if (path !== "/" && !jobRoute) {
  document.title = path === "/jobs" ? t("Offene Stellen | MH") : path.startsWith("/jobs/") || path.startsWith("/apply/") || path.startsWith("/r/") ? t("Bewerbung | MH") : path === "/register" ? t("Unternehmenskonto erstellen | MH") : path === '/auth' ? t("Konto absichern | MH") : path === '/onboarding' ? t("Workspace einrichten | MH") : workspace ? t("Anmelden | MH Recruiting Workspace") : t("Seite nicht gefunden | MH");
  document.querySelector('meta[name="robots"]')?.setAttribute("content", "noindex, nofollow");
  document.querySelector('link[rel="canonical"]')?.remove();
  document.querySelector('script[type="application/ld+json"]')?.remove();
}
const page = path === "/jobs" ? <Suspense fallback={<p>{t("Wird geladen …")}</p>}><JobPortal/></Suspense> : /^\/jobs\/\d+$/.test(path) ? <Suspense fallback={<p>{t("Wird geladen …")}</p>}><ApplyPage portal/></Suspense> : /^\/apply\/\d+$/.test(path) ? <Suspense fallback={<p>{t("Wird geladen …")}</p>}><ApplyPage/></Suspense> : /^\/r\/[A-Za-z0-9_-]{20,64}$/.test(path) ? <Suspense fallback={<p>{t("Wird geladen …")}</p>}><AdRedirect/></Suspense> : path === "/" ? <Landing /> : path === '/auth' ? <Suspense fallback={<p>{t("Konto wird geladen …")}</p>}><AuthPage/></Suspense> : path === '/onboarding' ? <Suspense fallback={<p>{t("Einrichtung wird geladen …")}</p>}><Onboarding/></Suspense> : path === "/register" ? <Suspense fallback={<p>{t("Registrierung wird geladen …")}</p>}><Registration /></Suspense> : workspace ? <Suspense fallback={<p>{t("Workspace wird geladen …")}</p>}><App /></Suspense> : <main style={{padding:40,fontFamily:"system-ui"}}><h1>{t("Seite nicht gefunden")}</h1><p>{t("Diese Adresse gibt es nicht.")}</p><a href="/">{t("Zur MH-Startseite")}</a></main>;
const description = document.querySelector('meta[name="description"]');
if (description) description.setAttribute('content', t(description.getAttribute('content') || ''));
const root = document.getElementById("root")!;
const bootstrap=document.getElementById('mh-job-bootstrap');
if(jobRoute){
  const initial=bootstrap?JSON.parse(bootstrap.textContent||'null'):null;
  // Keep server-rendered content visible until its interactive module is ready.
  if(path==='/jobs')void import('./JobPortal').then(({JobPortal})=>createRoot(root).render(<JobPortal initialResult={initial?.data} initialFilters={initial?.filters} initialOffset={initial?.offset}/>));
  else void import('./Apply').then(({ApplyPage})=>createRoot(root).render(<ApplyPage portal initialPage={initial?.data} campaignId={path.split('/')[2]}/>));
}
else if(path==='/')void import('./Landing').then(({Landing})=>{const landing=<React.StrictMode><Landing/></React.StrictMode>;if(root.hasChildNodes()&&language==='de')hydrateRoot(root,landing);else createRoot(root).render(landing);});
else createRoot(root).render(<React.StrictMode>{page}</React.StrictMode>);
