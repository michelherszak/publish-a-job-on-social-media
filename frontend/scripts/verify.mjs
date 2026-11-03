import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { spawn } from "node:child_process";
import { once } from "node:events";
const html = await readFile("dist/index.html", "utf8");
assert.match(html, /<h1>Recruiting-Kampagnen/);
assert.equal((html.match(/<h1[ >]/g) || []).length, 1);
for (const id of ["ablauf", "tokens", "preise", "start"]) assert.match(html, new RegExp(`id="${id}"`));
assert.ok(html.indexOf('id="tokens"') < html.indexOf('id="preise"'));
assert.match(html, /application\/ld\+json/);
const data = JSON.parse(html.match(/<script type="application\/ld\+json">(.*?)<\/script>/s)[1]);
assert.equal(data["@type"], "WebPage");
const app = await readFile("dist/app/index.html", "utf8");
assert.match(app, /noindex, nofollow/);
assert.doesNotMatch(app, /rel="canonical"/);
const canonical = html.match(/rel="canonical" href="([^"]+)"/);
const sitemap = await readFile("dist/sitemap.xml", "utf8");
const robots = await readFile("dist/robots.txt", "utf8");
if (canonical) {
  assert.match(html, /index, follow, max-image-preview:large/);
  assert.ok(sitemap.includes(`<loc>${canonical[1]}</loc>`));
  assert.ok(robots.includes(`Sitemap: ${canonical[1]}sitemap.xml`));
} else { assert.match(html, /noindex, nofollow/); assert.match(robots, /Disallow: \//); }
assert.doesNotMatch(sitemap, /\/app/);
const server = spawn(process.execPath, ["scripts/serve.mjs"], { env: { ...process.env, PORT: "4187", HOST: "127.0.0.1", JOBS_API_ORIGIN: "http://127.0.0.1:1" }, stdio: ["ignore", "pipe", "pipe"] });
try {
  await Promise.race([once(server.stdout,"data"), once(server,"exit").then(()=>{throw Error("Verification server exited");})]);
  const base = "http://127.0.0.1:4187";
  assert.equal((await fetch(base)).status, 200);
  for(const route of ['/jobs','/jobs/123']){const job=await fetch(base+route);assert.equal(job.status,503);assert.equal(job.headers.get('x-robots-tag'),'noindex, nofollow');}
  const login = await fetch(base+"/app"); assert.equal(login.status,200); assert.equal(login.headers.get("x-robots-tag"),"noindex, nofollow");
  assert.equal(login.headers.get("x-frame-options"),"DENY");
  assert.match(login.headers.get("content-security-policy"), /frame-ancestors 'none'/);
  assert.match(login.headers.get("content-security-policy"), /script-src 'self'/);
  const registration = await fetch(base+"/register"); assert.equal(registration.status,200); assert.equal(registration.headers.get("x-robots-tag"),"noindex, nofollow");
  assert.doesNotMatch(sitemap, /\/register/);
  for(const route of ['auth','onboarding']){const page=await fetch(base+'/'+route);assert.equal(page.status,200);assert.equal(page.headers.get('x-robots-tag'),'noindex, nofollow');assert.match(await page.text(),/noindex, nofollow/);assert.doesNotMatch(sitemap,new RegExp('/'+route));assert.equal((await fetch(base+'/'+route+'/',{redirect:'manual'})).status,308);}
  const missing = await fetch(base+"/does-not-exist"); assert.equal(missing.status,404); assert.match(await missing.text(),/Seite nicht gefunden/);
  assert.equal((await fetch(base+"/app/", {redirect:"manual"})).status,308);
  assert.equal((await fetch(base+"/index.html", {redirect:"manual"})).status,308);
  assert.equal((await fetch(base+"/sitemap.xml")).status,200);
  console.log("SEO checks passed: pre-rendered content, route metadata, sitemap, robots, redirects, and HTTP 404.");
} finally { server.kill(); }
