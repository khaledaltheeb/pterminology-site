const fs=require('fs'),vm=require('vm'),path=require('path');
const root=process.argv[2]||'_site';
const runtime=fs.readFileSync(path.join(root,'assets/js/lab-v12.js'),'utf8');
vm.runInThisContext(runtime,{filename:'lab-v12.js'});
const api=globalThis.__PTERMINOLOGY_LAB_V15__;
if(!api) throw new Error('v15 test API missing');
function defs(folder){return fs.readdirSync(path.join(root,folder),{withFileTypes:true}).filter(x=>x.isDirectory()).map(x=>{const file=path.join(root,folder,x.name,'index.html');const html=fs.readFileSync(file,'utf8');const m=html.match(/<script type="application\/json" id="lab-definition">([\s\S]*?)<\/script>/);if(!m)throw new Error('definition missing '+file);return JSON.parse(m[1]);});}
const cognitive=defs('cognitive-lab');if(cognitive.length!==48)throw new Error('expected 48 cognitive definitions');
for(const d of cognitive){for(let stage=0;stage<5;stage++){for(let trial=0;trial<4;trial++){const t=api.makeTrial(d,stage,trial);const values=t.options.map(o=>String(typeof o==='object'?o.value:o));if(!values.includes(String(t.answer)))throw new Error(`answer absent: ${d.slug} stage ${stage} trial ${trial}`);if(!t.prompt||values.length<2)throw new Error('invalid trial '+d.slug);}}}
const speed=cognitive.find(x=>x.slug==='simple-reaction');const color=api.makeTrial(speed,0,0);if(typeof color.answer!=='string'||!color.options.some(x=>typeof x==='object'&&x.hex))throw new Error('color interaction contract failed');
const assessments=defs('assessment-lab');if(assessments.length!==40)throw new Error('expected 40 assessments');
for(const d of assessments){const zero={};d.questions.forEach((_,i)=>zero[i]=0);const low=api.assessmentScore(d,zero);if(!Number.isFinite(low.raw)||!Number.isFinite(low.percent)||!low.complete)throw new Error('score failed '+d.slug);const label=api.interpretAssessment(d,low);if(!Array.isArray(label)||label.length!==2||!label[0])throw new Error('interpretation failed '+d.slug);const partial=api.assessmentScore(d,{0:0});if(partial.answered!==1||partial.complete)throw new Error('partial scoring failed '+d.slug);}
console.log(JSON.stringify({cognitive:cognitive.length,assessments:assessments.length,color_answer:color.answer,status:'passed'}));
