from __future__ import annotations

import json
import sys
from pathlib import Path

from defer_encyclopedia_index_v20 import main as defer_encyclopedia_index

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
BASE = "/pterminology-site/"

SERVICE_WORKER = r'''/* pterminology v20 performance service worker */
const CACHE='pterminology-v20-global-quality';
const HOME='/pterminology-site/';
const CORE=[HOME,HOME+'manifest.webmanifest',HOME+'assets/css/marshmallow-v12.css',HOME+'assets/css/encyclopedia-v14.css',HOME+'assets/js/encyclopedia-v14.js'];
self.addEventListener('install',event=>{self.skipWaiting();event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(CORE)).catch(()=>undefined));});
self.addEventListener('activate',event=>{event.waitUntil(Promise.all([caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))),self.clients.claim()]));});
async function networkFirst(request){try{const response=await fetch(request,{cache:'no-store'});if(response&&response.ok){const cache=await caches.open(CACHE);cache.put(request,response.clone());}return response;}catch(error){return(await caches.match(request))||(request.mode==='navigate'?await caches.match(HOME):Response.error());}}
async function staleWhileRevalidate(request){const cached=await caches.match(request);const network=fetch(request,{cache:'no-cache'}).then(async response=>{if(response&&response.ok){const cache=await caches.open(CACHE);cache.put(request,response.clone());}return response;}).catch(()=>null);return cached||(await network)||Response.error();}
self.addEventListener('fetch',event=>{const request=event.request;if(request.method!=='GET')return;const url=new URL(request.url);if(url.origin!==self.location.origin)return;if(request.mode==='navigate'||/\.(?:js|css|json|xml)$/.test(url.pathname)){event.respondWith(networkFirst(request));return;}event.respondWith(staleWhileRevalidate(request));});
'''


def main() -> None:
    if not SITE.exists():
        raise SystemExit(f"Site root not found: {SITE}")
    defer_encyclopedia_index()
    (SITE / "sw.js").write_text(SERVICE_WORKER, encoding="utf-8")
    manifest_path = SITE / "manifest.webmanifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["id"] = BASE
    manifest["start_url"] = BASE
    manifest["scope"] = BASE
    manifest["display"] = "standalone"
    manifest["display_override"] = ["window-controls-overlay", "standalone", "minimal-ui"]
    manifest["orientation"] = "any"
    manifest["background_color"] = "#fff8fc"
    manifest["theme_color"] = "#67d5cd"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {
        "version": 20,
        "cache_name": "pterminology-v20-global-quality",
        "skip_waiting": "skipWaiting" in SERVICE_WORKER,
        "clients_claim": "clients.claim" in SERVICE_WORKER,
        "old_cache_deleted": "keys.filter(key=>key!==CACHE)" in SERVICE_WORKER,
        "network_first_scripts": "js|css|json|xml" in SERVICE_WORKER,
        "deferred_encyclopedia_index": True,
    }
    if not all(report[key] for key in ("skip_waiting", "clients_claim", "old_cache_deleted", "network_first_scripts", "deferred_encyclopedia_index")):
        raise SystemExit(report)
    (SITE / "api" / "pwa-v14.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
