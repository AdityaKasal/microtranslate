# Getting this onto a handset

Everything below the dashed line was measured on this laptop. The mobile
packaging options were researched, **not built or benchmarked here** — treat
the effort estimates as estimates.

## What actually has to ship

| Piece | Size | Notes |
|---|---|---|
| `model.bin` (int8) | 236 MB | or 79 MB for the small build |
| `source.spm` / `target.spm` | ~1.6 MB | sentencepiece vocabularies |
| `shared_vocabulary.json` | 1 MB | |
| inference runtime | 2–6 MB | CTranslate2 compiled for arm64 |
| `lexicon.json` + neutro logic | ~8 KB | pure string work, no dependencies |

**240 MB total** for the quality build, delivered as a post-install download
rather than inside the APK/IPA.

`scripts/engine.py` deliberately imports only `ctranslate2` and
`sentencepiece`. torch and transformers are build-time tools for quantization
and evaluation; neither goes near the device.

## Two runtime paths

**CTranslate2 — best size and speed, more build work.**
CTranslate2 supports AArch64/ARM64, but
[there is no official Android build](https://github.com/OpenNMT/CTranslate2/issues/1683),
and [prebuilt Android wheels were still only a request as of September 2026](https://github.com/OpenNMT/CTranslate2/issues/2105).
You cross-compile it yourself: Android NDK + CMake for `arm64-v8a`, or an
`xcframework` for iOS, then a JNI or Swift bridge. sentencepiece needs the same
treatment — it has a C++ library and existing mobile bindings.

[Kevin-KIM98/offline-translator](https://github.com/Kevin-KIM98/offline-translator)
is a working reference doing exactly this combination — CTranslate2 with
OPUS-MT int8, C++ core, Android and iOS bridges — and is the fastest way to
see the shape of the build.

**ONNX Runtime Mobile — more size and latency, much less build work.**
Official Android (Maven) and iOS (CocoaPods) packages with Java and Swift
APIs, so no NDK toolchain to assemble. Export the Marian checkpoint via
`optimum`. Expect a larger artifact and slower decoding than CTranslate2 for
an encoder–decoder model. **Unverified here** — worth an afternoon's spike
before committing either way.

Recommendation: if this is a product on a deadline, spike ONNX Runtime Mobile
first, because the toolchain risk is near zero. Move to CTranslate2 when size
or battery becomes the binding constraint.

## The register layer ports for free

`neutro.py` is regex and dictionary lookups — no model, no tensors, no
dependencies. It is a direct transliteration to Kotlin or Swift, and
`data/lexicon.json` loads as-is. At 0.58 ms per sentence on a laptop it stays
irrelevant to latency on a phone.

Keep it as data, not code: the lexicon will need entries added after real
listeners hear real output, and that should not require a release.

---

## Measured headroom

Speech is roughly 15 characters per second. This model does 480 chars/s
single-threaded on an M5 Pro — about 32× real time. A phone core several times
slower still clears real time by a wide margin, which is the whole reason
on-device is viable for this language pair.

For live use, run greedy (`--beam 1`): 32 ms per sentence versus 87 ms at
beam 4, for a small quality cost that matters far less than latency when
someone is listening live.

## Where the quality ceiling is

The int8 quantization is not the limit — it costs very little against fp32.
The limit is the 230M-parameter base model. To go further:

1. **Fine-tune on neutral Latin American text.** This bakes the register into
   the weights instead of patching the output, and fixes what regex cannot
   reach (word order, idiom, the `os` → `les`/`los` choice). Distillation
   works well here: translate a large English corpus with a strong model,
   then train this one on the result.
2. **Domain-adapt.** For a specific setting — a church service, a classroom,
   a clinic — a few thousand in-domain sentence pairs buys more than any
   general model upgrade.

Both need GPU hours. The PC was unreachable while this was built, so neither
was attempted; the Mac's battery is the wrong place to run them.
