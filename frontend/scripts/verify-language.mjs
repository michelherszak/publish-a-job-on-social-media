import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
const require = createRequire(import.meta.url);
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

// Load the actual source modules with browser language preferences in isolated contexts.
// No browser settings, backend data or external providers are changed.
function appModules(languages, server = false, fixtures = {}, search = '') {
  const cache = new Map();
  function load(filename) {
    filename = path.resolve(filename);
    if (cache.has(filename)) return cache.get(filename).exports;
    const module = {exports:{}};
    cache.set(filename,module);
    let source = fs.readFileSync(filename,'utf8');
    // Render real components with read-only states normally obtained from the API.
    const file = ts.createSourceFile(filename, source, ts.ScriptTarget.Latest, true);
    const edits = [];
    function instrument(node) {
      if (ts.isVariableDeclaration(node) && ts.isArrayBindingPattern(node.name) && node.initializer && ts.isCallExpression(node.initializer) && node.initializer.expression.getText(file) === 'useState') {
        const call = node.initializer;
        const key = node.name.elements[0].name.getText(file);
        edits.push([call.getStart(file),call.end,`__testState(${JSON.stringify(path.basename(filename))},${JSON.stringify(key)},${call.arguments[0]?.getText(file) || 'undefined'})`]);
      }
      ts.forEachChild(node,instrument);
    }
    instrument(file);
    for (const [start,end,replacement] of edits.sort((a,b)=>b[0]-a[0])) source = source.slice(0,start)+replacement+source.slice(end);
    const code = ts.transpileModule(source.replaceAll('import.meta.env','({})'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText;
    const localRequire = spec => {
      if (spec.endsWith('.css')) return {};
      if (!spec.startsWith('.')) return require(spec);
      const base = path.resolve(path.dirname(filename),spec);
      if (base.endsWith('.json')) return JSON.parse(fs.readFileSync(base,'utf8'));
      return load(['.ts','.tsx'].map(ext=>base+ext).find(p=>fs.existsSync(p)) || base);
    };
    const context = {module,exports:module.exports,require:localRequire,console,Intl,URL,URLSearchParams,crypto:{randomUUID:()=> 'language-test'},sessionStorage:{getItem:()=>null},__testState:(file,key,initial)=>React.useState(Object.hasOwn(fixtures[file] || {},key)?fixtures[file][key]:initial),navigator:{languages,language:languages[0]},...(server?{}:{window:{location:{pathname:'/',search,hash:'',hostname:'localhost'}}})};
    vm.runInNewContext(code,context,{filename});
    return module.exports;
  }
  return name => load('src/'+name+'.ts'+(name==='i18n'||name==='pricing'?'':'x'));
}
const node = appModules(['en-US'],true)('i18n');
assert.equal(node.language,'de','Prerender is German even when Node exposes an English navigator');
for(const [preferences,expected] of [[['de-AT','en'],'de'],[['en-US','de'],'en'],[['fr-FR','de-CH'],'de'],[['fr'],'en'],[[],'en'],[['DE_de'],'de'],[[' en-IE '],'en']]) {
  assert.equal(node.detectLanguage(preferences),expected);
}
const noop=()=>{};
const brief={role:'Engineer {name}',location:'Berlin',employment_type:'',tasks:'',requirements:'',benefits:'',salary:'',tone:'',channels:['Instagram','Meta']};
for(const language of ['de','en']) {
  const load=appModules([language+'-'+(language==='de'?'DE':'GB')]);
  const i18n=load('i18n');
  assert.equal(i18n.language,language);
  assert.equal(i18n.t('Customers'),language==='de'?'Kunden':'Customers');
  assert.equal(i18n.t('unmapped customer content'),'unmapped customer content');
  const landing=renderToStaticMarkup(React.createElement(load('Landing').Landing));
  assert.ok(landing.includes(language==='de'?'Recruiting-Kampagnen.':'Recruiting campaigns.'));
  assert.ok(landing.includes(language==='de'?'Wie viele Personen bearbeiten Kampagnen?':'How many people edit campaigns?'));
  assert.ok(landing.includes(language==='de'?'19,00':'19.00'),'EUR formatting follows the locale');
  const wizard=renderToStaticMarkup(React.createElement(load('CampaignWizard').CampaignWizard,{mode:'new',briefing:brief,setBriefing:noop,orgs:[{id:1,name:'Original Company'}],orgId:1,setOrgId:noop,isAgency:false,onClose:noop,onSave:noop,busy:false,error:'',saved:false,wallet:{managed:false,active:true,available:0}}));
  assert.ok(wizard.includes(language==='de'?'Wen möchtet ihr einstellen?':'Who are you looking to hire?'));
  assert.ok(wizard.includes('Engineer {name}'),'Saved input is never translated or interpolated');
  const channelWizard=renderToStaticMarkup(React.createElement(appModules([language],false,{'CampaignWizard.tsx':{step:2}})('CampaignWizard').CampaignWizard,{mode:'new',briefing:brief,setBriefing:noop,orgs:[{id:1,name:'Original Company'}],orgId:1,setOrgId:noop,isAgency:false,onClose:noop,onSave:noop,busy:false,error:'',saved:false,wallet:{managed:false,active:true,available:0}}));
  assert.equal((channelWizard.match(/type="checkbox"/g) || []).length,2,'The briefing only offers Instagram and Meta');
  assert.ok(channelWizard.includes('<strong>Instagram</strong>') && channelWizard.includes('<strong>Meta</strong>'));
  assert.ok(!channelWizard.includes('LinkedIn') && !channelWizard.includes('XING'));
  const campaign={id:1,organization_id:1,role:brief.role,location:'Berlin',status:'Draft',channels:brief.channels,briefing:brief,generated:{jobAd:'Original German campaign text <private>'},change_request:'',updated_at:0};
  const studio=renderToStaticMarkup(React.createElement(load('ContentStudio').ContentStudio,{campaign,orgName:()=> 'Original Company',activeTab:'social',onTab:noop,drafts:{},onChange:noop,onSave:noop,onDiscard:noop,onEdit:noop,onGenerate:noop,canEdit:true,busy:false,error:'',cost:''}));
  assert.ok(studio.includes(language==='de'?'Aus Entwürfen wird eure Kampagne.':'Turn drafts into your campaign.'));
  assert.ok(studio.includes('Original German campaign text &lt;private&gt;'));
  assert.ok(studio.includes(language==='de'?'Änderungen speichern':'Save changes'));
  assert.ok(studio.includes('cs-tab-social') && studio.includes('cs-tab-meta'));
  assert.equal((studio.match(/role="tab"/g) || []).length,2,'Only Instagram and Meta are studio tabs');
  assert.ok(!studio.includes('<select'),'The studio does not contain a campaign selector');
  assert.ok(!studio.includes('cs-tab-jobAd') && !studio.includes('cs-tab-linkedin') && !studio.includes('cs-tab-xing') && !studio.includes('cs-tab-video'));
  assert.ok(studio.includes(language==='de'?'Stellenbeschreibung auf MH':'Job description on MH'));
  const photo={id:7,name:'Company photo {name}.jpg',width:1200,height:1600,revision:1,selected:true,feed:{x:0.5,y:0.5,zoom:1},story:{x:0.5,y:0.5,zoom:1}};
  const photoModule=appModules([language],false,{'CampaignImages.tsx':{images:[photo],loading:false},'ContentStudio.tsx':{view:'preview'}});
  const photoProps={campaign,orgName:()=> 'Original Company',activeTab:'social',onTab:noop,drafts:{},onChange:noop,onSave:async()=>true,onDiscard:noop,onEdit:noop,onGenerate:noop,canEdit:true,busy:false,error:'',cost:''};
  for(const activeTab of ['social','meta']){
    const withPhoto=renderToStaticMarkup(React.createElement(photoModule('ContentStudio').ContentStudio,{...photoProps,activeTab}));
    assert.ok(withPhoto.includes(language==='de'?'Kampagnenbilder':'Campaign images'));
    assert.ok(withPhoto.includes('Company photo {name}.jpg'),'Uploaded filenames remain unchanged');
    assert.equal((withPhoto.match(/class="ci-crop ci-feed"/g)||[]).length,2,'The image is shown in the crop editor and channel preview');
    assert.ok(withPhoto.includes(language==='de'?'Bild und Text speichern':'Save image and copy'));
    assert.ok(withPhoto.includes('type="file"'));
  }
  const readOnly=renderToStaticMarkup(React.createElement(photoModule('ContentStudio').ContentStudio,{...photoProps,canEdit:false}));
  assert.ok(!readOnly.includes('type="file"'),'Customer view does not offer uploads');
  const dirtyPhoto=renderToStaticMarkup(React.createElement(photoModule('ContentStudio').ContentStudio,{...photoProps,imageDraft:{id:7,revision:1,feed:{x:0.5,y:0.5,zoom:1.5},story:photo.story}}));
  assert.ok(dirtyPhoto.includes(language==='de'?'Eine Änderung ungespeichert':'One unsaved change'));

}

const catalog = JSON.parse(fs.readFileSync('src/translations.json','utf8'));
const products = JSON.parse(fs.readFileSync('../pricing_catalog.json','utf8'));
for (const [key, entry] of Object.entries(catalog)) {
  assert.ok(entry.de && entry.en, `Missing DE/EN translation: ${key}`);
  const slots = value => (value.match(/\{\w+\}/g) || []).sort();
  assert.deepEqual(slots(entry.de), slots(entry.en), `Translation placeholders differ: ${key}`);
}
for (const product of Object.values(products)) {
  // Tier names are proper names; localized annual and token labels require entries.
  if (!['Starter','Team','Scale'].includes(product.name)) assert.ok(catalog[product.name], `Missing product label: ${product.name}`);
}
for (const name of fs.readdirSync('src').filter(name=>/\.tsx?$/.test(name))) {
  const file = ts.createSourceFile(name,fs.readFileSync('src/'+name,'utf8'),ts.ScriptTarget.Latest,true);
  function check(node) {
    if (ts.isCallExpression(node) && node.expression.getText(file)==='t' && node.arguments[0] && ts.isStringLiteral(node.arguments[0])) {
      assert.ok(catalog[node.arguments[0].text],`${name}: missing translation ${node.arguments[0].text}`);
    }
    if (ts.isJsxText(node) && /[A-Za-zÄÖÜäöüß]/.test(node.text)) {
      const unchanged = new Set(['M','MH','mh','mh.','MH Content Studio','MH CONTENT STUDIO','MH RECRUITING','MH ·','MH Recruiting Workspace','RECRUITING WORKSPACE','LinkedIn','Instagram','Meta','Facebook','XING','Website','FACEBOOK & INSTAGRAM','FACEBOOK','Instagram:','Tokens','Version 02','Status','Name','Text']);
      assert.ok(unchanged.has(node.text.trim()),`${name}: untranslated JSX text ${node.text.trim()}`);
    }
    if (ts.isJsxAttribute(node) && ['subtitle','eyebrow','label','title','aria-label','placeholder','alt'].includes(node.name.text) && node.initializer && ts.isStringLiteral(node.initializer)) {
      const value = node.initializer.text;
      assert.ok(value === 'https://' || (node.name.text === 'alt' && value === '') || catalog[value],`${name}: untranslated ${node.name.text}: ${value}`);
    }
    ts.forEachChild(node,check);
  }
  check(file);
}
const errors = JSON.parse(execFileSync('python3',['-c',`
import ast, json
from pathlib import Path
messages = set()
for path in Path('backend').glob('*.py'):
    if path.name.startswith('test_'): continue
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'HTTPException' and len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
            messages.add(node.args[1].value)
print(json.dumps(sorted(messages)))
`],{cwd:'..',encoding:'utf8'}));
for (const message of errors) assert.ok(catalog[message],`Missing API error translation: ${message}`);

for (const lang of ['de','en']) {
  const english = lang === 'en';
  const company = {id:1,name:'Original Company',industry:'Original industry',location:'Berlin',brand_description:'Original description',benefits:'Original benefits',tone:'Original tone',contact_name:'Original Name',contact_email:'original@example.invalid',website:''};
  const campaign = {id:1,organization_id:1,role:'Original role',location:'Berlin',status:'Review',channels:['Website'],briefing:brief,generated:{jobAd:'Original campaign copy'},change_request:'',updated_at:0};
  const user = {id:1,name:'Original User',email:'original@example.invalid',role:'firmen_admin',base_role:'firmen_admin',organization_id:1,security_required:false,email_verified:true,security_pending:false};
  const ledger = [{description:'Starter Jahresabo Monatsguthaben (Rest des Vormonats verfällt)',created_at:1,included_delta:250,purchased_delta:0}];
  const render = (module,component,props={},states={},search='') => renderToStaticMarkup(React.createElement(appModules([lang],false,states,search)(module)[component],props));
  const i18n = appModules([lang])('i18n');
  assert.equal(i18n.systemText('Kampagnenentwurf #42 · 50 Tokens'),english?'Campaign draft #42 · 50 tokens':'Kampagnenentwurf #42 · 50 Tokens');
  assert.equal(i18n.historyText({action:'commented',message:'Campaign created'}),'Campaign created');
  assert.equal(i18n.historyText({action:'changes_requested',message:'Briefing angelegt'}),'Briefing angelegt');
  assert.equal(i18n.historyText({action:'created',message:'Briefing angelegt'}),english?'Briefing created':'Briefing angelegt');
  assert.equal(i18n.systemText('Campaign created'),english?'Campaign created':'Kampagne angelegt');
  assert.ok(i18n.systemText('Personalbedarf: paused; Zuständigkeiten aktualisiert').includes(english?'Search paused':'Suche pausiert'));
  assert.ok(i18n.systemText('Facebook: Veröffentlichung manuell dokumentiert; keine Anbieterbestätigung').includes(english?'publication recorded manually':'Veröffentlichung manuell dokumentiert')); 
  assert.ok(i18n.systemText('1.000 MH-Tokens gekauft').includes(english?'purchased':'gekauft'));
  assert.ok(i18n.systemText('Was bedeutet „familiär“ bei dieser Stelle konkret? Bitte ein belegbares Beispiel ergänzen.').includes(english?'What does':'Was bedeutet'));
  for (const [screen,expected] of Object.entries({overview:english?'Your campaigns and approvals':'Deine Kampagnen und Freigaben',campaigns:english?'Campaigns':'Kampagnen',approvals:english?'Review campaign content before internal approval.':'Prüfe die Kampagneninhalte vor der internen Freigabe.',analytics:english?'Confirmed application receipts':'Bestätigte Bewerbung',settings:english?'Manage your account, users and integrations.':'Konto, Benutzer und Integrationen verwalten.',studio:english?'Turn drafts into your campaign.':'Aus Entwürfen wird eure Kampagne.'})) {
    const html = render('App','App',{}, {'App.tsx':{checkingSession:false,user,screen,orgs:[company],campaigns:[campaign],selectedId:1,users:[user],activity:[{id:1,actor:'Original User',message:'Campaign created',created_at:1}],history:[{id:1,action:'created',message:'Briefing angelegt',created_at:1}],wallet:{managed:true,active:true,available:1250,included:1000,purchased:250,ledger}}});
    assert.ok(html.includes(expected),`${lang}: workspace ${screen}`);
    assert.ok(!html.includes('QUALITY CONTROL') || english);
    assert.ok(!html.includes('firmen_admin</') && !html.includes('firmen admin ·'));
  }
  assert.ok(render('App','App',{}, {'App.tsx':{checkingSession:false,user:{...user,role:'platform_admin',base_role:'platform_admin',organization_id:null},screen:'customers',orgs:[company]}}).includes(english?'Customers':'Kunden'));
  const config={ready:true,mode:'test',countries:{DE:'Deutschland'},catalog:products};
  const billing=render('Billing','Billing',{}, {'Billing.tsx':{config,status:{managed:true,status:'active',plan:'starter_yearly',included:1000,purchased:250,country:'DE',active:true,hold:'Tarifänderung muss geprüft werden',period_end:0,credit_period_end:0,ledger}}});
  assert.ok(billing.includes(english?'Starter annual subscription':'Starter Jahresabo'));
  assert.ok(billing.includes(english?'Plan change requires review':'Tarifänderung muss geprüft werden'));
  assert.ok(billing.includes(english?'monthly allowance':'Monatsguthaben'));
  assert.ok(render('Billing','Registration',{}, {'Billing.tsx':{config}}).includes(english?'Your company at MH.':'Dein Unternehmen bei MH.'));
  for(const action of ['forgot','reset','invite','resend','verify','recover','recover-verify','recover-reset']) {
    const html=render('Auth','AuthPage',{}, {}, '?action='+action);
    assert.ok(html.includes(english?'Go to sign in':'Zur Anmeldung'),`${lang}: auth ${action}`);
  }
  assert.ok(render('Auth','SecurityPanel',{user:{...user,email_verified:false},onReady:noop}).includes(english?'Verify email':'E-Mail bestätigen'));
  for (const recovery of [false, true]) {
    const security=render('Auth','SecurityPanel',{user:{...user,mfa_enabled:true,security_pending:true},onReady:noop},{'Auth.tsx':{usingRecovery:recovery}});
    assert.ok(security.includes(english?'Confirm your sign-in':'Anmeldung bestätigen'));
    assert.ok(security.includes(recovery?(english?'Enter an unused recovery code.':'Gib einen unbenutzten Wiederherstellungscode ein.'):(english?'Open your authenticator app and enter the current six-digit code.':'Öffne deine Authenticator-App und gib den aktuellen sechsstelligen Code ein.')));
    assert.ok(security.includes(recovery?(english?'Use authenticator app':'Authenticator-App verwenden'):(english?'Use a recovery code':'Wiederherstellungscode verwenden')));
    assert.ok(!security.includes('SECURE YOUR ACCOUNT')&&!security.includes('Two-factor authentication'));
  }
  const reconnect=render('Auth','SecurityPanel',{user:{...user,mfa_enabled:true,security_pending:true},onReady:noop},{'Auth.tsx':{reconnecting:true}});
  assert.ok(reconnect.includes(english?'Connect authenticator app':'Authenticator-App verbinden'));
  assert.ok(reconnect.includes(english?'Show QR code':'QR-Code anzeigen'));
  assert.ok(reconnect.includes(english?'Enter an unused MH recovery code.':'Gib einen unbenutzten MH-Wiederherstellungscode ein.'));
  assert.ok(render('Onboarding','Onboarding',{}, {'Onboarding.tsx':{user,state:{paid:true,profile_done:false,company}}}).includes(english?'Company profile':'Firmenprofil'));
  assert.ok(render('Invitations','Invitations',{}, {'Invitations.tsx':{pending:[{email:'original@example.invalid',role:'firmen_admin',expires_at:1}]}}).includes(i18n.roleLabel('firmen_admin')));
  assert.ok(render('EmailPreviews','EmailPreviews',{}, {'EmailPreviews.tsx':{loading:false,items:[{id:'registration',label:'Registrierung',description:'Bestätigt nach der Registrierung den Zugriff auf das Postfach.',subject:'Original subject',text:'Original mail text',sender:'original@example.invalid',recipient:'original@example.invalid'}]}}).includes(english?'Registration':'Registrierung'));
  const recoveryAdmin=render('AccountRecoveries','AccountRecoveries',{user:{...user,mfa_enabled:true},onSecurityReady:noop},{'AccountRecoveries.tsx':{loading:false,selectedId:'fixture-case',items:[{id:'fixture-case',email:'original@example.invalid',name:'Original person',company:'Original company',state:'verified',created_at:1}]}});
  assert.ok(recoveryAdmin.includes(english?'Approve and send recovery link':'Freigeben und Wiederherstellungslink senden'));
  assert.ok(render('Apply','ApplyPage',{}, {'Apply.tsx':{page:{title:'Original role',company:'Original Company',location:'Berlin',text:'Original copy',retention_days:30}}}).includes(english?'Apply now':'Jetzt bewerben'));
  const jobs=render('JobPortal','JobPortal',{}, {'JobPortal.tsx':{result:{jobs:[{id:1,title:'Original role',company:'Original Company',location:'Berlin',employment:'full_time',work_mode:'hybrid',salary:'Original salary',image:true}],total:1,companies:['Original Company'],test:true}}});
  assert.ok(jobs.includes(english?'Jobs in skilled trades and care.':'Jobs im Handwerk und in der Pflege.'));
  assert.ok(jobs.includes(english?'Full-time':'Vollzeit'));
  assert.ok(jobs.includes('Original role')&&jobs.includes('href="/jobs/1"'));
  const consent=render('Apply','ApplyPage',{portal:true},{'Apply.tsx':{page:{title:'Original role',company:'Original Company',location:'Berlin',text:'Original copy',retention_days:30,image:true}}});
  assert.ok(consent.includes(english?'Reject all / withdraw':'Alles ablehnen / widerrufen'));
  assert.ok(consent.includes(english?'Allow marketing / retargeting':'Marketing / Retargeting erlauben'));
  assert.ok(!consent.includes('connect.facebook.net'));
  const plan={revision:1,country:'DE',employment:'full_time',work_mode:'hybrid',ends_at:0,ends_on:'',budget_cents:15000,duration_days:14,retargeting:true,contact_email:'fixture@example.invalid',privacy_url:'',retention_days:90};
  const jobPlan=render('JobCampaign','JobCampaign',{campaign:{...campaign,status:'Live'},canManage:true,dirty:false,onDirty:noop},{'JobCampaign.tsx':{plan,data:{plan,enabled:true,url:'/jobs/1',tasks:[{channel:'Meta',kind:'paid',state:'prepared',url:'/r/fixture'}],provider_live:false}}});
  assert.ok(jobPlan.includes(english?'One job. One shared budget.':'Eine Stelle. Ein gemeinsames Budget.'));
  assert.ok(jobPlan.includes(english?'Prepared · not published externally':'Vorbereitet · nicht extern veröffentlicht'));
  const readonlyJobPlan=render('JobCampaign','JobCampaign',{campaign:{...campaign,status:'Live'},canManage:false,dirty:false,onDirty:noop},{'JobCampaign.tsx':{plan,data:{plan,enabled:true,url:'/jobs/1',tasks:[],provider_live:false}}});
  assert.ok(!readonlyJobPlan.includes(english?'Activate MH and start local workflow':'MH aktivieren und lokalen Workflow starten'));
  const workflow={id:1,mode:'simulation',enabled:true,budget_cents:15000,simulated_spent_cents:100,remaining_cents:14900,actual_spent_cents:0,audience:1,ads_end_at:1791300000,image:true,tasks:[{id:1,channel:'Instagram',kind:'organic',state:'simulated',reason:'',provider_id:'sim_fixture',attempts:1,allocation_cents:0,spent_cents:0,impressions:0,clicks:0,url:'/r/fixture',text:'Original copy {name}',placement:'profile_or_story_link'},{id:2,channel:'Meta',kind:'retargeting',state:'waiting',reason:'no_audience',provider_id:'',attempts:0,allocation_cents:3750,spent_cents:0,impressions:0,clicks:0,url:'/r/fixture',text:'Original copy',placement:'clickable_ad_or_post'}]};
  const workflowView=render('CampaignWorkflow','CampaignWorkflow',{workflow,campaignId:1,canManage:true,dirty:false,onUpdated:async()=>{}});
  assert.ok(workflowView.includes(english?'Delivered in local simulation':'Im lokalen Test ausgeliefert'));
  assert.ok(workflowView.includes(english?'Test ad delivery locally':'Werbeauslieferung lokal testen'));
  assert.ok(workflowView.includes(english?'No consenting readers without a submitted application yet.':'Noch keine zustimmenden Leser ohne abgesendete Bewerbung.'));
  assert.ok(workflowView.includes('Original copy {name}'));
  const readonlyWorkflow=render('CampaignWorkflow','CampaignWorkflow',{workflow,campaignId:1,canManage:false,dirty:false,onUpdated:async()=>{}});
  assert.ok(!readonlyWorkflow.includes(english?'Test ad delivery locally':'Werbeauslieferung lokal testen'));
  const engagement=render('JobCampaign','JobEngagement',{campaigns:[campaign]},{'JobCampaign.tsx':{report:{applications:1,totals:{requests:10,consented_views:4,engaged:2,form_started:2,consented_applications:1,retargeting_eligible:1}}}});
  assert.ok(engagement.includes(english?'Visits with analytics consent':'Besuche mit Analyse-Einwilligung'));
  assert.ok(engagement.includes(english?'no Meta audience created':'keine Meta-Zielgruppe erstellt'));
  assert.ok(render('Tracking','TrackingAnalytics',{campaigns:[campaign],canReadApplications:true}).includes(english?'Which ad brings applications?':'Welche Anzeige bringt Bewerbungen?'));
  assert.ok(render('SocialPublishing','MetaConnection',{}, {'SocialPublishing.tsx':{status:{ready:false,pages:[],connection:null}}}).includes(english?'Connect your own company Page':'Eigene Unternehmensseite verbinden'));
  assert.ok(render('SocialPublishing','FacebookPublishing',{campaign,dirty:false,admin:true}).includes(english?'Publish on the company Page':'Auf der Unternehmensseite veröffentlichen'));
  const need={version:1,owner_id:null,response_owner_id:null,state:'open',desired_start:'',open_questions:'',response_hours:null,close_reason:'',missing:['Arbeitsort'],questions:['Was bedeutet „familiär“ bei dieser Stelle konkret? Bitte ein belegbares Beispiel ergänzen.']};
  const recruiting=render('RecruitingWorkspace','RecruitingWorkspace',{campaign,campaigns:[campaign],onCampaign:noop,onNew:noop,onStudio:noop,onRefresh:noop,canWrite:true,onDirty:noop}, {'RecruitingWorkspace.tsx':{data:{need,team:[],applications:[],publications:[]},need}});
  assert.ok(recruiting.includes(english?'From staffing need to interview':'Vom Personalbedarf zum Gespräch'));
  assert.ok(recruiting.includes(english?'What does':'Was bedeutet'));
}
console.log('Language checks passed: browser preferences, complete DE/EN catalog and all public, auth, onboarding, admin, workspace, billing, recruiting, tracking, job portal, consent, distribution and social screens; customer copy unchanged.');
