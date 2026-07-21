import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const log = require('../assets/sleep-log-v49.js');

assert.equal(log.durationMinutes('23:30', '07:00'), 450);
assert.equal(log.durationMinutes('22:00', '22:00'), null);
assert.equal(log.durationMinutes('25:00', '07:00'), null);

const valid = { date:'2026-07-21', bedtime:'23:00', wakeTime:'07:00', quality:'7', energy:'6', note:'ليلة مستقرة' };
assert.equal(log.validate(valid).valid, true);
assert.equal(log.summarize(valid).hours, 8);
assert.match(log.summarize(valid).message, /غير تشخيصية/);

for (const field of ['quality','energy']) {
  assert.equal(log.validate({ ...valid, [field]: '-1' }).valid, false);
  assert.equal(log.validate({ ...valid, [field]: '11' }).valid, false);
  assert.equal(log.validate({ ...valid, [field]: '5.5' }).valid, false);
}
assert.equal(log.validate({ ...valid, note:'x'.repeat(501) }).valid, false);
assert.equal(log.summarize({ ...valid, bedtime:'02:00', wakeTime:'05:00' }).flags.length > 0, true);

let records = [];
records = log.upsert(records, valid);
records = log.upsert(records, { ...valid, quality:'8' });
assert.equal(records.length, 1, 'same date must replace instead of duplicate');
assert.equal(records[0].quality, '8');

for (let i = 0; i < 200; i += 1) {
  records = log.upsert(records, { ...valid, date:`2026-${String(Math.floor(i / 28) + 1).padStart(2,'0')}-${String((i % 28) + 1).padStart(2,'0')}` });
}
assert.equal(records.length, log.MAX_RECORDS);
assert.deepEqual(log.safeParse('broken'), []);
assert.deepEqual(log.safeParse('{}'), []);

const csv = log.toCsv([valid]);
assert.equal(csv.startsWith('\uFEFFdate,'), true);
assert.match(csv, /"ليلة مستقرة"/);
console.log('sleep-log-v49 tests passed');
