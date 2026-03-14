from core.html_report import render_page

REQUIRED_COLUMNS = ["Time", "Length", "TCP Len", "Retrans"]

MTU_SPLIT = 1400
BUCKET = 1.0


def _f(v):
    try:
        return float(str(v).strip().replace(",", "."))
    except:
        return 0.0


def _i(v):
    try:
        return int(float(str(v).strip().replace(",", ".")))
    except:
        return 0


def _is_true(v):
    s = str(v).strip().lower()
    return s not in ("", "0", "false", "none")


def _build_relative_timeline(rows):
    have_delta = any(_f(r.get("Delta")) > 0 for r in rows)

    if have_delta:
        out = []
        t = 0.0
        for r in rows:
            d = _f(r.get("Delta"))
            if d < 0:
                d = 0.0
            t += d
            out.append((t, r))
        return out, "delta"

    valid = []
    for r in rows:
        t = _f(r.get("Time"))
        if t > 0:
            valid.append((t, r))

    valid.sort(key=lambda x: x[0])

    if not valid:
        return [], "none"

    start = valid[0][0]
    out = [(t - start, r) for t, r in valid]
    return out, "time"


def detect(rows):
    capture_start = rows[0].get("_capture_start", "")
    capture_end = rows[0].get("_capture_end", "")

    timed_rows, timeline_source = _build_relative_timeline(rows)
    if not timed_rows:
        raise Exception("no valid packet timestamps found")

    duration = timed_rows[-1][0]

    buckets = {}
    small_total = 0
    small_re = 0
    large_total = 0
    large_re = 0
    prev_large_t = None

    size_hist = {
        "small": 0,
        "medium": 0,
        "large": 0,
        "jumboish": 0,
    }

    for t_rel, r in timed_rows:
        b = int(t_rel // BUCKET)

        length = _i(r.get("Length"))
        tcp_len = _i(r.get("TCP Len"))
        retrans = _is_true(r.get("Retrans"))

        if tcp_len <= 0:
            continue

        if b not in buckets:
            buckets[b] = {
                "large_pkts": 0,
                "large_re": 0,
                "gap_sum_ms": 0.0,
                "gap_count": 0,
                "gap_max_ms": 0.0,
            }

        if length <= 600:
            size_hist["small"] += 1
        elif length <= 1200:
            size_hist["medium"] += 1
        elif length <= MTU_SPLIT:
            size_hist["large"] += 1
        else:
            size_hist["jumboish"] += 1

        if length > MTU_SPLIT:
            large_total += 1
            buckets[b]["large_pkts"] += 1

            if retrans:
                large_re += 1
                buckets[b]["large_re"] += 1

            if prev_large_t is not None:
                gap_ms = (t_rel - prev_large_t) * 1000.0
                if gap_ms < 0:
                    gap_ms = 0.0
                buckets[b]["gap_sum_ms"] += gap_ms
                buckets[b]["gap_count"] += 1
                if gap_ms > buckets[b]["gap_max_ms"]:
                    buckets[b]["gap_max_ms"] = gap_ms

            prev_large_t = t_rel
        else:
            small_total += 1
            if retrans:
                small_re += 1

    small_rate = (small_re / small_total * 100.0) if small_total else 0.0
    large_rate = (large_re / large_total * 100.0) if large_total else 0.0

    times = []
    gap_avg_ms = []
    gap_max_ms = []
    re_rate_pct = []
    large_pkts = []

    onset = None

    for b in sorted(buckets):
        sec = b
        data = buckets[b]

        avg_gap = (
            data["gap_sum_ms"] / data["gap_count"]
            if data["gap_count"] > 0
            else 0.0
        )
        max_gap = data["gap_max_ms"]
        rate = (
            data["large_re"] / data["large_pkts"] * 100.0
            if data["large_pkts"] > 0
            else 0.0
        )

        times.append(sec)
        gap_avg_ms.append(avg_gap)
        gap_max_ms.append(max_gap)
        re_rate_pct.append(rate)
        large_pkts.append(data["large_pkts"])
        if onset is None and data["large_pkts"] > 200 and rate > 10.0:
            onset = sec

    peak_gap_ms = max(gap_max_ms, default=0.0)
    peak_re_rate = max(re_rate_pct, default=0.0)
    peak_large_pkts = max(large_pkts, default=0)

    text = []
    text.append("MTU blackhole detector")
    text.append("")
    text.append("Detects cases where large TCP packets fail while smaller packets succeed.")
    text.append("Typical cause: blocked PMTUD or missing ICMP fragmentation-needed messages.")
    text.append("")
    text.append(f"Capture start: {capture_start}")
    text.append(f"Capture end: {capture_end}")
    text.append("")
    text.append(f"Capture duration: {duration:.1f} s")
    text.append(f"Timeline source: {timeline_source}")
    text.append("")
    text.append(f"Small packet retrans rate: {small_rate:.2f} %")
    text.append(f"Large packet retrans rate: {large_rate:.2f} %")
    text.append("")
    text.append(f"Large packet threshold: {MTU_SPLIT} bytes")
    text.append("Graph 1: delay between large TCP packets.")
    text.append("Graph 2: retransmission rate for large packets per second.")
    text.append("Graph 3: packet size distribution for TCP data packets.")
    text.append("Graph 4: large packet count per second.")
    text.append("")
    text.append(f"Peak delay between large packets: {peak_gap_ms:.1f} ms")
    text.append(f"Peak large-packet retrans rate: {peak_re_rate:.2f} %")
    text.append(f"Peak large-packet count per second: {peak_large_pkts}")
    text.append("")
    text.append(
        f"Note: MTU_SPLIT (currently {MTU_SPLIT}) controls what is considered a large packet."
    )
    text.append(
        "Adjust this value in the plugin if the suspected path MTU is much lower or higher."
    )

    if onset is not None:
        text.append("")
        text.append(f"Possible MTU problem starting around {onset}s")

    return {
        "title": "mtu_blackhole",
        "text": "\n".join(text),
        "charts": [
            {
                "type": "time_bars_dual",
                "title": "Graph 1: Delay between large TCP packets",
                "x": times,
                "y": gap_avg_ms,
                "y2": gap_max_ms,
                "y_suffix": " ms",
                "y_decimals": 0,
                "color1": "#6b7280",
                "color2": "#b00020",
                "onset": onset,
                "height": 300,
                "footer": "Gray bars = average delay, red markers = max delay",
                "highlight_y": re_rate_pct,
                "highlight_threshold": 8.0,
                "highlight_color": "rgba(255,0,0,0.08)",
            },
            {
                "type": "time_bars",
                "title": "Graph 2: Large-packet retransmission rate per second",
                "x": times,
                "y": re_rate_pct,
                "y_suffix": " %",
                "y_decimals": 1,
                "color": "#6b7280",
                "onset": onset,
                "height": 260,
                "footer": "Gray bars = retransmission rate for packets > MTU_SPLIT",
            },
            {
                "type": "histogram",
                "title": "Graph 3: TCP data packet size distribution",
                "values": [
                    size_hist["small"],
                    size_hist["medium"],
                    size_hist["large"],
                    size_hist["jumboish"],
                ],
                "labels": [
                    "0-600 B",
                    "601-1200 B",
                    f"1201-{MTU_SPLIT} B",
                    f">{MTU_SPLIT} B",
                ],
                "colors": ["#9ca3af", "#6b7280", "#3b82f6", "#b00020"],
                "y_suffix": "",
                "y_decimals": 0,
                "height": 260,
                "footer": "Rightmost bar is the packet class most relevant to MTU blackholing",
            },
            {
                "type": "time_bars",
                "title": "Graph 4: Large packet count per second",
                "x": times,
                "y": large_pkts,
                "y_suffix": "",
                "y_decimals": 0,
                "color": "#3b82f6",
                "onset": onset,
                "height": 260,
                "footer": "Blue bars = packets > MTU_SPLIT seen per second",
            },
        ],
    }


def render(r):
    return render_page(r["title"], r["text"], r["charts"])