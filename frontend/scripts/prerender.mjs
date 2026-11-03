import { createServer, loadEnv } from "vite";
import { readFile, writeFile, mkdir } from "node:fs/promises";
const env = { ...loadEnv("production", process.cwd(), ""), ...process.env };
let origin = "";
if (env.SITE_URL) {
  const url = new URL(env.SITE_URL);
  if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash || url.pathname !== "/" || ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)) throw new Error("SITE_URL must be a public HTTPS origin without a path, query or credentials.");
  origin = url.origin;
}
if (process.argv.includes("--public") && !origin) throw new Error("Public build requires SITE_URL=https://your-real-domain in .env.production.local or the environment.");
const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom" });
let markup;
try { markup = (await server.ssrLoadModule("/src/entry-server.tsx")).render(); } finally { await server.close(); }
const template = await readFile("dist/index.html", "utf8");
let landing = template.replace('<div id="root"></div>', `<div id="root">${markup}</div>`);
const schema = { "@context": "https://schema.org", "@type": "WebPage", name: "MH Recruiting Workspace", description: "Recruiting-Kampagnen gemeinsam planen, abstimmen und exportieren. Geplante Pilottarife mit flexiblen Tokens.", inLanguage: "de-DE", ...(origin ? { url: origin + "/", isPartOf: { "@type": "WebSite", name: "MH Recruiting Workspace", url: origin + "/" } } : {}) };
landing = landing.replace("</head>", `<script type="application/ld+json">${JSON.stringify(schema).replaceAll("<", "\\u003c")}</script>\n</head>`);
if (origin) landing = landing.replace('content="noindex, nofollow"', 'content="index, follow, max-image-preview:large"').replace("</head>", `<link rel="canonical" href="${origin}/" /><meta property="og:url" content="${origin}/" /></head>`);
await writeFile("dist/index.html", landing);
await mkdir("dist/app", { recursive: true });
const privateTemplate = template.replace(/<title>.*?<\/title>/, "<title>Anmelden | MH Recruiting Workspace</title>").replace(/<meta (?:property="og:[^"]+"|name="twitter:[^"]+")[^>]*>/g, "").replace(/<meta name="description"[^>]*>/, '<meta name="description" content="Mit bestehendem Testkonto im MH Recruiting Workspace anmelden." />');
await writeFile("dist/app/index.html", privateTemplate.replace('<div id="root"></div>', '<div id="root"><p>Für die Anmeldung bitte JavaScript aktivieren.</p><a href="/">Zur Startseite</a></div>'));
await mkdir("dist/register", { recursive: true });
await writeFile("dist/register/index.html", privateTemplate.replace("Anmelden | MH Recruiting Workspace", "Unternehmenskonto erstellen | MH"));
for(const route of ['auth','onboarding','apply','r','jobs']){await mkdir(`dist/${route}`,{recursive:true});await writeFile(`dist/${route}/index.html`,privateTemplate.replace('Anmelden | MH Recruiting Workspace',route==='auth'?'Konto absichern | MH':'Workspace einrichten | MH'));}
await writeFile("dist/404.html", privateTemplate.replace("Anmelden | MH Recruiting Workspace", "Seite nicht gefunden | MH").replace('<div id="root"></div>', '<div id="root"><h1>Seite nicht gefunden</h1><a href="/">Zur Startseite</a></div>'));
await writeFile("dist/robots.txt", origin ? `User-agent: *\nAllow: /\nSitemap: ${origin}/sitemap.xml\n` : "User-agent: *\nDisallow: /\n");
await writeFile("dist/sitemap.xml", `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${origin ? `<url><loc>${origin}/</loc></url>` : ""}</urlset>`);
console.log(origin ? `Public SEO build ready for ${origin}.` : "Preview build: noindex. Set SITE_URL and run npm run build:public for publication.");
