"""Vertical YouTube Short (1080x1920, ~30-45s). Usage: python3 short.py <workdir>
<workdir> needs data.json (same shape as the main video's, plus a "short" block, see README) and
narration.json with exactly three scenes: hook, chart, cta (run tts.py on it first).
Writes <workdir>/BTC_Short.mp4 and BTC_Short.srt
"""
import sys, os, json, subprocess
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R  # reuses fonts, colours, logo and drawing helpers (reads the same workdir)
import skia

WD = sys.argv[1]
W, H, FPS = 1080, 1920, 30
D, DUR, CAPS = R.D, R.DUR, R.CAPS
S = D["short"]
PRE, POST = 0.3, 0.5
text, rrect, paint, fmt, k, money = R.text, R.rrect, R.paint, R.fmt, R.k, R.money
WHITE, GREY, GREEN, RED, ORANGE, PANEL, GRID = R.WHITE, R.GREY, R.GREEN, R.RED, R.ORANGE, R.PANEL, R.GRID
ep = R.ep


def bg(cv):
    cv.clear(0xFF02044A)
    for (x, y, r, c, a) in [(W, 0, 1100, R.BRAND_B, 0.45), (0, H, 1100, R.BRAND_A, 0.30)]:
        sh = skia.GradientShader.MakeRadial((x, y), r, [R.col(c, a), R.col(c, 0)])
        cv.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))
    R.logo(cv, 60, 80, 96)
    w = text(cv, "BITCOIN DAILY", 176, 130, 38, "black", WHITE)
    text(cv, "by SWC", 176 + w + 12, 130, 38, "bold", R.BRAND_A)
    text(cv, D["date"].upper() + "  ·  " + S.get("time", ""), 176, 172, 26, "semi", GREY)


def s_hook(cv, t):
    bg(cv)
    a = ep(t, 0.1, 0.7)
    v = D["start_price"] + (D["price"] - D["start_price"]) * ep(t, 0.2, 1.8)
    text(cv, "BITCOIN", W / 2, 470, 56, "black", ORANGE, a, "c")
    text(cv, fmt(v), W / 2, 700, 230, "anton", WHITE, a, "c")
    up = D["chg"] >= 0; c = GREEN if up else RED
    pa = ep(t, 1.6, 2.1)
    rrect(cv, W / 2 - 190, 760, 380, 90, 45, c, 0.2 * pa)
    text(cv, f"{'▲ +' if up else '▼ '}{D['chg']:.1f}%  24H", W / 2, 822, 46, "black", c, pa, "c")
    for i, line in enumerate(S["headline"][:2]):
        qa = ep(t, 2.6 + i * 0.4, 3.2 + i * 0.4)
        text(cv, line, W / 2, 1060 + i * 120, 100, "anton", WHITE if i == 0 else R.BRAND_A, qa, "c", dy=(1 - qa) * 30)


def s_chart(cv, t):
    bg(cv)
    text(cv, S.get("chart_title", "The last 24 hours"), 60, 330, 64, "black", WHITE, ep(t, 0.1, 0.6))
    hr = D["hourly"]; vals = [D["start_price"]] + [h[1] for h in hr]
    lo = min(vals) * 0.997; hi = max(max(vals), D["level"]) * 1.002
    X0, Y0, CW, CH = 80, 400, 920, 560
    rrect(cv, 40, 370, 1000, 640, 32, PANEL, ep(t, 0.1, 0.6))
    R.draw_line(cv, R.chart_pts(X0, Y0, CW, CH, vals, lo, hi), ep(t, 0.4, 3.5), ORANGE, 8, Y0 + CH)
    la = ep(t, 3.2, 3.8); y = Y0 + CH - CH * (D["level"] - lo) / (hi - lo)
    R.dashed(cv, X0, X0 + CW * la, y, ORANGE, la, 5)
    text(cv, f"{k(D['level'])} {D['level_label'].upper()}", X0 + 10, y - 18, 34, "black", ORANGE, la)
    chips = S["chips"][:3]
    for i, (lab, val, tone) in enumerate(chips):
        a = ep(t, 4.0 + i * 1.2, 4.6 + i * 1.2); y0 = 1060 + i * 150
        c = R.TONE.get(tone, WHITE)
        rrect(cv, 40, y0, 1000, 124, 28, PANEL, a)
        text(cv, lab, 80, y0 + 76, 38, "bold", GREY, a)
        text(cv, val, 1000, y0 + 82, 64, "anton", c, a, "r")


def s_cta(cv, t):
    bg(cv)
    a = ep(t, 0.1, 0.6)
    text(cv, "WATCH", W / 2, 420, 60, "black", GREY, a, "c")
    text(cv, S["watch_level"], W / 2, 640, 220, "anton", ORANGE, a, "c")
    for i, (line, tone) in enumerate(S["scenarios"][:2]):
        b = ep(t, 1.0 + i * 1.5, 1.6 + i * 1.5); c = R.TONE.get(tone, WHITE); y0 = 760 + i * 170
        rrect(cv, 60, y0, 960, 140, 28, c, 0.16 * b)
        text(cv, line, W / 2, y0 + 90, 46, "black", c, b, "c")
    d = ep(t, 4.0, 4.6)
    R.logo(cv, W / 2 - 70, 1130, 140, d)
    text(cv, "Full breakdown every morning", W / 2, 1340, 46, "black", WHITE, d, "c")
    text(cv, "on SWC Trading", W / 2, 1400, 46, "black", R.BRAND_A, d, "c")
    text(cv, "Not financial advice", W / 2, 1470, 30, "semi", GREY, d, "c")


def caption(cv, name, ts):
    cs = CAPS.get(name, [])
    for i, (a, b, s) in enumerate(cs):
        nxt = cs[i + 1][0] if i + 1 < len(cs) else b + 0.4
        if a - 0.05 <= ts < max(b + 0.1, nxt if nxt - b < 0.6 else b + 0.1):
            # wrap to 2 lines if needed
            f = skia.Font(R.TF["black"], 54); words = s.split(); lines = [""]
            for wd in words:
                cand = (lines[-1] + " " + wd).strip()
                if f.measureText(cand) > 940 and lines[-1]: lines.append(wd)
                else: lines[-1] = cand
            for j, ln in enumerate(lines[:2]):
                w = f.measureText(ln); y = 1640 + j * 76
                rrect(cv, W / 2 - w / 2 - 22, y - 56, w + 44, 74, 16, 0xFF000000, 0.75)
                cv.drawString(ln, W / 2 - w / 2, y, f, paint(WHITE))
            return


SC = [("hook", s_hook), ("chart", s_chart), ("cta", s_cta)]


def render_scene(name, fn, preview=False):
    R.SC = 1.0
    dur = DUR[name] + PRE + POST
    surf = skia.Surface(W, H)
    if preview:
        with surf as cv: fn(cv, dur - 0.8 - PRE); caption(cv, name, dur - 0.8 - PRE - 1.5)
        surf.makeImageSnapshot().save(f"{WD}/short_preview_{name}.png", skia.kPNG); return 0
    n = int(round(dur * FPS)); tmp = f"{WD}/short_{name}.tmp.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for i in range(n):
        tt = i / FPS
        with surf as cv:
            fn(cv, tt - PRE); caption(cv, name, tt - PRE)
            R.brand_bar(cv, 0, H - 10, W * tt / dur, 10)
            a = max(1 - min(1, tt / 0.25), min(1, max(0, (tt - (dur - 0.25)) / 0.25)))
            if a > 0: cv.drawRect(skia.Rect.MakeWH(W, H), paint(0xFF000000, a))
        ff.stdin.write(surf.makeImageSnapshot().tobytes())
    ff.stdin.close()
    if ff.wait() == 0: os.replace(tmp, f"{WD}/short_{name}.mp4")
    return n


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "preview":
        for nm, fn in SC: render_scene(nm, fn, True)
        sys.exit(0)
    frames = {nm: render_scene(nm, fn) for nm, fn in SC}
    segs = []; sr = None
    for nm, _ in SC:
        a, sr = sf.read(f"{WD}/a_{nm}.wav"); total = int(round(frames[nm] / FPS * sr)); pre = int(PRE * sr)
        seg = np.zeros(total, dtype=np.float32); seg[pre:pre + len(a)] = a[:total - pre]; segs.append(seg)
    sf.write(f"{WD}/short_voice.wav", np.concatenate(segs), sr)
    def ts(x):
        ms = int(round(x * 1000)); return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
    srt, off, idx = [], 0.0, 1
    for nm, _ in SC:
        for a, b, s in CAPS.get(nm, []):
            srt.append(f"{idx}\n{ts(off + PRE + a)} --> {ts(off + PRE + b)}\n{s}\n"); idx += 1
        off += frames[nm] / FPS
    open(f"{WD}/BTC_Short.srt", "w").write("\n".join(srt))
    open(f"{WD}/short_list.txt", "w").write("".join(f"file 'short_{nm}.mp4'\n" for nm, _ in SC))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{WD}/short_list.txt", "-c", "copy", f"{WD}/short_video_only.mp4"], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{WD}/short_video_only.mp4", "-i", f"{WD}/short_voice.wav", "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-af", "loudnorm=I=-14:TP=-1.5", "-shortest", "-movflags", "+faststart",
                    f"{WD}/BTC_Short.mp4"], check=True)
    print("OK", f"{WD}/BTC_Short.mp4")
