import assert from 'node:assert/strict';
import { test } from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { createRequire } from 'node:module';
import jsQR from 'jsqr';
const require = createRequire(import.meta.url);
const ts = require('typescript');
const React = require('react');

// Execute the actual components and their handlers with a tiny deterministic hook host.
// API requests, timers and navigation are isolated doubles. This is not a browser E2E test.
function screen(moduleName, { states = {}, props = {}, api, search = '', language = 'de', component = moduleName, qr } = {}) {
  const slots = [], effects = [], timers = new Map(), listeners = new Map(), navigations = [], calls = [];
  let cursor = 0, tree, uuid = 0;
  const hooks = {
    ...React,
    useRef(initial) { const i = cursor++; slots[i] ??= { current: initial }; return slots[i]; },
    useMemo(factory, deps) {
      const i = cursor++, old = slots[i];
      if (!old || deps.some((value, j) => !Object.is(value, old.deps[j]))) slots[i] = { value: factory(), deps };
      return slots[i].value;
    },
    useEffect(callback, deps) {
      const i = cursor++, old = slots[i];
      if (!old || !deps || deps.some((value, j) => !Object.is(value, old.deps[j]))) {
        slots[i] = { deps, cleanup: old?.cleanup };
        effects.push(() => { old?.cleanup?.(); slots[i].cleanup = callback(); });
      }
    },
  };
  function state(name, initial) {
    const i = cursor++;
    if (!slots[i]) slots[i] = { value: Object.hasOwn(states, name) ? states[name] : typeof initial === 'function' ? initial() : initial };
    return [slots[i].value, value => { slots[i].value = typeof value === 'function' ? value(slots[i].value) : value; }];
  }
  async function request(url, options = {}) {
    const call = { url, method: options.method || 'GET', body: options.body, headers: options.headers };
    calls.push(call);
    const data = await api?.(call);
    return data;
  }
  const cache = new Map();
  const browser = { location: { search, hash:'', hostname: 'localhost', assign: url => navigations.push(url) }, setInterval: callback => { const id = timers.size + 1; timers.set(id, callback); return id; }, addEventListener: (name, cb) => listeners.set(name, cb), removeEventListener: (name, cb) => { if (listeners.get(name) === cb) listeners.delete(name); } };
  function load(filename) {
    filename = path.resolve(filename);
    if (cache.has(filename)) return cache.get(filename).exports;
    const module = { exports: {} }; cache.set(filename, module);
    let source = fs.readFileSync(filename, 'utf8');
    const file = ts.createSourceFile(filename, source, ts.ScriptTarget.Latest, true), edits = [];
    function visit(node) {
      if (ts.isVariableDeclaration(node) && ts.isArrayBindingPattern(node.name) && node.initializer && ts.isCallExpression(node.initializer) && node.initializer.expression.getText(file) === 'useState') {
        edits.push([node.initializer.getStart(file), node.initializer.end, `__state(${JSON.stringify(node.name.elements[0].name.getText(file))},${node.initializer.arguments[0]?.getText(file) || 'undefined'})`]);
      }
      ts.forEachChild(node, visit);
    }
    visit(file);
    for (const [start, end, replacement] of edits.sort((a, b) => b[0] - a[0])) source = source.slice(0, start) + replacement + source.slice(end);
    const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText;
    function localRequire(spec) {
      if (spec === 'react') return hooks;
      if (spec.endsWith('.css')) return {};
      if (spec === './authenticatorQr' && qr) return { authenticatorQr: qr };
      if (spec === './api') return { billingRequest: (url, body) => request(url, { method: body === undefined ? 'GET' : 'POST', body }), secureFetch: request };
      if (!spec.startsWith('.')) return require(spec);
      const base = path.resolve(path.dirname(filename), spec);
      if (base.endsWith('.json')) return JSON.parse(fs.readFileSync(base, 'utf8'));
      return load(['.ts', '.tsx'].map(ext => base + ext).find(f => fs.existsSync(f)) || base);
    }
    vm.runInNewContext(code, { module, exports: module.exports, require: localRequire, __state: state, console, Intl, URL, URLSearchParams, crypto: { randomUUID: () => `onboarding-test-${++uuid}` }, window: browser, navigator: { languages: [language] }, document: { visibilityState: 'visible', activeElement: null, body: { style: {} }, addEventListener:(name,cb)=>listeners.set('document:'+name,cb), removeEventListener:(name,cb)=>{if(listeners.get('document:'+name)===cb)listeners.delete('document:'+name);} }, sessionStorage: { getItem: () => null, setItem: () => {} }, clearInterval: id => timers.delete(id) }, { filename });
    return module.exports;
  }
  const Component = load(`src/${moduleName}.tsx`)[component];
  function render() { cursor = 0; tree = Component(props); return tree; }
  function nodes() {
    const all = [];
    function walk(value) { if (Array.isArray(value)) value.forEach(walk); else if (React.isValidElement(value)) { all.push(value); walk(value.props.children); } }
    walk(tree); return all;
  }
  const find = predicate => { const matches = nodes().filter(predicate); assert.equal(matches.length, 1, 'Expected one matching control'); return matches[0]; };
  async function settle() { for (let i = 0; i < 10; i++) { render(); while (effects.length) effects.shift()(); await new Promise(resolve => setImmediate(resolve)); } render(); }
  render();
  return { render, settle, find, nodes, calls, timers, listeners, navigations, unmount: () => slots.forEach(slot => slot?.cleanup?.()) };
}
const user = { email: 'onboarding@example.test', email_verified: true, mfa_enabled: true, security_pending: false };
const company = { id: 7, name: 'Fiktiver Testbetrieb', industry: 'Handwerk', location: 'Hamburg', brand_description: 'Ein fiktiver Betrieb.', benefits: 'Nur verifizierte Vorteile', tone: 'Original custom tone' };
const setup = (extra = {}) => ({ required: true, done: false, paid: true, profile_done: false, company, campaign: null, ...extra });
const response = (data, ok = true) => ({ ok, json: async () => data });
const event = { preventDefault() {} };
const plain = value => Array.isArray(value) ? value.map(plain).join('') : React.isValidElement(value) ? plain(value.props.children) : value == null || typeof value === 'boolean' ? '' : String(value);
const button = (s, text) => s.find(n => n.type === 'button' && plain(n).includes(text));
const digit = (s, index = 0) => s.find(n => n.type === 'input' && n.props['aria-label'] === `Ziffer ${index + 1} von 6`);
const child = (s, name) => s.find(n => typeof n.type === 'function' && n.type.name === name);
const baseApi = (state, other = () => { throw new Error('Unexpected request'); }) => call => call.url === '/auth/me' ? user : call.url === '/onboarding' ? state : other(call);

const workspaceMfaUser = { ...user, id: 7, name: 'Fiktiver Test', role: 'firmen_admin', base_role: 'firmen_admin', organization_id: 7, security_required: true, mfa_enabled: false, security_pending: true };
for (const search of ['', '?billing=start', '?billing=success', '?social=connected']) {
  await test(`Workspace entry ${search || '/app'} shares QR setup and blocks premature workspace requests`, async () => {
    const s = screen('App', { search, api: call => {
      assert.equal(call.url, '/auth/session'); return { authenticated: true, user: workspaceMfaUser };
    } });
    await s.settle();
    assert.equal(child(s, 'SecurityPanel').props.user.mfa_enabled, false);
    assert.ok(!s.nodes().some(n => n.type?.name === 'Billing'));
    assert.equal(s.calls.length, 1); assert.equal(s.timers.size, 0); s.unmount();
  });
}
await test('Billing sign-in leads to the shared QR gate and retains a visible retry error', async () => {
  let statusFails = false;
  const s = screen('App', { search: '?billing=start', api: call => {
    if (call.url === '/auth/session') return { authenticated: false, user: null };
    if (call.url === '/auth/login') return response({});
    assert.equal(call.url, '/auth/me');
    return statusFails ? response({ detail: 'Isolated status failure' }, false) : response(workspaceMfaUser);
  } });
  await s.settle(); s.find(n => n.type === 'form').props.onSubmit(event); await s.settle();
  child(s, 'SecurityPanel'); statusFails = true;
  child(s, 'SecurityPanel').props.onReady(); await s.settle();
  assert.ok(s.nodes().some(n => n.props.role === 'alert' && plain(n).includes('Isolated status failure')));
  statusFails = false; child(s, 'SecurityPanel').props.onReady(); await s.settle();
  assert.ok(!s.nodes().some(n => n.props.role === 'alert')); s.unmount();
});

await test('Security must finish before billing or company setup loads', async () => {
  const s = screen('Onboarding', { api: call => { assert.equal(call.url, '/auth/me'); return { ...user, security_pending: true }; } });
  await s.settle(); child(s, 'SecurityPanel');
  assert.ok(!s.nodes().some(n => n.type === 'form' || n.type?.name === 'Billing'));
  assert.equal(s.calls.length, 1); s.unmount();
});
await test('Stripe success URL cannot unlock profile; confirmed server state does', async () => {
  let state = setup({ paid: false });
  const s = screen('Onboarding', { search: '?billing=success', api: call => baseApi(state)(call) });
  await s.settle(); assert.equal(child(s, 'Billing').props.onboarding, true);
  assert.ok(!s.nodes().some(n => n.type === 'form'));
  state = setup(); s.timers.values().next().value(); await s.settle();
  assert.equal(s.find(n => n.type === 'input' && n.props.autoComplete === 'address-level2').props.value, 'Hamburg');
  assert.equal(s.timers.size, 0); s.unmount();
});
await test('Profile uses three required answers and keeps collapsed optional values on save', async () => {
  let state = setup(), saved;
  const s = screen('Onboarding', { api: baseApi(state, call => { assert.equal(call.url, '/onboarding/profile'); saved = call.body; return {}; }) });
  await s.settle();
  assert.equal(s.nodes().filter(n => ['input', 'textarea'].includes(n.type) && n.props.required).length, 3);
  assert.equal(s.find(n => n.type === 'details').props.open, undefined);
  s.find(n => n.type === 'form').props.onSubmit(event); await s.settle();
  assert.equal(saved.benefits, company.benefits); assert.equal(saved.tone, company.tone);
  assert.ok(!s.calls.some(c => c.url.includes('generate'))); s.unmount();
});
await test('Failed profile save keeps typed input; rapid resubmit runs one request', async () => {
  let reject, count = 0;
  const s = screen('Onboarding', { api: baseApi(setup(), () => { count++; return new Promise((_, fail) => { reject = fail; }); }) });
  await s.settle(); s.find(n => n.type === 'input' && n.props.autoComplete === 'address-level2').props.onChange({ target: { value: 'Kiel' } }); s.render();
  const submit = s.find(n => n.type === 'form').props.onSubmit;
  submit(event); submit(event); await s.settle(); assert.equal(count, 1);
  reject(new Error('Test failure')); await s.settle();
  assert.equal(s.find(n => n.type === 'input' && n.props.autoComplete === 'address-level2').props.value, 'Kiel');
  assert.ok(s.nodes().some(n => n.props.role === 'alert' && plain(n).includes('Test failure'))); s.unmount();
});
await test('Profile whitespace is not sent as a completed answer', async () => {
  const s = screen('Onboarding', { api: baseApi(setup()) }); await s.settle();
  s.find(n => n.type === 'input' && n.props.autoComplete === 'address-level2').props.onChange({ target: { value: '   ' } }); s.render();
  s.find(n => n.type === 'form').props.onSubmit(event); await s.settle();
  assert.equal(s.calls.filter(c => c.method === 'POST').length, 0); assert.ok(s.nodes().some(n => n.props.role === 'alert')); s.unmount();
});
await test('Company defaults populate the brief; save later persists deferral and goes to dashboard without generating or completing', async () => {
  let state = setup({ profile_done: true });
  const s = screen('Onboarding', { api: call => baseApi(state, c => {
    if (c.url === '/tokens/wallet') return { managed: true, active: true, available: 250 };
    if (c.url === '/onboarding/defer') { assert.equal(c.body.campaign_id,42); state={...state,deferred:true};return {}; }
    assert.equal(c.url, '/campaigns'); state = { ...state, campaign: { id: 42, status: 'Draft', generated: '{}' } }; return { id: 42 };
  })(call) });
  await s.settle(); button(s, 'Kampagne Schritt für Schritt').props.onClick(); await s.settle();
  const wizard = child(s, 'CampaignWizard'); assert.equal(wizard.props.briefing.location, company.location); assert.equal(wizard.props.briefing.tone, company.tone); assert.equal(wizard.props.briefing.benefits, company.benefits);
  await wizard.props.onSave(false); await s.settle();
  assert.equal(s.calls.filter(c => c.url === '/campaigns').length, 1);
  assert.ok(!s.calls.some(c => c.url.includes('/generate') || c.url.includes('/complete')));
  assert.deepEqual(s.navigations,['/app']);s.unmount();
});
await test('Failed draft save or deferral never navigates; retry reuses the persisted draft',async()=>{
  let state=setup({profile_done:true}), failSave=true, failDefer=true;
  const s=screen('Onboarding',{api:c=>baseApi(state,c=>{
    if(c.url==='/tokens/wallet')return{managed:true,active:true,available:250};
    if(c.url==='/campaigns'){if(failSave)throw Error('Save unavailable');state={...state,campaign:{id:42,status:'Draft',generated:'{}'}};return{id:42};}
    if(c.url==='/campaigns/42')return response({});
    if(c.url==='/onboarding/defer'){if(failDefer)throw Error('Deferral unavailable');return{};}
    throw Error('Unexpected request');
  })(c)});
  await s.settle();await button(s,'Kampagne Schritt für Schritt').props.onClick();await s.settle();
  await child(s,'CampaignWizard').props.onSave(false);await s.settle();assert.equal(s.navigations.length,0);assert.equal(s.calls.filter(c=>c.url==='/onboarding/defer').length,0);
  failSave=false;await child(s,'CampaignWizard').props.onSave(false);await s.settle();assert.equal(s.navigations.length,0);assert.equal(child(s,'CampaignWizard').props.saved,true);
  failDefer=false;await child(s,'CampaignWizard').props.onSave(false);await s.settle();assert.deepEqual(s.navigations,['/app']);assert.equal(s.calls.filter(c=>c.url==='/campaigns').length,2);s.unmount();
});
await test('Local test package is explicitly requested, keeps its label and never auto-completes onboarding',async()=>{
  let state=setup({profile_done:true});
  const s=screen('Onboarding',{api:c=>baseApi(state,c=>{
    if(c.url==='/tokens/wallet')return{managed:true,active:true,available:250,generation_mode:'local_test'};
    if(c.url==='/campaigns')return{id:42};
    if(c.url==='/campaigns/42/generate?test_package=true'){state={...state,campaign:{id:42,status:'Draft',generated:'{"jobAd":"Fixture local template"}',generation_mode:'local_test'}};return response({});}
    throw Error('Unexpected request');
  })(c)});await s.settle();await button(s,'Kampagne Schritt für Schritt').props.onClick();await s.settle();
  assert.equal(child(s,'CampaignWizard').props.wallet.generation_mode,'local_test');
  await child(s,'CampaignWizard').props.onSave(true,true);await s.settle();
  assert.ok(s.nodes().some(n=>n.props.role==='status'&&plain(n).includes('keine KI-Generierung')));
  assert.equal(s.navigations.length,0);assert.ok(!s.calls.some(c=>c.url.includes('/complete')||c.url.includes('/defer')));s.unmount();
});
await test('Wizard explains local test cost in DE/EN and sends the test flag only after both confirmations',async()=>{
  for(const language of ['de','en']){
    const submissions=[];
    const s=screen('CampaignWizard',{language,states:{step:3},props:{mode:'new',briefing:{role:'Elektriker',location:'Berlin',tasks:'',requirements:'',benefits:'',salary:'',tone:'',channels:['Instagram','Meta']},setBriefing(){},orgs:[company],orgId:7,setOrgId(){},isAgency:false,onClose(){},onSave:(...args)=>submissions.push(args),busy:false,error:'',saved:true,wallet:{managed:true,active:true,available:250,generation_mode:'local_test'}}});
    const label=language==='de'?'Testpaket für 50':'Create test package for 50';assert.equal(button(s,label).props.disabled,true);
    assert.ok(plain(s.render()).includes(language==='de'?'keine Daten an OpenAI':'No data is sent to OpenAI'));
    s.find(n=>n.type==='form').props.onSubmit(event);assert.equal(submissions.length,0);
    s.nodes().filter(n=>n.type==='input'&&n.props.type==='checkbox').forEach(n=>n.props.onChange({target:{checked:true}}));s.render();
    assert.equal(button(s,label).props.disabled,false);s.find(n=>n.type==='form').props.onSubmit(event);assert.deepEqual(submissions,[[true,true]]);s.unmount();
  }
});
await test('Generation retry reuses saved campaign and key; it never auto-approves', async () => {
  let state = setup({ profile_done: true }), attempts = 0;
  const s = screen('Onboarding', { api: call => baseApi(state, c => {
    if (c.url === '/tokens/wallet') return { managed: true, active: true, available: 250 };
    if (c.url === '/campaigns') { state = { ...state, campaign: { id: 42, status: 'Draft', generated: '{}' } }; return { id: 42 }; }
    if (c.url === '/campaigns/42') return response({});
    if (c.url === '/campaigns/42/generate') { if (++attempts === 1) return response({ detail: 'Test provider failure' }, false); state = { ...state, campaign: { id: 42, status: 'Draft', generated: JSON.stringify({ jobAd: 'A factual draft' }) } }; return response({}); }
    throw new Error('Unexpected request');
  })(call) });
  await s.settle(); button(s, 'Kampagne Schritt für Schritt').props.onClick(); await s.settle();
  await child(s, 'CampaignWizard').props.onSave(true); await s.settle(); assert.equal(child(s, 'CampaignWizard').props.saved, true);
  await child(s, 'CampaignWizard').props.onSave(true); await s.settle();
  assert.equal(s.calls.filter(c => c.url === '/campaigns').length, 1);
  const generations = s.calls.filter(c => c.url.endsWith('/generate'));
  assert.equal(generations.length, 2); assert.equal(generations[0].headers['Idempotency-Key'], generations[1].headers['Idempotency-Key']);
  assert.ok(!s.calls.some(c => c.url === '/onboarding/complete' || c.body?.includes?.('Review'))); child(s, 'JobDescription'); s.unmount();
});
await test('Saved briefing resumes the same campaign with only supported channels', async () => {
  const brief = { role: 'Elektriker', location: 'Kiel', channels: ['Instagram', 'LinkedIn', 'Meta'], benefits: 'Original saved benefit', tone: 'Original saved tone' };
  const s = screen('Onboarding', { api: baseApi(setup({ profile_done: true, campaign: { id: 42, generated: '{}', status: 'Draft' } }), c => c.url === '/tokens/wallet' ? { managed: true, active: true, available: 250 } : brief && { briefing: brief }) });
  await s.settle(); button(s, 'Gespeichertes Briefing').props.onClick(); await s.settle();
  const wizard = child(s, 'CampaignWizard'); assert.equal(wizard.props.briefing.location, 'Kiel'); assert.equal(wizard.props.briefing.benefits, brief.benefits); assert.equal(wizard.props.briefing.channels.join(','), 'Instagram,Meta');
  assert.ok(!s.calls.some(c => c.method === 'POST')); s.unmount();
});
await test('Completion requires successful review; failed completion remains retryable', async () => {
  let reviewOK = false, completeOK = false, state = setup({ profile_done: true, campaign: { id: 42, status: 'Draft', generated: '{"jobAd":"Reviewed factual copy"}' } });
  const s = screen('Onboarding', { api: call => baseApi(state, c => {
    if (c.url === '/campaigns/42') return response({}, reviewOK);
    if (c.url === '/onboarding/complete') { if (!completeOK) throw new Error('Completion unavailable'); state = { ...state, done: true }; return {}; }
    throw new Error('Unexpected request');
  })(call) });
  await s.settle(); await button(s, 'Entwurf gelesen').props.onClick(); await s.settle(); assert.ok(!s.calls.some(c => c.url === '/onboarding/complete'));
  reviewOK = true; await button(s, 'Entwurf gelesen').props.onClick(); await s.settle(); assert.ok(s.nodes().some(n => n.props.role === 'alert'));
  completeOK = true; await button(s, 'Entwurf gelesen').props.onClick(); await s.settle();
  assert.ok(s.nodes().some(n => n.type === 'a' && n.props.href === '/app' && plain(n).includes('Zum Workspace')));
  assert.ok(!s.calls.some(c => c.url.endsWith('/generate'))); s.unmount();
});
await test('Initial server failure can retry; non-onboarding accounts go to workspace', async () => {
  let available = false;
  const s = screen('Onboarding', { api: call => { if (!available) throw new Error('Offline fixture'); return call.url === '/auth/me' ? user : setup({ required: false }); } });
  await s.settle(); button(s, 'Erneut versuchen');
  available = true; // A restored account with no onboarding requirement must redirect.
  await button(s, 'Erneut versuchen').props.onClick(); await s.settle(); assert.equal(s.navigations[0], '/app'); s.unmount();
});
const catalog = JSON.parse(fs.readFileSync('../pricing_catalog.json', 'utf8'));
const config = { ready: true, mode: 'test', catalog, countries: { DE: 'Deutschland' } };
const status = { managed: true, status: 'pending', plan: '', included: 0, purchased: 0, active: false, country: 'DE', hold: '', ledger: [] };
await test('Pending plan booking shows clear DE/EN progress, resumes the same checkout and never books again', async () => {
  for(const language of ['de','en']){
    const pending={...status,checkout:{sku:'team',status:'open',url:'https://checkout.stripe.com/test/fixture',expires_at:9999999999}};
    const s=screen('Billing',{language,props:{onboarding:true},api:c=>c.url==='/billing/config'?config:pending});await s.settle();
    assert.equal(s.nodes().filter(n=>n.type==='article').length,0);
    const booking=plain(s.find(n=>n.props.className==='pay-return'));
    assert.ok(booking.includes('Team'));assert.ok(booking.includes(language==='de'?'buche bitte nicht erneut':'please do not book again'));
    await button(s,language==='de'?'Buchung bei Stripe öffnen':'Open booking at Stripe').props.onClick();
    assert.deepEqual(s.navigations,['https://checkout.stripe.com/test/fixture']);assert.ok(!s.calls.some(c=>c.method==='POST'));
    s.unmount();assert.equal(s.timers.size,0);assert.equal(s.listeners.size,0);
  }
});
await test('Stripe confirmation waiting survives a minute, refresh failures and focus; only confirmed status advances',async()=>{
  let state={...status,checkout:{sku:'team',status:'open',url:'https://checkout.stripe.com/test/fixture',expires_at:9999999999}}, fail=false, confirmed=0;
  const s=screen('Billing',{props:{onboarding:true,onConfirmed(){confirmed++;}},search:'?billing=success',api:c=>{if(c.url==='/billing/config')return config;if(fail)throw Error('Delayed status fixture');return state;}});
  await s.settle();assert.equal(confirmed,0);assert.ok(!s.nodes().some(n=>n.type==='button'&&plain(n).includes('Buchung bei Stripe öffnen')));
  for(let i=0;i<13;i++){s.timers.values().next().value();await s.settle();}assert.equal(s.timers.size,1);assert.equal(confirmed,0);
  fail=true;s.listeners.get('focus')();await s.settle();assert.ok(s.nodes().some(n=>n.props.role==='alert'));
  fail=false;state={...status,active:true,status:'active',plan:'team',included:1500,checkout:null};
  await button(s,'Zahlung prüfen & weiter').props.onClick();await s.settle();
  assert.equal(confirmed,1);assert.equal(s.timers.size,0);assert.ok(!s.nodes().some(n=>n.props.role==='alert'||n.props.className==='pay-return'));
  button(s,'Weiter zum Firmenprofil').props.onClick();assert.equal(confirmed,2);
  assert.ok(!s.calls.some(c=>c.method==='POST'));s.unmount();
});
await test('A failed checkout creation can retry the same plan without getting stuck in confirmation waiting',async()=>{
  const creating={...status,checkout:{sku:'team',status:'creating',url:null,expires_at:9999999999}};
  const s=screen('Billing',{props:{onboarding:true},api:c=>c.url==='/billing/config'?config:creating});await s.settle();
  assert.equal(s.nodes().filter(n=>n.type==='article').length,3);
  assert.ok(!s.nodes().some(n=>n.type==='button'&&plain(n).includes('Buchung bei Stripe öffnen')));
  assert.ok(s.nodes().filter(n=>n.type==='button'&&plain(n).includes('Mit Kreditkarte')).every(n=>n.props.disabled));
  s.unmount();
});
await test('Legacy workspace checkout return preserves success/cancellation through onboarding redirect',async()=>{
  for(const result of ['success','cancelled']){
    const s=screen('App',{search:'?billing='+result,api:c=>{if(c.url==='/auth/session')return{authenticated:true,user:{...workspaceMfaUser,mfa_enabled:true,security_pending:false}};assert.equal(c.url,'/onboarding');return{done:false};}});
    await s.settle();assert.deepEqual(s.navigations,['/onboarding?billing='+result]);s.unmount();
  }
});
await test('Persisted deferral allows dashboard loading on a fresh visit without bypassing security',async()=>{
  const s=screen('App',{api:c=>{
    if(c.url==='/auth/session')return{authenticated:true,user:{...workspaceMfaUser,mfa_enabled:true,security_pending:false}};
    if(c.url==='/onboarding')return{done:false,deferred:true};
    if(c.url==='/tokens/wallet')return response({managed:true,active:true,available:250,included:250,purchased:0,ledger:[],generation_mode:'local_test'});
    if(c.url==='/analytics')return response({campaigns:0,drafts:0,review:0,live:0});
    if(['/organizations','/campaigns','/activity'].includes(c.url))return response([]);
    throw Error('Unexpected request '+c.url);
  }});await s.settle();assert.equal(s.navigations.length,0);assert.ok(s.calls.some(c=>c.url==='/campaigns'));s.unmount();
});
await test('Social preview separates explicit A/B copy without altering custom or ambiguous text',()=>{
  const variants=content=>screen('SocialPreview',{component:'previewVariants',props:content}).render();
  const sample='Variante A · Direkt\nFirst caption\n\nVariante B · Persönlich\nSecond caption';
  assert.equal(variants(sample).length,2);assert.equal(variants(sample)[1].text,'Second caption');
  for(const text of ['Unstructured custom copy','Preamble\n'+sample,'Variant A\nOnly one variant'])assert.equal(variants(text)[0].text,text);
});
await test('Meta preview maps multiline German and English fields and preserves unknown copy',()=>{
  const parse=text=>screen('SocialPreview',{component:'metaPreviewCopy',props:text}).render();
  for(const text of ['Primary Text: Body\nSecond line\nHeadline: Title\nDescription: Detail','Haupttext: Body\nSecond line\nÜberschrift: Title\nBeschreibung: Detail']){
    const copy=parse(text);assert.equal(copy.body,'Body\nSecond line');assert.equal(copy.headline,'Title');assert.equal(copy.description,'Detail');
  }
  for(const text of ['Custom copy\nHeadline: keep this too','Headline: Only a heading','Primary Text: One\nPrimary Text: Two'])assert.equal(parse(text).body,text);
});
await test('Platform previews select variants and story locally, with no invented engagement or outgoing actions',()=>{
  for(const language of ['de','en'])for(const channel of ['social','meta']){
    const formats=[],s=screen('SocialPreview',{language,props:{channel,content:'Variant A\nFirst caption\nVariant B\nSecond caption',company:company.name,role:'Fixture role',location:'Hamburg',campaignId:8,format:'feed',onFormat:f=>formats.push(f),crop:null}});
    assert.ok(plain(s.render()).includes('First caption'));button(s,language==='de'?'Variante B':'Variant B').props.onClick();s.render();assert.ok(plain(s.render()).includes('Second caption'));assert.ok(!plain(s.render()).includes('First caption'));
    button(s,'Story').props.onClick();assert.equal(formats[0],'story');assert.equal(s.calls.length,0);assert.equal(s.nodes().filter(n=>n.type==='a').length,0);
    assert.ok(!/\d+ (likes|Gefällt mir|Kommentare)/.test(plain(s.render())));
  }
});
await test('Short multiline captions can expand; short ordinary captions are never clipped',()=>{
  const props={channel:'social',company:company.name,role:'Fixture role',location:'Hamburg',campaignId:8,format:'feed',onFormat(){},crop:null};
  const short=screen('SocialPreview',{props:{...props,content:'Short caption'}});assert.equal(short.find(n=>n.props.className?.startsWith('sp-copy ')).props.className,'sp-copy ');
  const lines=screen('SocialPreview',{props:{...props,content:'One\nTwo\nThree\nFour\nFive'}});assert.ok(lines.find(n=>n.props.className?.startsWith('sp-copy ')).props.className.includes('sp-copy-short'));button(lines,'Mehr anzeigen').props.onClick();lines.render();assert.equal(lines.find(n=>n.props.className?.startsWith('sp-copy ')).props.className,'sp-copy ');assert.ok(plain(lines.render()).includes('Five'));
});
await test('Content Studio preview uses unsaved channel copy and the selected draft crop without saving or generating',async()=>{
  const photo={id:3,name:'Fixture image',selected:true,width:1200,height:1600,revision:1,feed:{x:.5,y:.5,zoom:1},story:{x:.5,y:.5,zoom:1}},draft={id:3,revision:1,feed:{x:.2,y:.3,zoom:1.5},story:{x:.4,y:.5,zoom:2}};
  const s=screen('ContentStudio',{states:{view:'preview'},props:{campaign:{id:8,organization_id:7,role:'Fixture role',location:'Hamburg',status:'Draft',briefing:{},generated:{social:'Saved text'},change_request:''},orgName:()=>company.name,activeTab:'social',drafts:{social:'Unsaved caption'},imageDraft:draft,onTab(){},onChange(){},onSave(){throw Error('Unexpected save');},onDiscard(){},onEdit(){},onGenerate(){throw Error('Unexpected generation');},canEdit:true,busy:false,error:'',cost:''},api:call=>{assert.equal(call.url,'/campaigns/8/images');return response({images:[photo]});}});
  await s.settle();const preview=child(s,'SocialPreview');assert.equal(preview.props.content,'Unsaved caption');assert.equal(preview.props.photo.id,3);assert.equal(preview.props.crop.feed.x,.2);preview.props.onFormat('story');s.render();assert.equal(child(s,'SocialPreview').props.format,'story');assert.ok(s.calls.every(c=>c.method==='GET'));s.unmount();
});

const stepCampaign = (id, extra={}) => ({id,organization_id:7,role:`Fixture role ${id}`,status:'Draft',generated:{jobAd:'Fixture copy'},change_request:'',updated_at:id,...extra});
await test('Next steps prioritize current feedback and review; completed campaigns and obsolete feedback do not create tasks',()=>{
  const opened=[], campaigns=[stepCampaign(1),stepCampaign(2,{status:'Live',change_request:'Old feedback'}),stepCampaign(3,{change_request:'Fix factual detail'}),stepCampaign(4,{status:'Review',change_request:'Previously addressed feedback'}),stepCampaign(5,{generated:{jobAd:'   '}})];
  const s=screen('NextSteps',{props:{campaigns,canWrite:true,canApprove:true,orgName:()=>company.name,onOpen:c=>opened.push(c)}});
  const tasks=s.nodes().filter(n=>n.type==='button');assert.deepEqual(tasks.map(n=>n.props['aria-label'].split(' · ')[0]),['Feedback bearbeiten','Freigabe ausstehend','Entwurf prüfen','Briefing fortsetzen']);
  tasks[0].props.onClick();tasks[1].props.onClick();assert.equal(opened[0],campaigns[2]);assert.equal(opened[1],campaigns[3]);
  assert.equal(s.find(n=>n.type==='details').props.open,undefined);assert.equal(plain(s.find(n=>n.type==='summary')),'Ein weiterer Schritt');assert.equal(s.calls.length,0);s.unmount();
});
await test('Next steps respect editing and approval rights; empty and Live-only lists show All done in DE/EN',()=>{
  const campaigns=[stepCampaign(1),stepCampaign(2,{status:'Review'}),stepCampaign(3,{status:'Live'})];
  for(const [canWrite,canApprove,expected] of [[true,false,1],[false,true,1],[false,false,0]]){
    const s=screen('NextSteps',{props:{campaigns,canWrite,canApprove,orgName:()=>company.name,onOpen(){}}});assert.equal(s.nodes().filter(n=>n.type==='button').length,expected);s.unmount();
  }
  for(const language of ['de','en'])for(const campaigns of [[],[stepCampaign(3,{status:'Live'})]]){
    const s=screen('NextSteps',{language,props:{campaigns,canWrite:true,canApprove:true,orgName:()=>company.name,onOpen(){}}});assert.ok(plain(s.render()).includes(language==='de'?'Alles erledigt':'All done'));assert.equal(s.nodes().filter(n=>n.type==='button').length,0);s.unmount();
  }
});
await test('Next-step links open the intended campaign in Content Studio without changing its status or spending tokens',async()=>{
  const campaign={...stepCampaign(8),briefing:{},channels:['Instagram','Meta'],location:'Berlin'}, other={...stepCampaign(9),briefing:{},channels:['Instagram','Meta'],location:'Berlin'};
  const s=screen('App',{api:c=>{
    if(c.url==='/auth/session')return{authenticated:true,user:{...workspaceMfaUser,mfa_enabled:true,security_pending:false}};
    if(c.url==='/onboarding')return{done:false,deferred:true};
    if(c.url==='/tokens/wallet')return response({managed:true,active:true,available:250,included:250,purchased:0,ledger:[]});
    if(c.url==='/analytics')return response({campaigns:2,draft:2,review:0,live:0,metrics:[]});
    if(c.url==='/campaigns')return response([other,campaign]);
    if(c.url==='/organizations')return response([company]);
    if(c.url==='/activity')return response([{id:1,actor:'Fixture colleague',message:'Campaign updated',created_at:1}]);
    throw Error('Unexpected request '+c.url);
  }});await s.settle();const history=s.find(n=>n.type==='details'&&n.props.className==='dashboard-activity');assert.equal(history.props.open,undefined);assert.ok(!plain(s.render()).includes('TEAM FEED'));
  child(s,'NextSteps').props.onOpen(campaign);s.render();assert.equal(child(s,'ContentStudio').props.campaign.id,8);assert.equal(child(s,'ContentStudio').props.campaign.status,'Draft');assert.ok(s.calls.every(c=>c.method==='GET'));s.unmount();
});
await test('Extra steps remain accessible without crowding the initial three-task list',()=>{
  const s=screen('NextSteps',{props:{campaigns:Array.from({length:6},(_,i)=>stepCampaign(i+1)),canWrite:true,canApprove:true,orgName:()=>company.name,onOpen(){}}});
  assert.deepEqual(s.nodes().filter(n=>n.type==='div'&&n.props.className==='next-steps-list').map(n=>n.props.children.length),[3,3]);
  assert.equal(s.nodes().filter(n=>n.type==='button').length,6);assert.equal(plain(s.find(n=>n.type==='summary')),'3 weitere Schritte');s.unmount();
});
await test('Onboarding billing removes management/topups while retaining prices, consent and status refresh', async () => {
  for (const onboarding of [true, false]) {
    const s = screen('Billing', { props: { onboarding }, api: c => c.url === '/billing/config' ? config : status }); await s.settle();
    assert.equal(s.nodes().filter(n => n.type === 'article').length, onboarding ? 3 : 6);
    assert.equal(s.nodes().filter(n => n.type === 'input' && n.props.type === 'checkbox').length, 2);
    button(s, 'Status aktualisieren');
    assert.equal(s.nodes().some(n => n.type === 'button' && plain(n).includes('Rechnungen, Karte')), !onboarding);
    button(s, 'Jährlich').props.onClick(); s.render(); assert.ok(plain(s.nodes().filter(n => n.type === 'article')).includes('190,00'));
    assert.ok(s.nodes().filter(n => n.type === 'button' && plain(n).includes('Mit Kreditkarte')).every(n => n.props.disabled)); s.unmount();
  }
});
await test('Billing load failures can retry without stale error or enabling an unverified purchase', async () => {
  let available = false, resolveStatus;
  const s = screen('Billing', { props: { onboarding: true }, api: c => {
    if (!available) throw new Error('Offline billing fixture');
    if (c.url === '/billing/config') return config;
    return new Promise(resolve => { resolveStatus = resolve; });
  } });
  await s.settle(); button(s, 'Erneut versuchen'); available = true;
  button(s, 'Erneut versuchen').props.onClick(); await s.settle();
  assert.ok(!s.nodes().some(n => n.props.role === 'alert'));
  resolveStatus(status); await s.settle();
  assert.equal(s.nodes().filter(n => n.type === 'article').length, 3);
  assert.ok(s.nodes().filter(n => n.type === 'button' && plain(n).includes('Mit Kreditkarte')).every(n => n.props.disabled)); s.unmount();
  const loading = screen('Billing', { props: { onboarding: true }, states: { config, business: true, pdfConsent: true } });
  assert.ok(loading.nodes().filter(n => n.type === 'button' && plain(n).includes('Mit Kreditkarte')).every(n => n.props.disabled)); loading.unmount();
});
await test('Billing needs both explicit consents and loaded server status; checkout retry keeps request ID', async () => {
  const s = screen('Billing', { props: { onboarding: true }, api: c => {
    if (c.url === '/billing/config') return config;
    if (c.url === '/billing/status') return status;
    assert.equal(c.url, '/billing/checkout'); throw new Error('Test checkout unavailable');
  } });
  await s.settle(); let checks = s.nodes().filter(n => n.type === 'input' && n.props.type === 'checkbox');
  checks[0].props.onChange({ target: { checked: true } }); s.render(); assert.ok(s.nodes().filter(n => n.type === 'button' && plain(n).includes('Mit Kreditkarte')).every(n => n.props.disabled));
  checks = s.nodes().filter(n => n.type === 'input' && n.props.type === 'checkbox'); checks[1].props.onChange({ target: { checked: true } }); s.render();
  const book = () => s.nodes().find(n => n.type === 'button' && plain(n).includes('Mit Kreditkarte'));
  assert.equal(book().props.disabled, false); await book().props.onClick(); await s.settle(); await book().props.onClick(); await s.settle();
  const orders = s.calls.filter(c => c.url === '/billing/checkout'); assert.equal(orders.length, 2); assert.equal(orders[0].body.request_id, orders[1].body.request_id); assert.equal(orders[0].body.business, true); assert.equal(orders[0].body.pdf_consent, true); assert.equal(orders[0].body.sku, 'starter');
  assert.equal(orders[0].body.onboarding,true);
  assert.equal(s.navigations.length, 0); s.unmount();
});


const qrFixtureSecret = 'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP';
const qrFixtureEmail = 'qr+fixture@example.test';
const qrFixtureUri = `otpauth://totp/${encodeURIComponent('MH:' + qrFixtureEmail)}?secret=${qrFixtureSecret}&issuer=MH&algorithm=SHA1&digits=6&period=30`;
const pendingMfaUser = { ...user, email: qrFixtureEmail, mfa_enabled: false, security_pending: true };
await test('Website and login email survive QR decoding and are clearly labeled in DE and EN', async () => {
  for (const language of ['de', 'en']) {
    for (const [website, issuer] of [['http://127.0.0.1:5181', 'MH · 127.0.0.1 (5181)'], ['https://jobs.mh.example', 'MH · jobs.mh.example'], ['https://jobs.mh.example:443', 'MH · jobs.mh.example'], ['http://[::1]:5181', 'MH · ··1 (5181)']]) {
      const uri = `otpauth://totp/${encodeURIComponent(issuer)}:${encodeURIComponent(qrFixtureEmail)}?secret=${qrFixtureSecret}&issuer=${encodeURIComponent(issuer)}&algorithm=SHA1&digits=6&period=30`;
      const s = screen('Auth', { component: 'SecurityPanel', language, props: { user: pendingMfaUser, onReady() {} }, api: () => ({secret:qrFixtureSecret,uri,website}) });
      await button(s, language==='de'?'Authenticator einrichten':'Set up authenticator').props.onClick(); await s.settle();
      const image = s.find(n => n.type === 'img');
      const PNG = require(require.resolve('pngjs', {paths:[require.resolve('qrcode')]})).PNG;
      const png = PNG.sync.read(Buffer.from(image.props.src.split(',')[1], 'base64'));
      const decoded = new URL(jsQR(new Uint8ClampedArray(png.data), png.width, png.height).data);
      assert.equal(decoded.searchParams.get('issuer'), issuer);
      assert.equal(decodeURIComponent(decoded.pathname.slice(1)), `${issuer}:${qrFixtureEmail}`);
      assert.equal(decoded.searchParams.get('secret'), qrFixtureSecret);
      const identity = plain(s.find(n=>n.props.className==='auth-setup-identity'));
      assert.ok(identity.includes(website) && identity.includes(qrFixtureEmail));
      assert.ok(identity.includes(language==='de'?'Benutzerkonto':'User account'));
      s.unmount();
    }
  }
});
await test('Website metadata must match the website in the authenticator QR', async () => {
  const issuer = 'MH · jobs.mh.example';
  const uri = `otpauth://totp/${encodeURIComponent(issuer)}:${encodeURIComponent(qrFixtureEmail)}?secret=${qrFixtureSecret}&issuer=${encodeURIComponent(issuer)}&algorithm=SHA1&digits=6&period=30`;
  for (const website of ['https://other.example', 'https://user:password@jobs.mh.example', 'javascript:alert(1)']) {
    const s = screen('Auth', { component:'SecurityPanel', props:{user:pendingMfaUser,onReady(){}}, api:()=>({secret:qrFixtureSecret,uri,website}) });
    await button(s, 'Authenticator einrichten').props.onClick(); await s.settle();
    assert.ok(!s.nodes().some(n=>n.type==='img'));
    assert.equal(s.find(n=>n.type==='details').props.open,true);
    s.unmount();
  }
});
await test('Authenticator QR decodes to the exact account and seed; setup cannot double-submit', async () => {
  const s = screen('Auth', { component: 'SecurityPanel', props: { user: pendingMfaUser, onReady() {} }, api: c => {
    assert.equal(c.url, '/auth/mfa/setup'); return { secret: qrFixtureSecret, uri: qrFixtureUri };
  } });
  const start = button(s, 'Authenticator einrichten').props.onClick;
  await Promise.all([start(), start()]); await s.settle();
  assert.equal(s.calls.length, 1);
  const image = s.find(n => n.type === 'img'); assert.ok(image.props.src.startsWith('data:image/png;base64,'));
  const PNG = require(require.resolve('pngjs', { paths: [require.resolve('qrcode')] })).PNG;
  const png = PNG.sync.read(Buffer.from(image.props.src.split(',')[1], 'base64'));
  const scanned = jsQR(new Uint8ClampedArray(png.data), png.width, png.height);
  assert.equal(scanned?.data, qrFixtureUri);
  assert.equal(s.find(n => n.type === 'details').props.open, undefined);
  assert.equal(s.find(n => n.type === 'input' && n.props.readOnly).props.value, qrFixtureSecret);
  assert.ok(!s.nodes().some(n => n.type === 'a' && n.props.href?.startsWith('otpauth')));
  s.unmount();
});
await test('QR failure keeps manual setup and never approves MFA automatically', async () => {
  let ready = false;
  const s = screen('Auth', { component: 'SecurityPanel', props: { user: pendingMfaUser, onReady() { ready = true; } }, qr: async () => { throw new Error('Isolated QR failure'); }, api: c => {
    assert.equal(c.url, '/auth/mfa/setup'); return { secret: qrFixtureSecret, uri: qrFixtureUri };
  } });
  await button(s, 'Authenticator einrichten').props.onClick(); await s.settle();
  assert.equal(s.find(n => n.type === 'details').props.open, true);
  assert.equal(s.find(n => n.type === 'input' && n.props.readOnly).props.value, qrFixtureSecret);
  assert.ok(!s.nodes().some(n => n.type === 'img')); assert.equal(ready, false); s.unmount();
});
await test('Wrong authenticator code retains QR; success removes it and shows recovery codes', async () => {
  let accepted = false, ready = false;
  const s = screen('Auth', { component: 'SecurityPanel', props: { user: pendingMfaUser, onReady() { ready = true; } }, api: c => {
    if (c.url === '/auth/mfa/setup') return { secret: qrFixtureSecret, uri: qrFixtureUri };
    assert.equal(c.url, '/auth/mfa/confirm'); if (!accepted) throw new Error('Isolated wrong code'); return { recovery_codes: ['fictional-one-use-code'] };
  } });
  await button(s, 'Authenticator einrichten').props.onClick(); await s.settle();
  digit(s).props.onChange({ target: { value: '123456' } }); s.render();
  s.find(n => n.type === 'form').props.onSubmit(event); await s.settle(); assert.ok(s.nodes().some(n => n.type === 'img')); assert.equal(ready, false);
  accepted = true; s.find(n => n.type === 'form').props.onSubmit(event); await s.settle();
  assert.ok(!s.nodes().some(n => n.type === 'img' || n.type === 'details' || n.props.value === qrFixtureSecret));
  assert.ok(s.nodes().some(n => n.type === 'pre' && plain(n).includes('fictional-one-use-code'))); assert.equal(ready, false);
  button(s, 'Codes gesichert').props.onClick(); assert.equal(ready, true); s.unmount();
});
await test('Existing MFA uses challenge rather than a new QR setup', async () => {
  for (const language of ['de', 'en']) {
    let ready = false;
    const s = screen('Auth', { language, component: 'SecurityPanel', props: { user: { ...user, security_pending: true }, onReady() { ready = true; } }, api: c => { assert.equal(c.url, '/auth/mfa/challenge'); assert.equal(c.body.code, '123456'); return { recovery_codes: [] }; } });
    assert.ok(!s.nodes().some(n => n.type === 'img' || n.type === 'details'));
    assert.equal(plain(s.find(n => n.type === 'h1')), language === 'de' ? 'Anmeldung bestätigen' : 'Confirm your sign-in');
    assert.ok(!s.nodes().some(n => /SECURE YOUR ACCOUNT|Two-factor authentication|Enter the current code from your authenticator app or an unused recovery code\./.test(plain(n))));
    const inputs = s.nodes().filter(n => n.type === 'input'); assert.equal(inputs.length, 6);
    const input = inputs[0]; assert.equal(input.props.inputMode, 'numeric'); assert.equal(input.props.maxLength, 6);
    assert.equal(input.props['aria-label'], language === 'de' ? 'Ziffer 1 von 6' : 'Digit 1 of 6');
    input.props.onChange({ target: { value: '123456' } }); s.render();
    assert.equal(ready, false); s.find(n => n.type === 'form').props.onSubmit(event); await s.settle();
    assert.equal(s.calls.length, 1); assert.equal(ready, true); s.unmount();
  }
});

await test('Recovery alternative clears old input/errors and keeps failed challenges retryable', async () => {
  let fail = true, ready = false;
  const s = screen('Auth', { component: 'SecurityPanel', props: { user: { ...user, security_pending: true }, onReady() { ready = true; } }, api: c => {
    assert.equal(c.url, '/auth/mfa/challenge'); if (fail) throw new Error('Isolated wrong code');
    assert.equal(c.body.code, 'fictional-long-recovery-code-12345'); return { recovery_codes: [] };
  } });
  digit(s).props.onChange({ target: { value: '123456' } }); s.render();
  s.find(n => n.type === 'form').props.onSubmit(event); await s.settle();
  assert.equal(ready, false); assert.ok(s.nodes().some(n => n.props.role === 'alert'));
  button(s, 'Wiederherstellungscode verwenden').props.onClick(); s.render();
  const input = s.find(n => n.type === 'input');
  assert.equal(input.props.value, ''); assert.equal(input.props.inputMode, 'text'); assert.equal(input.props.maxLength, 100); assert.equal(input.props.pattern, undefined);
  assert.ok(!s.nodes().some(n => n.props.role === 'alert')); fail = false;
  input.props.onChange({ target: { value: 'fictional-long-recovery-code-12345' } }); s.render();
  s.find(n => n.type === 'form').props.onSubmit(event); await s.settle(); assert.equal(ready, true);
  button(s, 'Authenticator-App verwenden').props.onClick(); s.render();
  assert.equal(digit(s).props.inputMode, 'numeric'); assert.equal(s.calls.length, 2); s.unmount();
});

await test('Six code boxes advance focus, correct digits and block incomplete codes', async () => {
  const s=screen('Auth',{component:'SecurityPanel',props:{user,onReady(){}},api:()=>{throw new Error('Incomplete codes must not be sent');}});
  let focused=-1;
  for(let index=0;index<6;index++)digit(s,index).ref({focus(){focused=index;},select(){}});
  assert.equal(button(s,'Code bestätigen').props.disabled,true);
  for(let index=0;index<6;index++) {
    digit(s,index).props.onChange({target:{value:String(index+1)}});s.render();
    assert.equal(focused,Math.min(index+1,5));
  }
  assert.equal(button(s,'Code bestätigen').props.disabled,false);
  const key=(index,value)=>{let prevented=false;digit(s,index).props.onKeyDown({key:value,preventDefault(){prevented=true;}});s.render();assert.equal(prevented,true);};
  key(5,'Backspace');assert.equal(digit(s,5).props.value,'');assert.equal(focused,5);
  key(5,'Backspace');assert.equal(digit(s,4).props.value,'');assert.equal(focused,4);
  key(4,'ArrowLeft');assert.equal(focused,3);key(3,'ArrowRight');assert.equal(focused,4);
  key(4,'Home');assert.equal(focused,0);key(0,'End');assert.equal(focused,5);
  digit(s,1).props.onChange({target:{value:'9'}});s.render();
  assert.equal(digit(s,0).props.value,'1');assert.equal(digit(s,1).props.value,'9');assert.equal(digit(s,2).props.value,'3');
  await s.find(n=>n.type==='form').props.onSubmit(event);s.render();
  assert.equal(s.calls.length,0);assert.equal(focused,4);s.unmount();
});

await test('Pasted and autofilled codes fill all six boxes without submitting automatically', async () => {
  let ready=false;
  const s=screen('Auth',{component:'SecurityPanel',props:{user,onReady(){ready=true;}},api:c=>{assert.equal(c.body.code,'012345');return {recovery_codes:[]};}});
  let prevented=false;
  digit(s,3).props.onPaste({preventDefault(){prevented=true;},clipboardData:{getData(){return '987 654';}}});s.render();
  assert.equal(prevented,true);assert.equal(s.nodes().filter(n=>n.props['aria-label']).map(n=>n.props.value).join(''),'987654');
  assert.equal(s.calls.length,0);
  digit(s).props.onChange({target:{value:'letters'}});s.render();assert.equal(digit(s).props.value,'9');
  digit(s).props.onChange({target:{value:'012345'}});s.render();
  assert.equal(digit(s).props.value,'0');assert.equal(digit(s,5).props.value,'5');assert.equal(ready,false);
  await s.find(n=>n.type==='form').props.onSubmit(event);await s.settle();assert.equal(ready,true);s.unmount();
});

await test('Verification, QR setup, MFA sign-in and recovery saving use one shared card and primary action', () => {
  for (const [account, states] of [[{ ...user, email_verified: false }, {}], [{ ...user, mfa_enabled: false }, {}], [user, {}], [user, { codes: ['fictional-recovery'] }]]) {
    const s = screen('Auth', { component: 'SecurityPanel', props: { user: account, onReady() {} }, states });
    s.find(n => n.type === 'section' && n.props.className === 'pay-registration-card auth-card');
    assert.equal(s.nodes().filter(n => n.type === 'h1').length, 1);
    assert.equal(s.nodes().filter(n => n.type === 'button' && n.props.className === 'pay-primary').length, 1); s.unmount();
  }
});

await test('A QR for another account or unsupported TOTP settings is never displayed', async () => {
  for (const uri of [qrFixtureUri.replace('issuer=MH', 'issuer=Other'), qrFixtureUri.replace('digits=6', 'digits=8'), qrFixtureUri.replace('period=30', 'period=60'), qrFixtureUri.replace('algorithm=SHA1', 'algorithm=SHA256'), qrFixtureUri.replace(encodeURIComponent('MH:' + qrFixtureEmail), encodeURIComponent('MH:other@example.test'))]) {
    const s = screen('Auth', { component: 'SecurityPanel', props: { user: pendingMfaUser, onReady() {} }, api: c => { assert.equal(c.url, '/auth/mfa/setup'); return { secret: qrFixtureSecret, uri }; } });
    await button(s, 'Authenticator einrichten').props.onClick(); await s.settle();
    assert.ok(!s.nodes().some(n => n.type === 'img')); assert.equal(s.find(n => n.type === 'details').props.open, true); s.unmount();
  }
});

await test('Reconnecting an existing app needs recovery proof before QR and a real challenge after scanning', async () => {
  let proofAccepted=false,codeAccepted=false,ready=false;
  const s=screen('Auth',{component:'SecurityPanel',props:{user:{...pendingMfaUser,mfa_enabled:true},onReady(){ready=true;}},api:c=>{
    if(c.url==='/auth/mfa/reconnect') {
      assert.equal(c.body.code,'fictional-unused-recovery');
      if(!proofAccepted)throw new Error('Isolated rejected recovery');
      return {secret:qrFixtureSecret,uri:qrFixtureUri};
    }
    assert.equal(c.url,'/auth/mfa/challenge');assert.equal(c.body.code,'123456');
    if(!codeAccepted)throw new Error('Isolated wrong app code');return {recovery_codes:[]};
  }});
  button(s,'Authenticator-App verbinden').props.onClick();s.render();
  assert.equal(s.calls.length,0);assert.ok(!s.nodes().some(n=>n.type==='img'));
  assert.equal(s.find(n=>n.type==='input').props.inputMode,'text');
  s.find(n=>n.type==='input').props.onChange({target:{value:'fictional-unused-recovery'}});s.render();
  s.find(n=>n.type==='form').props.onSubmit(event);await s.settle();
  assert.ok(!s.nodes().some(n=>n.type==='img'));assert.equal(ready,false);
  proofAccepted=true;const submit=s.find(n=>n.type==='form').props.onSubmit;
  await Promise.all([submit(event),submit(event)]);await s.settle();
  assert.equal(s.calls.length,2);assert.ok(s.find(n=>n.type==='img').props.src.startsWith('data:image/png;base64,'));
  const input=digit(s);assert.equal(input.props.inputMode,'numeric');assert.equal(input.props.value,'');
  assert.equal(ready,false);input.props.onChange({target:{value:'123456'}});s.render();
  s.find(n=>n.type==='form').props.onSubmit(event);await s.settle();assert.ok(s.nodes().some(n=>n.type==='img'));assert.equal(ready,false);
  codeAccepted=true;s.find(n=>n.type==='form').props.onSubmit(event);await s.settle();
  assert.equal(ready,true);assert.ok(!s.nodes().some(n=>n.type==='img'||n.props.value===qrFixtureSecret));
  assert.ok(!s.calls.some(c=>c.url==='/auth/mfa/setup'||c.url==='/auth/mfa/confirm'));s.unmount();
});

await test('Canceling app reconnection removes QR and secret without unlocking the account', async()=>{
  let ready=false;
  const s=screen('Auth',{component:'SecurityPanel',props:{user:{...pendingMfaUser,mfa_enabled:true},onReady(){ready=true;}},api:c=>{assert.equal(c.url,'/auth/mfa/reconnect');return {secret:qrFixtureSecret,uri:qrFixtureUri};}});
  button(s,'Authenticator-App verbinden').props.onClick();s.render();
  s.find(n=>n.type==='input').props.onChange({target:{value:'fictional-unused-recovery'}});s.render();
  await s.find(n=>n.type==='form').props.onSubmit(event);await s.settle();
  assert.ok(s.nodes().some(n=>n.type==='img'));button(s,'Zur Code-Eingabe').props.onClick();s.render();
  assert.ok(!s.nodes().some(n=>n.type==='img'||n.props.value===qrFixtureSecret));
  assert.equal(plain(s.find(n=>n.type==='h1')),'Anmeldung bestätigen');assert.equal(ready,false);assert.equal(s.calls.length,1);s.unmount();
});
await test('Lost-factor recovery requests and mailbox confirmation are explicit and never unlock an account', async()=>{
  const s=screen('Auth',{component:'AuthPage',search:'?action=recover',api:c=>{assert.equal(c.url,'/auth/recovery/request');return {message:'Wenn das Konto dafür infrage kommt, wurde eine E-Mail vorbereitet. Prüfe dein Postfach.',local_mail:false};}});
  await s.settle();assert.equal(s.calls.length,0);
  s.find(n=>n.type==='input').props.onChange({target:{value:'fixture@example.test'}});s.render();
  const submit=s.find(n=>n.type==='form').props.onSubmit;await Promise.all([submit(event),submit(event)]);await s.settle();assert.equal(s.calls.length,1);assert.equal(s.navigations.length,0);s.unmount();
  const proof=screen('Auth',{component:'AuthPage',search:'?action=recover-verify&token=fixture-email-proof-token',api:c=>{assert.equal(c.url,'/auth/recovery/verify');return {case_id:'fixture-case-123'};}});
  await proof.settle();assert.equal(proof.calls.length,0);assert.ok(!proof.nodes().some(n=>n.type==='input'));
  await proof.find(n=>n.type==='form').props.onSubmit(event);await proof.settle();
  assert.ok(plain(proof.find(n=>n.props.role==='status')).includes('unabhängig prüfen'));assert.ok(plain(proof.find(n=>n.type==='strong')).includes('fixture-case-123'));assert.equal(proof.navigations.length,0);proof.unmount();
});

await test('Approved recovery requires matching new passwords; cancel and expired links never change credentials', async()=>{
  let fail=true;
  const s=screen('Auth',{component:'AuthPage',search:'?action=recover-reset&token=fixture-approved-reset-token',api:c=>{assert.equal(c.url,'/auth/recovery/reset');if(fail)throw new Error('Wiederherstellungsanfrage ist ungültig oder abgelaufen.');return {ok:true};}});
  await s.settle();assert.equal(s.calls.length,0);
  s.nodes().filter(n=>n.type==='input')[0].props.onChange({target:{value:'fixture-new-secure-password'}});s.render();
  await s.find(n=>n.type==='form').props.onSubmit(event);await s.settle();assert.equal(s.calls.length,0);
  s.nodes().filter(n=>n.type==='input')[1].props.onChange({target:{value:'fixture-new-secure-password'}});s.render();
  await s.find(n=>n.type==='form').props.onSubmit(event);await s.settle();assert.ok(s.nodes().some(n=>n.props.role==='alert'));
  fail=false;await s.find(n=>n.type==='form').props.onSubmit(event);await s.settle();
  assert.ok(!s.nodes().some(n=>n.type==='input'));assert.ok(plain(s.find(n=>n.props.role==='status')).includes('neuen Authenticator'));assert.equal(s.navigations.length,0);s.unmount();
  const cancel=screen('Auth',{component:'AuthPage',search:'?action=recover-verify&token=fixture-email-proof-token',api:c=>{assert.equal(c.url,'/auth/recovery/cancel');return {ok:true};}});
  await button(cancel,'Diese Anfrage abbrechen').props.onClick();await cancel.settle();assert.equal(cancel.calls.length,1);assert.ok(!cancel.nodes().some(n=>n.type==='form'));cancel.unmount();
});

await test('Admin recovery review needs independent proof, matching account email and six fresh digits',async()=>{
  let fail=true;
  const request={id:'fixture-case-123',email:'fixture@example.test',name:'Fictional person',company:'Fictional company',state:'verified',created_at:1};
  const s=screen('AccountRecoveries',{props:{user,onSecurityReady(){}},api:c=>{
    if(c.url==='/admin/account-recoveries')return {requests:[request]};
    assert.equal(c.url,'/admin/account-recoveries/fixture-case-123/review');assert.equal(c.body.code,'123456');assert.equal(c.body.ownership_verified,true);
    if(fail)throw new Error('fixture-wrong-admin-code');return {ok:true};
  }});
  await s.settle();assert.equal(button(s,'Freigeben und').props.disabled,true);
  s.find(n=>n.type==='input'&&n.props.type==='email').props.onChange({target:{value:request.email}});
  s.find(n=>n.type==='input'&&n.props.maxLength===240).props.onChange({target:{value:'fixture-independent-contact-123'}});s.render();
  digit(s).props.onChange({target:{value:'123456'}});s.render();assert.equal(button(s,'Freigeben und').props.disabled,true);
  s.find(n=>n.type==='input'&&n.props.type==='checkbox').props.onChange({target:{checked:true}});s.render();assert.equal(button(s,'Freigeben und').props.disabled,false);
  await s.find(n=>n.type==='form').props.onSubmit(event);await s.settle();assert.equal(digit(s).props.value,'');assert.ok(s.nodes().some(n=>n.props.role==='alert'));
  fail=false;digit(s).props.onChange({target:{value:'123456'}});s.render();const submit=s.find(n=>n.type==='form').props.onSubmit;
  await Promise.all([submit(event),submit(event)]);await s.settle();assert.equal(s.calls.filter(c=>c.url.endsWith('/review')).length,2);assert.ok(s.nodes().some(n=>n.props.role==='status'));s.unmount();
});
console.log('Onboarding/authenticator/recovery checks passed with isolated fixtures; no browser/provider E2E claim.');
