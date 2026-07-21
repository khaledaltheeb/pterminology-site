(function (root) {
  'use strict';

  const STORAGE_KEY = 'pt-sleep-log-v49';
  const MAX_RECORDS = 180;

  function minutes(value) {
    if (!/^\d{2}:\d{2}$/.test(value || '')) return null;
    const [h, m] = value.split(':').map(Number);
    if (h > 23 || m > 59) return null;
    return h * 60 + m;
  }

  function durationMinutes(bedtime, wakeTime) {
    const start = minutes(bedtime);
    const end = minutes(wakeTime);
    if (start === null || end === null) return null;
    const value = end >= start ? end - start : 1440 - start + end;
    return value > 0 && value <= 1440 ? value : null;
  }

  function validate(record) {
    const errors = [];
    if (!/^\d{4}-\d{2}-\d{2}$/.test(record.date || '')) errors.push('أدخل تاريخًا صحيحًا.');
    const duration = durationMinutes(record.bedtime, record.wakeTime);
    if (duration === null) errors.push('تحقق من وقت النوم والاستيقاظ.');
    ['quality', 'energy'].forEach((name) => {
      const value = Number(record[name]);
      if (!Number.isInteger(value) || value < 0 || value > 10) errors.push(`يجب أن تكون قيمة ${name} بين 0 و10.`);
    });
    if ((record.note || '').length > 500) errors.push('الملاحظة يجب ألا تتجاوز 500 حرف.');
    return { valid: errors.length === 0, errors, duration };
  }

  function summarize(record) {
    const checked = validate(record);
    if (!checked.valid) return { errors: checked.errors };
    const hours = Math.round((checked.duration / 60) * 10) / 10;
    const flags = [];
    if (hours < 4 || hours > 12) flags.push('مدة النوم المسجلة بعيدة عن النطاق المعتاد وتستحق مراجعة الظروف أو استشارة مختص إذا تكررت.');
    if (Number(record.quality) <= 3) flags.push('جودة النوم منخفضة حسب تقييمك الشخصي؛ راقب التكرار والأثر الوظيفي بدل الحكم من ليلة واحدة.');
    if (Number(record.energy) <= 3) flags.push('الطاقة منخفضة؛ تجنب القيادة أو المهام الخطرة عند النعاس الشديد.');
    return { hours, flags, message: 'هذه خلاصة تنظيمية غير تشخيصية ولا تمثل مقياسًا سريريًا.' };
  }

  function upsert(records, record) {
    const normalized = records.filter((item) => item.date !== record.date);
    normalized.push(record);
    normalized.sort((a, b) => a.date.localeCompare(b.date));
    return normalized.slice(-MAX_RECORDS);
  }

  function safeParse(value) {
    try {
      const parsed = JSON.parse(value || '[]');
      return Array.isArray(parsed) ? parsed : [];
    } catch (_) { return []; }
  }

  function toCsv(records) {
    const header = ['date','bedtime','wakeTime','quality','energy','note'];
    const escape = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`;
    return '\uFEFF' + [header.join(','), ...records.map((r) => header.map((k) => escape(r[k])).join(','))].join('\n');
  }

  const api = { STORAGE_KEY, MAX_RECORDS, durationMinutes, validate, summarize, upsert, safeParse, toCsv };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.PTSleepLog = api;

  if (typeof document === 'undefined') return;
  const form = document.querySelector('[data-sleep-log]');
  if (!form) return;
  const status = form.querySelector('[role="status"]');
  const results = document.querySelector('[data-sleep-results]');
  const consent = form.querySelector('[name="localConsent"]');

  function readRecords() { return safeParse(localStorage.getItem(STORAGE_KEY)); }
  function writeRecords(records) { localStorage.setItem(STORAGE_KEY, JSON.stringify(records)); }
  function announce(text) { status.textContent = text; }
  function render() {
    const records = readRecords();
    results.innerHTML = records.length ? records.slice().reverse().map((r) => {
      const s = summarize(r);
      return `<tr><td>${r.date}</td><td>${s.hours ?? '—'} ساعة</td><td>${r.quality}/10</td><td>${r.energy}/10</td><td>${(r.note || '').replace(/[<>&]/g, '')}</td></tr>`;
    }).join('') : '<tr><td colspan="5">لا توجد سجلات محفوظة على هذا الجهاز.</td></tr>';
  }
  function recordFromForm() {
    return Object.fromEntries(new FormData(form).entries());
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const record = recordFromForm();
    const checked = validate(record);
    if (!checked.valid) { announce(checked.errors.join(' ')); return; }
    const summary = summarize(record);
    document.querySelector('[data-sleep-summary]').textContent = `${summary.hours} ساعة. ${summary.message} ${summary.flags.join(' ')}`;
    if (consent.checked) {
      writeRecords(upsert(readRecords(), record));
      render();
      announce('تم حفظ السجل محليًا على هذا الجهاز بعد موافقتك.');
    } else announce('تم الحساب دون حفظ. فعّل خيار الحفظ المحلي لحفظ السجل.');
  });

  document.querySelector('[data-delete-sleep]').addEventListener('click', () => {
    localStorage.removeItem(STORAGE_KEY); form.reset(); render(); announce('حُذفت جميع سجلات النوم المحلية من هذا الجهاز.');
  });
  document.querySelector('[data-print-sleep]').addEventListener('click', () => window.print());
  document.querySelector('[data-export-json]').addEventListener('click', () => download('sleep-log.json', JSON.stringify(readRecords(), null, 2), 'application/json'));
  document.querySelector('[data-export-csv]').addEventListener('click', () => download('sleep-log.csv', toCsv(readRecords()), 'text/csv;charset=utf-8'));
  function download(name, content, type) {
    const url = URL.createObjectURL(new Blob([content], { type }));
    const link = document.createElement('a'); link.href = url; link.download = name; link.click(); URL.revokeObjectURL(url);
  }
  render();
}(typeof window !== 'undefined' ? window : globalThis));
