// Server HTML for every visitor, including social previews and search crawlers.
// Fetch only public fields from one operator-configured origin; never forward cookies.
import {createHash} from 'node:crypto';
const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const json=value=>JSON.stringify(value).replaceAll('<','\\u003c').replaceAll('\u2028','\\u2028').replaceAll('\u2029','\\u2029');
const filterNames=['q','location','company','employment','work_mode'];
export function originValue(value){if(!value)return '';const u=new URL(value);if(!['http:','https:'].includes(u.protocol)||u.username||u.password||u.search||u.hash||u.pathname!=='/')throw Error('JOBS_API_ORIGIN must be an HTTP(S) origin without credentials or path');return u.origin;}
export async function publicData(origin,path){if(!origin)throw Error('Public jobs API is not configured');const r=await fetch(origin+path,{redirect:'error',signal:AbortSignal.timeout(5000),headers:{Accept:'application/json'}});if(r.status===404)return null;if(!r.ok)throw Error('Public jobs API unavailable');const text=await r.text();if(text.length>4_000_000)throw Error('Public jobs response too large');return JSON.parse(text);}
export function indexable(site,data,enabled){return !!site&&enabled&&data?.test===false;}
export function jobSchema(data,site,description){
 if(!data.date_posted||!data.company||!data.title||!data.text?.trim()||!data.location)return null;
 const date=new Date(data.date_posted*1000);if(!Number.isFinite(date.getTime())||date>Date.now())return null;
 const schema={'@context':'https://schema.org','@type':'JobPosting',title:data.title,description,datePosted:date.toISOString().slice(0,10),identifier:{'@type':'PropertyValue',name:data.company,value:String(data.id)},hiringOrganization:{'@type':'Organization',name:data.company},url:site+'/jobs/'+data.id,directApply:true};
 if(data.ends_at)schema.validThrough=new Date(data.ends_at*1000).toISOString();
 const employment={full_time:'FULL_TIME',part_time:'PART_TIME',temporary:'TEMPORARY',mini_job:'PART_TIME',apprenticeship:'OTHER'}[data.employment];if(employment)schema.employmentType=employment;
 if(data.work_mode==='remote'){schema.jobLocationType='TELECOMMUTE';schema.applicantLocationRequirements={'@type':'Country',name:'DE'};}
 else schema.jobLocation={'@type':'Place',address:{'@type':'PostalAddress',addressLocality:data.location,addressCountry:'DE'}};
 // Salary stays visible text until a verified amount, currency and pay period exist.
 return schema;
}
export async function pageHtml({url,template,renderer,api,site,enabled,css}){
 const id=url.pathname.match(/^\/jobs\/(\d+)$/)?.[1];
 const filters=Object.fromEntries(filterNames.map(k=>[k,url.searchParams.get(k)||'']));
 if(filterNames.some(k=>filters[k].length>(k==='company'?160:k==='employment'||k==='work_mode'?30:100)))return errorPage(template,400,'Ungültige Suchfilter.');
 const rawPage=url.searchParams.get('page')||'1';if(!/^\d+$/.test(rawPage)||Number(rawPage)<1||Number(rawPage)>4167)return errorPage(template,400,'Ungültige Stellenseite.');
 const offset=(Number(rawPage)-1)*24;
 const data=await publicData(api,id?'/jobs/'+id:'/jobs?'+new URLSearchParams({...filters,offset:String(offset)}));
 if(!data)return errorPage(template,404,'Diese Stelle ist nicht mehr verfügbar.');
 if(id&&(!data.text||!data.title||!data.company))throw Error('Invalid public job response');
 if(!id&&(!Array.isArray(data.jobs)||!Number.isFinite(data.total)))throw Error('Invalid public directory response');
 const available=indexable(site,data,enabled);const filtered=Object.values(filters).some(Boolean);
 const robots=available&&(!filtered||id)?'index, follow, max-image-preview:large':'noindex, follow';
 const canonical=site+(id?'/jobs/'+id:'/jobs'+(offset>0&&!filtered?'?page='+rawPage:''));
 const title=id?`${data.title} in ${data.location} | ${data.company} | MH`:'Jobs im Handwerk und in der Pflege | MH';
 const description=id?`${data.title} bei ${data.company} in ${data.location}.${data.salary?' '+data.salary+'.':''} Direkt auf MH bewerben – ohne Konto und ohne Lebenslaufpflicht.`:'Offene Jobs im Handwerk und in der Pflege in Deutschland. Stelle in deiner Nähe finden und ohne Konto oder Lebenslaufpflicht direkt beim Arbeitgeber bewerben.';
 const schema=id&&available?jobSchema(data,site,renderer.jobDescription(data.text)):null;
 const body=id?renderer.renderJob(data,id):renderer.renderDirectory(data,filters,offset);
 const bootstrap={data,...(!id?{filters,offset}:{})};
 const tags=`<meta name="description" content="${escape(description)}"><meta name="robots" content="${robots}">${site?`<link rel="canonical" href="${escape(canonical)}">`:''}<meta property="og:type" content="website"><meta property="og:locale" content="de_DE"><meta property="og:site_name" content="MH Jobs"><meta property="og:title" content="${escape(title)}"><meta property="og:description" content="${escape(description)}">${site?`<meta property="og:url" content="${escape(canonical)}">`:''}${id&&data.image&&site?`<meta property="og:image" content="${escape(site+'/api/jobs/'+id+'/image')}"><meta property="og:image:alt" content="${escape(data.title)}">`:''}<meta name="twitter:card" content="${id&&data.image?'summary_large_image':'summary'}">${schema?`<script type="application/ld+json">${json(schema)}</script>`:''}<script id="mh-job-bootstrap" type="application/json">${json(bootstrap)}</script>${css.map(file=>`<link rel="stylesheet" href="/${escape(file)}">`).join('')}`;
 const html=cleanTemplate(template).replace(/<title>.*?<\/title>/s,`<title>${escape(title)}</title>`).replace('</head>',tags+'</head>').replace('<div id="root"></div>',`<div id="root">${body}</div>`);
 return {status:200,html,robots,hashes:hashes(html)};
}
export function cleanTemplate(template){return template.replace(/<meta (?:name="(?:description|robots|twitter:[^"]+)"|property="og:[^"]+")[^>]*>/g,'').replace(/<link rel="canonical"[^>]*>/g,'').replace(/<script type="application\/ld\+json">[\s\S]*?<\/script>/g,'');}
export function hashes(html){return Array.from(html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)).filter(m=>m[1]).map(m=>"'sha256-"+createHash('sha256').update(m[1]).digest('base64')+"'");}
export function errorPage(template,status,message){const html=cleanTemplate(template).replace(/<title>.*?<\/title>/s,`<title>${escape(message)} | MH</title>`).replace('</head>','<meta name="robots" content="noindex, nofollow"></head>').replace('<div id="root"></div>',`<div id="root"><main class="apply-page"><h1>${escape(message)}</h1><a href="/jobs">Alle offenen Stellen</a></main></div>`).replace(/<script\b[^>]*src=[^>]*><\/script>/g,'');return {status,html,robots:'noindex, nofollow',hashes:[]};}
export function sitemap(site,data){if(!site||!Array.isArray(data.jobs)||data.jobs.length>49998)throw Error('Invalid sitemap data');return '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+[`${site}/`,`${site}/jobs`,...data.jobs.map(j=>`${site}/jobs/${j.id}`)].map((loc,i)=>`<url><loc>${escape(loc)}</loc>${i>1&&data.jobs[i-2].updated_at?`<lastmod>${new Date(data.jobs[i-2].updated_at*1000).toISOString()}</lastmod>`:''}</url>`).join('')+'</urlset>';}
