// Translation + speech worker. This must be a real same-origin file, not a
// blob: URL -- a blob worker is not controlled by the service worker, so
// everything it fetched (the library, the model weights) escaped the cache
// and the app could not work offline.
import { pipeline, env } from "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.7.6";
env.allowLocalModels = false;
let pipe = null, asr = null, asrName = "";
self.onmessage = async (e) => {
  const { type, payload } = e.data;
  if (type === "load") {
    try {
      pipe = await pipeline("translation", "Xenova/opus-mt-en-es", {
        dtype: "q8",
        progress_callback: (p) => self.postMessage({ type:"progress", payload:p }),
      });
      self.postMessage({ type:"ready", payload:{ device: pipe?.model?.device || "wasm" } });
    } catch (err) {
      self.postMessage({ type:"error", payload:String(err && err.message || err) });
    }
    return;
  }
  if (type === "loadAsr") {
    try {
      asrName = { fast:  "Xenova/whisper-base.en",
                  best:  "Xenova/whisper-small.en",
                  max:   "Xenova/whisper-medium.en"
                }[(payload && payload.size) || "best"] || "Xenova/whisper-small.en";
      asr = await pipeline("automatic-speech-recognition", asrName, {
        dtype: "q8",
        progress_callback: (p) => self.postMessage({ type:"progress", payload:p }),
      });
      self.postMessage({ type:"asrReady" });
    } catch (err) {
      self.postMessage({ type:"asrError", payload:String(err && err.message || err) });
    }
    return;
  }
  if (type === "transcribe") {
    try {
      const t0 = performance.now();
      const r = await asr(payload.audio, {
        chunk_length_s: 30, stride_length_s: 5,
        num_beams: asrName.includes("base") ? 2 : 4,   // beams buy accuracy
        condition_on_previous_text: false });
      self.postMessage({ type:"transcript",
        payload:{ id: payload.id, text:(r.text||"").trim(), ms: performance.now()-t0 } });
    } catch (err) {
      self.postMessage({ type:"asrError", payload:String(err && err.message || err) });
    }
    return;
  }
  if (type === "translate") {
    try {
      const t0 = performance.now();
      const res = await pipe(payload.lines, { max_new_tokens: 320,
        num_beams: payload.fast ? 1 : 4, do_sample: false });
      const ms = performance.now() - t0;
      const outs = (Array.isArray(res) ? res : [res]).map(r => r.translation_text);
      self.postMessage({ type:"result", payload:{ id:payload.id, outs, ms } });
    } catch (err) {
      self.postMessage({ type:"error", payload:String(err && err.message || err) });
    }
  }
};
