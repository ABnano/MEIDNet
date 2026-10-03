// Record the Studio's one-minute "How it works" tour as a video file, plus a poster image.
//
//   node scripts/record_tour.mjs [STUDIO_URL] [OUT_DIR]
//
// STUDIO_URL is a running Studio (default http://127.0.0.1:8765, e.g. `meidnet studio --no-open`); OUT_DIR defaults to
// docs/assets. Needs Node 22+ and Microsoft Edge or Google Chrome (set BROWSER to its path if it is not found).
// The frames are the page's own (tourVideoSVG): first every frame is drawn to a JPEG with no time pressure, then the
// JPEGs are played into a MediaRecorder at exactly the frame rate, so the video runs at the right speed on any machine.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const URL_ = process.argv[2] || 'http://127.0.0.1:8765';
const OUT = process.argv[3] || path.join(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')), '..', 'docs', 'assets');
const FPS = 30, BPS = 2_500_000;
const BROWSER = process.env.BROWSER || [
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', 'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/microsoft-edge',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'].find(p => fs.existsSync(p));
if (!BROWSER) { console.error('No Edge or Chrome found: set BROWSER to its path.'); process.exit(2); }
fs.mkdirSync(OUT, { recursive: true });

const port = 9790 + Math.floor(Math.random() * 9);
const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'meidnet_tour_'));
const browser = spawn(BROWSER, ['--headless=new', `--remote-debugging-port=${port}`, '--no-first-run', `--user-data-dir=${prof}`,
  '--window-size=1280,900', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let ws, id = 0; const pending = new Map();
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
async function ev(expr) {
  const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.result?.exceptionDetails) throw new Error(r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text);
  return r.result?.result?.value;
}

/* runs inside the page: two passes, then the duration a player reports */
async function record(fps, bps) {
  const W = 1280, H = 720, frame = 1000 / fps, n = Math.floor(TOUR.total / frame) + 1;
  const type = ['video/mp4;codecs=avc1.42E01F', 'video/mp4', 'video/webm;codecs=vp9', 'video/webm']
    .find(t => window.MediaRecorder && MediaRecorder.isTypeSupported(t));
  if (!type) throw new Error('this browser cannot record video');
  const work = document.createElement('canvas'); work.width = W; work.height = H; const wctx = work.getContext('2d');
  const img = new Image(), jpgs = [];
  for (let k = 0; k < n; k++) {
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(tourVideoSVG(Math.min(TOUR.total, k * frame)));
    await img.decode(); wctx.drawImage(img, 0, 0, W, H);
    jpgs.push(await new Promise(r => work.toBlob(r, 'image/jpeg', 0.95)));
  }
  const canvas = document.createElement('canvas'); canvas.width = W; canvas.height = H; const ctx = canvas.getContext('2d');
  const stream = canvas.captureStream(0), track = stream.getVideoTracks()[0], chunks = [];
  const rec = new MediaRecorder(stream, { mimeType: type, videoBitsPerSecond: bps });
  rec.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
  const first = await createImageBitmap(jpgs[0]); ctx.drawImage(first, 0, 0); first.close();
  let next = createImageBitmap(jpgs[Math.min(1, n - 1)]);
  rec.start(1000); const t0 = performance.now(); let late = 0; track.requestFrame();
  for (let k = 1; k < n; k++) {
    const bmp = await next; if (k + 1 < n) next = createImageBitmap(jpgs[k + 1]);
    const wait = t0 + k * frame - performance.now(); if (wait > 0) await new Promise(r => setTimeout(r, wait)); else if (wait < -frame / 2) late++;
    ctx.drawImage(bmp, 0, 0); bmp.close(); track.requestFrame();
  }
  await new Promise(r => setTimeout(r, frame));
  await new Promise(r => { rec.onstop = r; rec.stop(); });
  const blob = new Blob(chunks, { type });
  const url = URL.createObjectURL(blob), v = document.createElement('video'); v.muted = true; v.preload = 'auto'; v.src = url;
  await new Promise(r => { v.onloadedmetadata = r; v.onerror = r; });
  if (!Number.isFinite(v.duration)) { v.currentTime = 1e7; await Promise.race([new Promise(r => { v.ondurationchange = r; v.ontimeupdate = r; }), new Promise(r => setTimeout(r, 4000))]); }
  const duration = v.duration; URL.revokeObjectURL(url);
  const buf = new Uint8Array(await blob.arrayBuffer()); let bin = '';
  for (let k = 0; k < buf.length; k += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(k, k + 0x8000));
  return { type, bytes: blob.size, frames: n, late, duration, expected: TOUR.total / 1000, b64: btoa(bin) };
}
async function poster(ms) {
  const c = document.createElement('canvas'); c.width = 1280; c.height = 720; const img = new Image();
  img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(tourVideoSVG(ms)); await img.decode();
  c.getContext('2d').drawImage(img, 0, 0, 1280, 720); return c.toDataURL('image/png');
}

let code = 0;
try {
  for (let i = 0; i < 60 && !ws; i++) {
    try { const tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); const t = tabs.find(x => x.type === 'page'); if (t) ws = new WebSocket(t.webSocketDebuggerUrl); } catch (e) { }
    if (!ws) await sleep(500);
  }
  await new Promise(r => ws.addEventListener('open', r, { once: true }));
  ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
  await send('Runtime.enable'); await send('Page.enable');
  await send('Page.navigate', { url: URL_.replace(/\/$/, '') + '/?tour=0' });
  let ready = false;
  for (let i = 0; i < 180 && !ready; i++) { await sleep(500); try { ready = await ev(`typeof TOUR!=='undefined' && TOUR.total>0 && !!S.ev && document.getElementById('chain').textContent.startsWith('Ready:')`); } catch (e) { } }
  if (!ready) throw new Error('the Studio did not finish loading at ' + URL_);
  await sleep(1500);                                    // the training-data count arrives just after Ready
  const p = await ev(`(${poster})(tourStart(0)+TOUR_SCENES[0].ms*0.95)`);
  fs.writeFileSync(path.join(OUT, 'meidnet_tour_poster.png'), Buffer.from(p.split(',')[1], 'base64'));
  console.log('recording (about two minutes) ...');
  const r = await ev(`(${record})(${FPS}, ${BPS})`);
  const ext = r.type.includes('mp4') ? 'mp4' : 'webm', file = path.join(OUT, 'meidnet_tour.' + ext);
  fs.writeFileSync(file, Buffer.from(r.b64, 'base64'));
  console.log(`${file}: ${r.type}, ${(r.bytes / 1e6).toFixed(2)} MB, ${r.frames} frames, ${r.late} late, ` +
    `duration ${Number.isFinite(r.duration) ? r.duration.toFixed(2) + ' s' : r.duration} (expected ${r.expected.toFixed(2)} s)`);
  if (Number.isFinite(r.duration) && Math.abs(r.duration - r.expected) > 1.5) { console.error('the video length is off: frames were drawn too slowly'); code = 1; }
} catch (e) { console.error(e.stack || e); code = 1; }
finally { try { browser.kill(); } catch (e) { } }
process.exit(code);
