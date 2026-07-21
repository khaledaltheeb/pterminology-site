(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.PTWeeklyReviewV36 = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const STORAGE_KEY = 'pt-weekly-function-review-v36';
  const FIELDS = ['sleep', 'energy', 'focus', 'relationships', 'tasks'];

  function asInteger(value) {
    if (value === null || value === undefined || typeof value === 'boolean') return NaN;
    if (typeof value === 'string' && value.trim() === '') return NaN;
    const number = Number(value);
    return Number.isInteger(number) ? number : NaN;
  }

  function validateRating(value) {
    const number = asInteger(value);
    return Number.isInteger(number) && number >= 0 && number <= 10;
  }

  function validateEntry(entry) {
    if (!entry || typeof entry !== 'object') return { ok: false, errors: ['الإدخال غير صالح.'] };
    const errors = [];
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(entry.date || ''))) errors.push('اختر تاريخًا صحيحًا.');
    for (const field of FIELDS) {
      if (!validateRating(entry[field])) errors.push(`قيمة ${field} يجب أن تكون عددًا صحيحًا من 0 إلى 10.`);
    }
    const note = String(entry.note || '').trim();
    if (note.length > 500) errors.push('الملاحظة يجب ألا تتجاوز 500 حرف.');
    return { ok: errors.length === 0, errors };
  }

  function calculateSummary(entry) {
    const validation = validateEntry(entry);
    if (!validation.ok) return { ok: false, errors: validation.errors };
    const values = FIELDS.map((field) => Number(entry[field]));
    const average = values.reduce((sum, value) => sum + value, 0) / values.length;
    const lowestIndex = values.indexOf(Math.min(...values));
    const highestIndex = values.indexOf(Math.max(...values));
    const labels = {
      sleep: 'النوم', energy: 'الطاقة', focus: 'التركيز', relationships: 'العلاقات', tasks: 'المهام'
    };
    let guidance = 'حافظ على خطوة صغيرة قابلة للتنفيذ هذا الأسبوع.';
    if (average <= 3) guidance = 'يظهر تعطل واسع في عدة مجالات. راقب الاستمرار وتأثيره واطلب دعمًا مهنيًا عند الحاجة.';
    else if (average <= 6) guidance = 'توجد ضغوط متوسطة. اختر مجالًا واحدًا فقط للتحسين ولا تحاول إصلاح كل شيء دفعة واحدة.';
    else guidance = 'الأداء مستقر نسبيًا. حافظ على العوامل التي ساعدت وحدد إنذارًا مبكرًا واحدًا للأسبوع القادم.';
    return {
      ok: true,
      average: Number(average.toFixed(1)),
      lowestField: FIELDS[lowestIndex],
      highestField: FIELDS[highestIndex],
      lowestLabel: labels[FIELDS[lowestIndex]],
      highestLabel: labels[FIELDS[highestIndex]],
      guidance,
      disclaimer: 'هذه قراءة تنظيمية غير تشخيصية ولا تمثل مقياسًا سريريًا.'
    };
  }

  function parseHistory(raw) {
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      return parsed.filter((item) => validateEntry(item).ok).slice(-52);
    } catch (_error) {
      return [];
    }
  }

  function loadHistory(storage) {
    return parseHistory(storage.getItem(STORAGE_KEY));
  }

  function saveEntry(storage, entry) {
    const validation = validateEntry(entry);
    if (!validation.ok) return validation;
    const history = loadHistory(storage).filter((item) => item.date !== entry.date);
    history.push({
      date: entry.date,
      sleep: Number(entry.sleep),
      energy: Number(entry.energy),
      focus: Number(entry.focus),
      relationships: Number(entry.relationships),
      tasks: Number(entry.tasks),
      note: String(entry.note || '').trim()
    });
    history.sort((a, b) => a.date.localeCompare(b.date));
    storage.setItem(STORAGE_KEY, JSON.stringify(history.slice(-52)));
    return { ok: true, history: history.slice(-52) };
  }

  function clearHistory(storage) {
    storage.removeItem(STORAGE_KEY);
    return { ok: true, history: [] };
  }

  function exportJson(history) {
    return JSON.stringify({ version: 36, exportedAt: new Date().toISOString(), entries: history }, null, 2);
  }

  function exportCsv(history) {
    const header = ['date', ...FIELDS, 'note'];
    const escape = (value) => `"${String(value == null ? '' : value).replace(/"/g, '""')}"`;
    return [header.join(','), ...history.map((item) => header.map((key) => escape(item[key])).join(','))].join('\n');
  }

  function download(name, content, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function entryFromForm(form) {
    const data = new FormData(form);
    return {
      date: data.get('date'),
      sleep: data.get('sleep'),
      energy: data.get('energy'),
      focus: data.get('focus'),
      relationships: data.get('relationships'),
      tasks: data.get('tasks'),
      note: data.get('note')
    };
  }

  function renderHistory(history, tableBody, emptyState) {
    tableBody.textContent = '';
    emptyState.hidden = history.length > 0;
    for (const item of history.slice().reverse()) {
      const summary = calculateSummary(item);
      const row = document.createElement('tr');
      const values = [item.date, item.sleep, item.energy, item.focus, item.relationships, item.tasks, summary.average];
      for (const value of values) {
        const cell = document.createElement('td');
        cell.textContent = value;
        row.appendChild(cell);
      }
      tableBody.appendChild(row);
    }
  }

  function renderChart(history, canvas, textAlternative) {
    textAlternative.textContent = history.length
      ? `سجل ${history.length} أسابيع. أحدث متوسط تنظيمي: ${calculateSummary(history[history.length - 1]).average} من 10.`
      : 'لا توجد بيانات محفوظة لعرض الرسم.';
    if (!canvas.getContext || history.length === 0) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width = Math.max(640, canvas.clientWidth * (window.devicePixelRatio || 1));
    const height = canvas.height = 260 * (window.devicePixelRatio || 1);
    ctx.clearRect(0, 0, width, height);
    ctx.lineWidth = 3;
    ctx.strokeStyle = '#145c61';
    ctx.beginPath();
    history.forEach((item, index) => {
      const summary = calculateSummary(item);
      const x = 40 + index * ((width - 80) / Math.max(1, history.length - 1));
      const y = height - 35 - (summary.average / 10) * (height - 70);
      if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  function init() {
    const form = document.querySelector('[data-weekly-review-v36]');
    if (!form) return;
    const status = document.getElementById('weekly-review-status');
    const result = document.getElementById('weekly-review-result');
    const tableBody = document.getElementById('weekly-review-history-body');
    const emptyState = document.getElementById('weekly-review-empty');
    const canvas = document.getElementById('weekly-review-chart');
    const chartText = document.getElementById('weekly-review-chart-text');
    const consent = document.getElementById('weekly-review-storage-consent');

    function refresh() {
      const history = loadHistory(localStorage);
      renderHistory(history, tableBody, emptyState);
      renderChart(history, canvas, chartText);
      return history;
    }

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      const entry = entryFromForm(form);
      const summary = calculateSummary(entry);
      if (!summary.ok) {
        status.textContent = summary.errors.join(' ');
        result.hidden = true;
        return;
      }
      result.hidden = false;
      result.innerHTML = `<h3>قراءة هذا الأسبوع</h3><p><strong>المتوسط التنظيمي:</strong> ${summary.average} من 10</p><p><strong>أقوى مجال:</strong> ${summary.highestLabel}</p><p><strong>المجال الذي يحتاج خطوة صغيرة:</strong> ${summary.lowestLabel}</p><p>${summary.guidance}</p><p>${summary.disclaimer}</p>`;
      if (consent.checked) {
        const saved = saveEntry(localStorage, entry);
        status.textContent = saved.ok ? 'تم الحفظ محليًا على هذا الجهاز فقط.' : saved.errors.join(' ');
        refresh();
      } else {
        status.textContent = 'تم حساب النتيجة دون حفظ أي بيانات.';
      }
    });

    document.getElementById('weekly-review-clear').addEventListener('click', function () {
      if (!window.confirm('هل تريد حذف جميع السجلات المحلية لهذه الأداة؟')) return;
      clearHistory(localStorage);
      status.textContent = 'حُذفت جميع السجلات المحلية.';
      result.hidden = true;
      form.reset();
      refresh();
    });

    document.getElementById('weekly-review-export-json').addEventListener('click', function () {
      download('weekly-function-review.json', exportJson(refresh()), 'application/json;charset=utf-8');
    });
    document.getElementById('weekly-review-export-csv').addEventListener('click', function () {
      download('weekly-function-review.csv', exportCsv(refresh()), 'text/csv;charset=utf-8');
    });
    document.getElementById('weekly-review-print').addEventListener('click', function () { window.print(); });
    refresh();
  }

  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
  }

  return {
    STORAGE_KEY,
    FIELDS,
    validateRating,
    validateEntry,
    calculateSummary,
    parseHistory,
    loadHistory,
    saveEntry,
    clearHistory,
    exportJson,
    exportCsv,
    init
  };
});