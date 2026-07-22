import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const log = require('../assets/sleep-log-v49.js');

assert.equal(log.durationMinutes('23:30', '07:00'), 450);
assert.equal(log.durationMinutes('22:00', '22:00'), null);
assert.equal(log.durationMinutes('25:00', '07:00'), null);

assert.equal(log.isValidDate('2026-07-21'), true);
assert.equal(log.isValidDate('2024-02-29'), true, 'valid leap day must pass');
assert.equal(log.isValidDate('2025-02-29'), false, 'invalid leap day must fail');
assert.equal(log.isValidDate('2026-99-99'), false);
assert.equal(log.isValidDate('2026-04-31'), false);
assert.equal(log.isValidDate('not-a-date'), false);

const valid = { date:'2026-07-21', bedtime:'23:00', wakeTime:'07:00', quality:'7', energy:'6', note:'ليلة مستقرة' };
assert.equal(log.validate(valid).valid, true);
assert.deepEqual(log.validate(valid).fieldErrors, {});
assert.equal(log.summarize(valid).hours, 8);
assert.match(log.summarize(valid).message, /غير تشخيصية/);

for (const field of ['quality','energy']) {
  assert.equal(log.validate({ ...valid, [field]: '-1' }).valid, false);
  assert.equal(log.validate({ ...valid, [field]: '11' }).valid, false);
  assert.equal(log.validate({ ...valid, [field]: '5.5' }).valid, false);
  assert.equal(log.validate({ ...valid, [field]: '' }).valid, false, `${field} must not accept blank text as zero`);
  assert.equal(log.validate({ ...valid, [field]: '   ' }).valid, false, `${field} must not accept whitespace as zero`);
  assert.equal(log.validate({ ...valid, [field]: undefined }).valid, false, `${field} is required`);
  assert.equal(typeof log.validate({ ...valid, [field]: '' }).fieldErrors[field], 'string');
}
const invalidDate = log.validate({ ...valid, date:'2026-99-99' });
assert.equal(invalidDate.valid, false);
assert.match(invalidDate.fieldErrors.date, /تاريخ/);
const invalidTimes = log.validate({ ...valid, bedtime:'22:00', wakeTime:'22:00' });
assert.equal(invalidTimes.valid, false);
assert.match(invalidTimes.fieldErrors.bedtime, /النوم/);
assert.match(invalidTimes.fieldErrors.wakeTime, /الاستيقاظ/);
assert.equal(log.validate({ ...valid, date:'2025-02-29' }).valid, false);
const longNote = log.validate({ ...valid, note:'x'.repeat(501) });
assert.equal(longNote.valid, false);
assert.match(longNote.fieldErrors.note, /500/);
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

const chartInput = Array.from({ length: 20 }, (_, index) => ({
  ...valid,
  date: `2026-07-${String(index + 1).padStart(2, '0')}`,
  bedtime: '23:00',
  wakeTime: index % 2 ? '07:00' : '06:30',
  quality: String(index % 11),
  energy: String((index + 2) % 11)
}));
const points = log.chartData(chartInput);
assert.equal(points.length, log.CHART_RECORDS, 'chart must limit itself to the latest 14 valid records');
assert.equal(points[0].date, '2026-07-07');
assert.equal(points.at(-1).date, '2026-07-20');
assert.equal(typeof points[0].hours, 'number');
assert.equal(typeof points[0].quality, 'number');
assert.equal(typeof points[0].energy, 'number');
assert.equal(log.chartData([{ ...valid, date: 'invalid' }]).length, 0, 'invalid records must not enter the chart');
assert.match(log.chartDescription(points), /14 سجلًا/);
assert.match(log.chartDescription(points), /2026-07-20/);
assert.match(log.chartDescription([]), /لا توجد بيانات/);

console.log('sleep-log-v49 tests passed');