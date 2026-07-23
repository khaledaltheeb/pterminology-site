(() => {
  "use strict";

  const state = { catalog: null };

  const qs = (selector, root = document) => root.querySelector(selector);
  const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];

  function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(attrs).forEach(([key, value]) => {
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key.startsWith("aria-")) node.setAttribute(key, value);
      else node.setAttribute(key, value);
    });
    (Array.isArray(children) ? children : [children]).forEach(child => {
      if (child == null) return;
      node.append(child.nodeType ? child : document.createTextNode(String(child)));
    });
    return node;
  }

  function list(items, className = "") {
    const ul = el("ul", { class: className });
    items.forEach(item => ul.append(el("li", { text: item })));
    return ul;
  }

  const licenseLabels = {
    requires_publisher_license: "يتطلب ترخيص ناشر",
    permission_required_before_embedding: "يتطلب إذن تضمين",
    classification_public_reference_only: "مرجع تصنيفي فقط",
    internal_template: "نموذج داخلي غير معياري",
    requires_professional_service: "خدمة مهنية خارج النظام",
    manual_rights_review: "مراجعة حقوق يدوية"
  };

  function activateView(id) {
    qsa(".tab").forEach(button => {
      const active = button.dataset.view === id;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    });
    qsa(".view").forEach(view => view.classList.toggle("active", view.id === id));
    const target = document.getElementById(id);
    if (target) target.focus({ preventScroll: true });
  }

  function setupTabs() {
    qsa(".tab").forEach(button => {
      button.setAttribute("role", "tab");
      button.setAttribute("aria-selected", String(button.classList.contains("active")));
      button.addEventListener("click", () => activateView(button.dataset.view));
    });
  }

  function renderDashboard(catalog) {
    qs("#conditionCount").textContent = catalog.conditions.length;
    qs("#instrumentCount").textContent = catalog.instruments.length;
    qs("#lessonCount").textContent = catalog.course.length;
    qs("#digitizableCount").textContent = catalog.instruments.filter(
      item => item.digital_status === "approved_for_production"
    ).length;

    const rules = qs("#governanceRules");
    catalog.governance.non_negotiable_rules.forEach(rule => rules.append(el("li", { text: rule })));

    const roleCards = qs("#roleCards");
    catalog.roles.forEach(role => {
      const card = el("article", { class: "card" });
      card.append(el("h3", { text: role.name }));
      card.append(el("p", { class: "badge", text: role.id }));
      card.append(el("h4", { text: "الصلاحيات" }), list(role.permissions));
      card.append(el("h4", { text: "القيود" }), list(role.restrictions));
      roleCards.append(card);
    });
  }

  function conditionMatches(condition, query) {
    if (!query) return true;
    const haystack = [
      condition.ar_name,
      condition.en_name,
      ...condition.classification,
      ...condition.entry_criteria,
      ...condition.steps.flatMap(step => [
        step.title,
        step.purpose,
        ...step.domains,
        ...step.candidate_tools
      ])
    ].join(" ").toLowerCase();
    return haystack.includes(query.toLowerCase());
  }

  function renderPathways(catalog, query = "") {
    const container = qs("#conditionList");
    container.replaceChildren();
    const items = catalog.conditions.filter(item => conditionMatches(item, query));
    items.forEach(condition => {
      const details = el("details", { class: "pathway" });
      const summary = el("summary");
      summary.append(
        el("span", { text: condition.ar_name }),
        el("span", { class: "badge", text: condition.en_name })
      );
      details.append(summary);

      const content = el("div", { class: "pathway-content" });
      const columns = el("div", { class: "two-col" });
      const entry = el("section");
      entry.append(el("h3", { text: "شروط الدخول" }), list(condition.entry_criteria));
      const flags = el("section");
      flags.append(el("h3", { text: "إشارات توقف أو إحالة عاجلة" }), list(condition.red_flags, "alert-list"));
      columns.append(entry, flags);
      content.append(columns);

      const classifications = el("p");
      classifications.append(el("strong", { text: "التصنيف المرجعي: " }));
      condition.classification.forEach(value => classifications.append(el("span", { class: "badge", text: value })));
      content.append(classifications);

      condition.steps.forEach(step => {
        const box = el("article", { class: "step" });
        box.append(el("h4", { text: `${step.id} — ${step.title}` }));
        box.append(el("p", { text: step.purpose }));
        const meta = el("div", { class: "meta" });
        step.domains.forEach(domain => meta.append(el("span", { class: "badge", text: domain })));
        box.append(meta);
        box.append(el("p", {}, [
          el("strong", { text: "أدوات مرشحة: " }),
          document.createTextNode(step.candidate_tools.join("، "))
        ]));
        box.append(el("p", {}, [
          el("strong", { text: "شرط الاكتمال: " }),
          document.createTextNode(step.completion)
        ]));
        step.next.forEach(route => {
          box.append(el("div", { class: "route" }, [
            el("strong", { text: `إذا: ${route.when} ← ` }),
            document.createTextNode(route.to)
          ]));
        });
        content.append(box);
      });
      details.append(content);
      container.append(details);
    });

    if (!items.length) container.append(el("p", { class: "panel", text: "لا توجد نتيجة مطابقة." }));
  }

  function instrumentMatches(item, query, license) {
    const licenseOk = !license || item.license_status === license;
    const text = [
      item.name, item.acronym, item.purpose, item.domain, item.age,
      item.qualification, item.diagnostic_role, ...item.required_companions,
      ...item.cautions
    ].join(" ").toLowerCase();
    return licenseOk && (!query || text.includes(query.toLowerCase()));
  }

  function renderInstruments(catalog) {
    const query = qs("#instrumentSearch").value.trim();
    const license = qs("#licenseFilter").value;
    const items = catalog.instruments.filter(item => instrumentMatches(item, query, license));
    qs("#instrumentSummary").textContent = `يظهر ${items.length} من أصل ${catalog.instruments.length} بطاقة.`;

    const container = qs("#instrumentList");
    container.replaceChildren();
    items.forEach(item => {
      const card = el("article", { class: "instrument-card" });
      const title = item.acronym && item.acronym !== "—" ? `${item.name} (${item.acronym})` : item.name;
      card.append(el("h3", { text: title }));
      card.append(
        el("span", { class: "badge", text: item.domain }),
        el("span", {
          class: item.license_status === "internal_template" ? "badge warning" : "badge blocked",
          text: licenseLabels[item.license_status] || item.license_status
        })
      );
      const dl = el("dl");
      [
        ["الغرض", item.purpose],
        ["العمر", item.age],
        ["التطبيق", item.administration],
        ["المجيبون", item.respondents],
        ["المؤهل", item.qualification],
        ["الدور", item.diagnostic_role],
        ["المكملات", item.required_companions.join("، ")],
        ["المصدر", item.official_source]
      ].forEach(([term, value]) => {
        dl.append(el("dt", { text: term }), el("dd", { text: value }));
      });
      card.append(dl);
      const caution = el("div", { class: "caution" });
      caution.append(el("strong", { text: "قيود التفسير: " }));
      caution.append(document.createTextNode(item.cautions.join("؛ ")));
      card.append(caution);
      container.append(card);
    });
  }

  function renderCourse(catalog) {
    const container = qs("#courseList");
    catalog.course.forEach((lesson, index) => {
      const card = el("article", { class: "course-card" });
      card.append(el("h3", { text: `${index + 1}. ${lesson.title}` }));
      card.append(el("p", { class: "badge", text: `${lesson.duration_minutes} دقيقة` }));
      card.append(el("h4", { text: "الأهداف" }), list(lesson.objectives));
      const details = el("details");
      details.append(el("summary", { text: "فتح محتوى الدرس واختبار المعرفة" }));
      lesson.sections.forEach(section => {
        const block = el("section", { class: "course-section" });
        block.append(el("h4", { text: section.heading }), el("p", { text: section.body }));
        details.append(block);
      });
      details.append(el("h4", { text: "اختبار المعرفة" }));
      lesson.knowledge_check.forEach(item => {
        const quiz = el("details", { class: "quiz" });
        quiz.append(el("summary", { text: item.question }), el("p", { text: item.answer }));
        details.append(quiz);
      });
      card.append(details);
      container.append(card);
    });
  }

  function renderQuality(catalog) {
    const gates = qs("#qualityGates");
    catalog.quality_gates.forEach(gate => {
      const card = el("article", { class: "quality-card" });
      card.append(el("h3", { text: `${gate.id} — ${gate.title}` }), el("p", { text: gate.pass }));
      gates.append(card);
    });
    const approvals = qs("#approvalList");
    catalog.governance.required_approvals.forEach(item => approvals.append(el("li", { text: item })));
  }

  function setupSimulation(catalog) {
    const select = qs("#simulationCondition");
    catalog.conditions.forEach(condition => {
      select.append(el("option", { value: condition.id, text: condition.ar_name }));
    });

    qs("#simulationForm").addEventListener("submit", event => {
      event.preventDefault();
      const result = qs("#simulationResult");
      result.hidden = false;
      result.className = "panel result";
      result.replaceChildren();

      if (!qs("#fictionalConsent").checked) {
        result.classList.add("danger");
        result.append(el("h3", { text: "المحاكاة موقوفة" }), el("p", { text: "يجب تأكيد أن البيانات افتراضية." }));
        return;
      }

      const condition = catalog.conditions.find(item => item.id === select.value);
      const urgent = qs("#urgentRisk").value === "yes";
      const sources = Number(qs("#sourceCount").value);
      const hearing = qs("#hearingStatus").value;
      const vision = qs("#visionStatus").value;
      const age = Number(qs("#simulationAge").value);
      const missing = [];

      if (urgent) {
        result.classList.add("danger");
        result.append(
          el("h3", { text: "توقف المسار: أولوية السلامة" }),
          el("p", { text: "لا تبدأ المقاييس. طبّق بروتوكول الطوارئ أو الحماية المعتمد في المؤسسة وأحل إلى الجهة المناسبة فورًا. هذه المنصة لا تدير الطوارئ." })
        );
        return;
      }

      if (sources < 2) missing.push("الحصول على مصدر معلومات مستقل ثانٍ على الأقل.");
      if (hearing === "unknown") missing.push("توثيق حالة السمع أو إحالة سمعية ملائمة.");
      if (hearing === "concern") missing.push("إكمال تقييم سمعي قبل تفسير نتائج اللغة أو التواصل أو التعلم.");
      if (vision === "unknown") missing.push("توثيق حالة البصر أو الفحص الوظيفي الملائم.");
      if (vision === "concern") missing.push("إكمال تقييم بصري قبل تفسير مهام تعتمد على الرؤية.");
      if (!Number.isFinite(age) || age < 0) missing.push("تصحيح العمر.");

      result.append(el("h3", { text: `خطة استكمال افتراضية — ${condition.ar_name}` }));
      result.append(el("p", { text: "هذه الخطة لا تختار نسخة اختبار ولا تحسب نقطة قطع ولا تصدر تشخيصًا." }));

      if (missing.length) {
        result.classList.add("warning");
        result.append(el("h4", { text: "نواقص تمنع الانتقال الكامل" }), list(missing));
      } else {
        result.classList.add("ok");
        result.append(el("p", { text: "اكتملت بوابات الصلاحية الأولية في المحاكاة. يمكن بدء أول مرحلة من المسار بعد التحقق من مؤهل المطبق وحقوق الأداة." }));
      }

      result.append(el("h4", { text: "المراحل المقترحة" }));
      const ordered = el("ol");
      condition.steps.forEach(step => {
        const li = el("li");
        li.append(el("strong", { text: step.title }), document.createTextNode(` — ${step.purpose}`));
        ordered.append(li);
      });
      result.append(ordered);
      result.append(el("h4", { text: "إشارات الخطر الخاصة بالمسار" }), list(condition.red_flags, "alert-list"));
    });
  }

  function setupFilters(catalog) {
    qs("#conditionSearch").addEventListener("input", event => renderPathways(catalog, event.target.value.trim()));
    qs("#instrumentSearch").addEventListener("input", () => renderInstruments(catalog));
    qs("#licenseFilter").addEventListener("change", () => renderInstruments(catalog));
  }

  async function init() {
    setupTabs();
    try {
      const response = await fetch("catalog.json", { cache: "no-store" });
      if (!response.ok) throw new Error(`catalog.json: HTTP ${response.status}`);
      const catalog = await response.json();
      const files = catalog.data_files;
      if (!files || !files.conditions || !files.course || !Array.isArray(files.instruments)) {
        throw new Error("سجل data_files غير مكتمل");
      }
      const fetchJson = async path => {
        const part = await fetch(path, { cache: "no-store" });
        if (!part.ok) throw new Error(`${path}: HTTP ${part.status}`);
        return part.json();
      };
      const [conditions, course, ...instrumentChunks] = await Promise.all([
        fetchJson(files.conditions),
        fetchJson(files.course),
        ...files.instruments.map(fetchJson)
      ]);
      catalog.conditions = conditions;
      catalog.course = course;
      catalog.instruments = instrumentChunks.flat();
      state.catalog = catalog;
      renderDashboard(catalog);
      renderPathways(catalog);
      renderInstruments(catalog);
      renderCourse(catalog);
      renderQuality(catalog);
      setupSimulation(catalog);
      setupFilters(catalog);
    } catch (error) {
      const main = qs("#main");
      main.prepend(el("div", {
        class: "safety-banner",
        text: `تعذر تحميل سجل المسارات. أوقف الاستخدام وراجع سلامة catalog.json. (${error.message})`
      }));
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
