const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const source = fs.readFileSync(path.join(__dirname, '../design_handoff_plm_dashboard/executive-app.js'), 'utf8');
const start = source.indexOf('// Explicit incoming domain links win;');
const end = source.indexOf('\nconsumeDashboardView();', start) + '\nconsumeDashboardView();'.length;
assert(start >= 0 && end > start, 'clean URL initialization must exist');
const code = source.slice(start, end);
function setup(hash, lastView) {
  let listener;
  let renders = 0;
  const context = { location: { hash, pathname: '/', search: '?fixture=1' }, viewPreferences: { lastView },
    history: { state: null, replaceState(_state, _title, url) { context.location.hash = ''; context.cleaned = url; } },
    document: { addEventListener(type, callback) { assert.equal(type, 'click'); listener = callback; } },
    render() { renders++; } };
  vm.runInNewContext(code, context);
  return { context, click(view) { let prevented = false; listener({ target: { closest() { return { dataset: { view } }; } }, preventDefault() { prevented = true; } }); return { prevented, renders }; } };
}
for (const [hash, saved, expected] of [['#dev', 'ra', 'dev'], ['#ra', 'dev', 'ra'], ['', 'ra', 'ra'], ['', 'dev', 'dev']]) {
  test(`incoming ${hash || 'root'} with saved ${saved}`, () => {
    const { context } = setup(hash, saved);
    assert.equal(context.viewPreferences.lastView, expected);
    assert.equal(context.location.hash, '');
    if (hash) assert.equal(context.cleaned, '/?fixture=1');
  });
}
test('menu navigation changes saved view without a hash', () => {
  const app = setup('', 'dev');
  assert.equal(app.click('ra').prevented, true);
  assert.equal(app.context.viewPreferences.lastView, 'ra');
  assert.equal(app.context.location.hash, '');
  assert.equal(app.click('dev').renders, 2);
  assert.equal(app.context.viewPreferences.lastView, 'dev');
});