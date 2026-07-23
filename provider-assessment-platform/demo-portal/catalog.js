"use strict";
window.PA_DEMO_DATA={
categories:[
{id:"development",label:"النمو العام"},{id:"communication",label:"اللغة والتواصل"},{id:"attention",label:"الانتباه والوظائف التنفيذية"},{id:"learning",label:"التعلم والتحصيل"},{id:"adaptive",label:"السلوك التكيفي والحياة اليومية"},{id:"sensory",label:"المعالجة والتنظيم الحسي"},{id:"motor",label:"الحركة والمشاركة"},{id:"emotional",label:"التنظيم الانفعالي والسلوك"}
],
explorers:[
{id:"development-overview",title:"الاستكشاف النمائي متعدد المجالات",category:"development",ages:["early","child","adolescent"],duration:"6–9 دقائق",description:"نظرة أولية على التواصل والتعلم والحركة والاستقلال والمشاركة دون مقارنة معيارية أو تشخيص.",guide:["أجب وفق الأداء المعتاد خلال الأسابيع الأربعة الأخيرة.","عند اختلاف الأداء بين البيئات دوّن الفرق.","اختر غير معروف بدل التخمين."],next:["communication-participation","adaptive-daily-living","motor-participation"],questions:[
{id:"dev1",domain:"communication",type:"radio",text:"كيف يعبّر الشخص عادةً عن احتياجاته الأساسية؟",options:[["independent","بوضوح واستقلالية",0],["support","يحتاج تذكيرًا أو أسئلة مساعدة",1],["limited","يعبّر بصورة محدودة أو غير ثابتة",2],["unknown","غير معروف",null]]},
{id:"dev2",domain:"learning",type:"select",text:"عند تعلّم مهارة جديدة، ما مقدار الدعم المعتاد؟",options:[["minimal","شرح أو نموذج واحد غالبًا",0],["repetition","تكرار وممارسة منظمة",1],["intensive","تجزئة كبيرة ومساعدة مستمرة",2],["unknown","غير معروف",null]]},
{id:"dev3",domain:"participation",type:"checkbox",text:"في أي سياقات تظهر الصعوبة؟",options:[["home","المنزل",1],["school","المدرسة أو التدريب",1],["community","المجتمع والأنشطة",1],["none","لا توجد صعوبة ثابتة",0]]},
{id:"dev4",domain:"context",type:"textarea",text:"ما المهارة الأقوى وما الموقف الأكثر صعوبة؟",required:false,maxLength:800}
]},
{id:"communication-participation",title:"استكشاف التواصل والمشاركة",category:"communication",ages:["early","child","adolescent","adult"],duration:"5–8 دقائق",description:"يفحص فهم الرسائل والتعبير وتبادل الأدوار والتواصل الوظيفي والوسائل البديلة.",guide:["احترم الكلام والإشارة والصور والكتابة والأجهزة كوسائل تواصل.","راعِ ثنائية اللغة واللهجة.","قيّم التواصل في الحياة اليومية."],next:["development-overview","adaptive-daily-living","sensory-regulation"],questions:[
{id:"com1",domain:"receptive",type:"radio",text:"كيف يفهم التعليمات اليومية المناسبة لعمره ولغته؟",options:[["usual","يفهمها عادةً",0],["repeat","يحتاج تكرارًا أو تبسيطًا",1],["visual","يحتاج دعمًا بصريًا أو عمليًا غالبًا",2],["unknown","غير معروف",null]]},
{id:"com2",domain:"expressive",type:"select",text:"كيف ينقل فكرة أو حدثًا يحتاج أكثر من جملة أو رمز؟",options:[["clear","بوضوح كافٍ",0],["partial","يحتاج أسئلة توضيحية",1],["difficult","يصعب فهم التسلسل أو المقصود",2],["unknown","غير معروف",null]]},
{id:"com3",domain:"functional",type:"checkbox",text:"ما الوظائف التي يصعب التعبير عنها؟",options:[["request","طلب المساعدة",1],["refuse","الرفض ووضع الحدود",1],["feelings","المشاعر أو الألم",1],["social","بدء تفاعل اجتماعي",1],["none","لا شيء مما سبق",0]]},
{id:"com4",domain:"context",type:"textarea",text:"اذكر مثالًا لرسالة نجح في إيصالها ومثالًا تعثّر فيه.",required:false,maxLength:800}
]},
{id:"attention-executive",title:"استكشاف الانتباه والتنظيم التنفيذي",category:"attention",ages:["child","adolescent","adult"],duration:"6–8 دقائق",description:"يتناول بدء المهمة والاستمرار والذاكرة العاملة وتنظيم الوقت والمرونة.",guide:["قارن الأداء بمتطلبات العمر والسياق.","دوّن أثر النوم والقلق والبيئة.","وجود صعوبة لا يثبت اضطراب فرط الحركة."],next:["learning-access","emotional-regulation","sensory-regulation"],questions:[
{id:"att1",domain:"initiation",type:"radio",text:"بعد تعليمات واضحة، كيف يبدأ المهمة؟",options:[["starts","دون تأخير ملحوظ",0],["prompt","يحتاج تذكيرًا",1],["repeated","يحتاج متابعة متكررة",2],["unknown","غير معروف",null]]},
{id:"att2",domain:"sustained",type:"select",text:"ما نمط الاستمرار في مهمة غير مفضلة؟",options:[["adequate","يستمر بالقدر المتوقع",0],["breaks","يحتاج فواصل منظمة",1],["abandons","يتركها غالبًا قبل الإكمال",2],["unknown","غير معروف",null]]},
{id:"att3",domain:"organization",type:"checkbox",text:"أين يظهر فقدان التنظيم؟",options:[["materials","الأغراض والمواد",1],["time","الوقت والمواعيد",1],["sequence","ترتيب الخطوات",1],["priorities","تحديد الأولويات",1],["none","لا يظهر بصورة ثابتة",0]]},
{id:"att4",domain:"context",type:"textarea",text:"متى يكون الانتباه أفضل؟ ومتى يضعف؟",required:false,maxLength:800}
]},
{id:"learning-access",title:"استكشاف الوصول إلى التعلم",category:"learning",ages:["child","adolescent","adult"],duration:"6–9 دقائق",description:"يفحص القراءة والكتابة والرياضيات وفهم التعليمات وفرص التعليم والتكييفات.",guide:["ميّز بين صعوبة المهارة وضعف فرصة التعليم.","راعِ لغة التعليم والغياب.","النتيجة لا تثبت اضطراب تعلم محدد."],next:["attention-executive","communication-participation","development-overview"],questions:[
{id:"lea1",domain:"instruction",type:"select",text:"هل حصل الشخص على تعليم منتظم ومناسب باللغة المستخدمة؟",options:[["yes","نعم بصورة كافية",0],["mixed","بعض الانقطاع أو تغير اللغة",1],["limited","فرص تعليم محدودة",2],["unknown","غير معروف",null]]},
{id:"lea2",domain:"reading",type:"radio",text:"كيف تؤثر القراءة في الوصول للمحتوى المناسب للعمر؟",options:[["no_barrier","لا تشكل عائقًا",0],["slow","بطيئة أو مجهدة",1],["major","تحد من الفهم أو المشاركة",2],["unknown","غير معروف",null]]},
{id:"lea3",domain:"supports",type:"checkbox",text:"ما التكييفات التي تحسن الأداء؟",options:[["time","وقت إضافي",0],["audio","دعم صوتي",0],["visual","مخططات وأمثلة بصرية",0],["chunking","تجزئة المهمة",0],["unknown","لم تُجرّب تكييفات كافية",1]]},
{id:"lea4",domain:"context",type:"textarea",text:"ما المهارة الأقوى؟ وما التدخل الذي جُرّب؟",required:false,maxLength:900}
]},
{id:"adaptive-daily-living",title:"استكشاف الوظائف اليومية والاستقلال",category:"adaptive",ages:["early","child","adolescent","adult"],duration:"6–8 دقائق",description:"ينظم الملاحظة حول العناية الذاتية والسلامة والمسؤوليات والمشاركة المجتمعية.",guide:["قيّم ما يفعله الشخص فعليًا.","راعِ الفرص والتوقعات الثقافية.","لا تستخدمه بدل مقياس تكيفي معياري."],next:["development-overview","communication-participation","motor-participation"],questions:[
{id:"ada1",domain:"self_care",type:"radio",text:"ما مقدار الدعم في العناية الذاتية المناسبة للعمر؟",options:[["independent","مستقل غالبًا",0],["prompts","تذكير أو إشراف",1],["hands_on","مساعدة مباشرة متكررة",2],["unknown","غير معروف",null]]},
{id:"ada2",domain:"safety",type:"select",text:"كيف يتعرف على المخاطر اليومية ويطلب المساعدة؟",options:[["safe","بصورة مناسبة غالبًا",0],["reminders","يحتاج تذكيرًا",1],["close","يحتاج إشرافًا قريبًا",2],["unknown","غير معروف",null]]},
{id:"ada3",domain:"community",type:"checkbox",text:"أين يحتاج دعمًا وظيفيًا؟",options:[["money","الشراء أو المال",1],["transport","التنقل",1],["appointments","المواعيد والخدمات",1],["choices","الاختيارات اليومية",1],["none","لا شيء مما سبق",0]]},
{id:"ada4",domain:"context",type:"textarea",text:"اذكر مهارة مستقلة ومهارة تحتاج هدف دعم.",required:false,maxLength:800}
]},
{id:"sensory-regulation",title:"استكشاف التنظيم الحسي",category:"sensory",ages:["early","child","adolescent","adult"],duration:"5–7 دقائق",description:"يرصد العلاقة بين الأصوات واللمس والحركة والضوء والتنظيم والمشاركة.",guide:["سجل المثير والسياق وما ساعد.","استبعد الألم والمشكلات الطبية.","لا تفسر كل سلوك على أنه حسي."],next:["emotional-regulation","communication-participation","motor-participation"],questions:[
{id:"sen1",domain:"sound",type:"radio",text:"كيف تؤثر الأصوات المعتادة في المشاركة؟",options:[["little","أثر قليل",0],["sometimes","تشتت أو انزعاج أحيانًا",1],["major","انسحاب أو انفعال متكرر",2],["unknown","غير معروف",null]]},
{id:"sen2",domain:"touch",type:"select",text:"ما الاستجابة للمس أو الملابس أو العناية الشخصية؟",options:[["tolerates","يتحملها عادةً",0],["preferences","تفضيلات واضحة",1],["interferes","تعطل أنشطة متكررة",2],["unknown","غير معروف",null]]},
{id:"sen3",domain:"visual",type:"checkbox",text:"ما البيئات الأكثر صعوبة؟",options:[["crowded","الأماكن المزدحمة",1],["bright","الإضاءة القوية",1],["messy","الخلفيات البصرية الكثيفة",1],["transitions","الانتقالات المفاجئة",1],["none","لا توجد بيئة ثابتة",0]]},
{id:"sen4",domain:"context",type:"textarea",text:"اذكر المثير والاستجابة والاستراتيجية التي ساعدت.",required:false,maxLength:800}
]},
{id:"motor-participation",title:"استكشاف الحركة والمشاركة",category:"motor",ages:["early","child","adolescent","adult"],duration:"5–8 دقائق",description:"ينظم ملاحظة التنقل والتوازن واستخدام اليدين والتعب والوصول للأنشطة.",guide:["فرّق بين القدرة والأداء اليومي.","دوّن الأجهزة والتكييفات.","الألم أو التراجع يحتاج تقييمًا صحيًا."],next:["adaptive-daily-living","development-overview","sensory-regulation"],questions:[
{id:"mot1",domain:"mobility",type:"radio",text:"كيف يتنقل في البيئة المعتادة؟",options:[["independent","باستقلال وأمان",0],["support","بدعم أو جهاز أحيانًا",1],["substantial","بمساعدة كبيرة",2],["unknown","غير معروف",null]]},
{id:"mot2",domain:"balance",type:"select",text:"هل يؤثر التوازن أو السقوط في الأنشطة؟",options:[["no","لا يظهر أثر ثابت",0],["some","في مواقف محددة",1],["frequent","بصورة متكررة",2],["unknown","غير معروف",null]]},
{id:"mot3",domain:"access",type:"checkbox",text:"ما التكييفات المستخدمة؟",options:[["device","جهاز تنقل",0],["seating","جلوس داعم",0],["tools","أدوات معدلة",0],["human","مساعدة بشرية",0],["needed","توجد حاجة غير ملباة",2]]},
{id:"mot4",domain:"context",type:"textarea",text:"ما النشاط الذي يريد المشاركة فيه ويواجه عائقًا؟",required:false,maxLength:800}
]},
{id:"emotional-regulation",title:"استكشاف التنظيم الانفعالي والسلوك",category:"emotional",ages:["child","adolescent","adult"],duration:"6–8 دقائق",description:"يرصد شدة الانفعال والتعافي والمحفزات والتواصل أثناء الضيق وأثر السلوك.",guide:["صف السلوك دون أوصاف وصمية.","افحص الألم والتواصل والبيئة.","الخطر المباشر يوقف الأداة."],next:["sensory-regulation","communication-participation","attention-executive"],questions:[
{id:"emo1",domain:"intensity",type:"radio",text:"عند الانزعاج، ما شدة الاستجابة مقارنة بالموقف؟",options:[["proportionate","متناسبة غالبًا",0],["elevated","أعلى أحيانًا وتحتاج دعمًا",1],["high","شديدة ومتكررة",2],["unknown","غير معروف",null]]},
{id:"emo2",domain:"recovery",type:"select",text:"كم يستغرق عادةً للعودة إلى النشاط؟",options:[["short","وقت قصير",0],["moderate","وقت متوسط مع دعم",1],["long","وقت طويل أو لا يعود",2],["unknown","غير معروف",null]]},
{id:"emo3",domain:"risk",type:"select",text:"هل ظهر خطر مباشر على الشخص أو الآخرين الآن؟",safety:true,options:[["no","لا يوجد خطر مباشر الآن",0],["concern","مخاوف تحتاج مراجعة قريبة",2],["immediate","خطر مباشر أو وشيك",5]]},
{id:"emo4",domain:"context",type:"textarea",text:"صف ما حدث قبل السلوك وأثناءه وما ساعد بعده.",required:false,maxLength:900}
]}
],
professional:[
{category:"التوحد",name:"M-CHAT-R/F",kind:"فحص أولي للأطفال الصغار",access:"دليل وشروط استخدام",status:"guide",note:"لا يثبت التشخيص ويلزم اتباع المقابلة اللاحقة الرسمية."},
{category:"التوحد",name:"ADOS-2",kind:"ملاحظة تشخيصية منظمة",access:"تدريب وترخيص",status:"locked",note:"البنود وخوارزميات التصحيح محمية."},
{category:"التوحد",name:"ADI-R",kind:"مقابلة نمائية تشخيصية",access:"تدريب وترخيص",status:"locked",note:"تستخدم ضمن تقييم شامل متعدد المصادر."},
{category:"التوحد",name:"CARS-2 / SRS-2",kind:"تقدير خصائص واستجابة اجتماعية",access:"حقوق ناشر وتأهيل",status:"locked",note:"لا تحسم التشخيص منفردة."},
{category:"الإعاقة الذهنية والتكيف",name:"Vineland-3 / ABAS-3",kind:"السلوك التكيفي",access:"تجاري ومرخص",status:"locked",note:"يحتاج مجيبًا مطلعًا وتفسيرًا مهنيًا."},
{category:"القدرات المعرفية",name:"WISC / WPPSI / WAIS / SB5",kind:"قدرات معرفية حسب العمر",access:"اختصاص وترخيص مرتفع",status:"locked",note:"المهام والمفاتيح والجداول محمية."},
{category:"القدرات المعرفية",name:"Leiter-3 / Raven",kind:"قدرات غير لفظية",access:"حسب حقوق الأداة",status:"locked",note:"غير لفظي لا يعني خلو الأداة من أثر الثقافة أو الوصول."},
{category:"الانتباه والتنفيذ",name:"Conners 4 / BRIEF-2",kind:"تقديرات الانتباه والتنفيذ",access:"تجاري ومرخص",status:"locked",note:"تحتاج مصادر وسياقات متعددة."},
{category:"الانتباه والتنفيذ",name:"Vanderbilt / SNAP-IV",kind:"فحص أعراض وأثر وظيفي",access:"وفق شروط النسخة",status:"guide",note:"أدوات فحص وليست تشخيصًا."},
{category:"التحصيل والتعلم",name:"WIAT-4 / WJ / KTEA-3",kind:"بطاريات تحصيل",access:"تجاري ومرخص",status:"locked",note:"التفسير يحتاج لغة التعليم وفرصه."},
{category:"التحصيل والتعلم",name:"CTOPP-2 / TOWRE-2 / GORT-5",kind:"مهارات قراءة محددة",access:"تجاري ومرخص",status:"locked",note:"تختار حسب سؤال الإحالة والعمر واللغة."},
{category:"اللغة والتواصل",name:"CELF-5 / PLS-5",kind:"لغة استقبالية وتعبيرية",access:"اختصاص نطق وترخيص",status:"locked",note:"يجب مراعاة ثنائية اللغة والعينة اللغوية."},
{category:"اللغة والتواصل",name:"Communication Matrix",kind:"تواصل مبكر وبديل",access:"مراجعة شروط الاستخدام",status:"guide",note:"يوثق وظائف ووسائل التواصل دون تشخيص."},
{category:"السمع",name:"OAE / ABR / Tympanometry / Audiometry",kind:"فحوص سمعية",access:"خدمة سمعيات مرخصة",status:"external",note:"تستورد الخلاصة ولا تحاكي الأجهزة."},
{category:"البصر",name:"Functional Vision / Learning Media",kind:"بصر وظيفي ووسيلة تعلم",access:"مختص مؤهل",status:"external",note:"لا يستبدل فحص العين الطبي."},
{category:"الحركة",name:"GMFCS / GMFM / MACS",kind:"تصنيف وقياس الوظيفة الحركية",access:"دليل وتأهيل بحسب الأداة",status:"guide",note:"التصنيف والقياس غرضان مختلفان."},
{category:"الحركة",name:"MABC-2 / BOT-2 / PDMS-2",kind:"مهارات وتناسق حركي",access:"تجاري ومرخص",status:"locked",note:"لا تقرر النتيجة المنفردة التشخيص."},
{category:"الحس",name:"Sensory Profile 2 / SPM-2",kind:"المعالجة الحسية والمشاركة",access:"تجاري ومرخص",status:"locked",note:"النتائج وصفية وتربط بالبيئة والمشاركة."},
{category:"السلوك والانفعال",name:"BASC-3 / CBCL / ASEBA",kind:"تقديرات سلوكية وانفعالية",access:"ترخيص وشروط استخدام",status:"locked",note:"لا تنتج تشخيصًا آليًا."},
{category:"السلوك والانفعال",name:"SDQ",kind:"نقاط القوة والصعوبات",access:"وفق شروط النسخة واللغة",status:"guide",note:"فحص ومتابعة وليس تشخيصًا."},
{category:"السلوك الوظيفي",name:"FBA + ABC Data",kind:"تقييم وظيفي للسلوك",access:"بروتوكول مهني",status:"guide",note:"لفهم السوابق والنتائج والوظيفة دون وصم."},
{category:"التأخر النمائي",name:"ASQ-3 / Bayley-4 / Battelle / DAYC-2",kind:"فحص وتقييم نمائي",access:"حقوق ناشر وتدريب",status:"locked",note:"الفحص الإيجابي يقود لتقييم أوسع."},
{category:"الوظيفة والمشاركة",name:"PEDI-CAT / WeeFIM",kind:"الأداء الوظيفي والمشاركة",access:"ترخيص وتأهيل",status:"locked",note:"للتخطيط والمتابعة لا للتشخيص."},
{category:"التواصل البديل",name:"AAC Assessment + SETT",kind:"اختيار نظام تواصل ووصول",access:"فريق متعدد التخصصات",status:"guide",note:"يشمل الشخص والبيئة والمهام وتجربة فعلية."}
]};
