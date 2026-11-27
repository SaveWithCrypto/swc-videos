"""Generate per-scene voiceover + caption timings. Usage: python3 tts.py <workdir> [voice]
Reads <workdir>/narration.json: [[scene, text], ...] for scenes intro, price, pressure, oi, etf, levels, outro.
Text may contain {display|spoken} pairs: the caption shows "display", the voice says "spoken".
Writes a_<scene>.wav, durations.json and captions.json. Downloads the Kokoro model from GitHub on first use.
"""
import json, sys, os, re, subprocess
import numpy as np, soundfile as sf

M = os.path.expanduser("~/.cache/kokoro"); os.makedirs(M, exist_ok=True)
BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
for fn, url in [("kokoro.onnx", "kokoro-v1.0.onnx"), ("voices.bin", "voices-v1.0.bin")]:
    if not os.path.exists(f"{M}/{fn}"):
        subprocess.run(["curl", "-sL", "-m", "600", "-o", f"{M}/{fn}", BASE + url], check=True)
from kokoro_onnx import Kokoro

PAIR = re.compile(r"\{([^|{}]*)\|([^{}]*)\}")
MAXC = 58  # max caption characters per line


def chunks(text):
    """Split into caption-sized pieces at sentence ends, then commas, then words (never inside {a|b})."""
    # protect pairs so splitting can't break them
    pairs = []
    def _p(m):
        pairs.append((m.group(1), m.group(2).replace(" ", "\x01"))); return f"\x00{len(pairs) - 1}\x00"
    prot = PAIR.sub(_p, text)
    disp = lambda s: re.sub(r"\x00(\d+)\x00", lambda m: pairs[int(m.group(1))][0], s)
    out = []
    for sent in re.split(r"(?<=[.!?])\s+", prot.strip()):
        parts = re.split(r"(?<=,)\s+", sent)
        buf = ""
        for p in parts:
            cand = (buf + " " + p).strip()
            if buf and len(disp(cand)) > MAXC:
                out.append(buf); buf = p
            else:
                buf = cand
        if buf: out.append(buf)
    final = []
    for c in out:  # hard-wrap anything still too long, at word boundaries
        words = c.split(" "); cur = ""
        for w in words:
            cand = (cur + " " + w).strip()
            if cur and len(disp(cand)) > MAXC: final.append(cur); cur = w
            else: cur = cand
        if cur: final.append(cur)
    res = []
    for c in final:
        d = re.sub(r"\x00(\d+)\x00", lambda m: pairs[int(m.group(1))][0], c)
        s = re.sub(r"\x00(\d+)\x00", lambda m: pairs[int(m.group(1))][1], c).replace("\x01", " ")
        res.append((d, s))
    return res


k = Kokoro(f"{M}/kokoro.onnx", f"{M}/voices.bin")
wd = sys.argv[1]; voice = sys.argv[2] if len(sys.argv) > 2 else "bf_emma"
speed = float(os.environ.get("TTS_SPEED", "1.0"))
dur, caps = {}, {}
for name, text in json.load(open(f"{wd}/narration.json")):
    audio, t, caps[name] = [], 0.0, []
    for d, s in chunks(text):
        a, sr = k.create(s, voice=voice, speed=speed, lang="en-gb" if voice.startswith("b") else "en-us")
        # trim leading/trailing near-silence, then add a natural pause
        nz = np.where(np.abs(a) > 0.01)[0]
        if len(nz): a = a[max(0, nz[0] - int(0.03 * sr)): nz[-1] + int(0.06 * sr)]
        gap = 0.32 if d.rstrip().endswith((".", "!", "?")) else 0.14
        caps[name].append([round(t, 3), round(t + len(a) / sr, 3), d])
        audio += [a.astype(np.float32), np.zeros(int(gap * sr), np.float32)]
        t += len(a) / sr + gap
    full = np.concatenate(audio)
    sf.write(f"{wd}/a_{name}.wav", full, sr); dur[name] = len(full) / sr
json.dump(dur, open(f"{wd}/durations.json", "w"))
json.dump(caps, open(f"{wd}/captions.json", "w"), indent=0, ensure_ascii=False)
print({k_: round(v, 1) for k_, v in dur.items()})
