#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const portal = path.resolve(here, "..", "demo-portal");
const fail = (message) => { throw new Error(message); };
const read = (name) => fs.readFileSync(path.join(portal, name), "utf8");

for (const name of ["index.html", "styles.css", "catalog.js", "app.js"]) {
  if (!fs.existsSync(path.join(portal, name))) fail(`Missing portal file: ${name}`);
}

const html = read("index.html");
const css = read("styles.css");
const app = read("app.js");
const catalogSource = read("catalog.js");

for (const marker of [
  'lang="ar"', 'dir="rtl"', 'id="account-dialog"', 'id="case-dialog"',
  'id="assessment-dialog"', 'id="result-dialog"', 'id="current-uid"',
  'id="professional-list"', 'id="explorer-list"', 'aria-live="polite"'
]) {
  if (!html.includes(marker)) fail(`HTML lacks marker: ${marker}`);
}
for (const script of ["catalog.js", "app.js"]) {
  if (!html.includes(`src="${script}"`)) fail(`HTML does not load ${script}`);
}
if (!html.includes("لا تنتج تشخيصًا") || !html.includes("التخزين محلي")) {
  fail("Safety and local-storage limitations must remain visible");
}
if (!css.includes(":focus-visible") || !css.includes("prefers-reduced-motion") || !css.includes("high-contrast")) {
  fail("Accessibility CSS controls are incomplete");
}
for (const marker of ["randomUUID", "UID-PROV", "UID-VIS", "sessions", "localStorage", "providerDecision", "urgent_stop"]) {
  if (!app.includes(marker)) fail(`Application lacks behavior marker: ${marker}`);
}
for (const forbidden of ["fetch(", "XMLHttpRequest", "WebSocket", "navigator.sendBeacon"]) {
  if (app.includes(forbidden)) fail(`Static demo must not transmit case data: ${forbidden}`);
}

const context = { window: {} };
vm.runInNewContext(catalogSource, context, { filename: "catalog.js" });
const data = context.window.PA_DEMO_DATA;
if (!data || !Array.isArray(data.categories) || !Array.isArray(data.explorers) || !Array.isArray(data.professional)) {
  fail("Catalog structure is invalid");
}
if (data.categories.length !== 8) fail(`Expected 8 categories, found ${data.categories.length}`);
if (data.explorers.length !== 8) fail(`Expected 8 exploratory tools, found ${data.explorers.length}`);
if (data.professional.length < 20) fail(`Expected at least 20 professional entries, found ${data.professional.length}`);

const ids = new Set(data.explorers.map((item) => item.id));
const types = new Set();
for (const tool of data.explorers) {
  if (!tool.id || !tool.title || !tool.category || !Array.isArray(tool.ages) || !tool.ages.length) fail(`Incomplete tool: ${tool.id || "unknown"}`);
  if (!Array.isArray(tool.questions) || tool.questions.length < 4) fail(`Tool ${tool.id} needs at least four items`);
  if (!Array.isArray(tool.next)) fail(`Tool ${tool.id} lacks next steps`);
  for (const nextId of tool.next) if (!ids.has(nextId)) fail(`Unknown next step ${nextId}`);
  for (const question of tool.questions) {
    types.add(question.type);
    if (!question.id || !question.text || !question.domain || !question.type) fail(`Incomplete question in ${tool.id}`);
    if (["radio", "select", "checkbox"].includes(question.type) && (!Array.isArray(question.options) || question.options.length < 2)) fail(`Question ${question.id} lacks options`);
  }
}
for (const type of ["radio", "select", "checkbox", "textarea"]) if (!types.has(type)) fail(`Missing input type: ${type}`);
for (const status of ["locked", "guide", "external"]) if (!data.professional.some((item) => item.status === status)) fail(`Missing professional status: ${status}`);

console.log(`Validated portal with ${data.explorers.length} exploratory tools and ${data.professional.length} professional guide entries.`);
