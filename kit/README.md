# Bitcoin Daily by SWC: kit

This kit lives in the GitHub repository SaveWithCrypto/swc-videos, folder `kit/`. Scheduled runs clone the repo and use it from there, so nothing on Rick's Mac is needed except the Claude desktop app's built-in browser.

Used by the scheduled "Bitcoin briefing" task (07:45 / 12:45 / 20:45 UK).

## Files
- `fetch.js`: paste into the built-in browser's javascript_tool on any https://nioctib.live page. Returns pressure (spot/perp buy % and net $M for 30m/1h/4h/12h/24h), 24 hourly rows `[label, close, oiB, high, low]`, OI stats, funding stats, spot share of volume, and ETF daily totals (last 6 sessions; `pending: true` = not reported yet).
- `tts.py <workdir> [voice]`: voiceover from `<workdir>/narration.json` → `a_<scene>.wav`, `durations.json`, `captions.json`. Default voice `bf_emma` (British female), speed from env `TTS_SPEED` (default 1.0). Downloads the Kokoro model from GitHub on first use. Needs `pip install --break-system-packages kokoro-onnx soundfile`.
- `render.py <workdir>`: renders `<workdir>/BTC_Daily.mp4` (1080p, burnt-in captions) and `BTC_Daily.srt`. Needs `pip install --break-system-packages skia-python numpy soundfile`, plus ffmpeg. `CAPTIONS=0` env var renders without burnt-in captions. `render.py <workdir> preview` writes one PNG per scene for checking.
- `thumbnail.py <workdir>`: 1280x720 YouTube thumbnail → `<workdir>/BTC_Daily_thumbnail.png`, using `data.json` (hourly, level, chg, start_price) and its `thumb` field: {"line1": short white line, "line2": big gradient line (≤5 characters works best, e.g. "$61K?"), "tone": red/green/orange, "tag": "BITCOIN DAILY"}. ≤4 words in total.
- `short.py <workdir>`: vertical YouTube Short (1080x1920, 30–45 s) → `BTC_Short.mp4` + `BTC_Short.srt`. Uses a data.json with the same fields as the main video plus a `short` block: {"time": "12:45 UK", "headline": [line1, line2 (≤12 chars each)], "chart_title", "chips": [[label, value, tone] ×3], "watch_level": "$61K", "scenarios": [[text, "green"], [text, "red"]]}. narration.json has exactly 3 scenes, hook (~8 s), chart (~13 s), cta (~14 s): see short_data.example.json and short_narration.example.json. Run tts.py first.
- `YOUTUBE.md`: the tested procedure for publishing videos, Shorts and community posts to SWC Trading.
- `logo.png`: the SWC logo, used by render.py and thumbnail.py (keep it next to them).
- `data.example.json`, `narration.example.json`: a worked example (26 Nov 2026, 14:13). Copy the shape exactly.

## narration.json
Seven entries, in this order: intro, price, pressure, oi, etf, levels, outro. Each scene's narration should follow the same beats as the example, because on-screen elements animate in on cues tuned to it (cue times stretch with each scene's length):
- intro: the headline move, a hook question, and the date.
- price: the 24h low (~3s in), the high (~5s), the current price, then the key level (~11s).
- pressure: explain spot vs futures, then the spot read (~10s), the futures read (~15s), the 24h futures net figure (~21s), and spot share of volume (~26s).
- oi: the OI change (~5s), what it implies (~14s), funding (~18s).
- etf: the recent flows (~2–7s), the total, then any special note (holiday, etc.) at ~13s.
- levels: the key level (~2s), the upside scenario (~8s), the downside scenario (~14s).
- outro: two things to watch, a comments CTA, "not financial advice".
Write numbers as `{display|spoken}` pairs, e.g. `{$61,000|sixty one thousand}`, `{3.5%|three and a half percent}`, `{ETFs|E T Fs}`, `{IBIT|I bit}`. Captions show the first part and the voice says the second.
Tone: warm, friendly and conversational, like the example: open with "Hi everyone, and welcome back to Bitcoin Daily by {SWC|S W C}!", use contractions and "you", and close with "Thanks so much for watching, and I'll see you tomorrow!".
NEVER mention nioctib.live, TMG, Jordan or Thatt Martini Guy in narration, captions or on-screen text.

## data.json fields
date, price, start_price, start_label, chg, low, high, hourly (24 rows from fetch.js), pressure (rows `[window, spotBuyPct, spotNetM, perpBuyPct, perpNetM]` for 30m,1h,4h,12h,24h), spot_share, oi, oi_chg_24h, funding, funding_min7, funding_max7, etf (`[["18 Nov", totalM], ...]`, last 5 reported sessions), etf_footnote (or ""), etf_sub, etf_note (`[heading, line1, line2, line3]` or null), hook, level, level_label ("resistance"/"support"), titles {price, pressure, oi, etf, levels}, oi_caption, oi_callout {tone: red/green/orange/blue, lines: [l1, l2]}, levels {key, up: [lo, hi], down, up_text: [heading, [lines]], down_text: [heading, [lines]]}, watch [q1, q2].
