// Record the Studio's one-minute "How it works" tour as a video file, plus a poster image.
//
//   node scripts/record_tour.mjs [STUDIO_URL] [OUT_DIR]
//
// STUDIO_URL is a running Studio (default http://127.0.0.1:8765, e.g. `meidnet studio --no-open`); OUT_DIR defaults to
// docs/assets. Needs Node 22+ and Microsoft Edge or Google Chrome (set BROWSER to its path if it is not found).
// The frames are the page's own (tourVideoSVG). The browser's video encoder (WebCodecs) gets each frame with its exact
// timestamp, so the video runs at the right speed however slowly the frames are drawn; a small muxer from the
// jsDelivr CDN (webm-muxer for VP9, or mp4-muxer when only H.264 is available) writes the file.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const URL_ = process.argv[2] || 'http://127.0.0.1:8765';
const OUT = process.argv[3] || path.join(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..', 'docs', 'assets');
const FPS = 30, BPS = 2_000_000;
const BROWSER = process.env.BROWSER || [
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', 'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/microsoft-edge',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'].find(p => fs.existsSync(p));
if (!BROWSER) { console.error('No Edge or Chrome found: set BROWSER to its path.'); process.exit(2); }
fs.mkdirSync(OUT, { recursive: true });

const port = 9790 + Math.floor(Math.random() * 9);
const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'meidnet_tour_'));
// software rendering: the same pixels on every machine, and no GPU process that can stall a headless canvas
const browser = spawn(BROWSER, ['--headless=new', `--remote-debugging-port=${port}`, '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
  '--ignore-gpu-blocklist', '--no-first-run', '--disable-extensions', '--disable-component-extensions-with-background-pages',
  `--user-data-dir=${prof}`, '--window-size=1280,900', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let ws, id = 0; const pending = new Map();
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
async function ev(expr) {
  const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.result?.exceptionDetails) throw new Error(r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text);
  return r.result?.result?.value;
}

/* runs inside the page: every frame with its exact timestamp into the browser's encoder, then the duration a player reports */
async function record(fps, bps) {
  const W = 1280, H = 720, n = Math.floor(TOUR.total * fps / 1000) + 1, us = 1e6 / fps;
  if (!window.VideoEncoder) throw new Error('this browser has no WebCodecs video encoder');
  // H.264 (mp4) when the browser's encoder really produces output, else VP9 (webm): a headless browser may
  // accept an H.264 configuration and then never emit a chunk, so the first frames are a trial.
  const c = document.createElement('canvas'); c.width = W; c.height = H; const x = c.getContext('2d'), img = new Image();
  const frames = [];                                          // drawn once, encoded by whichever codec works
  window.__rec = { phase: 'drawing', done: 0, of: n, chunks: 0 };
  for (let k = 0; k < n; k++) {
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(tourVideoSVG(Math.min(TOUR.total, k * 1000 / fps)));
    await img.decode(); x.drawImage(img, 0, 0, W, H);
    frames.push(await createImageBitmap(c)); window.__rec.done = k + 1;
  }
  async function encodeAll(codec) {
    let mux, type, cfg;
    if (codec === 'avc') {
      cfg = { codec: 'avc1.42001f', width: W, height: H, bitrate: bps, framerate: fps, avc: { format: 'avc' }, hardwareAcceleration: 'prefer-software' };
      if (!(await VideoEncoder.isConfigSupported(cfg)).supported) return null;
      const M = await import('https://cdn.jsdelivr.net/npm/mp4-muxer@5/+esm');
      mux = new M.Muxer({ target: new M.ArrayBufferTarget(), video: { codec: 'avc', width: W, height: H }, fastStart: 'in-memory' }); type = 'video/mp4';
    } else {
      cfg = { codec: 'vp09.00.10.08', width: W, height: H, bitrate: bps, framerate: fps };
      if (!(await VideoEncoder.isConfigSupported(cfg)).supported) return null;
      const M = await import('https://cdn.jsdelivr.net/npm/webm-muxer@5/+esm');
      mux = new M.Muxer({ target: new M.ArrayBufferTarget(), video: { codec: 'V_VP9', width: W, height: H } }); type = 'video/webm';
    }
    let err = null, chunks = 0;
    const enc = new VideoEncoder({ output: (chunk, meta) => { chunks++; window.__rec.chunks = chunks; mux.addVideoChunk(chunk, meta); }, error: e => { err = e; } });
    enc.configure(cfg);
    window.__rec.phase = 'encoding ' + codec; window.__rec.done = 0;
    for (let k = 0; k < n; k++) {
      const f = new VideoFrame(frames[k], { timestamp: Math.round(k * us), duration: Math.round(us) });
      enc.encode(f, { keyFrame: k % (2 * fps) === 0 }); f.close();
      while (enc.encodeQueueSize > 6) await new Promise(r => setTimeout(r, 4));
      if (err) { enc.close(); return null; }
      if (k === 90 && chunks === 0) { enc.close(); return null; }          // accepted the config but produces nothing
      window.__rec.done = k + 1;
    }
    window.__rec.phase = 'flushing ' + codec;
    const flushed = await Promise.race([enc.flush().then(() => true), new Promise(r => setTimeout(() => r(false), 60000))]);
    if (!flushed || err) { try { enc.close(); } catch (e) { } return null; }
    window.__rec.phase = 'muxing ' + codec; mux.finalize(); window.__rec.phase = 'muxed ' + codec;
    return { type, buffer: mux.target.buffer };
  }
  // VP9/WebM first: libvpx is built into every Chromium and its muxer never stalls; H.264 only when VP9 is missing
  const out = (await encodeAll('vp9')) || (await encodeAll('avc'));
  frames.forEach(f => f.close());
  if (!out) throw new Error('neither the H.264 nor the VP9 encoder produced a file');
  const { type } = out, late = 0, blob = new Blob([out.buffer], { type });
  // how long a player says the file is (a headless browser may not decode it at all: then NaN, and the frame count is the check)
  const url = URL.createObjectURL(blob), v = document.createElement('video'); v.muted = true; v.preload = 'auto'; v.src = url;
  await Promise.race([new Promise(r => { v.onloadedmetadata = r; v.onerror = r; }), new Promise(r => setTimeout(r, 5000))]);
  const duration = v.duration;
  // hand the file to the browser's download (the driver pointed downloads at OUT_DIR): no giant string over the protocol
  const name = 'meidnet_tour.' + (type.includes('mp4') ? 'mp4' : 'webm');
  const a = document.createElement('a'); a.href = url; a.download = name; document.body.appendChild(a); a.click();
  window.__rec.phase = 'downloading ' + name;
  return { type, bytes: blob.size, frames: n, late, duration, expected: TOUR.total / 1000, name };
}
async function poster(ms) {
  const c = document.createElement('canvas'); c.width = 1280; c.height = 720; const img = new Image();
  img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(tourVideoSVG(ms)); await img.decode();
  c.getContext('2d').drawImage(img, 0, 0, 1280, 720); return c.toDataURL('image/png');
}

let code = 0;
try {
  for (let i = 0; i < 60 && !ws; i++) {   // our own tab: an installed extension may open a page of its own at start-up
    try { const t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json(); if (t.webSocketDebuggerUrl) ws = new WebSocket(t.webSocketDebuggerUrl); } catch (e) { }
    if (!ws) await sleep(500);
  }
  await new Promise(r => ws.addEventListener('open', r, { once: true }));
  ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
  await send('Runtime.enable'); await send('Page.enable');
  await send('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: path.resolve(OUT), eventsEnabled: true });
  await send('Page.navigate', { url: URL_.replace(/\/$/, '') + '/studio/?tour=0' });
  let ready = false;
  for (let i = 0; i < 180 && !ready; i++) { await sleep(500); try { ready = await ev(`typeof TOUR!=='undefined' && TOUR.total>0 && !!S.ev && document.getElementById('chain').textContent.startsWith('Ready:')`); } catch (e) { } }
  if (!ready) throw new Error('the Studio did not finish loading at ' + URL_);
  await sleep(1500);                                    // the training-data count arrives just after Ready
  const p = await ev(`(${poster})(tourStart(0)+TOUR_SCENES[0].ms*0.95)`);
  fs.writeFileSync(path.join(OUT, 'meidnet_tour_poster.png'), Buffer.from(p.split(',')[1], 'base64'));
  console.log('recording (a few minutes) ...');
  const watch = setInterval(async () => { try { const s = await ev('window.__rec ? JSON.stringify(window.__rec) : ""'); if (s) console.log('  ' + s); } catch (e) { } }, 10000);
  const r = await ev(`(${record})(${FPS}, ${BPS})`); clearInterval(watch);
  const file = path.join(OUT, r.name);
  for (let i = 0; i < 600; i++) {            // wait until the download has landed and stopped growing
    await sleep(500);
    if (fs.existsSync(file) && !fs.readdirSync(OUT).some(f => f.endsWith('.crdownload'))) { const a = fs.statSync(file).size; await sleep(800); if (fs.statSync(file).size === a && a > 0) break; }
  }
  if (!fs.existsSync(file)) throw new Error('the browser did not save ' + file);
  console.log(`${file}: ${r.type}, ${(r.bytes / 1e6).toFixed(2)} MB, ${r.frames} frames, ${r.late} late, ` +
    `duration ${Number.isFinite(r.duration) ? r.duration.toFixed(2) + ' s' : r.duration} (expected ${r.expected.toFixed(2)} s)`);
  if (Number.isFinite(r.duration) && Math.abs(r.duration - r.expected) > 1.5) { console.error('the video length is off'); code = 1; }
  if (r.frames !== Math.floor(r.expected * 1000 * FPS / 1000) + 1) { console.error('frame count does not match the tour length'); code = 1; }
} catch (e) { console.error(e.stack || e); code = 1; }
finally { try { browser.kill(); } catch (e) { } }
process.exit(code);
