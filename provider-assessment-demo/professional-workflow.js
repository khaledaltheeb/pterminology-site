"use strict";
(function(){
  const D=window.PA_DEMO_DATA;
  if(!D||!Array.isArray(D.professional))return;

  const view=document.getElementById("view-professional");
  if(!view)return;
  const panel=document.createElement("section");
  panel.className="panel professional-control-panel";
  panel.innerHTML=`<div class="section-heading compact"><div><p class="eyebrow">تخطيط وتوثيق التطبيق المهني</p><h3>عيّن المركز أو المختص وسجّل النتيجة</h3><p class="muted">هذه الوظيفة توثق تطبيقًا مرخصًا أو نتيجة خارجية؛ لا تفتح بنود المقاييس المحمية داخل المنصة.</p></div><button id="new-professional-record" class="button primary" type="button">تسجيل تطبيق مهني</button></div><div id="professional-record-stats" class="meta-row"></div>`;
  view.insertBefore(panel,view.children[2]||null);

  const dialog=document.createElement("dialog");
  dialog.id="professional-record-dialog";
  dialog.className="dialog xlarge";
  dialog.innerHTML=`<form id="professional-record-form" method="dialog"><div class="dialog-heading"><div><p class="eyebrow">سجل الحالة الحالي</p><h2>تخطيط أو تسجيل مقياس مهني</h2></div><button class="icon-button" value="cancel" aria-label="إغلاق">×</button></div><div class="callout warning">لا تستخدم هذا النموذج لنسخ بنود الاختبار أو مفاتيح التصحيح. عند اختيار «مكتمل» يجب أن يكون التطبيق قد تم بأداة أصلية مرخصة وبواسطة شخص مؤهل.</div><div class="form-grid"><label class="field"><span>الحالة</span><select name="caseId" required></select></label><label class="field"><span>المقياس أو الفحص</span><select name="toolId" required></select></label><label class="field"><span>من سينفذ التطبيق؟</span><select name="assignedEntity" required><option value="current_provider">مقدم الخدمة الحالي</option><option value="specialist">مختص محدد</option><option value="center_team">فريق المركز</option><option value="external_center">مركز خارجي</option><option value="multidisciplinary_team">فريق متعدد التخصصات</option><option value="family_self_report">الأسرة أو الشخص — عند ملاءمة النموذج فقط</option></select></label><label class="field"><span>الاختصاص</span><select name="specialty" required><option value="psychology">علم النفس</option><option value="psychiatry">الطب النفسي</option><option value="developmental_pediatrics">طب الأطفال النمائي</option><option value="speech_language">النطق واللغة</option><option value="occupational_therapy">العلاج الوظيفي</option><option value="physical_therapy">العلاج الطبيعي</option><option value="audiology">السمعيات</option><option value="vision">العيون أو ضعف البصر</option><option value="special_education">التربية الخاصة</option><option value="behavior_analysis">تحليل السلوك</option><option value="neurology">الأعصاب أو النفس العصبي</option><option value="rehabilitation">التأهيل</option><option value="assistive_technology">التكنولوجيا المساندة</option><option value="multidisciplinary">فريق متعدد التخصصات</option></select></label><label class="field"><span>طريقة التطبيق أو الاستلام</span><select name="administrationMode" required><option value="planned_only">مخطط ولم يطبق بعد</option><option value="licensed_digital">تطبيق رقمي مرخص</option><option value="official_paper">نموذج ورقي أصلي</option><option value="structured_interview">مقابلة منظمة</option><option value="direct_observation">ملاحظة مباشرة</option><option value="performance_task">مهمة أداء مباشرة</option><option value="rating_form">استبانة ولي أمر أو معلم أو تقرير ذاتي</option><option value="device_clinical">فحص سريري أو بواسطة جهاز</option><option value="imported_report">استيراد خلاصة تقرير خارجي</option></select></label><label class="field"><span>حالة التطبيق</span><select name="recordStatus" required><option value="planned">مخطط</option><option value="scheduled">تم تحديد موعد</option><option value="completed">مكتمل</option><option value="result_imported">تم استلام النتيجة</option><option value="incomplete_invalid">غير مكتمل أو غير صالح</option><option value="cancelled">ملغى</option></select></label><label class="field"><span>تاريخ التطبيق أو الخطة</span><input name="administrationDate" type="date" required></label><label class="field"><span>الإصدار واللغة</span><input name="versionLanguage" maxlength="160" placeholder="مثال: الإصدار الثالث — العربية، أو الإنجليزية مع مترجم"></label><label class="field"><span>نوع النتيجة المسجلة</span><select name="outcome"><option value="no_conclusion">لا توجد خلاصة بعد</option><option value="within_expected">ضمن المتوقع وفق التقرير</option><option value="follow_up">تحتاج متابعة أو معلومات إضافية</option><option value="elevated_concern">مؤشرات مرتفعة وفق التقرير</option><option value="inconclusive">غير حاسمة أو متعارضة</option><option value="invalid">النتيجة غير صالحة للتفسير</option><option value="urgent">تحتاج إجراء سلامة عاجل</option></select></label><label class="field"><span>الخطوة التالية</span><select name="nextAction"><option value="review">مراجعة النتيجة مع المختص</option><option value="another_tool">إضافة مقياس مكمل</option><option value="collect_sources">جمع مصادر معلومات إضافية</option><option value="team_review">مراجعة فريق متعدد التخصصات</option><option value="support_plan">تخطيط الدعم</option><option value="close">إنهاء المسار الحالي</option><option value="urgent_safety">اتباع بروتوكول السلامة</option></select></label></div><label class="field"><span>اسم المركز أو المختص — اختياري</span><input name="performerName" maxlength="160" placeholder="اسم مستعار أو اسم الجهة عند السماح بتسجيله"></label><label class="field"><span>الدرجة أو مرجع التقرير — دون نسخ مواد محمية</span><textarea name="scoreReference" rows="3" maxlength="1200" placeholder="مثال: رقم التقرير، نوع الدرجة، التصنيف الوصفي أو موضع الملف"></textarea></label><label class="field"><span>ملاحظات مقدم الخدمة</span><textarea name="notes" rows="5" maxlength="2400" placeholder="السياق، التكييفات، حدود التطبيق، التعارض بين المصادر وما يحتاج متابعة"></textarea></label><label class="option-card authorization-check"><input name="authorizationConfirmed" type="checkbox"><span>أؤكد أن التطبيق المكتمل تم بواسطة مستخدم مؤهل وبنسخة أصلية مرخصة أو أنني أسجل خلاصة تقرير خارجي فقط.</span></label><div class="dialog-actions"><button class="button ghost" value="cancel">إلغاء</button><button class="button primary" type="submit" value="default">حفظ داخل سجل الحالة</button></div></form>`;
  document.body.appendChild(dialog);
  const form=dialog.querySelector("form");
  const caseSelect=form.elements.caseId;
  const toolSelect=form.elements.toolId;

  const esc=value=>String(value??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");
  const recordId=()=>`PRO-${crypto?.randomUUID?.().replaceAll("-","").slice(0,16).toUpperCase()||Date.now().toString(36).toUpperCase()}`;
  const entityLabel=value=>({current_provider:"مقدم الخدمة الحالي",specialist:"مختص محدد",center_team:"فريق المركز",external_center:"مركز خارجي",multidisciplinary_team:"فريق متعدد التخصصات",family_self_report:"الأسرة أو الشخص"})[value]||value;
  const statusLabel=value=>({planned:"مخطط",scheduled:"موعد محدد",completed:"مكتمل",result_imported:"نتيجة مستلمة",incomplete_invalid:"غير مكتمل أو غير صالح",cancelled:"ملغى"})[value]||value;

  function currentCases(){return Array.isArray(store?.cases)?store.cases:[]}
  function populate(selectedTool=""){
    caseSelect.innerHTML='<option value="">اختر الحالة</option>'+currentCases().map(c=>`<option value="${esc(c.caseId)}">${esc(c.alias)} — ${esc(c.caseId)}</option>`).join("");
    const sorted=[...D.professional].sort((a,b)=>String(a.category).localeCompare(String(b.category),"ar")||String(a.name).localeCompare(String(b.name),"ar"));
    toolSelect.innerHTML='<option value="">اختر المقياس</option>'+sorted.map(t=>`<option value="${esc(t.id||t.name)}"${selectedTool===(t.id||t.name)?" selected":""}>${esc(t.category)} — ${esc(t.name)}</option>`).join("");
    form.elements.administrationDate.value=new Date().toISOString().slice(0,10);
  }
  function openRecord(tool=""){
    if(!currentCases().length){toast("أنشئ حالة أولًا قبل تخطيط المقياس المهني.");newCase();return}
    form.reset();populate(tool);dialog.showModal?dialog.showModal():dialog.setAttribute("open","");
  }
  function professionalRecords(){return currentCases().flatMap(c=>(c.professionalAssessments||[]).map(r=>({...r,caseAlias:c.alias,caseId:c.caseId})))}
  function renderStats(){
    const all=professionalRecords(),completed=all.filter(r=>["completed","result_imported"].includes(r.recordStatus)).length,planned=all.filter(r=>["planned","scheduled"].includes(r.recordStatus)).length;
    document.getElementById("professional-record-stats").innerHTML=`<span>${all.length} سجل مهني</span><span>${planned} مخطط أو مجدول</span><span>${completed} مكتمل أو مستورد</span>`;
  }
  function findTool(id){return D.professional.find(t=>(t.id||t.name)===id)}

  form.addEventListener("submit",event=>{
    event.preventDefault();
    if(!form.reportValidity())return;
    const fd=new FormData(form),c=fcase(String(fd.get("caseId"))),tool=findTool(String(fd.get("toolId")));
    if(!c||!tool){toast("تعذر تحديد الحالة أو المقياس.");return}
    const recordStatus=String(fd.get("recordStatus"));
    const confirmed=fd.get("authorizationConfirmed")==="on";
    if(["completed","result_imported"].includes(recordStatus)&&!confirmed){form.elements.authorizationConfirmed.focus();toast("يجب تأكيد الترخيص والمؤهل أو أن السجل خلاصة تقرير خارجي.");return}
    const now=new Date().toISOString();
    const record={recordId:recordId(),toolId:tool.id||tool.name,toolName:tool.name,category:tool.category,conditions:tool.conditions||[],activationStatus:tool.activationStatus||"guide_only",assignedEntity:String(fd.get("assignedEntity")),specialty:String(fd.get("specialty")),performerName:String(fd.get("performerName")||"").trim(),administrationMode:String(fd.get("administrationMode")),recordStatus,administrationDate:String(fd.get("administrationDate")),versionLanguage:String(fd.get("versionLanguage")||"").trim(),authorizationConfirmed:confirmed,outcome:String(fd.get("outcome")),scoreReference:String(fd.get("scoreReference")||"").trim(),notes:String(fd.get("notes")||"").trim(),nextAction:String(fd.get("nextAction")),recordedAt:now,recordedByUid:identity.uid,recordedByRole:identity.role};
    c.professionalAssessments=Array.isArray(c.professionalAssessments)?c.professionalAssessments:[];
    c.professionalAssessments.push(record);c.updatedAt=now;save();render();renderStats();dialog.close?dialog.close():dialog.removeAttribute("open");toast("تم حفظ التطبيق المهني داخل سجل الحالة وUID الحالي.");showCase(c.caseId);
  });

  const originalRenderProfessional=renderProfessional;
  renderProfessional=function(){
    originalRenderProfessional();
    const q=el.ps.value.trim().toLowerCase(),cat=el.pf.value;
    const filtered=D.professional.filter(x=>(!cat||x.category===cat)&&(!q||`${x.name} ${x.kind} ${x.note} ${x.category}`.toLowerCase().includes(q)));
    document.querySelectorAll("#professional-list .catalog-row").forEach((row,index)=>{
      const tool=filtered[index];if(!tool)return;
      const actions=document.createElement("div");actions.className="catalog-action";actions.innerHTML=`<button class="button secondary small-button" type="button" data-plan-professional="${esc(tool.id||tool.name)}">تخطيط أو تسجيل نتيجة</button>`;row.appendChild(actions);
    });
  };

  const originalShowCase=showCase;
  showCase=function(caseId){
    originalShowCase(caseId);
    const c=fcase(caseId),root=document.getElementById("case-detail-content");if(!c||!root)return;
    const records=Array.isArray(c.professionalAssessments)?[...c.professionalAssessments].reverse():[];
    const block=document.createElement("section");block.className="professional-case-records";
    block.innerHTML=`<div class="section-heading compact"><div><h3>المقاييس والفحوص المهنية</h3><p class="muted">${records.length} سجلًا مخططًا أو منفذًا</p></div><button class="button secondary small-button" type="button" data-new-professional-for-case="${esc(c.caseId)}">إضافة مقياس مهني</button></div><div class="session-list">${records.length?records.map(r=>`<article class="session-row"><div><span class="badge ${r.outcome==="urgent"?"danger":["completed","result_imported"].includes(r.recordStatus)?"success":"warning"}">${esc(statusLabel(r.recordStatus))}</span><h4>${esc(r.toolName)}</h4><p>${esc(entityLabel(r.assignedEntity))}${r.performerName?` — ${esc(r.performerName)}`:""}</p>${r.scoreReference?`<p><strong>النتيجة أو المرجع:</strong> ${esc(r.scoreReference)}</p>`:""}${r.notes?`<p><strong>الملاحظات:</strong> ${esc(r.notes)}</p>`:""}</div><div class="session-meta"><time>${esc(r.administrationDate)}</time><span class="code small">${esc(r.recordId)}</span></div></article>`).join(""):'<div class="empty-state">لا توجد فحوص مهنية مسجلة بعد.</div>'}</div>`;
    const actions=root.querySelector(".dialog-actions.spread");root.insertBefore(block,actions||null);
  };

  document.addEventListener("click",event=>{
    const target=event.target.closest("button");if(!target)return;
    if(target.id==="new-professional-record")openRecord();
    if(target.dataset.planProfessional)openRecord(target.dataset.planProfessional);
    if(target.dataset.newProfessionalForCase){populate();caseSelect.value=target.dataset.newProfessionalForCase;dialog.showModal?dialog.showModal():dialog.setAttribute("open","");}
  });

  renderProfessional();renderStats();
})();
