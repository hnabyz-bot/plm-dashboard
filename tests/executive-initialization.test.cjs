const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const source = fs.readFileSync(path.join(__dirname, '../design_handoff_plm_dashboard/executive-app.js'), 'utf8');
function declaration(name) {
  let line = source.split(/\r?\n/).find(value => value.startsWith(`function ${name}(`) || value.startsWith(`async function ${name}(`));
  if (!line) return '';
  if (name === 'init') line = line.slice(0, line.indexOf('}init().catch') + 1);
  return line;
}
function data() {
  const stamp = '2026-01-01T00:00:00Z';
  return {
    health: { generated_at: stamp, today: '2026-01-01', items: [], project_health: [{project:'Keep',open:1},{project:'Hide',open:1}] },
    insights: { generated_at: stamp, today: '2026-01-01', product_lines:[{name:'Synthetic family',projects:['keep','hide']}], project_status:[{identifier:'keep',project:'Keep'},{identifier:'hide',project:'Hide'}], milestones:[] },
    weekly: { generated_at: stamp, today: '2026-01-01', lines:[{name:'Synthetic family',carry:[{id:1,project:'Keep'},{id:2,project:'Hide'}]}] },
    ra: { generated: stamp, open_requests:[], registry:{} },
    'config/tracked-projects': { version:1, excluded:[], updated_at:stamp }
  };
}
function setup(values, included = ['keep']) {
  const nodes = new Map();
  const node = selector => {
    if (!nodes.has(selector)) nodes.set(selector, {value:'all',textContent:'',innerHTML:'',open:false,append(){},querySelectorAll(){return [];}});
    return nodes.get(selector);
  };
  const context = { console, document:{createElement(){return {}; }}, window:{scrollY:0}, $:node,
    localStorage:{getItem(){return JSON.stringify({version:1,included});}},
    fetch:async url=>{
      context.requests.push(url);
      if (url.startsWith('/runtime/dashboard')) return context.runtimeBundle ? {ok:true,status:200,json:async()=>context.runtimeBundle} : {ok:false,status:context.runtimeStatus||404};
      const name=url.replace(/^\/?data\//,'').replace(/\.json$/,'');
      const value=values[name];
      if(value instanceof Error) return {ok:false,status:503};
      return {ok:true,status:200,json:async()=>value};
    },
    empty: value=>value, captureViewDetails(){},captureViewFilters(){},refreshRAFilterOptions(){},rebuildScopeOptions(){},updateLiveStatus(){},
    render(){context.renders.push({ids:JSON.parse(JSON.stringify(context.activeProjectIds())), weekly:JSON.parse(JSON.stringify(context.W))});},renders:[],requests:[]
  };
  vm.createContext(context);
  vm.runInContext("var H=null,I=null,W=null,R=null,scopeConfig=null,localIncluded=null,rawWeekly=null,lines=[],view='dev',historicalSnapshots=null,liveBundleMeta=null,liveBusy=false,liveReaderError=null,liveFingerprint=null,liveLastBundle=null,liveDeferred=false,liveClientAttemptAt=null,liveClientErrorAt=null,layoutPointer=null,liveStarted=false;const SELECTION_KEY='synthetic-selection';const buckets={carry:'carry'};",context);
  const names=['allProjectIds','activeProjectIds','loadLocalSelection','model','applySelectionScope','validLiveDev','validateSourceBundle','liveContentFingerprint','readStaticSourceBundle','applyLatestBundle','checkLatestData','init'];
  vm.runInContext(names.map(declaration).filter(Boolean).join('\n'),context);
  return {context,nodes};
}
for (const invalid of ['mixed generation times','invalid schema','different snapshot days']) {
  test(`initial ${invalid} never renders or commits partial data`,async()=>{
    const values=data();
    if(invalid==='mixed generation times')values.insights.generated_at='2026-01-01T00:10:00Z';
    if(invalid==='invalid schema')values.health.items={};
    if(invalid==='different snapshot days')values.weekly.today='2026-01-02';
    const {context}=setup(values);
    await context.init();
    assert.equal(context.renders.length,0);
    assert.equal(context.H,null);
    assert.equal(context.I,null);
    assert.equal(context.scopeConfig,null);
  });
}
for (const included of [['keep'],[]]) {
  test(`manual recovery after initial failure restores saved selection ${JSON.stringify(included)}`,async()=>{
    const values=data();const health=values.health;values.health=new Error('synthetic first-read failure');
    const {context}=setup(values,included);
    await context.init();
    assert.equal(context.renders.length,0);
    values.health=health;
    await context.checkLatestData(true);
    assert.equal(context.liveReaderError,null);
    assert.deepEqual(JSON.parse(JSON.stringify(context.activeProjectIds())),included);
    assert.ok(context.renders.length>0);
    assert.deepEqual(context.renders.at(-1).ids,included);
    assert.deepEqual(JSON.parse(JSON.stringify(context.W.lines.flatMap(line=>line.carry||[]).map(item=>item.id))),included.length?[1]:[]);
  });
}
test('rejected manual bundle preserves the last validated view and selection',async()=>{
  const values=data();const {context}=setup(values);
  await context.init();
  const health=context.H;const views=context.renders.length;
  values.weekly={...values.weekly,generated_at:'2026-01-01T00:10:00Z'};
  await context.checkLatestData(true);
  assert.equal(context.H,health);
  assert.equal(context.renders.length,views);
  assert.deepEqual(JSON.parse(JSON.stringify(context.activeProjectIds())),['keep']);
  assert.ok(context.liveReaderError);
});
test('initial runtime bundle is validated before any static fallback or render',async()=>{
  const values=data();const {context}=setup(values);
  context.runtimeBundle={version:1,dev:{health:values.health,insights:{...values.insights,generated_at:'2026-01-01T00:10:00Z'},weekly:values.weekly},ra:values.ra,config:values['config/tracked-projects'],meta:{}};
  await context.init();
  assert.equal(context.renders.length,0);
  assert.equal(context.H,null);
  assert.deepEqual(Array.from(context.requests),['/runtime/dashboard']);
  assert.ok(context.liveReaderError);
});
test('initial runtime failure does not bypass it with static snapshots',async()=>{
  const {context}=setup(data());context.runtimeStatus=503;
  await context.init();
  assert.equal(context.renders.length,0);
  assert.equal(context.H,null);
  assert.deepEqual(Array.from(context.requests),['/runtime/dashboard']);
  assert.ok(context.liveReaderError);
});
test('initial domain population keeps RA filter options unique',async()=>{
  const values=data();values.ra.registry={columns:['synthetic-market'],families:['synthetic-family']};
  const {context,nodes}=setup(values);
  for(const id of ['market','family']){
    const select={value:'all',options:[],append(option){this.options.push(option.value);},set innerHTML(value){this.options=['all'];},get innerHTML(){return '';}};
    nodes.set('#'+id,select);
  }
  vm.runInContext(declaration('refreshRAFilterOptions'),context);
  await context.init();
  context.document.querySelectorAll=()=>[];
  context.clearInterval=()=>{};context.domainPopulate=1;
  context.restoreInitialViewPreferences=()=>{};context.startLiveUpdates=()=>{};
  const body=source.split(/\r?\n/).find(line=>line.startsWith('const domainPopulate=')).split('setInterval(()=>{')[1].split('},50);')[0];
  vm.runInContext(`(()=>{${body}})()`,context);
  assert.deepEqual(nodes.get('#market').options,['all','synthetic-market']);
  assert.deepEqual(nodes.get('#family').options,['all','synthetic-family']);
});