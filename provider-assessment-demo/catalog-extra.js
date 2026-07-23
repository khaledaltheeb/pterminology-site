"use strict";

(() => {
  const data = window.PA_DEMO_DATA;
  if (!data || !Array.isArray(data.explorers)) return;

  const extra = [
    {
      id: "social-participation",
      title: "استكشاف المشاركة والتفاعل الاجتماعي",
      category: "communication",
      ages: ["early", "child", "adolescent", "adult"],
      duration: "5–7 دقائق",
      description: "ينظم الملاحظة حول بدء التفاعل وتبادل الأدوار وفهم السياق والمشاركة مع الآخرين دون تشخيص نمط اجتماعي محدد.",
      guide: ["صف السلوك في مواقف طبيعية متعددة.", "راعِ اللغة والقلق والحواس وفرص التفاعل.", "لا تفسر الهدوء أو التفضيلات الفردية بوصفها اضطرابًا."],
      next: ["communication-participation", "emotional-regulation", "sensory-regulation"],
      questions: [
        { id: "soc1", domain: "initiation", type: "radio", text: "كيف يبدأ الشخص تفاعلًا عندما يحتاج مشاركة أو مساعدة؟", options: [["usual", "يبدأ بالطريقة المناسبة له غالبًا", 0], ["prompt", "يحتاج تلميحًا أو وسيطًا", 1], ["rare", "نادرًا ما يبدأ حتى عند الحاجة", 2], ["unknown", "غير معروف", null]] },
        { id: "soc2", domain: "reciprocity", type: "select", text: "كيف يستمر تبادل الأدوار في الحوار أو النشاط؟", options: [["balanced", "متبادل بالقدر المتوقع", 0], ["uneven", "غير متوازن أو قصير", 1], ["difficult", "يصعب استمراره غالبًا", 2], ["unknown", "غير معروف", null]] },
        { id: "soc3", domain: "participation", type: "checkbox", text: "أين تظهر صعوبة المشاركة؟", options: [["peers", "مع الأقران", 1], ["adults", "مع البالغين أو مقدمي الخدمة", 1], ["groups", "في المجموعات", 1], ["new", "في المواقف الجديدة", 1], ["none", "لا توجد صعوبة ثابتة", 0]] },
        { id: "soc4", domain: "context", type: "textarea", text: "اذكر موقفًا نجحت فيه المشاركة وموقفًا احتاج دعمًا.", required: false, maxLength: 900 }
      ]
    },
    {
      id: "play-flexibility",
      title: "استكشاف اللعب والمرونة",
      category: "development",
      ages: ["early", "child"],
      duration: "5–7 دقائق",
      description: "يرصد تنوع اللعب والتقليد والخيال والانتقال بين الأنشطة بما يناسب العمر والفرص المتاحة.",
      guide: ["استخدم أمثلة من اللعب الحر والمشترك.", "راعِ الاهتمامات الحقيقية بدل فرض لعبة محددة.", "سجل ما يساعد على الانتقال بين الأنشطة."],
      next: ["development-overview", "social-participation", "sensory-regulation"],
      questions: [
        { id: "pla1", domain: "play", type: "radio", text: "ما مدى تنوع استخدام الألعاب أو المواد؟", options: [["varied", "متنوع ومرن", 0], ["some", "تنوع محدود", 1], ["repetitive", "نمط ضيق أو متكرر غالبًا", 2], ["unknown", "غير معروف", null]] },
        { id: "pla2", domain: "imitation", type: "select", text: "كيف يقلد حركة أو فكرة جديدة أثناء اللعب؟", options: [["spontaneous", "بسهولة أو تلقائيًا", 0], ["model", "بعد نموذج وتكرار", 1], ["limited", "يصعب عليه حتى مع الدعم", 2], ["unknown", "غير معروف", null]] },
        { id: "pla3", domain: "flexibility", type: "checkbox", text: "متى يصعب الانتقال أو التغيير؟", options: [["ending", "إنهاء نشاط مفضل", 1], ["new_rules", "تغيير قواعد اللعب", 1], ["sharing", "مشاركة المواد أو الأدوار", 1], ["new_place", "اللعب في مكان جديد", 1], ["none", "لا توجد صعوبة ثابتة", 0]] },
        { id: "pla4", domain: "context", type: "textarea", text: "ما نوع اللعب المفضل؟ وما الدعم الذي يزيد المرونة؟", required: false, maxLength: 800 }
      ]
    },
    {
      id: "sleep-routine",
      title: "استكشاف النوم والروتين اليومي",
      category: "emotional",
      ages: ["early", "child", "adolescent", "adult"],
      duration: "4–6 دقائق",
      description: "ينظم معلومات وقت النوم والاستيقاظ والاستمرارية وأثر النوم في المشاركة اليومية دون تشخيص اضطراب نوم.",
      guide: ["اعتمد نمط أسبوعين إلى أربعة أسابيع.", "دوّن اختلاف أيام الدراسة والعطل.", "أحِل للمختص عند وجود أعراض طبية أو تدهور واضح."],
      next: ["attention-executive", "emotional-regulation", "development-overview"],
      questions: [
        { id: "slp1", domain: "settling", type: "radio", text: "كيف يبدأ النوم بعد روتين مناسب؟", options: [["usual", "خلال وقت مناسب غالبًا", 0], ["delayed", "يتأخر أحيانًا", 1], ["prolonged", "يتأخر كثيرًا أو يحتاج تدخلًا مستمرًا", 2], ["unknown", "غير معروف", null]] },
        { id: "slp2", domain: "continuity", type: "select", text: "ما نمط الاستيقاظ أو انقطاع النوم؟", options: [["stable", "مستقر غالبًا", 0], ["some", "استيقاظ متقطع أحيانًا", 1], ["frequent", "استيقاظ متكرر يؤثر في اليوم", 2], ["unknown", "غير معروف", null]] },
        { id: "slp3", domain: "context", type: "checkbox", text: "ما العوامل المرتبطة بصعوبة النوم؟", options: [["routine", "تغير الروتين", 1], ["screens", "الشاشات أو النشاط المتأخر", 1], ["anxiety", "القلق أو الانشغال", 1], ["environment", "الضوء أو الصوت أو الحرارة", 1], ["none", "لا يوجد عامل ثابت معروف", 0]] },
        { id: "slp4", domain: "impact", type: "textarea", text: "صف أثر النوم في الانتباه أو المزاج أو الحضور اليومي.", required: false, maxLength: 800 }
      ]
    },
    {
      id: "feeding-participation",
      title: "استكشاف الأكل والمشاركة في الوجبات",
      category: "adaptive",
      ages: ["early", "child", "adolescent", "adult"],
      duration: "5–7 دقائق",
      description: "يرصد تنوع الأطعمة وروتين الوجبة والاستقلال والعوامل الحسية والبيئية دون تقييم طبي للبلع أو التغذية.",
      guide: ["لا تستخدم الأداة عند اشتباه مشكلة بلع أو فقدان وزن؛ اطلب تقييمًا صحيًا.", "راعِ الثقافة والحساسيات والحمية الموصوفة.", "صف ما يحدث فعليًا أثناء الوجبة."],
      next: ["sensory-regulation", "adaptive-daily-living", "communication-participation"],
      questions: [
        { id: "fee1", domain: "variety", type: "radio", text: "ما مدى تنوع الأطعمة المقبولة؟", options: [["varied", "متنوع بما يكفي عادةً", 0], ["limited", "محدود لكنه قابل للتوسع", 1], ["very_limited", "ضيق جدًا ويؤثر في الروتين", 2], ["unknown", "غير معروف", null]] },
        { id: "fee2", domain: "participation", type: "select", text: "كيف يشارك في الوجبة المناسبة لعمره؟", options: [["independent", "باستقلال مناسب", 0], ["support", "يحتاج تذكيرًا أو تكييفًا", 1], ["intensive", "يحتاج مساعدة مباشرة متكررة", 2], ["unknown", "غير معروف", null]] },
        { id: "fee3", domain: "context", type: "checkbox", text: "ما الذي يؤثر في الوجبة؟", options: [["texture", "القوام", 1], ["smell", "الرائحة", 1], ["noise", "الضوضاء أو المكان", 1], ["routine", "تغير الروتين أو التقديم", 1], ["none", "لا يوجد عامل ثابت", 0]] },
        { id: "fee4", domain: "context", type: "textarea", text: "اذكر وجبة تسير جيدًا ووجبة تحتاج دعمًا.", required: false, maxLength: 800 }
      ]
    },
    {
      id: "school-participation",
      title: "استكشاف المشاركة المدرسية",
      category: "learning",
      ages: ["child", "adolescent"],
      duration: "6–8 دقائق",
      description: "ينظم المعلومات عن الحضور وفهم التعليمات وبدء العمل والمشاركة والتكييفات داخل البيئة التعليمية.",
      guide: ["اجمع معلومات من المدرسة والأسرة عند الإمكان.", "افصل بين المهارة وفرصة التعليم.", "سجل التكييفات التي حسنت الوصول."],
      next: ["learning-access", "attention-executive", "communication-participation"],
      questions: [
        { id: "sch1", domain: "attendance", type: "radio", text: "كيف يؤثر الحضور أو الانقطاع في التعلم؟", options: [["stable", "حضور مستقر", 0], ["some", "انقطاع محدود", 1], ["major", "انقطاع واضح يؤثر في التعلم", 2], ["unknown", "غير معروف", null]] },
        { id: "sch2", domain: "instruction", type: "select", text: "كيف يفهم التعليمات الصفية متعددة الخطوات؟", options: [["usual", "بالقدر المتوقع", 0], ["repeat", "يحتاج تكرارًا أو دعمًا بصريًا", 1], ["individual", "يحتاج شرحًا فرديًا متكررًا", 2], ["unknown", "غير معروف", null]] },
        { id: "sch3", domain: "participation", type: "checkbox", text: "أين تظهر عوائق المشاركة؟", options: [["whole_class", "الشرح الجماعي", 1], ["independent", "العمل المستقل", 1], ["group", "العمل الجماعي", 1], ["assessment", "الاختبارات والواجبات", 1], ["none", "لا توجد عوائق ثابتة", 0]] },
        { id: "sch4", domain: "supports", type: "textarea", text: "ما التكييف أو التدخل الذي حسّن المشاركة؟", required: false, maxLength: 900 }
      ]
    },
    {
      id: "self-advocacy",
      title: "استكشاف المناصرة الذاتية واتخاذ القرار",
      category: "adaptive",
      ages: ["adolescent", "adult"],
      duration: "5–7 دقائق",
      description: "يرصد قدرة الشخص على التعبير عن الاحتياجات والتفضيلات والحدود وطلب التكييف والمشاركة في القرارات.",
      guide: ["اسأل الشخص مباشرة متى أمكن.", "استخدم وسائل التواصل المناسبة له.", "لا تساوِ الحاجة للدعم مع غياب القدرة على الاختيار."],
      next: ["communication-participation", "adaptive-daily-living", "transition-adult-life"],
      questions: [
        { id: "adv1", domain: "communication", type: "radio", text: "كيف يعبّر عن احتياجاته أو رفضه؟", options: [["clear", "بطريقة واضحة ومفهومة", 0], ["support", "يحتاج أسئلة أو وسيلة مساعدة", 1], ["limited", "يصعب عليه التعبير أو لا يُمنح فرصة كافية", 2], ["unknown", "غير معروف", null]] },
        { id: "adv2", domain: "choices", type: "select", text: "ما مقدار مشاركته في القرارات اليومية؟", options: [["active", "مشاركة فعلية", 0], ["guided", "مشاركة مع دعم", 1], ["minimal", "مشاركة محدودة جدًا", 2], ["unknown", "غير معروف", null]] },
        { id: "adv3", domain: "access", type: "checkbox", text: "أين يحتاج دعمًا للمناصرة الذاتية؟", options: [["education", "التعليم أو التدريب", 1], ["health", "الخدمات الصحية", 1], ["work", "العمل", 1], ["community", "الخدمات المجتمعية", 1], ["none", "لا يوجد مجال ثابت", 0]] },
        { id: "adv4", domain: "context", type: "textarea", text: "اذكر قرارًا شارك فيه والدعم الذي جعله ممكنًا.", required: false, maxLength: 900 }
      ]
    },
    {
      id: "caregiver-priorities",
      title: "استكشاف أولويات الأسرة ومقدم الرعاية",
      category: "development",
      ages: ["early", "child", "adolescent", "adult"],
      duration: "5–7 دقائق",
      description: "ينظم الأولويات والقوة والضغوط والموارد التي يجب مراعاتها عند تخطيط الدعم دون تقييم الأسرة أو الحكم عليها.",
      guide: ["ابدأ بما يسير جيدًا.", "حدد هدفًا واحدًا أو اثنين قابلين للتنفيذ.", "افصل احتياجات الشخص عن احتياجات مقدم الرعاية مع احترام كليهما."],
      next: ["adaptive-daily-living", "development-overview", "emotional-regulation"],
      questions: [
        { id: "car1", domain: "priorities", type: "radio", text: "ما مدى وضوح الأولوية الحالية للأسرة؟", options: [["clear", "واضحة ومحددة", 0], ["several", "عدة أولويات تحتاج ترتيبًا", 1], ["overwhelmed", "يصعب تحديد نقطة بداية", 2], ["unknown", "غير معروف", null]] },
        { id: "car2", domain: "resources", type: "select", text: "ما مدى توفر الدعم العملي والمعلومات؟", options: [["adequate", "متوفر بالقدر الكافي", 0], ["partial", "متوفر جزئيًا", 1], ["limited", "محدود أو غير متاح", 2], ["unknown", "غير معروف", null]] },
        { id: "car3", domain: "context", type: "checkbox", text: "ما المجالات الأكثر ضغطًا؟", options: [["routine", "الروتين اليومي", 1], ["school", "التعليم أو التدريب", 1], ["services", "الوصول للخدمات", 1], ["community", "المشاركة المجتمعية", 1], ["none", "لا يوجد ضغط ثابت حاليًا", 0]] },
        { id: "car4", domain: "strengths", type: "textarea", text: "ما قوة الأسرة؟ وما التغيير الصغير الأكثر فائدة الآن؟", required: false, maxLength: 1000 }
      ]
    },
    {
      id: "behavior-context-observation",
      title: "استكشاف سياق السلوك ووظيفته المحتملة",
      category: "emotional",
      ages: ["early", "child", "adolescent", "adult"],
      duration: "7–10 دقائق",
      description: "يساعد على وصف ما يسبق السلوك وما يحدث بعده وتأثيره الوظيفي دون افتراض دافع أو تشخيص.",
      guide: ["اكتب ما يمكن ملاحظته لا التفسيرات.", "سجل أكثر من موقف قبل الاستنتاج.", "افحص التواصل والألم والحواس ومتطلبات المهمة."],
      next: ["communication-participation", "sensory-regulation", "emotional-regulation"],
      questions: [
        { id: "beh1", domain: "frequency", type: "radio", text: "ما مدى تكرار السلوك الذي تتم متابعته؟", options: [["rare", "نادر أو محدود", 0], ["sometimes", "يظهر أحيانًا", 1], ["frequent", "متكرر ويؤثر في المشاركة", 2], ["unknown", "غير معروف", null]] },
        { id: "beh2", domain: "impact", type: "select", text: "ما أثره في السلامة أو التعلم أو المشاركة؟", options: [["little", "أثر محدود", 0], ["moderate", "يعطل بعض المواقف", 1], ["major", "يعطل مجالات متعددة", 2], ["unknown", "غير معروف", null]] },
        { id: "beh3", domain: "antecedent", type: "checkbox", text: "ما الذي يسبق السلوك غالبًا؟", options: [["demand", "مطلب أو مهمة", 1], ["transition", "انتقال أو تغيير", 1], ["communication", "تعذر التواصل", 1], ["sensory", "مثير حسي أو ازدحام", 1], ["none", "لا يوجد نمط واضح", 0]] },
        { id: "beh4", domain: "context", type: "textarea", text: "صف موقفًا واحدًا: ما الذي حدث قبله، السلوك الملاحظ، وما حدث بعده؟", required: false, maxLength: 1200 }
      ]
    },
    {
      id: "fine-motor-access",
      title: "استكشاف المهارات الدقيقة والوصول للأدوات",
      category: "motor",
      ages: ["early", "child", "adolescent", "adult"],
      duration: "5–7 دقائق",
      description: "يرصد استخدام اليدين والأدوات والكتابة والأجهزة والتكييفات الوظيفية دون قياس حركي معياري.",
      guide: ["راقب النشاط الوظيفي الفعلي.", "راعِ الألم والتعب ووضعية الجلوس.", "سجل أثر التكييفات والأدوات البديلة."],
      next: ["motor-participation", "learning-access", "adaptive-daily-living"],
      questions: [
        { id: "fin1", domain: "manipulation", type: "radio", text: "كيف يستخدم الأشياء الصغيرة المناسبة للعمر؟", options: [["usual", "باستقلال مناسب", 0], ["slow", "ببطء أو جهد زائد", 1], ["support", "يحتاج مساعدة أو أداة بديلة", 2], ["unknown", "غير معروف", null]] },
        { id: "fin2", domain: "tools", type: "select", text: "كيف يستخدم أدوات الكتابة أو الأكل أو الأجهزة؟", options: [["effective", "بفاعلية غالبًا", 0], ["adapted", "أفضل مع تكييف", 1], ["limited", "الاستخدام محدود بصورة واضحة", 2], ["unknown", "غير معروف", null]] },
        { id: "fin3", domain: "access", type: "checkbox", text: "أين تظهر صعوبة الوصول؟", options: [["writing", "الكتابة والرسم", 1], ["self_care", "العناية الذاتية", 1], ["technology", "لوحة المفاتيح أو اللمس", 1], ["craft", "القص والتركيب والمهام اليدوية", 1], ["none", "لا توجد صعوبة ثابتة", 0]] },
        { id: "fin4", domain: "supports", type: "textarea", text: "ما الأداة أو الوضعية أو التكييف الذي حسّن الأداء؟", required: false, maxLength: 900 }
      ]
    },
    {
      id: "planning-working-memory",
      title: "استكشاف التخطيط والذاكرة العاملة",
      category: "attention",
      ages: ["child", "adolescent", "adult"],
      duration: "5–7 دقائق",
      description: "ينظم الملاحظة حول تذكر الخطوات وترتيبها ومتابعة الوقت وإكمال المهمة دون اختبار معرفي معياري.",
      guide: ["استخدم مهام يومية حقيقية.", "قارن الأداء مع وبدون دعم بصري.", "راعِ النوم واللغة والقلق وصعوبة المهمة."],
      next: ["attention-executive", "learning-access", "adaptive-daily-living"],
      questions: [
        { id: "pln1", domain: "working_memory", type: "radio", text: "كيف يتذكر تعليمات من خطوتين أو أكثر أثناء التنفيذ؟", options: [["usual", "يتذكرها غالبًا", 0], ["reminder", "يحتاج تذكيرًا", 1], ["stepwise", "يحتاج تقديم خطوة واحدة كل مرة", 2], ["unknown", "غير معروف", null]] },
        { id: "pln2", domain: "planning", type: "select", text: "كيف يرتب خطوات مهمة جديدة؟", options: [["plans", "يخطط بالقدر المتوقع", 0], ["template", "يحتاج نموذجًا أو قائمة", 1], ["direct", "يحتاج توجيهًا مباشرًا مستمرًا", 2], ["unknown", "غير معروف", null]] },
        { id: "pln3", domain: "organization", type: "checkbox", text: "أين يظهر أثر التخطيط؟", options: [["school", "الدراسة أو التدريب", 1], ["home", "المسؤوليات المنزلية", 1], ["appointments", "المواعيد والوقت", 1], ["projects", "المشروعات متعددة الخطوات", 1], ["none", "لا يظهر أثر ثابت", 0]] },
        { id: "pln4", domain: "supports", type: "textarea", text: "ما نوع القائمة أو التذكير أو النموذج الأكثر فائدة؟", required: false, maxLength: 900 }
      ]
    },
    {
      id: "wellbeing-participation",
      title: "استكشاف الرفاه والمشاركة الإيجابية",
      category: "emotional",
      ages: ["child", "adolescent", "adult"],
      duration: "5–7 دقائق",
      description: "يرصد الأنشطة ذات المعنى والروابط الاجتماعية والقدرة على التعافي والموارد الداعمة دون قياس اضطراب نفسي.",
      guide: ["ابدأ بنقاط القوة والاهتمامات.", "راعِ الاختلافات الثقافية والفردية.", "استخدم مسار السلامة عند وجود خطر مباشر بدل إكمال الأداة."],
      next: ["emotional-regulation", "social-participation", "adaptive-daily-living"],
      questions: [
        { id: "wel1", domain: "engagement", type: "radio", text: "كم يشارك في نشاط يراه ذا معنى أو متعة؟", options: [["regular", "بصورة منتظمة", 0], ["limited", "بصورة محدودة", 1], ["rare", "نادرًا أو توقف عنه", 2], ["unknown", "غير معروف", null]] },
        { id: "wel2", domain: "recovery", type: "select", text: "كيف يعود إلى نشاطه بعد يوم صعب أو ضغط؟", options: [["recovers", "يتعافى مع دعم معتاد", 0], ["slow", "يحتاج وقتًا ودعمًا إضافيًا", 1], ["persistent", "يبقى الأثر ويعطل المشاركة", 2], ["unknown", "غير معروف", null]] },
        { id: "wel3", domain: "resources", type: "checkbox", text: "ما الموارد الداعمة المتاحة؟", options: [["person", "شخص موثوق", 0], ["activity", "نشاط مفضل", 0], ["routine", "روتين منظم", 0], ["service", "خدمة أو مختص", 0], ["none", "لا يوجد دعم واضح حاليًا", 2]] },
        { id: "wel4", domain: "strengths", type: "textarea", text: "ما النشاط أو العلاقة التي تمنح الشخص معنى أو طاقة؟", required: false, maxLength: 900 }
      ]
    },
    {
      id: "transition-adult-life",
      title: "استكشاف الانتقال إلى حياة البالغين",
      category: "adaptive",
      ages: ["adolescent", "adult"],
      duration: "7–10 دقائق",
      description: "ينظم الاستعداد للتعليم اللاحق والعمل والحياة اليومية والتنقل والخدمات واتخاذ القرار دون تقرير أهلية.",
      guide: ["اجعل الشخص محور التخطيط.", "حدد هدفًا قابلًا للقياس لكل مجال ذي أولوية.", "وثق الدعم البيئي والخدمات المطلوبة لا الصعوبات فقط."],
      next: ["self-advocacy", "adaptive-daily-living", "planning-working-memory"],
      questions: [
        { id: "tra1", domain: "goals", type: "radio", text: "ما مدى وضوح أهداف التعليم أو العمل أو الحياة اليومية؟", options: [["clear", "واضحة ويشارك الشخص في صياغتها", 0], ["emerging", "قيد الاستكشاف", 1], ["unclear", "غير واضحة أو يقررها الآخرون فقط", 2], ["unknown", "غير معروف", null]] },
        { id: "tra2", domain: "daily_living", type: "select", text: "ما مقدار الدعم في إدارة اليوم والمواعيد والمسؤوليات؟", options: [["independent", "استقلال مناسب", 0], ["prompts", "تذكيرات وأدوات تنظيم", 1], ["direct", "دعم مباشر متكرر", 2], ["unknown", "غير معروف", null]] },
        { id: "tra3", domain: "participation", type: "checkbox", text: "ما المجالات التي تحتاج خطة انتقال؟", options: [["education", "التعليم أو التدريب", 1], ["employment", "العمل", 1], ["community", "التنقل والمجتمع", 1], ["services", "الخدمات والدعم القانوني", 1], ["none", "لا يوجد مجال محدد حاليًا", 0]] },
        { id: "tra4", domain: "next_step", type: "textarea", text: "ما الخطوة العملية التالية؟ ومن سيساعد في تنفيذها؟", required: false, maxLength: 1000 }
      ]
    }
  ];

  const existing = new Set(data.explorers.map((tool) => tool.id));
  for (const tool of extra) {
    if (!existing.has(tool.id)) data.explorers.push(tool);
  }
})();