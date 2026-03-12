import json

REQUIRED_COLUMNS = ["Delta", "TCP Len"]

MIN_MS = 3.0
MAX_MS = 100.0
GRAPH_THRESHOLD_PCT = 15.0

def _f(s):
    try:
        return float(str(s).strip().replace(",", "."))
    except:
        return None

def _i(s):
    try:
        return int(float(str(s).strip().replace(",", ".")))
    except:
        return 0

def detect(rows):
    all_delays = []

    for r in rows:
        tcp_len = _i(r.get("TCP Len"))
        d = _f(r.get("Delta"))
        if tcp_len > 0 and d is not None:
            all_delays.append(d * 1000.0)

    if not all_delays:
        raise Exception("no TCP data packet deltas found")

    burst_pct = 100.0 * sum(1 for v in all_delays if v <= MIN_MS) / len(all_delays)
    delays = [v for v in all_delays if MIN_MS < v <= MAX_MS]

    if not delays:
        severity = "LOW"
        text = (
            "This detector looks for application pacing or a rate limiter.\n\n"
            f"It ignores burst traffic up to {MIN_MS:.1f} ms and focuses on intervals between "
            f"{MIN_MS:.1f} ms and {MAX_MS:.1f} ms.\n\n"
            "Fault case: a strong peak around a fixed interval such as 10 ms, 20 ms, 25 ms or 50 ms.\n"
            "Normal case: most packets are sent in bursts, so very small intervals dominate.\n\n"
            f"Severity: {severity}\n"
            f"TCP data packets: {len(all_delays)}\n"
            f"Packets <= {MIN_MS:.1f} ms: {burst_pct:.1f}%\n\n"
            "No relevant pacing intervals were found."
        )
        return {
            "plot": False,
            "text": text
        }

    bins = {}
    for v in delays:
        b = round(v)
        bins[b] = bins.get(b, 0) + 1

    top_ms, top_count = max(bins.items(), key=lambda x: x[1])
    top_pct = 100.0 * top_count / len(delays)

    if top_pct < 15.0:
        severity = "LOW"
        interpretation = "No strong fixed send interval detected."
    elif top_pct < 25.0:
        severity = "MODERATE"
        interpretation = "Some interval clustering detected. Mild pacing may be present."
    else:
        severity = "HIGH"
        interpretation = "Strong interval clustering detected. A rate limiter or application pacing is likely."

    text = (
        "This detector looks for application pacing or a rate limiter.\n\n"
        f"It ignores burst traffic up to {MIN_MS:.1f} ms and focuses on intervals between "
        f"{MIN_MS:.1f} ms and {MAX_MS:.1f} ms.\n\n"
        "Fault case: a strong peak around a fixed interval such as 10 ms, 20 ms, 25 ms or 50 ms.\n"
        "Normal case: most packets are sent in bursts, so very small intervals dominate.\n\n"
        f"Severity: {severity}\n"
        f"TCP data packets: {len(all_delays)}\n"
        f"Packets <= {MIN_MS:.1f} ms: {burst_pct:.1f}%\n"
        f"Dominant interval: {top_ms} ms\n"
        f"Dominant interval share: {top_pct:.1f}%\n\n"
        f"{interpretation}"
    )

    plot = top_pct >= GRAPH_THRESHOLD_PCT

    if not plot:
        text += "\n\nNo graph generated because interval clustering is too weak to be visually meaningful."

    return {
        "plot": plot,
        "text": text,
        "severity": severity,
        "delays": delays
    }

def render(r):
    if not r["plot"]:
        return f"""<!doctype html>
<html>
<body style="font-family: sans-serif">
<h2>rate_limit</h2>
<p style="white-space: pre-line; max-width: 1000px">{r["text"]}</p>
</body>
</html>
"""

    color = {
        "LOW": "#444",
        "MODERATE": "#b36b00",
        "HIGH": "#b00020"
    }.get(r["severity"], "#444")

    delays_json = json.dumps(r["delays"])

    return f"""<!doctype html>
<html>
<body style="font-family: sans-serif">
<h2>rate_limit</h2>
<p style="white-space: pre-line; max-width: 1000px">{r["text"]}</p>
<canvas id="c" width="1200" height="600"></canvas>
<script>
d = {delays_json}
color = "{color}"

c = document.getElementById("c")
g = c.getContext("2d")

w = c.width
h = c.height
left = 80
right = 40
top = 40
bottom = 540

bins = {{}}
d.forEach(v => {{
  let b = Math.round(v)
  bins[b] = (bins[b] || 0) + 1
}})

keys = Object.keys(bins).map(Number).sort((a,b) => a-b)
maxv = Math.max(...Object.values(bins), 1)
mink = Math.min(...keys)
maxk = Math.max(...keys)
plotW = w - left - right
plotH = bottom - top
bar = plotW / Math.max(keys.length, 1)

g.font = "14px sans-serif"
g.strokeStyle = "#000"
g.fillStyle = "#000"

// axes
g.beginPath()
g.moveTo(left, top)
g.lineTo(left, bottom)
g.lineTo(w - right, bottom)
g.stroke()

// x ticks
g.textAlign = "center"
for (let i = 0; i <= 8; i++) {{
  let val = Math.round(mink + (maxk - mink) * i / 8)
  let x = left + (val - mink) * plotW / Math.max(maxk - mink, 1)
  g.beginPath()
  g.moveTo(x, bottom)
  g.lineTo(x, bottom + 6)
  g.stroke()
  g.fillText(val + " ms", x, bottom + 24)
}}
g.fillText("Packet interval (ms)", left + plotW / 2, bottom + 52)

// y ticks
g.textAlign = "right"
for (let i = 0; i <= 5; i++) {{
  let val = Math.round(maxv * i / 5)
  let y = bottom - plotH * i / 5
  g.beginPath()
  g.moveTo(left - 6, y)
  g.lineTo(left, y)
  g.stroke()
  g.fillText(String(val), left - 10, y + 4)
}}
g.save()
g.translate(24, (top + bottom) / 2)
g.rotate(-Math.PI / 2)
g.textAlign = "center"
g.fillText("Packet count", 0, 0)
g.restore()

// bars
g.fillStyle = color
keys.forEach((k, i) => {{
  let v = bins[k]
  let bh = v * plotH / maxv
  let x = left + i * bar
  let y = bottom - bh
  g.fillRect(x, y, Math.max(1, bar - 1), bh)
}})
</script>
</body>
</html>
"""