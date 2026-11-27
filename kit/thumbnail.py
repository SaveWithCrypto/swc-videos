"""YouTube thumbnail (1280x720 PNG). Usage: python3 thumbnail.py <workdir>
Reads <workdir>/data.json (uses hourly, level, chg, and "thumb": {"line1", "line2", "tone", "tag"}).
Writes <workdir>/BTC_Daily_thumbnail.png
"""
import skia, json, sys, os

WD = sys.argv[1]
D = json.load(open(f"{WD}/data.json"))
T = D.get("thumb", {"line1": "STUCK AT", "line2": f"${D['level'] // 1000}K?", "tone": "red", "tag": "BITCOIN DAILY"})
KIT = os.path.dirname(os.path.abspath(__file__))
W, H = 1280, 720
NAVY = 0xFF02044A; ORANGE = 0xFFF79A0A; PURPLE = 0xFFB80BE6; WHITE = 0xFFFFFFFF
RED = 0xFFFF3B3B; GREEN = 0xFF22E07A
TONE = {"red": RED, "green": GREEN, "orange": ORANGE}[T.get("tone", "red")]
anton = skia.Typeface.MakeFromFile("/usr/share/fonts/truetype/google-fonts/ofl/anton/Anton-Regular.ttf")
black = skia.Typeface.MakeFromFile("/usr/share/fonts/opentype/inter/Inter-Black.otf")
col = lambda c, a: skia.ColorSetA(c, int(255 * a))

surf = skia.Surface(W, H)
with surf as cv:
    cv.clear(NAVY)
    # brand glows
    for (x, y, r, c, a) in [(1180, 80, 700, PURPLE, 0.55), (60, 700, 650, ORANGE, 0.40)]:
        sh = skia.GradientShader.MakeRadial((x, y), r, [col(c, a), col(c, 0)])
        cv.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))
    # chart (right side): hourly closes rising into the key level
    vals = [D["start_price"]] + [h[1] for h in D["hourly"]]
    lo, hi = min(vals) - 300, max(max(vals), D["level"]) + 250
    X0, X1, Y0, Y1 = 560, 1240, 150, 640
    pts = [(X0 + (X1 - X0) * i / (len(vals) - 1), Y1 - (Y1 - Y0) * (v - lo) / (hi - lo)) for i, v in enumerate(vals)]
    path = skia.Path(); path.moveTo(*pts[0])
    for p in pts[1:]: path.lineTo(*p)
    area = skia.Path(path); area.lineTo(X1, H); area.lineTo(X0, H); area.close()
    cv.drawPath(area, skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeLinear([(0, Y0), (0, H)], [col(ORANGE, 0.45), col(PURPLE, 0.0)])))
    lp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=12, StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)
    lp.setShader(skia.GradientShader.MakeLinear([(X0, 0), (X1, 0)], [ORANGE, PURPLE]))
    cv.drawPath(path, lp)
    # key level line
    yl = Y1 - (Y1 - Y0) * (D["level"] - lo) / (hi - lo)
    cv.drawRect(skia.Rect.MakeLTRB(X0 - 30, yl - 5, W, yl + 5), skia.Paint(AntiAlias=True, Color=TONE))
    cv.drawCircle(*pts[-1], 18, skia.Paint(AntiAlias=True, Color=WHITE))
    cv.drawCircle(*pts[-1], 10, skia.Paint(AntiAlias=True, Color=TONE))
    # dark fade behind text
    cv.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=skia.GradientShader.MakeLinear([(0, 0), (760, 0)], [col(NAVY, 0.95), col(NAVY, 0)])))
    # tag pill
    f = skia.Font(black, 30); tag = T.get("tag", "BITCOIN DAILY"); tw = f.measureText(tag)
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(52, 198, tw + 44, 54), 27, 27), skia.Paint(AntiAlias=True, Color=TONE))
    cv.drawString(tag, 74, 236, f, skia.Paint(AntiAlias=True, Color=NAVY if TONE != RED else WHITE))
    # headline, with a dark outline for contrast
    def big(s, y, size, fill_shader=None, color=WHITE):
        fnt = skia.Font(anton, size)
        st = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=16, Color=NAVY, StrokeJoin=skia.Paint.kRound_Join)
        cv.drawString(s, 50, y, fnt, st)
        p = skia.Paint(AntiAlias=True, Color=color)
        if fill_shader: p.setShader(fill_shader)
        cv.drawString(s, 50, y, fnt, p)
        return fnt.measureText(s)
    big(T["line1"], 400, 150)
    big(T["line2"], 610, 230, skia.GradientShader.MakeLinear([(50, 0), (650, 0)], [ORANGE, PURPLE]))
    # logo
    lg = f"{KIT}/logo.png"
    if os.path.exists(lg):
        img = skia.Image.open(lg)
        cv.drawImageRect(img, skia.Rect.MakeXYWH(52, 40, 140, 140), skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear))
    # % badge (top right)
    chg = D["chg"]; c = GREEN if chg >= 0 else RED
    s = f"{'+' if chg >= 0 else ''}{chg:.1f}%"
    fb = skia.Font(anton, 72); bw = fb.measureText(s)
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(W - bw - 100, 40, bw + 56, 100), 22, 22), skia.Paint(AntiAlias=True, Color=col(0xFF000000, 0.55)))
    cv.drawString(s, W - bw - 72, 117, fb, skia.Paint(AntiAlias=True, Color=c))
surf.makeImageSnapshot().save(f"{WD}/BTC_Daily_thumbnail.png", skia.kPNG)
print("OK", f"{WD}/BTC_Daily_thumbnail.png")
