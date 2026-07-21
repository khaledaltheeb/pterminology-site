import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const tool = require('../assets/weekly-function-review-v36.js');

class MemoryStorage {
  constructor() { this.map = new Map(); }
  getItem(key) { return this.map.has(key) ? this.map.get(key) : null; }
  setItem(key, value) { this.map.set(key, String(value)); }
  removeItem(key) { this.map.delete(key); }
}

const valid = {
  date: '2026-07-21',
  sleep: 8,
  energy: 6,
  focus: 4,
  relationships: 7,
  tasks: 5,
  note: 'أسبوع مزدحم مع تحسن في النوم.'
};

assert.equal(tool.FIELDS.length, 5);
for (const field of tool.FIELDS) assert.ok(Object.hasOwn(valid, field), `missing ${field}`);

for (const value of [0, 1, 5, 10, '7']) assert.equal(tool.validateRating(value), true, `expected valid ${value}`);
for (const value of [-1, 11, 1.5, 'abc', '', null]) assert.equal(tool.validateRating(value), false, `expected invalid ${value}`);

assert.equal(tool.validateEntry(valid).ok, true);
assert.equal(tool.validateEntry({ ...valid, date: '21-07-2026' }).ok, false);
assert.equal(tool.validateEntry({ ...valid, sleep: 12 }).ok, false);
assert.equal(tool.validateEntry({ ...valid, note: 'x'.repeat(501) }).ok, false);

const summary = tool.calculateSummary(valid);
assert.equal(summary.ok, true);
assert.equal(summary.average, 6);
assert.equal(summary.lowestField, 'focus');
assert.equal(summary.highestField, 'sleep');
assert.match(summary.disclaimer, /غير تشخيصية/);

const low = tool.calculateSummary({ ...valid, sleep: 1, energy: 2, focus: 3, relationships: 2, tasks: 1 });
assert.match(low.guidance, /تعطل واسع/);
const medium = tool.calculateSummary({ ...valid, sleep: 4, energy: 5, focus: 6, relationships: 5, tasks: 4 });
assert.match(medium.guidance, /ضغوط متوسطة/);
const high = tool.calculateSummary({ ...valid, sleep: 8, energy: 8, focus: 9, relationships: 8, tasks: 9 });
assert.match(high.guidance, /مستقر نسبيًا/);

const storage = new MemoryStorage();
assert.deepEqual(tool.loadHistory(storage), []);
let saved = tool.saveEntry(storage, valid);
assert.equal(saved.ok, true);
assert.equal(saved.history.length, 1);
assert.equal(tool.loadHistory(storage)[0].date, valid.date);

saved = tool.saveEntry(storage, { ...valid, sleep: 9 });
assert.equal(saved.history.length, 1, 'same date should replace, not duplicate');
assert.equal(saved.history[0].sleep, 9);

for (let index = 0; index < 60; index += 1) {
  const day = String((index % 28) + 1).padStart(2, '0');
  const month = String(Math.floor(index / 28) + 1).padStart(2, '0');
  tool.saveEntry(storage, { ...valid, date: `2025-${month}-${day}`, note: '' });
}
assert.ok(tool.loadHistory(storage).length <= 52, 'history is capped at 52 entries');

const history = tool.loadHistory(storage);
const json = JSON.parse(tool.exportJson(history));
assert.equal(json.version, 36);
assert.equal(json.entries.length, history.length);
const csv = tool.exportCsv(history);
assert.match(csv, /^date,sleep,energy,focus,relationships,tasks,note/m);
assert.equal(csv.trim().split('\n').length, history.length + 1);

assert.deepEqual(tool.parseHistory('{bad json'), []);
assert.deepEqual(tool.parseHistory(JSON.stringify([{ broken: true }])), []);

const cleared = tool.clearHistory(storage);
assert.equal(cleared.ok, true);
assert.deepEqual(tool.loadHistory(storage), []);
assert.equal(storage.getItem(tool.STORAGE_KEY), null);

console.log(JSON.stringify({ weekly_function_review_v36: 'passed', assertions: 34 }));
