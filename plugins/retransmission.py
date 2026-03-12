REQUIRED_COLUMNS = ["Length", "Retrans"]

THRESHOLD = 1400
GRAPH_THRESHOLD = 0.1  # %

def detect(rows):
    small_total = 0
    large_total = 0
    small_re = 0
    large_re = 0

    for r in rows:
        try:
            length = float(r["Length"])
            retrans = int(r["Retrans"])
        except:
            continue

        if length <= THRESHOLD:
            small_total += 1
            if retrans:
                small_re += 1
        else:
            large_total += 1
            if retrans:
                large_re += 1

    small_rate = (small_re / small_total * 100.0) if small_total else 0.0
    large_rate = (large_re / large_total * 100.0) if large_total else 0.0
    diff = large_rate - small_rate
    max_rate = max(small_rate, large_rate)

    if diff > 5.0:
        severity = "HIGH"
        interpretation = "Large packets retransmit significantly more often."
    elif diff > 2.0:
        severity = "MODERATE"
        interpretation = "Large packets retransmit somewhat more often."
    else:
        severity = "LOW"
        interpretation = "Small and large packets have similar retransmission rates."

    text = (
        "This detector compares retransmission rates for small and large packets.\n\n"
        "Fault case: large packets retransmit significantly more often.\n"
        "Normal case: both packet sizes have similar retransmission rates.\n\n"
        f"Severity: {severity}\n\n"
        f"<= {THRESHOLD} bytes:\n"
        f"  packets: {small_total}\n"
        f"  retransmissions: {small_re}\n"
        f"  rate: {small_rate:.3f}%\n\n"
        f"> {THRESHOLD} bytes:\n"
        f"  packets: {large_total}\n"
        f"  retransmissions: {large_re}\n"
        f"  rate: {large_rate:.3f}%\n\n"
        f"Difference: {diff:.3f}%\n\n"
        f"{interpretation}"
    )

    if max_rate < GRAPH_THRESHOLD:
        text += (
            f"\n\nRetransmission levels are extremely low (<{GRAPH_THRESHOLD}%). "
            "No graph generated because the values would not be visually meaningful."
        )
        return {
            "plot": False,
            "text": text
        }

    return {
        "plot": True,
        "text": text,
        "severity": severity,
        "small_rate": small_rate,
        "large_rate": large_rate
    }

def render(r):
    if not r["plot"]:
        return f"""<!doctype html>
<html>
<body style="font-family:sans-serif">
<h2>retransmission</h2>
<p style="white-space:pre-line; max-width:1000px">{r["text"]}</p>
</body>
</html>
"""

    color = {
        "LOW": "#444",
        "MODERATE": "#b36b00",
        "HIGH": "#b00020"
    }.get(r["severity"], "#444")

    return f"""<!doctype html>
<html>
<body style="font-family:sans-serif">
<h2>retransmission</h2>
<p style="white-space:pre-line; max-width:1000px">{r["text"]}</p>
<canvas id="c" width="1000" height="600"></canvas>
<script>
small = {r["small_rate"]}
large = {r["large_rate"]}
color = "{color}"

c = document.getElementById("c")
g = c.getContext("2d")

w = c.width
h = c.height
left = 120
right = 60
top = 80
bottom = 500
plotW = w - left - right
plotH = bottom - top

maxv = Math.max(small, large, 1.0)

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
g.fillText("Retransmission rate (%)", 0, 0)
g.restore()

// bars
let bw = 140
let gap = 240
let x1 = 220
let x2 = x1 + gap

g.fillStyle = color

let h1 = small * plotH / maxv
let h2 = large * plotH / maxv

g.fillRect(x1, bottom - h1, bw, h1)
g.fillRect(x2, bottom - h2, bw, h2)

// labels
g.fillStyle = "#000"
g.textAlign = "center"
g.fillText("<=1400 bytes", x1 + bw/2, bottom + 24)
g.fillText(">1400 bytes", x2 + bw/2, bottom + 24)
g.fillText("Packet size group", left + plotW / 2, bottom + 60)

g.fillText(small.toFixed(3) + "%", x1 + bw/2, bottom - h1 - 8)
g.fillText(large.toFixed(3) + "%", x2 + bw/2, bottom - h2 - 8)
</script>
</body>
</html>
"""