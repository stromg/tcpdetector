# TCP Traffic Detector

A small tool that analyzes TCP captures exported from Wireshark and tries to detect common network problems.

The tool runs small plugins that look for typical traffic patterns such as packet loss, rate limiting, or long pauses in traffic.

Input: CSV exported from Wireshark.  
Output: simple HTML report.

## Current plugins

- `retransmission`
- `rate_limit`
- `packet_pause`

Each plugin detects a different TCP symptom.

### 1. retransmission

Detects packet loss by counting TCP retransmissions.

When packets are lost in the network, TCP resends them.

Typical causes:

- physical link errors
- Wi‑Fi interference
- congestion drops
- overloaded routers
- duplex problems
- MTU / tunnel issues in some cases

Normal traffic:

```text
packet
packet
packet
packet
packet
```

Packet loss:

```text
packet
packet
packet
   X   (packet lost)
packet
packet
retransmit packet
```

What the plugin detects:

```text
retransmission rate (%)
difference between small and large packets
```

### 2. rate_limit

Detects traffic pacing or rate limiting.

Some systems send packets at fixed intervals.

Typical causes:

- traffic shaping
- QoS policers
- application pacing
- bandwidth limiters
- token bucket style limiters

Normal TCP traffic:

```text
packet packet packet
packet packet
packet packet packet
```

Rate limited traffic:

```text
packet
----- 10 ms -----
packet
----- 10 ms -----
packet
----- 10 ms -----
packet
```

What the plugin detects:

```text
strong peak in packet interval histogram
```

Typical suspicious values:

```text
10 ms
20 ms
25 ms
50 ms
```

### 3. packet_pause

Detects long pauses between TCP data packets.

This is different from packet loss. Packets are not necessarily lost, but the flow temporarily stops.

Typical causes:

- congestion
- queueing
- Wi‑Fi airtime contention
- endpoint processing delay
- CPU delay
- traffic shaping
- policers

Normal traffic:

```text
packet
packet
packet
packet
packet
```

Packet pause:

```text
packet
packet
packet

----- 120 ms pause -----

packet
packet
```

What the plugin detects:

```text
packet pause rate (%)
max packet interval
```

A packet pause is a long time gap between TCP data packets. In the current plugin, a pause means a gap greater than the configured threshold.

## Design principle

Graphs are only generated when they support a meaningful conclusion.

If a metric is extremely small, the tool prints a summary instead of generating a graph.

Example:

```text
Retransmission levels are extremely low (<0.1%).
No graph generated because the values would not be visually meaningful.
```

This keeps the output focused on signal rather than noise.

## Summary

Each plugin detects a different symptom:

```text
retransmission -> packet loss
rate_limit     -> traffic shaping / pacing
packet_pause   -> long pauses in packet flow
```

Together they help identify common TCP problems such as:

```text
packet loss
rate limiting
Wi‑Fi interference
congestion
queueing delays
endpoint stalls
```

## File layout

Suggested layout:

```text
graph_detector.py
plugins/
    __init__.py
    retransmission.py
    rate_limit.py
    packet_pause.py
```

## Run the detector

Examples:

```bash
python3 graph_detector.py retransmission /tmp/ws_export.csv
python3 graph_detector.py rate_limit /tmp/ws_export.csv
python3 graph_detector.py packet_pause /tmp/ws_export.csv
```

The detector writes:

```text
graph.html
```

Open it in a browser.

## Wireshark Lua exporter

The included Lua script exports the CSV format expected by the Python tool.

Exported columns:

```text
Time
Delta
Source
Destination
Stream
Seq
Ack
TCP Len
Length
Retrans
DupAck
AckRTT
Window
```

### Install the Lua plugin

Do not run the script from the Lua console. It should be loaded as a Wireshark plugin.

#### Linux

Create the personal plugin directory if needed:

```bash
mkdir -p ~/.local/lib/wireshark/plugins
```

Copy the file:

```bash
cp export_tcp.lua ~/.local/lib/wireshark/plugins/
```

Restart Wireshark.

#### macOS

Create the personal plugin directory if needed:

```bash
mkdir -p ~/.local/lib/wireshark/plugins
```

Copy the file:

```bash
cp export_tcp.lua ~/.local/lib/wireshark/plugins/
```

Restart Wireshark.

If your setup uses a different personal plugin path, check it with:

```bash
wireshark -G folders
```

Look for:

```text
Personal Lua Plugins
```

#### Windows

Copy `export_tcp.lua` into your personal Wireshark plugins directory.

Typical location:

```text
%APPDATA%\Wireshark\plugins
```

If needed, create the folder first.

Then restart Wireshark.

### Verify that the plugin loaded

In Wireshark:

```text
Help -> About Wireshark -> Plugins
```

You should see `export_tcp.lua`.

### Use the exporter

1. Start Wireshark
2. Open a TCP capture
3. Let Wireshark dissect the packets
4. The exporter writes a CSV file

The Lua plugin automatically chooses an output path based on the operating system:

- Windows: `%TEMP%\ws_export.csv`
- Linux/macOS: `/tmp/ws_export.csv`

### Check the exported CSV

Linux/macOS:

```bash
head /tmp/ws_export.csv
```

Windows PowerShell:

```powershell
Get-Content "$env:TEMP\ws_export.csv" -TotalCount 5
```

## Notes

- The Lua exporter must be loaded at Wireshark startup
- `Field.new(...)` must be defined before taps are created
- The Python plugins expect the exported CSV header names exactly as written above
