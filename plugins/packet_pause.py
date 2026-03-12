REQUIRED_COLUMNS = ["Delta", "TCP Len"]

STALL_MS = 80.0
GRAPH_THRESHOLD = 0.1  # %

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
    total_data_packets = 0
    pauses = 0
    max_pause = 0.0

    for r in rows:
        tcp_len = _i(r.get("TCP Len"))
        d = _f(r.get("Delta"))

        if tcp_len > 0 and d is not None:
            ms = d * 1000.0
            total_data_packets += 1
            if ms > max_pause:
                max_pause = ms
            if ms >= STALL_MS:
                pauses += 1

    if total_data_packets == 0:
        raise Exception("no TCP data packets found")

    pause_rate = 100.0 * pauses / total_data_packets

    if pause_rate == 0:
        severity = "LOW"
        interpretation = "No packet pauses detected."
    elif pause_rate < 0.1:
        severity = "LOW"
        interpretation = "Very low packet pause level detected. Only isolated pauses were seen."
    elif pause_rate < 1.0:
        severity = "MODERATE"
        interpretation = "Some long packet pauses were detected."
    else:
        severity = "HIGH"
        interpretation = "Frequent long packet pauses were detected."
        
    text = (
        "This detector looks for long packet pauses (TCP stalls).\n\n"
        f"A packet pause means an unusually long time gap between TCP data packets. "
        f"In this plugin, a pause means >= {STALL_MS:.0f} ms.\n\n"
        "Possible causes: rate limiting, queueing, congestion, Wi-Fi contention or endpoint delays.\n\n"
        f"Severity: {severity}\n"
        f"TCP data packets: {total_data_packets}\n"
        f"Packet pauses >= {STALL_MS:.0f} ms: {pauses}\n"
        f"Packet pause rate: {pause_rate:.3f}%\n"
        f"Max packet interval: {max_pause:.3f} ms\n\n"
        f"{interpretation}"
    )

    if pause_rate < GRAPH_THRESHOLD:
        text += (
            f"\n\nPacket pause levels are extremely low (<{GRAPH_THRESHOLD}%). "
            "No graph generated because the values would not be visually meaningful."
        )
        return {
            "plot": False,
            "text": text,
            "severity": severity,
            "pause_rate": pause_rate,
            "max_pause": max_pause
        }

    return {
        "plot": True,
        "text": text,
        "severity": severity,
        "pause_rate": pause_rate,
        "max_pause": max_pause
    }

def render(r):
    if not r["plot"]:
        return f"""<!doctype html>
<html>
<body style="font-family:sans-serif">
<h2>stall</h2>
<p style="white-space:pre-line; max-width:1000px">{r["text"]}</p>
</body>
</html>
"""

    color = {
        "LOW": "#444",
        "MODERATE": "#b36b00",
        "HIGH": "#b00020"
    }.get(r["severity"], "#444")

    pause_rate = r["pause_rate"]
    max_pause = r["max_pause"]

    return f"""<!doctype html>
<html>
<body style="font-family:sans-serif">
<h2>packet_pause</h2>
<p style="white-space:pre-line; max-width:1000px">{r["text"]}</p>
<canvas id="c" width="1000" height="600"></canvas>
<script>
pauseRate = {pause_rate}
maxPause = {max_pause}
color = "{color}"

c = document.getElementById("c")
g = c.getContext("2d")

w = c.width
h = c.height
left = 120
right = 60
top = 80
bottom = 500
plotH = bottom - top

maxv = Math.max(pauseRate, 1.0)

g.font = "14px sans-serif"
g.strokeStyle = "#000"
g.fillStyle = "#000"

// axes
g.beginPath()
g.moveTo(left, top)
g.lineTo(left, bottom)
g.lineTo(w - right, bottom)
g.stroke()

// y ticks
g.textAlign = "right"
for (let i = 0; i <= 5; i++) {{
  let v = maxv * i / 5
  let y = bottom - plotH * i / 5
  g.beginPath()
  g.moveTo(left - 6, y)
  g.lineTo(left, y)
  g.stroke()
  g.fillText(v.toFixed(3) + "%", left - 10, y + 4)
}}

// y title
g.save()
g.translate(28, (top + bottom) / 2)
g.rotate(-Math.PI / 2)
g.textAlign = "center"
g.fillText("Packet pause rate (%)", 0, 0)
g.restore()

// single bar
let bw = 180
let x = 350
let bh = pauseRate * plotH / maxv

g.fillStyle = color
g.fillRect(x, bottom - bh, bw, bh)

g.fillStyle = "#000"
g.textAlign = "center"
g.fillText("TCP data packets", x + bw/2, bottom + 24)
g.fillText(pauseRate.toFixed(3) + "%", x + bw/2, bottom - bh - 8)
g.fillText("Max interval: " + maxPause.toFixed(3) + " ms", x + bw/2, bottom + 54)
</script>
</body>
</html>
"""
