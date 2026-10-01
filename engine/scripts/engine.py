"""en -> Latin American Spanish translation engine.

CTranslate2 + sentencepiece only. No torch, no transformers: this is the exact
code path that ports to a phone.
"""
from __future__ import annotations
import pathlib
import ctranslate2
import sentencepiece as spm

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "models" / "ct2-en-es-int8"


class Engine:
    def __init__(self, model_dir=DEFAULT_MODEL, device="cpu", threads=4,
                 compute_type="default"):
        model_dir = pathlib.Path(model_dir)
        self.translator = ctranslate2.Translator(
            str(model_dir), device=device, inter_threads=1,
            intra_threads=threads, compute_type=compute_type,
        )
        self.sp_src = spm.SentencePieceProcessor(str(model_dir / "source.spm"))
        self.sp_tgt = spm.SentencePieceProcessor(str(model_dir / "target.spm"))

    def translate(self, texts, beam_size=4, max_decoding_length=512):
        if isinstance(texts, str):
            single, texts = True, [texts]
        else:
            single = False
        # Marian requires an explicit EOS on the source; without it the
        # decoder never terminates and output repeats.
        batch = [self.sp_src.encode(t, out_type=str) + ["</s>"] for t in texts]
        results = self.translator.translate_batch(
            batch, beam_size=beam_size, max_decoding_length=max_decoding_length,
            replace_unknowns=True,
        )
        out = [self.sp_tgt.decode(r.hypotheses[0]) for r in results]
        return out[0] if single else out


if __name__ == "__main__":
    import sys, time
    eng = Engine()
    probes = [
        "Good morning, and welcome to the service.",
        "Do you have your tickets? You all need to park the car first.",
        "She put the juice in the fridge next to the potatoes.",
        "I need to use the computer, but my cell phone works too.",
        "Please take a seat. We will begin in five minutes.",
        "The plumber is coming to the apartment on the third floor.",
    ]
    if len(sys.argv) > 1:
        probes = [" ".join(sys.argv[1:])]
    t0 = time.time()
    for src, tgt in zip(probes, eng.translate(probes)):
        print(f"EN  {src}\nES  {tgt}\n")
    print(f"[{len(probes)} sentences in {time.time()-t0:.2f}s]")
