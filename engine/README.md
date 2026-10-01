# microtranslate — English → neutral Latin American Spanish, on a phone

A 240 MB translation model that runs offline on a handset, plus a rewriting
layer that forces output into **español neutro** (the pan-regional register
used for Latin American dubbing) rather than the European Spanish the base
model drifts toward.

Built on `Helsinki-NLP/opus-mt-tc-big-en-es` (Marian, ~230M params), quantized
to int8 with CTranslate2.

## Why not a general-purpose small LLM

For a single language pair, a dedicated encoder–decoder NMT model beats a
general decoder LLM at a fraction of the size. This model is 240 MB and scores
BLEU 28.3 on FLORES-200; a general 1–3B model would be 4–12× larger, slower,
and no better at this one job. TranslateGemma starts at 4B.

## Results (FLORES-200 devtest, en→es, 1012 sentences)

| Build | Size | BLEU | chrF2 | Register probe |
|---|---|---|---|---|
| tc-big int8 + neutro | **240 MB** | **28.29** | 56.40 | **28/28** |
| tc-big int8, raw | 240 MB | 28.31 | 56.42 | 10/28 |
| small int8 + neutro | **83 MB** | 26.38 | 54.97 | 28/28 |

The register layer costs **0.02 BLEU** — statistical noise — while taking the
Latin American register probe from 10/28 to 28/28. It changes 1.2% of FLORES
outputs and runs in **0.58 ms per sentence**, negligible beside ~60 ms of
translation.

Two metrics are reported because BLEU *cannot* measure what the layer does:
the FLORES Spanish reference is itself partly European (it contains
`conducir`, `portátil`, `móvil`, `ordenador`, `patata`, `billete`), so
correcting those words is scored as an error. BLEU is here to prove the layer
does no damage; the probe set is what measures register.

## Speed (M5 Pro, int8, beam 4)

| Threads | sent/s | src chars/s | ms/sentence |
|---|---|---|---|
| 1 | 3.5 | 480 | 285 |
| 2 | 6.7 | 916 | 149 |
| 4 | 11.5 | 1,574 | 87 |
| 8 | 17.3 | 2,368 | 58 |
| 4, greedy | 31.5 | 4,315 | 32 |

Speech runs at roughly **15 characters per second**. Even single-threaded this
is ~32× faster than real time, so live use is not compute-bound — the headroom
absorbs a phone being several times slower than this laptop.

## Browser build (no server, with audio)

`webapp/` is a two-file static site that runs the whole pipeline client-side:
speech in via Whisper, translation via OPUS-MT, the register layer, and speech
out via the OS voice. Both models are fetched once and cached; after that it
works offline. Measured 1.3 s end to end on an 11-second clip. See
[webapp/README.md](webapp/README.md).

## Local web UI (Python backend)

```bash
.venv/bin/uvicorn scripts.server:app --port 8732
```

Then open <http://localhost:8732>. The page shows the register layer rather
than hiding it: edited words are highlighted with the model's original wording
on hover, every substitution is listed as a `before → after` pair, and a
toggle flips the output panel between raw and rewritten so the difference is
visible side by side. Model, decoding strategy, latency, throughput and model
size are all live. Four preset examples load vocabulary that actually exercises
the differences — including a *false friends* set that demonstrates the cases
the layer must **not** touch (`país`, `París`, `sed`, `conducir a`,
`coche bomba`).

Runs entirely locally; no text leaves the machine.

## CLI

```bash
./.venv/bin/python scripts/translate.py "Where did you all park the car?"
# ¿Dónde estacionaron el auto?

echo "Listen, all of you. Come here and pray with me." \
  | ./.venv/bin/python scripts/translate.py
# Escuchen, vengan aquí y oren conmigo.

./.venv/bin/python scripts/translate.py --model small --beam 1 "..."
```

## Layout

```
scripts/engine.py       CTranslate2 + sentencepiece inference (no torch)
scripts/neutro.py       the español neutro rewriting layer
scripts/translate.py    CLI
scripts/bench.py        FLORES BLEU/chrF + throughput
scripts/bench_subset.py splits BLEU by reference register
scripts/probe.py        register accuracy on 28 targeted probes
scripts/test_safety.py  30 false-positive regression tests
data/lexicon.json       substitutions, with exclusions documented
data/register_probes.tsv
notes/register.md       what the layer does, and what it deliberately will not
notes/deploy.md         getting this onto Android and iOS
```

`engine.py` imports only `ctranslate2` and `sentencepiece` — that is the exact
code path that ports to a handset. torch and transformers are build-time only.
