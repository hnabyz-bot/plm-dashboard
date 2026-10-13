// #106: a saved view key that no longer exists (e.g. a removed screen) must not leave the first paint
// without an active menu item — the key is validated before the menu is built.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '../design_handoff_plm_dashboard');

function shellWithSavedView(view) {
  const els = { app: { innerHTML: '' }, content: { innerHTML: '', scrollTop: 0 } };
  const saved = JSON.stringify({ view, homeSeeded: true });
  const context = { console, setTimeout, clearTimeout, localStorage: { getItem: () => saved, setItem() {} },
    document: { documentElement: { setAttribute() {}, style: { setProperty() {} } }, getElementById: id => els[id], querySelectorAll: () => [],
      addEventListener() {}, createElement: () => ({ classList: { contains: () => false, remove() {}, add() {} }, style: {} }), body: { appendChild() {} } } };
  context.window = context;
  vm.createContext(context);
  for (const f of ['data.js', 'charts.js', 'ui.js', 'views/home.js', 'views/roadmap.js', 'app.js']) {
    vm.runInContext(fs.readFileSync(path.join(root, f), 'utf8'), context, { filename: f });
  }
  return els.app.innerHTML;   // app.js paints once on load — that is the first paint under test
}

test('removed saved view falls back to home and the first paint marks home active', () => {
  const html = shellWithSavedView('exec');
  assert.match(html, /nav-item active" data-view="home"/);
});

test('a valid saved view keeps its own menu item active', () => {
  const html = shellWithSavedView('roadmap');
  assert.match(html, /nav-item active" data-view="roadmap"/);
});
