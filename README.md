
# tcpdiag

**tcpdiag** is a small TCP diagnostics tool that turns Wireshark captures into quick visual reports.

Goal: understand network problems in **seconds**, not hours.

The tool detects common TCP issues such as:

- packet loss (retransmissions)
- traffic shaping / rate limiting
- long pauses in packet flow
- MTU blackholes (PMTUD failures)
- bandwidth distribution per service
- DSCP / QoS markings

tcpdiag converts packet data into a **single HTML report with graphs**.

---

# Quick start (10 seconds)

1. Install the Wireshark Lua exporter
2. Open a capture in Wireshark
3. Run tcpdiag

Example:

```
python3 tcpdiag.py bandwidth /tmp/ws_export.csv
```

This generates:

```
graph.html
```

Open it in your browser.

---

# How it works

tcpdiag has three parts:

```
Wireshark capture
      ↓
Lua exporter plugin
      ↓
CSV file
      ↓
tcpdiag Python plugins
      ↓
HTML report with graphs
```

The Lua plugin automatically exports packet data while Wireshark processes the capture.

No manual column selection required.

---

# Available plugins

| Plugin | Detects |
|------|------|
| retransmission | packet loss |
| rate_limit | traffic shaping / pacing |
| packet_pause | long pauses in packet flow |
| bandwidth | bandwidth per service / DSCP |
| mtu_blackhole | PMTUD / MTU failures |

Example:

```
python3 tcpdiag.py retransmission capture.csv
```

---

# Install Wireshark exporter

The Lua exporter must be installed so tcpdiag receives structured packet data.

Linux / macOS:

```
mkdir -p ~/.local/lib/wireshark/plugins
cp export_ws.lua ~/.local/lib/wireshark/plugins/
```

Restart Wireshark.

Windows:

```
%APPDATA%\Wireshark\plugins
```

Copy `export_ws.lua` there and restart Wireshark.

---

# Exported CSV

The Lua exporter automatically writes:

Linux / macOS

```
/tmp/ws_export.csv
```

Windows

```
%TEMP%\ws_export.csv
```

Fields include:

```
Time
Delta
Length
TCP Len
Retrans
DSCP
TCP ports
UDP ports
AckRTT
Window
```

---

# Example use cases

tcpdiag helps diagnose problems such as:

- MTU blackholing
- ISP traffic shaping
- QoS misconfiguration
- WiFi congestion
- retransmission bursts
- bandwidth hogging services

The tool is designed for **engineers troubleshooting real networks**.

---

# Design philosophy

tcpdiag focuses on:

- simplicity
- no dependencies
- fast troubleshooting
- visual explanations

Graphs are only generated when they add value.

If a metric is extremely small, the report prints a short summary instead.

This keeps the output focused on **signal rather than noise**.

---

# Project structure

```
tcpdiag.py

plugins/
    retransmission.py
    rate_limit.py
    packet_pause.py
    bandwidth.py
    mtu_blackhole.py

wireshark/
    export_ws.lua
```