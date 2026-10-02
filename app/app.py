"""
MEIDNet demo for Hugging Face Spaces (Gradio, free CPU).

Two tabs:
  • Generate — pick a perovskite family and targets; the published model runs a short latent
    search and shows candidates with their rule checklist, predictions and CIF downloads.
  • Explore (Studio) — the static MEIDNet Studio: every composition of four families scored by
    the model; move rule limits and targets and watch what passes (no compute needed).

For real work use `meidnet generate` / `meidnet studio` locally: https://babu09-meidnet.hf.space/docs/
"""
import os
import sys
import tempfile

import gradio as gr
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # the Space ships its own copy of the meidnet package

from meidnet.checkpoint import load_checkpoint, property_ranges  # noqa: E402
from meidnet.cli import published_checkpoint  # noqa: E402
from meidnet.config import GenerationSection  # noqa: E402
from meidnet.constraints import explain  # noqa: E402
from meidnet.family import load_family  # noqa: E402
from meidnet.generate import Designer  # noqa: E402

torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
os.chdir(HERE)
LM = load_checkpoint(published_checkpoint())
RANGES = property_ranges(LM)
STUDIO_HTML = os.path.join(HERE, "studio.html")


def run(family, band_gap, enthalpy, n, rounds, exclude, progress=gr.Progress()):
    exclude = [e.strip() for e in exclude.split(",") if e.strip()]
    try:
        fam = load_family("perovskite_abx3", variant=family, exclude=exclude or None)
    except Exception as e:
        return f"**Could not build the family:** {e}", [], ""
    g = GenerationSection(
        family="perovskite_abx3", variant=family,
        objectives=[{"property": "dir_gap", "loss": "l2", "weight": 10000, "select_weight": 1.0},
                    {"property": "heat_all", "loss": "l1", "weight": 6000, "select_weight": 0.4}],
        targets=[{"dir_gap": float(band_gap), "heat_all": float(enthalpy)}],
        per_target=int(n), population=16, rounds=int(rounds), steps=150, min_cosine_sep=0.98,
        exclude_elements=exclude,
    )
    out = tempfile.mkdtemp(prefix="meidnet_")
    log = []
    state = {"round": 0}

    def on_step(step, steps, loss):
        if step == 0:
            state["round"] += 1
        progress((state["round"] - 1 + step / steps) / int(rounds), desc=f"round {state['round']}/{int(rounds)}")

    res = Designer(LM, fam, g, log=lambda *a: log.append(" ".join(map(str, a))), on_step=on_step).run(out, ranges=RANGES)
    t = res.targets[0]
    md = [f"**{len(t.saved)} candidate(s)** from {t.attempts:,} element choices in {t.rounds_used} round(s). "
          f"Predicted values are the model's estimates — confirm with DFT or experiment."]
    files = []
    for c in t.saved:
        md.append(f"### {c.formula}  \n" + "  ".join(f"{g_}={e}" for g_, e in c.elements.items())
                  + f"  ·  a = {c.lattice_a:.3f} Å  \n"
                  f"predicted band gap **{c.predictions['dir_gap']:.2f} eV** (target {band_gap}), "
                  f"enthalpy **{c.predictions['heat_all']:.2f} eV/atom** (target {enthalpy})")
        for r in c.constraint_results:
            title, _ = explain(r["name"], fam.constraint_params(r["name"]) or {})
            val = f" = {r['value']:.3g}" if r["value"] is not None and r["name"] != "charge_neutrality" else ""
            md.append(f"- ✅ {title}{val}" + (f" — {r['detail']}" if r["name"] == "charge_neutrality" else ""))
        for f in c.flags:
            md.append(f"- ⚠️ {f}")
        files.append(os.path.join(out, c.file))
    if not t.saved:
        md.append("No composition passed every rule. Try more rounds, another family, or a target inside the "
                  f"training range (band gap {RANGES['dir_gap'][0]:.1f}–{RANGES['dir_gap'][1]:.1f} eV).")
    funnel = "\n".join(f"- {k}: {v}" for k, v in t.first_failure.most_common())
    return "\n".join(md), files, f"Rejections by first failing rule:\n{funnel}\n\n" + "\n".join(log[-25:])


with gr.Blocks(title="MEIDNet") as demo:
    gr.Markdown("# MEIDNet — inverse design of crystalline materials\n"
                "Property-conditioned generation in a structure–property latent space, constrained by the physical "
                "rules of a material family. Published model: cubic ABX₃ perovskites (Perov-5). "
                "[Documentation](https://babu09-meidnet.hf.space/docs/) · [Code](https://github.com/ABnano/MEIDNet) · "
                "[Paper](https://www.nature.com/articles/s41524-026-02153-3)")
    with gr.Tabs():
        with gr.Tab("Generate"):
            with gr.Row():
                with gr.Column():
                    family = gr.Dropdown(["halide", "oxide", "chalcogenide", "nitride"], value="halide", label="Family")
                    bg = gr.Slider(0.0, 8.0, value=2.0, step=0.05, label="Target band gap (eV)")
                    ent = gr.Slider(-1.0, 5.0, value=-0.1, step=0.05, label="Target formation enthalpy (eV/atom)")
                    n = gr.Slider(1, 5, value=3, step=1, label="Candidates")
                    rounds = gr.Slider(1, 6, value=3, step=1, label="Search rounds (more = slower, more diverse)")
                    exclude = gr.Textbox("", label="Exclude elements (comma-separated), e.g. Pb, Cd")
                    btn = gr.Button("Generate", variant="primary")
                    gr.Markdown("A 3-round search takes about a minute on this free CPU.")
                with gr.Column():
                    out_md = gr.Markdown()
                    out_files = gr.File(label="CIF files", file_count="multiple")
                    out_log = gr.Textbox(label="Search log", lines=10)
            btn.click(run, [family, bg, ent, n, rounds, exclude], [out_md, out_files, out_log])
        with gr.Tab("Explore (Studio)"):
            if os.path.exists(STUDIO_HTML):
                gr.Markdown("The design space of four perovskite families as the model sees it. Click a node, move a "
                            "rule limit or a target; counts and rankings update instantly. "
                            "[Open full-screen](/studio)")
                gr.HTML('<iframe src="/studio" style="width:100%;height:85vh;border:1px solid #ddd;border-radius:8px"></iframe>')
            else:
                gr.Markdown("Static Studio not bundled with this Space.")


if __name__ == "__main__":
    from fastapi import FastAPI
    from fastapi.responses import FileResponse
    import uvicorn

    app = FastAPI()

    @app.get("/studio")
    def studio():
        return FileResponse(STUDIO_HTML, media_type="text/html")

    app = gr.mount_gradio_app(app, demo, path="/")
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
