# microtranslate

English → **neutral Latin American Spanish**, running entirely in your browser.
Speech in, speech out, no server, no API key, no account.

**→ [Open it](https://adityakasal.github.io/microtranslate/)**

## How it works

| Stage | Model | Size | Where |
|---|---|---|---|
| Speech → English | `whisper-tiny.en` int8 | ~40 MB | in-browser (WASM) |
| English → Spanish | `opus-mt-en-es` int8 | ~119 MB | in-browser (WASM) |
| Register correction | `neutro.js` | 11 KB | in-browser (regex) |
| Spanish → speech | OS voice | 0 | built into the browser |

Both models download once, are cached by the browser, and the page then works
offline. The speech model is only fetched the first time you use the
microphone. Nothing you type or say ever leaves your device.

## The register layer

Off-the-shelf English→Spanish models produce *mixed* Spanish — on a 19-word
probe set, 15 outputs came back in European forms (`ordenador`, `nevera`,
`fontanero`, `aparcar el coche`) while others were already Latin American.
`neutro.js` rewrites the output into *español neutro*, the pan-regional
register used for Latin American dubbing.

It is not a find-and-replace. Many substitutions flip grammatical gender, so
the determiner and any agreeing adjective have to move with the noun:

```
el ordenador          → la computadora
los ordenadores nuevos → las computadoras nuevas
unas gafas oscuras     → unos lentes oscuros
Mi portátil es ligero  → Mi laptop es ligera
¿Tenéis vuestras...?   → ¿Tienen sus...?
```

It is also careful about what it must *not* touch: `país` is not a verb,
`sed` is thirst, `usted` is not an imperative, `conducir a` means *lead to*,
and `coche bomba` is a fixed term. Highlighted words in the UI show every edit,
with the model's original wording on hover.

Measured: register accuracy 10/28 → 28/28, at a cost of 0.02 BLEU on
FLORES-200 — statistical noise.

## Latency

Measured end to end on an 11-second clip: **1.3 s** (transcribe 1020 ms,
translate 254 ms).

Zero latency is not reachable, for linguistic rather than computational
reasons — a clause cannot be translated before it has been spoken, which is
why human simultaneous interpreters also run a few seconds behind. Instead of
waiting for a stop button, the page cuts audio at natural pauses and
translates each clause as it completes, trailing the speaker by roughly
1.5–2 s. Running on-device is what keeps that competitive: there is no network
round trip in the loop.

## The rest of the project

`engine/` holds everything behind the page: the quantization pipeline, the
Python implementation of the register layer, the evaluation harness and the
measurements.

```
engine/scripts/neutro.py      the register layer (source of truth)
engine/scripts/engine.py      CTranslate2 inference, no torch at runtime
engine/scripts/bench.py       FLORES-200 BLEU/chrF + throughput
engine/scripts/probe.py       register accuracy on 28 targeted probes
engine/scripts/test_safety.py 30 false-positive regression tests
engine/scripts/crosscheck.py  asserts neutro.js == neutro.py
engine/data/lexicon.json      substitutions, with exclusions documented
engine/notes/register.md      what the layer does, and what it refuses to do
engine/notes/deploy.md        getting this onto Android and iOS
```

The desktop build uses a larger model than the web page can afford —
`opus-mt-tc-big-en-es`, 240 MB at int8, BLEU 28.29 against the web build's
26.38.

| Build | Size | BLEU | Register probe |
|---|---|---|---|
| tc-big int8 + neutro | 240 MB | **28.29** | 28/28 |
| tc-big int8, raw | 240 MB | 28.31 | 10/28 |
| small int8 + neutro (this page) | 83 MB | 26.38 | 28/28 |

## Tests

No model weights, no network, a few seconds:

```bash
cd engine && ./run_tests.sh
```

Three things get checked: 30 strings that must survive the layer untouched
(`ciudad`, `verdad`, `usted`, `recoger`, `piso`), the rewrites themselves, and
that the JavaScript port matches the Python byte-for-byte across 2,096
strings. Every one of those regressions came from benchmarking on real text —
an early `-ís` rule turned `país` into `paen` and `París` into `Paren`, and
`sed` (thirst) into `sean`.

The heavier benchmarks need the model and FLORES-200:

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/fetch_base.py
.venv/bin/ct2-transformers-converter --model Helsinki-NLP/opus-mt-tc-big-en-es \
  --output_dir models/ct2-en-es-int8 --quantization int8
.venv/bin/python scripts/bench.py        # BLEU, chrF, throughput
.venv/bin/python scripts/probe.py        # register accuracy
```

## Running it elsewhere

Two static files. Any static host works, with two requirements: **HTTPS**
(or the browser will not grant microphone access — `localhost` is exempt), and
the host must not block `huggingface.co`, where the model weights come from.

## Credits

[OPUS-MT](https://huggingface.co/Helsinki-NLP) (Helsinki-NLP) and
[Whisper](https://openai.com/research/whisper), run in-browser by
[Transformers.js](https://huggingface.co/docs/transformers.js).
