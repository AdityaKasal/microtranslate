import os, pathlib
os.environ.setdefault("HF_HOME", str(pathlib.Path(__file__).resolve().parents[1] / "models" / "hf"))
from huggingface_hub import snapshot_download

MODEL = "Helsinki-NLP/opus-mt-tc-big-en-es"
p = snapshot_download(MODEL, allow_patterns=["*.json","*.spm","*.txt","*.bin","*.safetensors","*.model"])
print("downloaded to:", p)
tot = sum(f.stat().st_size for f in pathlib.Path(p).rglob("*") if f.is_file())
print(f"size: {tot/1e6:.1f} MB")
