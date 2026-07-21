import fs from 'node:fs';
import vm from 'node:vm';
const file=process.argv[2]||'_site/assets/js/lab-v12.js';
const source=fs.readFileSync(file,'utf8');
const sandbox={console,performance:{now:()=>0},globalThis:null};sandbox.globalThis=sandbox;
vm.createContext(sandbox);vm.runInContext(source,sandbox,{filename:file});
const api=sandbox.__PTERMINOLOGY_LAB_V15__;if(!api?.makeTrial)throw new Error('makeTrial export missing');
const make=api.makeTrial;
const firstFive=[
 {slug:'simple-reaction',mode:'simple_reaction'},
 {slug:'choice-reaction',mode:'choice_reaction'},
 {slug:'visual-reaction',mode:'visual_reaction'},
 {slug:'auditory-symbol',mode:'auditory_symbol'},
 {slug:'go-no-go',mode:'go_no_go'}
];
const failures=[];const report={firstFive:{},stroop:{}};
for(const def of firstFive){const trials=Array.from({length:5},(_,i)=>make(def,0,i));const signatures=trials.map(t=>JSON.stringify({prompt:t.prompt,answer:t.answer,audioCount:t.audioCount,delay:t.delay}));const unique=new Set(signatures).size;report.firstFive[def.slug]={unique,answers:[...new Set(trials.map(t=>t.answer))],kinds:[...new Set(trials.map(t=>t.kind))]};if(unique<2)failures.push(`${def.slug}: first five trials are identical`);for(const [i,t] of trials.entries()){if(!Array.isArray(t.options)||!t.options.some(o=>String(typeof o==='object'?o.value:o)===String(t.answer)))failures.push(`${def.slug}:${i}: answer absent from options`);}}
for(const [slug,mode] of [['stroop-basic','stroop_basic'],['stroop-advanced','stroop_advanced']]){const trials=Array.from({length:8},(_,i)=>make({slug,mode},0,i));const words=new Set(trials.map(t=>t.stimulusWord)),inks=new Set(trials.map(t=>t.stimulusInk)),pairs=new Set(trials.map(t=>`${t.stimulusWord}|${t.stimulusInk}`));report.stroop[slug]={words:[...words],inks:[...inks],pairs:pairs.size,rules:[...new Set(trials.map(t=>t.stimulusRule).filter(Boolean))]};if(words.size<3)failures.push(`${slug}: word labels do not vary enough`);if(inks.size<3)failures.push(`${slug}: ink colors do not vary enough`);if(pairs.size<4)failures.push(`${slug}: word/ink pairs repeat excessively`);for(const [i,t] of trials.entries()){if(!t.prompt.includes(`color:`)||!t.prompt.includes('data-word=')||!t.prompt.includes('data-ink='))failures.push(`${slug}:${i}: colored stimulus markup missing`);if(!t.stimulusWord||!t.stimulusInk)failures.push(`${slug}:${i}: stimulus metadata missing`);if(!t.options.some(o=>String(typeof o==='object'?o.value:o)===String(t.answer)))failures.push(`${slug}:${i}: answer absent from options`);}}
console.log(JSON.stringify({...report,failures},null,2));if(failures.length)process.exit(1);
