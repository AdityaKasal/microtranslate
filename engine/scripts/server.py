"""Local web UI for the en -> neutral Latin American Spanish model.

Returns both the raw model output and the neutro-rewritten output, plus a
word-level diff, so the register layer is visible rather than invisible.
"""
from __future__ import annotations
import difflib, pathlib, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from engine import Engine
from neutro import to_neutro

ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
MODELS = {"big": ROOT / "models" / "ct2-en-es-int8",
          "small": ROOT / "models" / "ct2-en-es-small-int8"}
_loaded: dict[str, Engine] = {}


def get_engine(name: str) -> Engine:
    if name not in _loaded:
        _loaded[name] = Engine(model_dir=MODELS[name], threads=4)
    return _loaded[name]


def segments(raw: str, neu: str):
    """Word-level diff -> [{text, changed}] over the neutro output."""
    a, b = raw.split(), neu.split()
    sm = difflib.SequenceMatcher(None, a, b)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.append({"text": " ".join(b[j1:j2]), "changed": False,
                        "was": None})
        elif tag in ("replace", "insert"):
            out.append({"text": " ".join(b[j1:j2]), "changed": True,
                        "was": " ".join(a[i1:i2]) or None})
    return [s for s in out if s["text"]]


class Req(BaseModel):
    text: str
    model: str = "big"
    beam: int = 4


app = FastAPI(title="microtranslate")


@app.post("/api/translate")
def translate(r: Req):
    lines = [l for l in r.text.splitlines() if l.strip()] or [""]
    eng = get_engine(r.model if r.model in MODELS else "big")
    t0 = time.perf_counter()
    raw = eng.translate(lines, beam_size=max(1, min(r.beam, 8)))
    ms = (time.perf_counter() - t0) * 1000
    neu = [to_neutro(h) for h in raw]
    src_chars = sum(len(l) for l in lines)
    return {
        "lines": [
            {"src": s, "raw": a, "neutro": b, "segments": segments(a, b)}
            for s, a, b in zip(lines, raw, neu)
        ],
        "ms": round(ms, 1),
        "ms_per_sentence": round(ms / len(lines), 1),
        "chars_per_s": round(src_chars / (ms / 1000)) if ms else 0,
        "changed": sum(1 for a, b in zip(raw, neu) if a != b),
        "sentences": len(lines),
        "model": r.model,
        "beam": r.beam,
    }


@app.get("/api/meta")
def meta():
    def size(p):
        return round(sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6)
    return {
        "models": [
            {"id": "big", "label": "tc-big", "mb": size(MODELS["big"]),
             "bleu": 28.29, "params": "230M"},
            {"id": "small", "label": "small", "mb": size(MODELS["small"]),
             "bleu": 26.38, "params": "74M"},
        ]
    }


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/app", StaticFiles(directory=ROOT.parent, html=True), name="webapp")
app.mount("/static", StaticFiles(directory=WEB), name="static")
