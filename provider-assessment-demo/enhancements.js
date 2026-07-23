"use strict";

(() => {
  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const assessmentTitle = (assessmentId) => {
    const item = window.PA_DEMO_DATA?.explorers?.find((entry) => entry.id === assessmentId);
    return item?.title || assessmentId;
  };

  const allSessions = () => {
    const sessions = [];
    for (const caseRecord of store.cases) {
      for (const session of caseRecord.sessions) {
        sessions.push({ caseRecord, session });
      }
    }
    return sessions.sort((a, b) => new Date(b.session.completedAt) - new Date(a.session.completedAt));
  };

  const signalText = (value) => {
    if (typeof value !== "number") return "غير متاح";
    if (value < 0.7) return `منخفض (${value.toFixed(2)})`;
    if (value < 1.5) return `متوسط (${value.toFixed(2)})`;
    return `مرتفع (${value.toFixed(2)})`;
  };

  const trend = (first, last) => {
    if (typeof first !== "number" || typeof last !== "number") {
      return { label: "غير قابل للمقارنة", className: "trend-flat" };
    }
    const difference = +(last - first).toFixed(2);
    if (Math.abs(difference) < 0.15) {
      return { label: "مستقر وصفيًا", className: "trend-flat" };
    }
    if (difference > 0) {
      return { label: `إشارة أعلى بـ ${difference.toFixed(2)}`, className: "trend-up" };
    }
    return { label: `إشارة أقل بـ ${Math.abs(difference).toFixed(2)}`, className: "trend-down" };
  };

  const repeatedGroups = (caseRecord) => {
    const groups = new Map();
    for (const session of caseRecord.sessions) {
      const list = groups.get(session.assessmentId) || [];
      list.push(session);
      groups.set(session.assessmentId, list);
    }
    return [...groups.entries()]
      .map(([assessmentId, sessions]) => ({
        assessmentId,
        sessions: sessions.sort((a, b) => new Date(a.completedAt) - new Date(b.completedAt)),
      }))
      .filter((group) => group.sessions.length > 1);
  };

  function installAnalyticsView() {
    const tabs = document.querySelector(".tabs");
    const guideTab = tabs?.querySelector('[data-view="guide"]');
    const guidePanel = document.getElementById("view-guide");
    if (!tabs || !guideTab || !guidePanel || document.getElementById("view-analytics")) return;

    const tab = document.createElement("button");
    tab.className = "tab";
    tab.type = "button";
    tab.dataset.view = "analytics";
    tab.setAttribute("aria-selected", "false");
    tab.textContent = "تحليل السجلات";
    tabs.insertBefore(tab, guideTab);

    const panel = document.createElement("section");
    panel.id = "view-analytics";
    panel.className = "view";
    panel.dataset.viewPanel = "analytics";
    panel.hidden = true;
    panel.innerHTML = `
      <div class="section-heading">
        <div>
          <p class="eyebrow">متابعة وصفية عبر الزمن</p>
          <h2>تحليل سجلات UID الحالي</h2>
        </div>
        <button id="print-analytics" class="button ghost" type="button">طباعة الملخص</button>
      </div>
      <div class="callout warning">المقارنة هنا وصفية داخل الأدوات الاستكشافية الأصلية، وليست تغيرًا معياريًا أو دليلًا على تحسن أو تدهور سريري.</div>
      <div id="analytics-stats" class="analytics-grid"></div>
      <article class="panel analytics-section">
        <div class="section-heading compact"><div><h3>الفحوصات المتكررة</h3><p class="muted">مقارنة أول وآخر جلسة للأداة نفسها داخل الحالة نفسها.</p></div></div>
        <div id="repeat-comparison"></div>
      </article>
      <article class="panel analytics-section">
        <div class="section-heading compact"><div><h3>الخط الزمني الكامل</h3><p class="muted">جميع الحالات والجلسات في مساحة UID الحالية.</p></div></div>
        <ol id="full-timeline" class="timeline"></ol>
      </article>
      <article class="panel analytics-section backup-panel">
        <div>
          <h3>النسخة الاحتياطية المحلية</h3>
          <p>يمكن تصدير مساحة UID الحالية واستعادتها على المتصفح نفسه. تُرفض أي نسخة تخص UID مختلفًا لمنع خلط السجلات.</p>
          <p class="uid-lock-note">المالك الحالي: <span id="backup-owner-uid" class="code"></span></p>
        </div>
        <div class="backup-actions">
          <button id="export-space" class="button secondary" type="button">تنزيل نسخة UID</button>
          <button id="import-space" class="button ghost" type="button">استعادة نسخة UID</button>
          <input id="import-space-file" type="file" accept="application/json,.json" hidden>
        </div>
      </article>`;
    guidePanel.before(panel);
  }

  function renderAnalytics() {
    const stats = document.getElementById("analytics-stats");
    const comparison = document.getElementById("repeat-comparison");
    const timeline = document.getElementById("full-timeline");
    const owner = document.getElementById("backup-owner-uid");
    if (!stats || !comparison || !timeline || !owner) return;

    const sessions = allSessions();
    const repeatedCases = store.cases.filter((caseRecord) => repeatedGroups(caseRecord).length > 0);
    const uniqueAssessments = new Set(sessions.map(({ session }) => session.assessmentId));
    const followUpCount = store.cases.filter((caseRecord) => caseRecord.status === "follow_up").length;

    stats.innerHTML = `
      <article class="analytics-card"><span>الحالات</span><strong>${store.cases.length}</strong></article>
      <article class="analytics-card"><span>الجلسات</span><strong>${sessions.length}</strong></article>
      <article class="analytics-card"><span>أدوات مختلفة</span><strong>${uniqueAssessments.size}</strong></article>
      <article class="analytics-card"><span>حالات المتابعة</span><strong>${followUpCount}</strong></article>`;

    const rows = [];
    for (const caseRecord of repeatedCases) {
      for (const group of repeatedGroups(caseRecord)) {
        const first = group.sessions[0];
        const last = group.sessions[group.sessions.length - 1];
        const direction = trend(first.averageSignal, last.averageSignal);
        rows.push(`
          <tr>
            <td><strong>${escapeHtml(caseRecord.alias)}</strong><br><span class="code small">${escapeHtml(caseRecord.caseId)}</span></td>
            <td>${escapeHtml(assessmentTitle(group.assessmentId))}<br><span>${group.sessions.length} جلسات</span></td>
            <td>${escapeHtml(signalText(first.averageSignal))}<br><time>${escapeHtml(fmt(first.completedAt))}</time></td>
            <td>${escapeHtml(signalText(last.averageSignal))}<br><time>${escapeHtml(fmt(last.completedAt))}</time></td>
            <td class="${direction.className}">${escapeHtml(direction.label)}</td>
          </tr>`);
      }
    }

    comparison.innerHTML = rows.length
      ? `<div class="analytics-table-wrap"><table class="analytics-table"><thead><tr><th>الحالة</th><th>الأداة</th><th>الجلسة الأولى</th><th>الجلسة الأخيرة</th><th>التغير الوصفي</th></tr></thead><tbody>${rows.join("")}</tbody></table></div>`
      : '<div class="empty-state">لا توجد أداة مكررة داخل الحالة نفسها حتى الآن.</div>';

    timeline.innerHTML = sessions.length
      ? sessions.map(({ caseRecord, session }) => `
          <li>
            <span class="timeline-marker" aria-hidden="true"></span>
            <div><strong>${escapeHtml(assessmentTitle(session.assessmentId))}</strong><p>${escapeHtml(caseRecord.alias)} — ${escapeHtml(session.outcomeLabel)}</p></div>
            <time>${escapeHtml(fmt(session.completedAt))}</time>
          </li>`).join("")
      : '<li><span class="timeline-marker" aria-hidden="true"></span><div><strong>لا توجد جلسات</strong><p>ابدأ جلسة استكشافية لإظهار الخط الزمني.</p></div></li>';

    owner.textContent = identity.uid;
  }

  function caseComparisonHtml(caseRecord) {
    const groups = repeatedGroups(caseRecord);
    if (!groups.length) {
      return '<div class="comparison-box"><h3>مقارنة الجلسات المتكررة</h3><p class="muted">لا توجد أداة مكررة لهذه الحالة بعد.</p></div>';
    }

    const rows = groups.map((group) => {
      const first = group.sessions[0];
      const last = group.sessions[group.sessions.length - 1];
      const direction = trend(first.averageSignal, last.averageSignal);
      return `<div class="comparison-row">
        <div><span>الأداة</span><strong>${escapeHtml(assessmentTitle(group.assessmentId))}</strong></div>
        <div><span>عدد الجلسات</span><strong>${group.sessions.length}</strong></div>
        <div><span>أول/آخر إشارة</span><strong>${escapeHtml(signalText(first.averageSignal))} ← ${escapeHtml(signalText(last.averageSignal))}</strong></div>
        <div><span>التغير الوصفي</span><strong class="${direction.className}">${escapeHtml(direction.label)}</strong></div>
      </div>`;
    }).join("");

    return `<div class="comparison-box"><h3>مقارنة الجلسات المتكررة</h3><div class="comparison-list">${rows}</div></div>`;
  }

  function enhanceCaseDialog(caseRecord) {
    const content = document.getElementById("case-detail-content");
    if (!content || !caseRecord) return;
    const sessionList = content.querySelector(".session-list");
    if (!sessionList || content.querySelector("[data-session-search]")) return;

    const tools = document.createElement("div");
    tools.className = "case-history-tools";
    tools.innerHTML = `
      <label class="field"><span>البحث داخل جلسات الحالة</span><input type="search" data-session-search placeholder="اسم الأداة، النتيجة أو الملاحظة"></label>
      <button class="button ghost" type="button" data-open-analytics>فتح التحليل الكامل</button>`;
    sessionList.before(tools);
    sessionList.insertAdjacentHTML("afterend", caseComparisonHtml(caseRecord));

    tools.querySelector("[data-session-search]")?.addEventListener("input", (event) => {
      const query = event.target.value.trim().toLowerCase();
      sessionList.querySelectorAll(".session-row").forEach((row) => {
        row.classList.toggle("hidden-session", Boolean(query) && !row.textContent.toLowerCase().includes(query));
      });
    });
  }

  function exportSpace() {
    const payload = {
      schema: "pa-demo-uid-backup-v1",
      warning: "Exploratory non-diagnostic local demo data",
      ownerUid: identity.uid,
      username: identity.username,
      exportedAt: new Date().toISOString(),
      data: JSON.parse(JSON.stringify(store)),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `provider-assessment-${identity.uid}.json`;
    link.click();
    URL.revokeObjectURL(url);
    toast("تم تنزيل نسخة مساحة UID الحالية.");
  }

  function sanitizeImportedStore(candidate) {
    if (!candidate || typeof candidate !== "object" || candidate.uid !== identity.uid || !Array.isArray(candidate.cases)) {
      throw new Error("uid_mismatch");
    }
    if (candidate.cases.length > 500) throw new Error("too_many_cases");

    let sessionCount = 0;
    const cases = candidate.cases.map((caseRecord) => {
      if (!caseRecord || typeof caseRecord !== "object" || typeof caseRecord.caseId !== "string" || typeof caseRecord.alias !== "string" || !Array.isArray(caseRecord.sessions)) {
        throw new Error("invalid_case");
      }
      sessionCount += caseRecord.sessions.length;
      return JSON.parse(JSON.stringify(caseRecord));
    });
    if (sessionCount > 5000) throw new Error("too_many_sessions");

    return {
      uid: identity.uid,
      schemaVersion: String(candidate.schemaVersion || "3"),
      cases,
      createdAt: candidate.createdAt || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
  }

  async function importSpace(file) {
    if (!file || file.size > 5 * 1024 * 1024) {
      toast("ملف النسخة غير صالح أو يتجاوز 5 ميجابايت.");
      return;
    }
    try {
      const payload = JSON.parse(await file.text());
      if (payload?.schema !== "pa-demo-uid-backup-v1" || payload.ownerUid !== identity.uid) {
        toast("رُفضت النسخة لأنها لا تخص UID الحالي.");
        return;
      }
      const imported = sanitizeImportedStore(payload.data);
      if (!window.confirm(`استبدال مساحة UID الحالية التي تحتوي ${store.cases.length} حالة بنسخة تحتوي ${imported.cases.length} حالة؟`)) return;
      store = imported;
      save();
      render();
      toast("تمت استعادة نسخة UID الحالية بنجاح.");
    } catch (_error) {
      toast("تعذر استعادة النسخة. تحقق من سلامة الملف وUID المالك.");
    }
  }

  installAnalyticsView();

  const originalRender = render;
  render = function enhancedRender() {
    originalRender();
    renderAnalytics();
  };

  const originalShowCase = showCase;
  showCase = function enhancedShowCase(caseId) {
    originalShowCase(caseId);
    enhanceCaseDialog(fcase(caseId));
  };

  document.addEventListener("click", (event) => {
    const target = event.target.closest("button");
    if (!target) return;
    if (target.id === "print-analytics") window.print();
    if (target.id === "export-space") exportSpace();
    if (target.id === "import-space") document.getElementById("import-space-file")?.click();
    if (target.hasAttribute("data-open-analytics")) {
      close(document.getElementById("case-detail-dialog"));
      view("analytics");
      renderAnalytics();
    }
  });

  document.getElementById("import-space-file")?.addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    importSpace(file);
    event.target.value = "";
  });

  renderAnalytics();
})();