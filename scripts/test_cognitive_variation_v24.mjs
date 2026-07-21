import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { performance } from 'node:perf_hooks';
const root=process.argv[2]||'_site';
const code=fs.readFileSync(path.join(root,'assets/js/lab-v12.js'),'utf8');
const context={console,performance,setTimeout,clearTimeout,globalThis:null};context.globalThis=context;vm.createContext(context);vm.runInContext(code,context);
const api=context.__PTERMINOLOGY_LAB_V15__;if(!api?.makeTrial)throw new Error('makeTrial unavailable');
const dirs=fs.readdirSync(path.join(root,'cognitive-lab'),{withFileTypes:true}).filter(x=>x.isDirectory()).map(x=>x.name).sort();
if(dirs.length!==48)throw new Error(`Expected 48 tools, found ${dirs.length}`);
const errors=[],rows=[],modes=new Map();
for(const slug of dirs){
 const html=fs.readFileSync(path.join(root,'cognitive-lab',slug,'index.html'),'utf8');
 const m=html.match(/<script type="application\/json" id="lab-definition">(.*?)<\/script>/s);if(!m){errors.push(`${slug}: definition missing`);continue;}
 const d=JSON.parse(m[1]);modes.set(d.mode,(modes.get(d.mode)||[]).concat(slug));
 const trials=[];for(let stage=0;stage<(d.stages||5);stage++)for(let i=0;i<(d.trials_per_stage||6);i++)trials.push(api.makeTrial(d,stage,i));
 for(const [i,t] of trials.entries()){
  const vals=t.options.map(x=>String(typeof x==='object'?x.value:x));
  if(!vals.includes(String(t.answer)))errors.push(`${slug} trial ${i}: answer absent`);
  if(new Set(vals).size!==vals.length)errors.push(`${slug} trial ${i}: duplicate options`);
  if(!t.prompt||!t.explanation)errors.push(`${slug} trial ${i}: incomplete content`);
 }
 const first5=trials.slice(0,5).map(t=>JSON.stringify([t.prompt,t.answer,t.stimulusWord,t.stimulusInk]));
 if(new Set(first5).size<2)errors.push(`${slug}: first five trials are identical`);
 if(slug.startsWith('stroop')){
  const words=trials.slice(0,8).map(t=>t.stimulusWord),inks=trials.slice(0,8).map(t=>t.stimulusInk);
  if(new Set(words).size<3)errors.push(`${slug}: word names do not vary`);
  if(new Set(inks).size<3)errors.push(`${slug}: ink colors do not vary`);
  if(trials.slice(0,8).some(t=>!t.stimulusWord||!t.stimulusInk))errors.push(`${slug}: missing ink metadata`);
  if(trials.slice(0,8).every(t=>t.stimulusWord===t.stimulusInk))errors.push(`${slug}: no incongruent trials`);
 }
 rows.push({slug,mode:d.mode,trials:trials.length,uniqueFirstFive:new Set(first5).size});
}
for(const [mode,slugs] of modes)if(!mode)errors.push(`missing mode: ${slugs.join(',')}`);
const report={version:24,tools:dirs.length,modes:modes.size,totalTrials:rows.reduce((s,x)=>s+x.trials,0),errorCount:errors.length,errors,rows};
fs.mkdirSync(path.join(root,'api'),{recursive:true});fs.writeFileSync(path.join(root,'api/cognitive-variation-v24.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));if(errors.length)process.exit(1);
