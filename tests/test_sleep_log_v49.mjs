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

const memory = new Map();
const workingStorage = {
  getItem: (key) => memory.get(key) ?? null,
  setItem: (key, value) => memory.set(key, value),
  removeItem: (key) => memory.delete(key)
};
assert.equal(log.storageWrite(workingStorage, [valid]).ok, true);
assert.deepEqual(log.storageRead(workingStorage).records, [valid]);
assert.equal(log.storageDelete(workingStorage).ok, true);
assert.deepEqual(log.storageRead(workingStorage).records, []);

const blockedStorage = {
  getItem() { throw new DOMException('blocked', 'SecurityError'); },
  setItem() { throw new DOMException('blocked', 'SecurityError'); },
  removeItem() { throw new DOMException('blocked', 'SecurityError'); }
};
assert.equal(log.storageRead(blockedStorage).ok, false, 'blocked reads must not throw');
assert.deepEqual(log.storageRead(blockedStorage).records, []);
assert.equal(log.storageWrite(blockedStorage, [valid]).ok, false, 'blocked writes must not claim success');
assert.equal(log.storageDelete(blockedStorage).ok, false, 'blocked deletion must not claim success');

const quotaStorage = { ...workingStorage, setItem() { throw new DOMException('full', 'QuotaExceededError'); } };
assert.equal(log.storageWrite(quotaStorage, [valid]).ok, false, 'quota failure must be reported');

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

assert.match(log.SVG_PRIVACY_NOTICE, /تواريخ النوم/);
assert.match(log.SVG_PRIVACY_NOTICE, /مدته/);
assert.match(log.SVG_PRIVACY_NOTICE, /درجات الجودة والطاقة/);
assert.match(log.SVG_PRIVACY_NOTICE, /لا يتضمن الملاحظات النصية/);
assert.match(log.SVG_PRIVACY_NOTICE, /راجع الملف قبل مشاركته/);
assert.match(log.SVG_PRIVACY_NOTICE, /المشاركة اختيارية وخارج التخزين المحلي/);

assert.equal(log.chartSvgDocument([]), null, 'empty data must not produce a misleading chart download');
const svg = log.chartSvgDocument(chartInput);
assert.match(svg, /^<\?xml version="1\.0" encoding="UTF-8"\?>/);
assert.match(svg, /<svg[^>]+xmlns="http:\/\/www\.w3\.org\/2000\/svg"/);
assert.match(svg, /<title id="title">مخطط اتجاهات النوم والجودة والطاقة<\/title>/);
assert.match(svg, /<desc id="desc">[^<]*14 سجلًا/);
assert.match(svg, /class="series series-hours"/);
assert.match(svg, /class="series series-quality"/);
assert.match(svg, /stroke-dasharray:9 5/);
assert.match(svg, /class="series series-energy"/);
assert.match(svg, /stroke-dasharray:2 5/);
assert.doesNotMatch(svg, /<script/i);
assert.doesNotMatch(svg, /ملاحظة اختبار غير تعريفية/, 'private notes must never enter the visual export');

console.log('sleep-log-v49 tests passed');
