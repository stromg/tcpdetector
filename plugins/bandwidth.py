from core.html_report import render_page

REQUIRED_COLUMNS = [
    "Time",
    "Length",
    "IP Proto",
    "DSCP",
    "TCP DstPort",
    "UDP DstPort",
]

TOP_N = 10
BUCKET = 1.0

IGNORE_PORTS = {
    5353,  # mDNS
    1900,  # SSDP
}

SERVICE_NAMES = {
    22: "SSH",
    53: "DNS",
    80: "HTTP",
    123: "NTP",
    443: "HTTPS",
    853: "DoT",
    5004: "RTP",
    5060: "SIP",
    5353: "mDNS",
}

DSCP_NAMES = {
    0: "CS0",
    8: "CS1",
    10: "AF11",
    12: "AF12",
    14: "AF13",
    16: "CS2",
    18: "AF21",
    20: "AF22",
    22: "AF23",
    24: "CS3",
    26: "AF31",
    28: "AF32",
    30: "AF33",
    32: "CS4",
    34: "AF41",
    36: "AF42",
    38: "AF43",
    40: "CS5",
    46: "EF",
    48: "CS6",
    56: "CS7",
}

DSCP_COLORS = {
    "CS0": "#6b7280",
    "CS1": "#9ca3af",
    "AF11": "#93c5fd",
    "AF12": "#60a5fa",
    "AF13": "#3b82f6",
    "CS2": "#86efac",
    "AF21": "#4ade80",
    "AF22": "#22c55e",
    "AF23": "#16a34a",
    "CS3": "#fde68a",
    "AF31": "#facc15",
    "AF32": "#eab308",
    "AF33": "#ca8a04",
    "CS4": "#fdba74",
    "AF41": "#fb923c",
    "AF42": "#f97316",
    "AF43": "#ea580c",
    "CS5": "#fca5a5",
    "EF": "#ef4444",
    "CS6": "#c084fc",
    "CS7": "#a855f7",
    "unknown": "#111827",
}


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


def _proto_and_port(r):
    proto_num = _i(r.get("IP Proto"))

    if proto_num == 6:
        return "TCP", _i(r.get("TCP DstPort"))
    if proto_num == 17:
        return "UDP", _i(r.get("UDP DstPort"))

    return None, None


def _dscp_label(v):
    d = _i(v)
    return DSCP_NAMES.get(d, "unknown")


def _service_name(port):
    return SERVICE_NAMES.get(port, "Unknown")


def _service_label(proto, port, dscp):
    name = _service_name(port)

    if name == "Unknown":
        return f"{proto} {port} {dscp}"

    return f"{name} {port} {dscp}"


def detect(rows):
    capture_start = rows[0].get("_capture_start", "")
    capture_end = rows[0].get("_capture_end", "")

    timed_rows, timeline_source = _build_relative_timeline(rows)
    if not timed_rows:
        raise Exception("no valid packet timestamps found")

    duration = timed_rows[-1][0]

    total_bytes = 0
    bucket_bytes = {}
    service_bytes = {}
    service_packets = {}
    dscp_packets = {}

    for t_rel, r in timed_rows:
        length = _i(r.get("Length"))
        if length <= 0:
            continue

        proto, port = _proto_and_port(r)
        if proto is None or port <= 0 or port in IGNORE_PORTS:
            continue

        dscp = _dscp_label(r.get("DSCP"))
        key = (proto, port, dscp)

        total_bytes += length

        b = int(t_rel // BUCKET)
        bucket_bytes[b] = bucket_bytes.get(b, 0) + length

        service_bytes[key] = service_bytes.get(key, 0) + length
        service_packets[key] = service_packets.get(key, 0) + 1

        dscp_packets[dscp] = dscp_packets.get(dscp, 0) + 1

    if total_bytes == 0:
        raise Exception("no usable TCP/UDP traffic found")

    total_mbps = (total_bytes * 8.0) / max(duration, 0.001) / 1_000_000.0

    times = sorted(bucket_bytes.keys())
    bw_mbps = [
        (bucket_bytes[t] * 8.0) / BUCKET / 1_000_000.0
        for t in times
    ]
    peak_bw = max(bw_mbps, default=0.0)

    top_services = []
    for key, byte_count in service_bytes.items():
        proto, port, dscp = key
        mbps = (byte_count * 8.0) / max(duration, 0.001) / 1_000_000.0
        top_services.append({
            "label": _service_label(proto, port, dscp),
            "mbps": mbps,
            "packets": service_packets[key],
        })

    top_services.sort(key=lambda x: x["mbps"], reverse=True)
    top_services = top_services[:TOP_N]

    dscp_items = sorted(
        dscp_packets.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    text = []
    text.append("Bandwidth per service / DSCP")
    text.append("")
    text.append(f"Capture start: {capture_start}")
    text.append(f"Capture end: {capture_end}")
    text.append("")
    text.append(f"Capture duration: {duration:.1f} s")
    text.append(f"Timeline source: {timeline_source}")
    text.append(f"Total observed bandwidth: {total_mbps:.3f} Mbit/s")
    text.append(f"Peak 1-second bandwidth: {peak_bw:.3f} Mbit/s")
    text.append("")
    text.append("Top service / DSCP combinations:")

    for item in top_services:
        text.append(
            f"- {item['label']} — {item['mbps']:.3f} Mbit/s — packets {item['packets']}"
        )

    text.append("")
    text.append(
        "Ports labeled 'Unknown' are not in the built-in service list and may represent non-standard or application-specific services."
    )

    charts = [
        {
            "type": "time_bars",
            "title": "Bandwidth over time",
            "x": times,
            "y": bw_mbps,
            "y_suffix": " Mbit/s",
            "y_decimals": 2,
            "color": "#6b7280",
            "height": 280,
            "footer": "Gray bars = total observed bandwidth per second",
        }
    ]

    if top_services:
        charts.append(
            {
                "type": "histogram",
                "title": "Top service / DSCP combinations",
                "values": [round(x["mbps"], 3) for x in top_services],
                "labels": [x["label"] for x in top_services],
                "colors": ["#6b7280"] * len(top_services),
                "y_suffix": "",
                "y_decimals": 0,
                "height": 360,
                "footer": "Bar height = average bandwidth over the whole capture",
            }
        )

    if dscp_items:
        charts.append(
            {
                "type": "histogram",
                "title": "DSCP distribution",
                "values": [x[1] for x in dscp_items],
                "labels": [x[0] for x in dscp_items],
                "colors": [DSCP_COLORS.get(x[0], "#111827") for x in dscp_items],
                "y_suffix": "",
                "y_decimals": 0,
                "height": 260,
                "footer": "Packet count per DSCP class",
            }
        )

    return {
        "title": "bandwidth",
        "text": "\n".join(text),
        "charts": charts,
    }


def render(r):
    return render_page(r["title"], r["text"], r["charts"])