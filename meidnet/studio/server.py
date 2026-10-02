"""
The Studio's server: serves the page, a small JSON API and (optionally) the documentation site.

Everything scientific happens in the same Python functions the command line uses
(``load_family``, ``enumerate_space``, ``Designer``), so what the page shows is what
``meidnet generate`` would do with the exported YAML.

Local use:      meidnet studio [meidnet.yaml]            (127.0.0.1, one user, no limits)
Public hosting: python -m meidnet.studio.server --host 0.0.0.0 --port 7860 --public --docs-dir site
                 • every browser tab gets its own search session (a random id it generates)
                 • search budgets are capped and only built-in families can be loaded
                 • at most MAX_RUNNING searches run at once; others are told to retry

API
    GET  /                      the page
    GET  /api/state             model, config, variants, property ranges, limits
    GET  /api/data              data summary (histograms)
    POST /api/family            {family, variant} → family + design space
    POST /api/search/start      {session, generation} → starts a search in a thread
    GET  /api/search/status?session=…
    POST /api/search/stop       {session}
    POST /api/export            {generation} → YAML of the configuration
    GET  /files/<path>          files written by searches (CIFs, reports)
    GET  /docs/…                the documentation site, if --docs-dir is given
"""
from __future__ import annotations

import argparse
import copy
import json
import mimetypes
import os
import re
import secrets
import shutil
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from meidnet import __version__
from meidnet.checkpoint import describe, load_checkpoint, property_ranges
from meidnet.config import MEIDNetConfig, config_from_dict, dump_config
from meidnet.designspace import enumerate_space
from meidnet.family import list_families, load_family
from meidnet.terms import SEARCH_TERMS

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_RUNNING = 2                       # concurrent searches on a public host
PUBLIC_LIMITS = {"per_target": 6, "population": 32, "rounds": 6, "steps": 400, "targets": 2}
JOB_TTL = 3600                        # seconds a finished session's files are kept
SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{4,64}$")


def default_config(model_path: str, run_root: str | None = None) -> MEIDNetConfig:
    """Config used when the Studio is started without a meidnet.yaml: the published perovskite model."""
    return config_from_dict({
        "name": "studio", "output_dir": run_root or "runs/studio", "model_path": model_path,
        "description": "MEIDNet Studio session (published Perov-5 model)",
        "generation": {
            "family": "perovskite_abx3", "variant": "halide",
            "objectives": [{"property": "dir_gap", "loss": "l2", "weight": 10000, "select_weight": 1.0},
                           {"property": "heat_all", "loss": "l1", "weight": 6000, "select_weight": 0.4}],
            "targets": [{"dir_gap": 2.0, "heat_all": -0.10}],
            "per_target": 3, "population": 24, "rounds": 3, "steps": 300, "min_cosine_sep": 0.98,
        },
    }, base_dir=os.getcwd())


class SearchJob:
    def __init__(self, session: str):
        self.session = session
        self.lock = threading.Lock()
        self.running = False
        self.done = False
        self.error = None
        self.log = []
        self.candidates = []
        self.progress = {"target": 0, "targets": 0, "round": 0, "rounds": 0, "step": 0, "steps": 0, "loss": None}
        self.stop_flag = False
        self.report = None
        self.run_dir = None
        self.started = time.time()
        self.finished = None

    def snapshot(self):
        with self.lock:
            return {"running": self.running, "done": self.done, "error": self.error, "log": self.log[-60:],
                    "candidates": self.candidates, "progress": dict(self.progress), "report": self.report,
                    "seconds": (self.finished or time.time()) - self.started}


class Studio:
    def __init__(self, cfg: MEIDNetConfig | None, model_path: str | None = None, public: bool = False,
                 run_root: str | None = None, docs_dir: str | None = None):
        self.public = public
        self.run_root = os.path.abspath(run_root or (os.path.join(os.getcwd(), "runs", "studio")))
        os.makedirs(self.run_root, exist_ok=True)
        if cfg is None:
            from meidnet.cli import published_checkpoint
            cfg = default_config(os.path.abspath(model_path or published_checkpoint()), self.run_root)
        elif model_path:
            cfg.model_path = os.path.abspath(model_path)
        self.cfg = cfg
        self.lm = load_checkpoint(cfg.checkpoint_path)
        self.ranges = property_ranges(self.lm)
        self.space_cache: dict[str, dict] = {}
        self.space_lock = threading.Lock()
        self.jobs: dict[str, SearchJob] = {}
        self.jobs_lock = threading.Lock()
        self.data_summary = None
        self.data_lock = threading.Lock()
        self.docs_dir = os.path.abspath(docs_dir) if docs_dir else None

    # ── state ────────────────────────────────────────────────────────────────
    def family_meta(self, name: str) -> dict:
        fam = load_family(name, default_variant=True)
        return {"name": fam.name, "title": fam.title, "description": fam.description, "variants": fam.variants,
                "n_sites": fam.n_sites, "sites": [{"group": g, "frac": list(f)} for g, f in fam.sites],
                "lattice": fam.lattice, "lattice_rule": fam.lattice_rule}

    def state(self) -> dict:
        g = self.cfg.generation
        hist = self.lm.meta.get("history") or {}
        val = (hist.get("val") or [None])[-1]
        return {
            "version": __version__, "public": self.public, "limits": PUBLIC_LIMITS if self.public else None,
            "docs_url": "/docs/" if self.docs_dir else None,
            "config": json.loads(json.dumps(self.cfg.model_dump(mode="json"), default=str)),
            "model": {"description": describe(self.lm), "legacy": self.lm.legacy,
                      "path": os.path.basename(self.lm.path) if self.public else self.lm.path,
                      "properties": self.lm.stats.to_dict(), "family": self.lm.family, "max_sites": self.lm.model.max_sites,
                      "validation": val, "note": self.lm.meta.get("note", "")},
            "ranges": self.ranges,
            "families": {n: self.family_meta(n) for n in list_families()},
            "current_family": g.family if g else "perovskite_abx3",
            "terms": {n: SEARCH_TERMS.doc(n) for n in SEARCH_TERMS.names()},
            "has_data": self.cfg.data is not None,
        }

    def data(self) -> dict:
        with self.data_lock:
            if self.data_summary is None:
                self.data_summary = self._compute_data_summary()
            return self.data_summary

    def _compute_data_summary(self) -> dict:
        import numpy as np
        from meidnet import svg
        if self.cfg.data is None:
            cand = os.path.join(os.getcwd(), "data", "perov5", "train.csv")
            if not os.path.exists(cand):
                return {"available": False, "note": "The published model was trained on Perov-5 (11,356 structures). "
                                                    "Run `meidnet download-data` to see its distributions here."}
            import pandas as pd
            df = pd.read_csv(cand)
            out = {"available": True, "rows": int(len(df)), "kept": int(len(df)), "skipped": {}, "charts": {},
                   "note": "Perov-5 training split (CDVAE), as used for the published model."}
            for col, lab, unit in (("heat_all", "Formation enthalpy", "eV/atom"), ("dir_gap", "Direct band gap", "eV")):
                out["charts"][col] = svg.histogram(df[col].values, lab, unit)
            return out
        from meidnet.pipeline import check
        info = check(self.cfg, write_report=False)
        rep = info["report"]
        out = {"available": True, "rows": rep.rows, "kept": rep.kept, "skipped": dict(rep.skipped),
               "examples": rep.examples, "charts": {}, "aligned": rep.aligned}
        recs = info["records"]
        for i, p in enumerate(self.cfg.data.properties):
            vals = np.array([r.properties[i] for r in recs]) if recs else np.array([])
            out["charts"][p.column] = svg.histogram(vals, p.display, p.unit or p.display)
        return out

    # ── family + design space ────────────────────────────────────────────────
    def _family_name(self, name: str | None) -> str:
        name = name or (self.cfg.generation.family if self.cfg.generation else "perovskite_abx3")
        if self.public and name not in list_families():
            raise ValueError(f"Only built-in families are available on this public server: {', '.join(list_families())}")
        return name

    def family(self, req: dict) -> dict:
        name = self._family_name(req.get("family"))
        key = json.dumps([name, req.get("variant")], sort_keys=True)
        with self.space_lock:
            if key in self.space_cache:
                return self.space_cache[key]
            fam = load_family(name, variant=req.get("variant"), default_variant=True)
            space = enumerate_space(fam, self.lm, max_compositions=int(req.get("max_compositions", 20000)))
            payload = {
                "name": fam.name, "title": fam.title, "variant": fam.variant, "describe": fam.describe(),
                "groups": {g: {"description": grp.description, "slots": grp.slots, "universe": grp.universe,
                               "elements": grp.elements, "sample": grp.sample,
                               "oxidation_states": grp.oxidation_states} for g, grp in fam.groups.items()},
                "sampling_order": fam.sampling_order, "lattice_rule": fam.lattice_rule, "lattice": fam.lattice,
                "constraints": fam.constraints, "search_terms": fam.search_terms,
                "sites": [{"group": g, "frac": list(f)} for g, f in fam.sites],
                "space": space,
            }
            self.space_cache[key] = payload
            return payload

    # ── search sessions ──────────────────────────────────────────────────────
    def _session(self, req: dict) -> str:
        s = str(req.get("session") or "local")
        if not SESSION_RE.match(s):
            raise ValueError("invalid session id")
        return s

    def _cleanup(self):
        now = time.time()
        with self.jobs_lock:
            for sid, job in list(self.jobs.items()):
                if job.done and job.finished and now - job.finished > JOB_TTL:
                    if job.run_dir and os.path.isdir(job.run_dir):
                        shutil.rmtree(job.run_dir, ignore_errors=True)
                    del self.jobs[sid]

    def _apply_limits(self, gen: dict) -> dict:
        if not self.public:
            return gen
        for k in ("per_target", "population", "rounds", "steps"):
            if k in gen:
                gen[k] = max(1, min(int(gen[k]), PUBLIC_LIMITS[k]))
        if "targets" in gen:
            gen["targets"] = gen["targets"][:PUBLIC_LIMITS["targets"]]
        gen.pop("plugins", None)
        gen["family"] = self._family_name(gen.get("family"))
        return gen

    def start_search(self, req: dict) -> dict:
        self._cleanup()
        sid = self._session(req)
        with self.jobs_lock:
            running = sum(1 for j in self.jobs.values() if j.running)
            old = self.jobs.get(sid)
            if old and old.running:
                return {"ok": False, "error": "your previous search is still running"}
            if running >= MAX_RUNNING:
                return {"ok": False, "error": f"{running} searches are running on this server right now - "
                                              "please try again in a minute", "busy": True}
            if old and old.run_dir and os.path.isdir(old.run_dir):
                shutil.rmtree(old.run_dir, ignore_errors=True)
            job = SearchJob(sid)
            job.running = True
            self.jobs[sid] = job
        gen = copy.deepcopy(self.cfg.generation.model_dump() if self.cfg.generation else {})
        gen.update(req.get("generation") or {})
        try:
            gen = self._apply_limits(gen)
            raw = dict(self.cfg.model_dump(mode="json"), generation=gen)
            if self.public:
                raw["plugins"] = []
            cfg = config_from_dict(raw, base_dir=self.cfg._base_dir)
        except Exception as e:
            with self.jobs_lock:
                self.jobs.pop(sid, None)
            return {"ok": False, "error": str(e)}
        cfg.model_path = self.cfg.checkpoint_path
        run_dir = os.path.join(self.run_root, f"{time.strftime('%Y%m%d_%H%M%S')}_{sid[:12]}_{secrets.token_hex(3)}")
        job.run_dir = run_dir
        threading.Thread(target=self._run_search, args=(job, cfg, run_dir), daemon=True).start()
        return {"ok": True, "run_dir": os.path.relpath(run_dir, self.run_root)}

    def _run_search(self, job: SearchJob, cfg, run_dir):
        try:
            from meidnet.generate import Designer
            from meidnet.pipeline import family_for
            from meidnet.report import generation_report
            from meidnet.train import pick_device
            fam = family_for(cfg, need_variant=True)
            device = pick_device(cfg.training.device)
            lm = self.lm if str(self.lm.device) == str(device) else load_checkpoint(cfg.checkpoint_path, device=device)
            g = cfg.generation
            job.progress.update({"targets": len(g.targets), "rounds": g.rounds, "steps": g.steps})

            def log(*a):
                msg = " ".join(str(x) for x in a)
                with job.lock:
                    job.log.append(msg)
                    if msg.startswith("=== target"):
                        job.progress["target"] += 1
                        job.progress["round"] = 0

            def on_step(step, steps, loss):
                with job.lock:
                    job.progress.update({"step": step, "steps": steps, "loss": loss})
                    if step == 0:
                        job.progress["round"] += 1

            def on_saved(c, tlog):
                with job.lock:
                    d = c.to_dict()
                    d["target_values"] = tlog.values
                    job.candidates.append(d)

            res = Designer(lm, fam, g, device=device, log=log, on_saved=on_saved, on_step=on_step,
                           should_stop=lambda: job.stop_flag).run(os.path.join(run_dir, "generation"),
                                                                   ranges=self.ranges)
            with open(os.path.join(run_dir, "meidnet.yaml"), "w", encoding="utf-8") as f:
                f.write(dump_config(cfg))
            rep = generation_report(cfg, lm, fam, res, os.path.join(run_dir, "generation_report.html"))
            with job.lock:
                job.report = os.path.relpath(rep, self.run_root).replace(os.sep, "/")
        except Exception:
            with job.lock:
                job.error = traceback.format_exc() if not self.public else "the search failed - see the server log"
                print(traceback.format_exc())
        finally:
            with job.lock:
                job.running = False
                job.done = True
                job.finished = time.time()

    def status(self, session: str) -> dict:
        job = self.jobs.get(session)
        if job is None:
            return {"running": False, "done": False, "error": None, "log": [], "candidates": [],
                    "progress": {"target": 0, "targets": 0, "round": 0, "rounds": 0, "step": 0, "steps": 0, "loss": None},
                    "report": None, "seconds": 0}
        return job.snapshot()

    def stop(self, session: str) -> None:
        job = self.jobs.get(session)
        if job:
            job.stop_flag = True

    def export(self, req: dict) -> str:
        gen = copy.deepcopy(self.cfg.generation.model_dump() if self.cfg.generation else {})
        gen.update(req.get("generation") or {})
        raw = dict(self.cfg.model_dump(mode="json"), generation=gen)
        if self.public:
            raw["model_path"] = "<path to the model file>"
            raw["output_dir"] = "runs/{name}"
            raw["plugins"] = []
        cfg = config_from_dict(raw, base_dir=self.cfg._base_dir)
        return dump_config(cfg)

    # ── files ────────────────────────────────────────────────────────────────
    def resolve_file(self, rel: str) -> str | None:
        """A run file (CIF, report) under run_root, or a docs file under docs_dir."""
        rel = unquote(rel).replace("\\", "/")
        if rel.startswith("docs/"):
            if not self.docs_dir:
                return None
            root, sub = self.docs_dir, rel[len("docs/"):]
            full = os.path.abspath(os.path.join(root, sub))
            if os.path.isdir(full):
                full = os.path.join(full, "index.html")
        else:
            root = self.run_root
            full = os.path.abspath(os.path.join(root, rel))
        if not full.startswith(os.path.abspath(root) + os.sep) and full != os.path.abspath(root):
            return None
        return full if os.path.isfile(full) else None


# ───────────────────────── HTTP plumbing ─────────────────────────
class Handler(BaseHTTPRequestHandler):
    studio: Studio = None

    def log_message(self, fmt, *args):  # quiet
        pass

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, default=float).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text") or "json" in ctype else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if ctype == "application/json" else "max-age=300")
        self.end_headers()
        self.wfile.write(body)

    def _json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 1_000_000:
            raise ValueError("request too large")
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def _file(self, rel):
        full = self.studio.resolve_file(rel)
        if not full:
            return self._send(404, "not found", "text/plain")
        ctype = mimetypes.guess_type(full)[0] or ("text/plain" if full.endswith((".cif", ".yaml", ".log", ".csv")) else "application/octet-stream")
        with open(full, "rb") as f:
            return self._send(200, f.read(), ctype)

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        s = self.studio
        try:
            if path in ("/", "/index.html"):
                with open(os.path.join(HERE, "studio.html"), "r", encoding="utf-8") as f:
                    return self._send(200, f.read(), "text/html")
            if path == "/api/state":
                return self._send(200, s.state())
            if path == "/api/data":
                return self._send(200, s.data())
            if path == "/api/search/status":
                sid = (parse_qs(u.query).get("session") or ["local"])[0]
                return self._send(200, s.status(sid))
            if path == "/docs":
                self.send_response(302)
                self.send_header("Location", "/docs/")
                self.end_headers()
                return
            if path.startswith("/docs/"):
                return self._file("docs/" + path[len("/docs/"):])
            if path.startswith("/files/"):
                return self._file(path[len("/files/"):])
            return self._send(404, {"error": "not found"})
        except Exception:
            return self._send(500, {"error": traceback.format_exc() if not s.public else "server error"})

    def do_POST(self):
        path = urlparse(self.path).path
        s = self.studio
        try:
            req = self._json()
            if path == "/api/family":
                return self._send(200, s.family(req))
            if path == "/api/search/start":
                return self._send(200, s.start_search(req))
            if path == "/api/search/stop":
                s.stop(s._session(req))
                return self._send(200, {"ok": True})
            if path == "/api/export":
                return self._send(200, s.export(req), "text/plain")
            return self._send(404, {"error": "not found"})
        except ValueError as e:
            return self._send(400, {"error": str(e)})
        except Exception:
            return self._send(500, {"error": traceback.format_exc() if not s.public else "server error"})


def export_static(cfg: MEIDNetConfig | None, out_path: str, model_path: str | None = None,
                  variants: list[tuple[str, str]] | None = None) -> str:
    """
    Write a self-contained copy of the Studio page with the state, data summary and
    design spaces embedded, so it works on a plain web host (no Python).  Searching is
    disabled in that copy; everything else behaves like the live Studio.
    """
    studio = Studio(cfg, model_path)
    variants = variants or [("perovskite_abx3", v) for v in ("halide", "oxide", "chalcogenide", "nitride")]
    fams = {}
    for name, var in variants:
        print(f"enumerating {name}/{var} ...")
        fams[f"{name}|{var}"] = studio.family({"family": name, "variant": var})
    payload = {"state": studio.state(), "data": studio.data(), "families": fams}
    with open(os.path.join(HERE, "studio.html"), "r", encoding="utf-8") as f:
        html = f.read()
    inject = "<script>window.MEIDNET_STATIC = " + json.dumps(payload, default=float) + ";</script>\n<script>"
    html = html.replace("<script>", inject, 1)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {out_path} ({os.path.getsize(out_path) / 1e6:.1f} MB)")
    return out_path


def warm_up(studio: Studio, variants=None):
    """Pre-compute the design spaces so the first visitor does not wait."""
    variants = variants or [("perovskite_abx3", v) for v in ("halide", "oxide", "chalcogenide", "nitride")]
    for name, var in variants:
        try:
            studio.family({"family": name, "variant": var})
        except Exception as e:  # pragma: no cover
            print(f"warm-up {name}/{var} failed: {e}")
    studio.data()


def serve(cfg: MEIDNetConfig | None, model_path: str | None = None, port: int = 8765, open_browser: bool = True,
          host: str = "127.0.0.1", public: bool = False, run_root: str | None = None, docs_dir: str | None = None):
    Handler.studio = Studio(cfg, model_path, public=public, run_root=run_root, docs_dir=docs_dir)
    if public:
        threading.Thread(target=warm_up, args=(Handler.studio,), daemon=True).start()
    httpd = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{'127.0.0.1' if host in ('0.0.0.0', '') else host}:{port}/"
    print(f"MEIDNet Studio {'(public mode) ' if public else ''}running at {url}  (Ctrl+C to stop)", flush=True)
    if open_browser and not public:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()


def main(argv=None):
    p = argparse.ArgumentParser(description="MEIDNet Studio server")
    p.add_argument("config", nargs="?", default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--public", action="store_true", help="multi-user mode with capped budgets (hosting)")
    p.add_argument("--run-root", default=None, help="where search outputs are written")
    p.add_argument("--docs-dir", default=None, help="serve this folder (a built MkDocs site) at /docs/")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args(argv)
    cfg = None
    if a.config:
        from meidnet.config import load_config
        cfg = load_config(a.config)
    serve(cfg, model_path=a.model, port=a.port, open_browser=not a.no_open, host=a.host, public=a.public,
          run_root=a.run_root, docs_dir=a.docs_dir)


if __name__ == "__main__":
    main()
