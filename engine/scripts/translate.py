#!/usr/bin/env python3
"""en -> neutral Latin American Spanish.

  translate.py "Where did you park the car?"
  echo "..." | translate.py
  translate.py --model small --raw "text"      # smaller model, no register layer
"""
import argparse, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from engine import Engine
from neutro import to_neutro

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODELS = {"big": ROOT / "models" / "ct2-en-es-int8",
          "small": ROOT / "models" / "ct2-en-es-small-int8"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="*")
    ap.add_argument("--model", choices=MODELS, default="big")
    ap.add_argument("--raw", action="store_true", help="skip the neutro layer")
    ap.add_argument("--beam", type=int, default=4, help="1 = greedy, fastest")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args()

    lines = [" ".join(a.text)] if a.text else [
        l.rstrip("\n") for l in sys.stdin if l.strip()]
    if not lines:
        ap.error("no input")

    eng = Engine(model_dir=MODELS[a.model], threads=a.threads)
    out = eng.translate(lines, beam_size=a.beam)
    if not a.raw:
        out = [to_neutro(o) for o in out]
    print("\n".join(out))

if __name__ == "__main__":
    main()
