"""BTC Daily video renderer.
Usage: python3 render.py <workdir>
<workdir> must contain data.json (see data.example.json) and a_<scene>.wav + durations.json from tts.py.
Writes <workdir>/BTC_Daily.mp4
"""
import skia, json, sys, subprocess, os
import numpy as np, soundfile as sf

WD = sys.argv[1]
W, H, FPS = 1920, 1080, 30
D = json.load(open(f"{WD}/data.json"))
DUR = json.load(open(f"{WD}/durations.json"))
CAPS = json.load(open(f"{WD}/captions.json")) if os.path.exists(f"{WD}/captions.json") else {}
CAPTIONS = os.environ.get("CAPTIONS", "1") == "1"
PRE, POST = 0.35, 0.65
# narration lengths the cue times were tuned for; cues scale with each day's narration length
BASE = {"intro": 15.08, "price": 16.62, "pressure": 33.32, "oi": 23.1, "etf": 20.76, "levels": 20.22, "outro": 14.68}
SC = 1.0

FD = "/usr/share/fonts/opentype/inter/"
TF = {k: skia.Typeface.MakeFromFile(FD + f) for k, f in
      {"reg": "Inter-Regular.otf", "semi": "Inter-SemiBold.otf", "bold": "Inter-Bold.otf", "black": "Inter-Black.otf"}.items()}
KIT = os.path.dirname(os.path.abspath(__file__))
LOGO = skia.Image.open(f"{KIT}/logo.png") if os.path.exists(f"{KIT}/logo.png") else None
BRAND_A, BRAND_B = 0xFFF79A0A, 0xFFB80BE6  # logo gradient: orange -> purple
TF["anton"] = skia.Typeface.MakeFromFile("/usr/share/fonts/truetype/google-fonts/ofl/anton/Anton-Regular.ttf")

BG = 0xFF0A0E17; PANEL = 0xFF131A28; GRID = 0xFF222B3D
WHITE = 0xFFF5F7FA; GREY = 0xFF8A94A8; ORANGE = 0xFFF7931A
GREEN = 0xFF22C55E; RED = 0xFFEF4444; BLUE = 0xFF3B82F6
TONE = {"red": RED, "green": GREEN, "orange": ORANGE, "blue": BLUE}


def clamp(x): return max(0.0, min(1.0, x))
def prog(t, a, b): return clamp((t - a) / (b - a))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3
def ep(t, a, b): return ease(prog(t, a * SC, b * SC))
def col(c, a=1.0): return skia.ColorSetA(c, int(skia.ColorGetA(c) * clamp(a)))


def paint(c, a=1.0, stroke=None):
    p = skia.Paint(AntiAlias=True, Color=col(c, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def text(cv, s, x, y, size, face="bold", c=WHITE, a=1.0, align="l", dy=0.0):
    if a <= 0: return 0
    f = skia.Font(TF[face], size); f.setSubpixel(True)
    w = f.measureText(s)
    if align == "c": x -= w / 2
    elif align == "r": x -= w
    cv.drawString(s, x, y + dy, f, paint(c, a))
    return w


def rrect(cv, x, y, w, h, r, c, a=1.0):
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), paint(c, a))


def logo(cv, x, y, size, a=1.0):
    if LOGO is None or a <= 0: return
    p = skia.Paint(AntiAlias=True); p.setAlphaf(clamp(a))
    cv.drawImageRect(LOGO, skia.Rect.MakeXYWH(x, y, size, size), skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), p)


def brand_bar(cv, x, y, w, h, a=1.0):
    sh = skia.GradientShader.MakeLinear([(x, 0), (x + max(w, 1), 0)], [col(BRAND_A, a), col(BRAND_B, a)])
    cv.drawRect(skia.Rect.MakeXYWH(x, y, w, h), skia.Paint(AntiAlias=True, Shader=sh))


def fmt(n): return f"${n:,.0f}"
def k(n): return f"${n / 1000:.1f}K".replace(".0K", "K")
def money(m): return f"{'+' if m >= 0 else '−'}${abs(m):,.0f}M"


def chrome(cv, t, dur, title):
    cv.clear(BG)
    sh = skia.GradientShader.MakeRadial((W * 0.8, -100), 1100, [col(ORANGE, 0.10), col(ORANGE, 0)])
    cv.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))
    logo(cv, 66, 38, 46)
    w = text(cv, "BITCOIN DAILY", 124, 72, 26, "black", WHITE)
    w2 = text(cv, "by SWC", 124 + w + 10, 72, 26, "bold", BRAND_A)
    text(cv, "·  " + D["date"].upper(), 124 + w + w2 + 26, 72, 26, "semi", GREY)
    text(cv, f"BTC  {fmt(D['price'])}", W - 70, 72, 26, "bold", WHITE, align="r")
    cv.drawLine(70, 100, W - 70, 100, paint(GRID, 1, 2))
    if title:
        a = ep(t, 0.1, 0.7)
        text(cv, title, 70, 190, 64, "black", WHITE, a, dy=(1 - a) * 20)
    text(cv, "NOT FINANCIAL ADVICE", W - 70, 132, 20, "semi", GREY, align="r")


def caption(cv, name, ts):
    cs = CAPS.get(name, [])
    cur = None
    for i, (a, b, s) in enumerate(cs):
        nxt = cs[i + 1][0] if i + 1 < len(cs) else b + 0.4
        if a - 0.05 <= ts < max(b + 0.1, nxt if nxt - b < 0.6 else b + 0.1):
            cur = s; break
    if not cur: return
    f = skia.Font(TF["bold"], 42); f.setSubpixel(True); w = f.measureText(cur)
    rrect(cv, W / 2 - w / 2 - 28, 990, w + 56, 66, 14, 0xFF000000, 0.72)
    cv.drawString(cur, W / 2 - w / 2, 1037, f, paint(WHITE))


def frame(cv, name, fn, tt, dur):
    cv.clear(BG)
    cv.save(); cv.translate(W * 0.05, 0); cv.scale(0.9, 0.9)
    fn(cv, tt - PRE, dur - PRE)
    cv.restore()
    if CAPTIONS: caption(cv, name, tt - PRE)
    brand_bar(cv, 0, H - 6, W * clamp(tt / dur), 6)
    fade(cv, tt, dur)


def fade(cv, t, dur):
    a = max(1 - clamp(t / 0.35), clamp((t - (dur - 0.35)) / 0.35))
    if a > 0: cv.drawRect(skia.Rect.MakeWH(W, H), paint(0xFF000000, a))


def chart_pts(x0, y0, w, h, vals, lo, hi):
    n = len(vals)
    return [(x0 + w * i / (n - 1), y0 + h - h * (v - lo) / (hi - lo)) for i, v in enumerate(vals)]


def draw_line(cv, pts, reveal, c, width=6, y_bottom=None):
    if reveal <= 0: return
    path = skia.Path(); path.moveTo(*pts[0])
    for p in pts[1:]: path.lineTo(*p)
    x0, x1 = pts[0][0], pts[-1][0]
    cv.save(); cv.clipRect(skia.Rect.MakeLTRB(x0 - 20, 0, x0 + (x1 - x0) * reveal + 4, H))
    if y_bottom:
        ap = skia.Path(path); ap.lineTo(x1, y_bottom); ap.lineTo(x0, y_bottom); ap.close()
        sh = skia.GradientShader.MakeLinear([(0, min(p[1] for p in pts)), (0, y_bottom)], [col(c, 0.35), col(c, 0)])
        cv.drawPath(ap, skia.Paint(AntiAlias=True, Shader=sh))
    cv.drawPath(path, paint(c, 1, width))
    cv.restore()
    kk = reveal * (len(pts) - 1); i = min(int(kk), len(pts) - 2); f = kk - i
    if reveal < 1:
        cv.drawCircle(pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f, 11, paint(c))


def dashed(cv, x0, x1, y, c, a, w=3):
    p = paint(c, a, w); p.setPathEffect(skia.DashPathEffect.Make([18, 12], 0)); cv.drawLine(x0, y, x1, y, p)


# ---------------- scenes ----------------
def s_intro(cv, t, dur):
    chrome(cv, t, dur, None)
    a = ep(t, 0.2, 0.9)
    logo(cv, W / 2 - 75, 140 + (1 - a) * 20, 150, a)
    text(cv, "BITCOIN DAILY  BY SWC", W / 2, 345, 40, "black", BRAND_A, a, "c")
    v = D["start_price"] + (D["price"] - D["start_price"]) * ep(t, 0.4, 3.0)
    text(cv, fmt(v), W / 2, 560, 230, "anton", WHITE, a, "c")
    pa = ep(t, 2.6, 3.2); up = D["chg"] >= 0; c = GREEN if up else RED
    rrect(cv, W / 2 - 160, 610, 320, 74, 37, c, 0.18 * pa)
    text(cv, f"{'▲ +' if up else '▼ '}{D['chg']:.1f}%  24H", W / 2, 662, 36, "black", c, pa, "c")
    qa = ep(t, 5.6, 6.4)
    text(cv, D["hook"], W / 2, 850, 72, "black", WHITE, qa, "c", dy=(1 - qa) * 24)


def s_price(cv, t, dur):
    chrome(cv, t, dur, D["titles"]["price"])
    hr = D["hourly"]; vals = [D["start_price"]] + [h[1] for h in hr]
    labels = [D.get("start_label", "")] + [h[0] for h in hr]
    lo_v, hi_v = min(D["low"], *vals), max(D["high"], *vals, D["level"])
    step = 500 if hi_v - lo_v < 3000 else 1000 if hi_v - lo_v < 7000 else 2000
    lo = (lo_v // step) * step - step * 0.5; hi = (hi_v // step + 1) * step + step * 0.2
    X0, Y0, CW, CH = 190, 260, 1520, 680
    yv = lambda v: Y0 + CH - CH * (v - lo) / (hi - lo)
    g = (int(lo // step) + 1) * step
    while g < hi:
        cv.drawLine(X0, yv(g), X0 + CW, yv(g), paint(GRID, 1, 1.5))
        text(cv, k(g), X0 - 24, yv(g) + 9, 24, "semi", GREY, align="r"); g += step
    n = len(vals) - 1
    for i in range(0, n + 1, max(1, n // 4)):
        text(cv, labels[i], X0 + CW * i / n, Y0 + CH + 44, 22, "semi", GREY, align="c")
    draw_line(cv, chart_pts(X0, Y0, CW, CH, vals, lo, hi), ep(t, 0.4, 7.0), ORANGE, 6, Y0 + CH)
    lows = [h[4] for h in hr]; highs = [h[3] for h in hr]
    li = 1 + lows.index(min(lows)); hi_i = 1 + highs.index(max(highs))
    for val, lab, c, tt, xi, off in [(D["low"], "24H LOW", RED, 2.8, li, 40), (D["high"], "24H HIGH", GREEN, 5.2, hi_i, -18)]:
        a = ep(t, tt, tt + 0.6); x = X0 + CW * xi / n
        cv.drawCircle(x, yv(val), 10 * a, paint(c, a))
        al = "r" if x > X0 + CW * 0.7 else "l"
        text(cv, f"{lab}  {fmt(val)}", x + (-22 if al == "r" else 22), yv(val) + off, 30, "black", c, a, al)
    a = ep(t, 10.5, 11.3); y = yv(D["level"])
    dashed(cv, X0, X0 + CW * a, y, ORANGE, a, 4)
    if a > 0:
        lab = f"{k(D['level'])}  {D['level_label'].upper()}"
        f = skia.Font(TF["black"], 28); bw = f.measureText(lab) + 60
        by = y - 70 if y - 70 > Y0 else y + 16
        rrect(cv, X0 + 40, by, bw, 54, 12, ORANGE, a)
        text(cv, lab, X0 + 40 + bw / 2, by + 38, 28, "black", BG, a, "c")


def s_pressure(cv, t, dur):
    chrome(cv, t, dur, D["titles"]["pressure"])
    rows = D["pressure"]
    for ci, (name, bi, di, tt, sub) in enumerate([("SPOT", 1, 2, 9.5, "Real coins changing hands"), ("FUTURES", 3, 4, 14.5, "Leveraged bets")]):
        x0 = 110 + ci * 870; w = 830
        a0 = ep(t, 1.0 + ci * 2.2, 1.8 + ci * 2.2)
        rrect(cv, x0, 240, w, 560, 24, PANEL, a0)
        text(cv, name, x0 + 40, 305, 40, "black", WHITE, a0)
        text(cv, sub, x0 + 40, 345, 24, "semi", GREY, a0)
        cx = x0 + 120 + 270
        for ri, r in enumerate(rows):
            y = 400 + ri * 78
            text(cv, r[0], x0 + 40, y + 30, 28, "bold", GREY, a0)
            cv.drawRect(skia.Rect.MakeXYWH(x0 + 120, y + 6, 540, 34), paint(GRID, a0))
            ba = ep(t, tt + ri * 0.25, tt + ri * 0.25 + 0.8)
            pct = r[bi]; dv = r[di]
            span = max(-270, min(270, (pct - 50) / 8 * 270)) * ba
            c = GREEN if pct >= 50 else RED
            xa, xb = sorted([cx, cx + span])
            cv.drawRect(skia.Rect.MakeLTRB(xa, y + 6, xb, y + 40), paint(c, ba))
            text(cv, f"{pct:.1f}%", x0 + w - 40, y + 21, 26, "black", c, ba, "r")
            text(cv, money(dv), x0 + w - 40, y + 47, 20, "semi", GREY, ba, "r")
        cv.drawLine(cx, 395, cx, 790, paint(WHITE, 0.5 * a0, 2))
        text(cv, "50%", cx, 388, 20, "semi", GREY, a0, "c")
        text(cv, "◀ SELLERS", x0 + 125, 785, 20, "bold", RED, 0.8 * a0)
        text(cv, "BUYERS ▶", x0 + 655, 785, 20, "bold", GREEN, 0.8 * a0, "r")
    fut = rows[-1][4]; c = RED if fut < 0 else GREEN
    a = ep(t, 21.0, 21.7)
    rrect(cv, 110, 840, 1000, 110, 20, c, 0.16 * a)
    w = text(cv, money(fut), 150, 917, 64, "anton", c, a)
    text(cv, f"net futures {'selling' if fut < 0 else 'buying'} in 24h", 150 + w + 30, 908, 32, "bold", WHITE, a)
    b = ep(t, 26.3, 27.0)
    rrect(cv, 1150, 840, 660, 110, 20, ORANGE, 0.16 * b)
    w = text(cv, f"{D['spot_share']:.0f}%", 1190, 917, 64, "anton", ORANGE, b)
    text(cv, "of volume is spot", 1190 + w + 24, 908, 32, "bold", WHITE, b)


def s_oi(cv, t, dur):
    chrome(cv, t, dur, D["titles"]["oi"])
    hr = D["hourly"]
    X0, Y0, CW, CH = 130, 260, 1080, 600
    rrect(cv, X0 - 40, Y0 - 30, CW + 80, CH + 110, 24, PANEL, ep(t, 0.2, 0.8))
    pr = [h[1] for h in hr]; oi = [h[2] for h in hr]
    pad_p = (max(pr) - min(pr)) * 0.08 + 1; pad_o = (max(oi) - min(oi)) * 0.08 + 1e-3
    r = ep(t, 0.8, 6.5)
    draw_line(cv, chart_pts(X0, Y0 + 30, CW, CH - 60, pr, min(pr) - pad_p, max(pr) + pad_p), r, ORANGE, 5)
    draw_line(cv, chart_pts(X0, Y0 + 30, CW, CH - 60, oi, min(oi) - pad_o, max(oi) + pad_o), r, BLUE, 5)
    la = ep(t, 1.0, 1.6)
    rrect(cv, X0, Y0 + CH + 30, 22, 22, 6, ORANGE, la); text(cv, "Price", X0 + 34, Y0 + CH + 50, 24, "bold", WHITE, la)
    rrect(cv, X0 + 160, Y0 + CH + 30, 22, 22, 6, BLUE, la); text(cv, "Open interest", X0 + 194, Y0 + CH + 50, 24, "bold", WHITE, la)
    text(cv, D.get("oi_caption", ""), X0 + CW, Y0 + CH + 50, 24, "semi", GREY, la, "r")
    cx, cw = 1290, 520
    a = ep(t, 4.8, 5.5); up = D["oi_chg_24h"] >= 0
    rrect(cv, cx, 230, cw, 230, 24, PANEL, a)
    text(cv, "OPEN INTEREST", cx + 36, 285, 24, "bold", GREY, a)
    text(cv, f"${D['oi']:.2f}B", cx + 36, 380, 84, "anton", WHITE, a)
    text(cv, f"{'▲ +' if up else '▼ '}{D['oi_chg_24h']:.1f}% in 24h", cx + 36, 432, 30, "black", BLUE, a)
    b = ep(t, 18.3, 19.0)
    rrect(cv, cx, 490, cw, 230, 24, PANEL, b)
    text(cv, "FUNDING RATE", cx + 36, 545, 24, "bold", GREY, b)
    text(cv, f"{'+' if D['funding'] >= 0 else '−'}{abs(D['funding']):.4f}%", cx + 36, 630, 64, "anton", WHITE, b)
    gx, gy, gw = cx + 36, 680, cw - 72
    cv.drawRect(skia.Rect.MakeXYWH(gx, gy, gw, 10), paint(GRID, b))
    rng = (D["funding_max7"] - D["funding_min7"]) or 1
    pos = clamp((D["funding"] - D["funding_min7"]) / rng)
    cv.drawRect(skia.Rect.MakeXYWH(gx, gy, gw * pos * ep(t, 18.8, 20.0), 10), paint(GREEN if D["funding"] >= 0 else RED, b))
    text(cv, "7D LOW", gx, gy + 34, 18, "semi", GREY, b); text(cv, "7D HIGH", gx + gw, gy + 34, 18, "semi", GREY, b, "r")
    c = ep(t, 13.6, 14.3); tone = TONE.get(D["oi_callout"]["tone"], RED)
    rrect(cv, cx, 760, cw, 190, 24, tone, 0.16 * c)
    text(cv, D["oi_callout"]["lines"][0], cx + 36, 835, 44, "black", tone, c, dy=(1 - c) * 16)
    text(cv, D["oi_callout"]["lines"][1], cx + 36, 895, 44, "black", WHITE, c, dy=(1 - c) * 16)


def s_etf(cv, t, dur):
    chrome(cv, t, dur, D["titles"]["etf"])
    rows = D["etf"]; vals = [v for _, v in rows]
    pos, neg = max(0, max(vals)), max(0, -min(vals))
    top, bot = 330, 900
    base = top + (bot - top) * pos / ((pos + neg) or 1)
    scale = (bot - top - 60) / ((pos + neg) or 1)
    n = len(rows); bw = 180; gap = 70; X0 = 200
    cv.drawLine(150, base, 150 + n * (bw + gap) + 20, base, paint(GREY, ep(t, 0.3, 0.8), 3))
    for i, (d, v) in enumerate(rows):
        a = ep(t, 1.8 + i * 0.45, 2.6 + i * 0.45)
        x = X0 + i * (bw + gap); h = -v * scale * a; c = RED if v < 0 else GREEN
        if a > 0:
            cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(x, min(base, base + h), x + bw, max(base, base + h)), 10, 10), paint(c, 0.9))
        lab_y = base - 20 if v < 0 else base + 40
        text(cv, d.upper(), x + bw / 2, lab_y, 26, "bold", GREY, ep(t, 0.4, 1.0), "c")
        text(cv, money(v), x + bw / 2, base + h + (44 if v < 0 else -18), 32, "black", WHITE, a, "c")
    if D.get("etf_footnote"):
        text(cv, D["etf_footnote"], 150, 975, 22, "semi", GREY, ep(t, 3.0, 3.6))
    a = ep(t, 6.6, 7.3); tot = sum(vals); c = RED if tot < 0 else GREEN
    rrect(cv, 1440, 260, 400, 360, 24, PANEL, a)
    text(cv, f"{n} SESSIONS", 1640, 330, 28, "bold", GREY, a, "c")
    s = f"{'+' if tot >= 0 else '-'}${abs(tot) / 1000:.2f}B" if abs(tot) >= 1000 else f"{'+' if tot >= 0 else '-'}${abs(tot):.0f}M"
    text(cv, s, 1640, 460, 110 if len(s) < 8 else 90, "anton", c, a, "c")
    text(cv, f"net {'outflows' if tot < 0 else 'inflows'}", 1640, 520, 30, "bold", WHITE, a, "c")
    text(cv, D.get("etf_sub", ""), 1640, 570, 24, "semi", GREY, a, "c")
    note = D.get("etf_note")
    if note:
        b = ep(t, 12.6, 13.3)
        rrect(cv, 1440, 660, 400, 270, 24, ORANGE, 0.15 * b)
        text(cv, note[0], 1640, 735, 40 if len(note[0]) <= 13 else 32, "black", ORANGE, b, "c")
        for i, line in enumerate(note[1:4]):
            text(cv, line, 1640, 795 + i * 45, 30 if i == 0 else 26, "bold" if i == 0 else "semi", WHITE if i == 0 else GREY, b, "c")


def s_levels(cv, t, dur):
    chrome(cv, t, dur, D["titles"]["levels"])
    L = D["levels"]
    allv = [L["key"], L["down"], D["price"], *L["up"]]
    span = max(allv) - min(allv)
    lo, hi = min(allv) - span * 0.12, max(allv) + span * 0.12
    X0, X1, Y0, CH = 380, 1170, 250, 720
    yv = lambda v: Y0 + CH - CH * (v - lo) / (hi - lo)
    cv.drawLine(X0, Y0, X0, Y0 + CH, paint(GRID, ep(t, 0.3, 1.0), 3))
    g = ep(t, 8.2, 9.0)
    cv.drawRect(skia.Rect.MakeLTRB(X0, yv(L["up"][1]), X1, yv(L["up"][0])), paint(GREEN, 0.25 * g))
    if L["up"][1] - L["up"][0] < span * 0.03: dashed(cv, X0, X1, yv(L["up"][0]), GREEN, g)
    up_lab = k(L["up"][0]) if L["up"][0] == L["up"][1] else f"{k(L['up'][0])} – {k(L['up'][1])}"
    text(cv, up_lab, X0 - 24, yv(sum(L["up"]) / 2) + 10, 30, "black", GREEN, g, "r")
    r = ep(t, 13.8, 14.6)
    dashed(cv, X0, X1, yv(L["down"]), RED, r)
    text(cv, k(L["down"]), X0 - 24, yv(L["down"]) + 10, 30, "black", RED, r, "r")
    kk = ep(t, 1.8, 2.6)
    cv.drawLine(X0, yv(L["key"]), X0 + (X1 - X0) * kk, yv(L["key"]), paint(ORANGE, kk, 6))
    text(cv, k(L["key"]), X0 - 24, yv(L["key"]) + 12, 40, "black", ORANGE, kk, "r")
    p = ep(t, 0.6, 1.2); yp = yv(D["price"])
    nudge = 40 if abs(yp - yv(L["key"])) < 30 else 0
    cv.drawCircle(X0 + 120, yp, 14, paint(WHITE, p))
    text(cv, f"NOW  {fmt(D['price'])}", X0 + 150, yp + 12 + nudge, 30, "bold", WHITE, p)

    def arrow(y_from, y_to, c, a):
        if a <= 0: return
        x = 900; ye = y_from + (y_to - y_from) * a; s = -1 if y_to < y_from else 1
        cv.drawLine(x, y_from, x, ye, paint(c, 1, 10))
        pth = skia.Path(); pth.moveTo(x - 26, ye - s * 4); pth.lineTo(x + 26, ye - s * 4); pth.lineTo(x, ye + s * 30); pth.close()
        cv.drawPath(pth, paint(c))
    arrow(yp - 20, yv(L["up"][0]) + 10, GREEN, ep(t, 8.0, 9.4))
    arrow(yp + 20, yv(L["down"]) - 10, RED, ep(t, 13.6, 15.0))
    for (hd, lines), c, (a0, a1), y0 in [(L["up_text"], GREEN, (8.6, 9.3), 270), (L["down_text"], RED, (14.0, 14.7), 600)]:
        a = ep(t, a0, a1)
        rrect(cv, 1260, y0, 560, 290, 24, PANEL, a)
        text(cv, hd, 1300, y0 + 65, 30, "black", c, a)
        for i, line in enumerate(lines[:3]):
            text(cv, line, 1300, y0 + 130 + i * 50, 30, "semi", WHITE, a)


def s_outro(cv, t, dur):
    chrome(cv, t, dur, "What to watch")
    for i, (s, tt) in enumerate(zip(D["watch"][:2], (0.4, 2.4))):
        a = ep(t, tt, tt + 0.7); y = 330 + i * 170
        rrect(cv, 110, y, 1700, 130, 24, PANEL, a)
        text(cv, f"0{i + 1}", 160, y + 88, 64, "anton", ORANGE, a)
        text(cv, s, 300, y + 84, 52 if len(s) < 40 else 42, "black", WHITE, a, dy=(1 - a) * 14)
    text(cv, D.get("cta", "Which way does it break?  Tell me in the comments ↓"), W / 2, 760, 40, "bold", WHITE, ep(t, 7.6, 8.3), "c")
    la = ep(t, 9.5, 10.3)
    logo(cv, W / 2 - 230, 820, 90, la)
    text(cv, "Subscribe to SWC for your daily Bitcoin update", W / 2 - 120, 878, 30, "bold", WHITE, la)
    text(cv, "Not financial advice  ·  Do your own research", W / 2, 990, 26, "semi", GREY, ep(t, 10.5, 11.2), "c")


SCENES = [("intro", s_intro), ("price", s_price), ("pressure", s_pressure), ("oi", s_oi),
          ("etf", s_etf), ("levels", s_levels), ("outro", s_outro)]


def render(name, fn, preview=False):
    global SC
    SC = DUR[name] / BASE[name]
    dur = DUR[name] + PRE + POST
    surf = skia.Surface(W, H)
    if preview:
        tt = dur - 0.8
        tt = max(PRE + 0.5, min(dur - 0.8, float(os.environ.get("PREVIEW_T", "1e9"))))
        with surf as cv: frame(cv, name, fn, tt, dur + 10)
        surf.makeImageSnapshot().save(f"{WD}/preview_{name}.png", skia.kPNG); return
    n = int(round(dur * FPS)); tmp = f"{WD}/scene_{name}.tmp.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                           "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for i in range(n):
        tt = i / FPS
        with surf as cv:
            frame(cv, name, fn, tt, dur)
        ff.stdin.write(surf.makeImageSnapshot().tobytes())
    ff.stdin.close()
    if ff.wait() == 0: os.replace(tmp, f"{WD}/scene_{name}.mp4")
    return n


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "preview":
        for nm, fn in SCENES: render(nm, fn, True)
        sys.exit(0)
    from concurrent.futures import ProcessPoolExecutor
    frames = {}
    with ProcessPoolExecutor(2) as ex:
        for nm, n in zip([s[0] for s in SCENES], ex.map(render, [s[0] for s in SCENES], [s[1] for s in SCENES])):
            frames[nm] = n
    segs = []; sr = None
    for nm, _ in SCENES:
        a, sr = sf.read(f"{WD}/a_{nm}.wav"); total = int(round(frames[nm] / FPS * sr)); pre = int(PRE * sr)
        seg = np.zeros(total, dtype=np.float32); seg[pre:pre + len(a)] = a[:total - pre]; segs.append(seg)
    sf.write(f"{WD}/voice.wav", np.concatenate(segs), sr)
    # SRT subtitles for YouTube upload
    def ts(x):
        ms = int(round(x * 1000)); return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
    srt, off, idx = [], 0.0, 1
    for nm, _ in SCENES:
        for a, b, s in CAPS.get(nm, []):
            srt.append(f"{idx}\n{ts(off + PRE + a)} --> {ts(off + PRE + b)}\n{s}\n"); idx += 1
        off += frames[nm] / FPS
    open(f"{WD}/BTC_Daily.srt", "w").write("\n".join(srt))
    open(f"{WD}/list.txt", "w").write("".join(f"file 'scene_{nm}.mp4'\n" for nm, _ in SCENES))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{WD}/list.txt", "-c", "copy", f"{WD}/video_only.mp4"], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{WD}/video_only.mp4", "-i", f"{WD}/voice.wav", "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-16:TP=-1.5", "-shortest",
                    "-movflags", "+faststart", f"{WD}/BTC_Daily.mp4"], check=True)
    print("OK", f"{WD}/BTC_Daily.mp4")
