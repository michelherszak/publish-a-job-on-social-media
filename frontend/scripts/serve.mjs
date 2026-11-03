import { createHash } from "node:crypto";
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import {pageHtml,publicData,originValue,indexable,errorPage,sitemap} from "./jobs-seo.mjs";
import { resolve, extname, sep } from "node:path";
const root = resolve("dist");
const api=originValue(process.env.JOBS_API_ORIGIN || (process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8011'));
const enabled=process.env.JOBS_INDEXABLE === '1';
const landing=await readFile(resolve(root,'index.html'),'utf8');
const site=landing.match(/rel="canonical" href="(https:\/\/[^" ]+)\/"/)?.[1]||'';
const jobsTemplate=await readFile(resolve(root,'jobs/index.html'),'utf8');
const renderer=await import('../dist/server/entry-jobs.js');
const manifest=JSON.parse(await readFile(resolve(root,'.vite/manifest.json'),'utf8'));
function styles(key,seen=new Set()){if(seen.has(key))return [];seen.add(key);const item=manifest[key];return item?[...(item.css||[]),...(item.imports||[]).flatMap(k=>styles(k,seen))]:[];}
const jobCss=Array.from(new Set([...styles('src/JobPortal.tsx'),...styles('src/Apply.tsx')]));
const types = { ".html":"text/html; charset=utf-8", ".js":"text/javascript; charset=utf-8", ".css":"text/css; charset=utf-8", ".svg":"image/svg+xml", ".xml":"application/xml; charset=utf-8", ".txt":"text/plain; charset=utf-8" };
const scriptHashes = [];
for (const page of ["index.html", "app/index.html", "register/index.html", "auth/index.html", "onboarding/index.html", "apply/index.html", "r/index.html", "jobs/index.html", "404.html"]) {
  const html = await readFile(resolve(root,page),"utf8");
  for (const match of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)) {
    if (match[1]) scriptHashes.push("'sha256-" + createHash("sha256").update(match[1]).digest("base64") + "'");
  }
}
const development=process.env.NODE_ENV !== 'production';
const connect = "'self'" + (development ? " http://127.0.0.1:8011 http://localhost:8011"+(api?' '+api:'') : '');
const csp = `default-src 'self'; script-src 'self' ${scriptHashes.join(' ')}; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:${development&&api?' '+api:''}; connect-src ${connect}; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'`;
const server=createServer(async (req, res) => {
  res.setHeader("Content-Security-Policy",csp);
  res.setHeader("X-Frame-Options","DENY");
  res.setHeader("X-Content-Type-Options","nosniff");
  res.setHeader("Referrer-Policy","no-referrer");
  res.setHeader("Permissions-Policy","camera=(), microphone=(), geolocation=()");
  if (!["GET", "HEAD"].includes(req.method)) { res.writeHead(405, { Allow: "GET, HEAD" }); return res.end(); }
  let path;
  try { path = decodeURIComponent(new URL(req.url, "http://localhost").pathname); } catch { res.writeHead(400); return res.end(); }
  if (path.startsWith('/server/') || path==='/server' || path.startsWith('/.vite/') || path.includes('/.')) { res.writeHead(404); return res.end(); }
  if (/^\/jobs(?:\/\d+)?\/$/.test(path) || /^\/jobs\/0+\d+$/.test(path)) { const normalized=path.replace(/\/$/,'').replace(/\/jobs\/(\d+)$/,(_,id)=>'/jobs/'+Number(id));res.writeHead(308,{Location:normalized+new URL(req.url,'http://localhost').search});return res.end(); }
  if(path==='/robots.txt' || path==='/sitemap.xml'){
    try{
      if(site&&enabled){
        const data=await publicData(api,'/jobs/sitemap');
        if(!data)throw Error('Sitemap unavailable');
        if(indexable(site,data,enabled)){
          const body=path==='/robots.txt'?`User-agent: *\nAllow: /\nSitemap: ${site}/sitemap.xml\n`:sitemap(site,data);
          res.writeHead(200,{'Content-Type':path==='/robots.txt'?'text/plain; charset=utf-8':'application/xml; charset=utf-8','Cache-Control':'no-cache'});return res.end(req.method==='HEAD'?undefined:body);
        }
      }
    }catch{res.writeHead(503,{'Retry-After':'60','X-Robots-Tag':'noindex, nofollow'});return res.end('Job sitemap temporarily unavailable');}
  }
  if(path==='/jobs'||/^\/jobs\/\d+$/.test(path)){
    let page;
    try{page=await pageHtml({url:new URL(req.url,'http://localhost'),template:jobsTemplate,renderer,api,site,enabled,css:jobCss});}
    catch{page=errorPage(jobsTemplate,503,'Stellen sind gerade nicht erreichbar. Bitte später erneut versuchen.');}
    const pageCsp=csp.replace(/script-src 'self'[^;]*;/,"script-src 'self' "+[...scriptHashes,...page.hashes].join(' ')+';');
    res.writeHead(page.status,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','Content-Security-Policy':pageCsp,'X-Robots-Tag':page.robots,...(page.status===503?{'Retry-After':'60'}:{})});return res.end(req.method==='HEAD'?undefined:page.html);
  }
  if (["/app/", "/register/", "/auth/", "/onboarding/"].includes(path)) { res.writeHead(308, { Location: path.slice(0,-1) + new URL(req.url, "http://localhost").search }); return res.end(); }
  if (path === "/index.html") { res.writeHead(308, { Location: "/" }); return res.end(); }
  const dynamicRoute = path === '/jobs' || /^\/jobs\/\d+$/.test(path) ? 'jobs' : /^\/apply\/\d+$/.test(path) ? 'apply' : /^\/r\/[A-Za-z0-9_-]{20,64}$/.test(path) ? 'r' : null;
  let file = dynamicRoute ? resolve(root,dynamicRoute,'index.html') : path === "/" ? resolve(root,"index.html") : ["/app", "/register", "/auth", "/onboarding"].includes(path) ? resolve(root,path.slice(1),"index.html") : resolve(root, "." + path);
  if (!file.startsWith(root + sep)) { res.writeHead(403); return res.end(); }
  let status = 200;
  try { if (!(await stat(file)).isFile()) throw Error(); } catch { file = resolve(root,"404.html"); status = 404; }
  try {
    const headers = { "Content-Type": types[extname(file)] || "application/octet-stream", "X-Content-Type-Options": "nosniff", "Cache-Control": file.includes(`${sep}assets${sep}`) ? "public, max-age=31536000, immutable" : "no-cache" };
    if (['/app','/register','/auth','/onboarding','/apply/','/r/','/jobs'].some(route=>path.startsWith(route)) || status === 404) headers["X-Robots-Tag"] = "noindex, nofollow";
    headers['Referrer-Policy']='no-referrer';
    res.writeHead(status, headers); res.end(req.method === "HEAD" ? undefined : await readFile(file));
  } catch { res.writeHead(500); res.end("Build unavailable. Run npm run build first."); }
}).listen(Number(process.env.PORT || 4181), process.env.HOST || "127.0.0.1", () => console.log(`MH build: http://${process.env.HOST || "127.0.0.1"}:${server.address().port}`));
