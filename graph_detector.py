"""
Expected CSV columns from the Wireshark Lua exporter

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
"""

import csv
import sys
import importlib

if len(sys.argv) != 3:
    print("usage: python3 graph_detector.py <plugin> <file.csv>")
    sys.exit(1)

plugin_name = sys.argv[1]
csv_file = sys.argv[2]

try:
    plugin = importlib.import_module("plugins." + plugin_name)
except Exception as e:
    print("failed to load plugin:", plugin_name)
    print(e)
    sys.exit(1)

try:
    with open(csv_file, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
except Exception as e:
    print("failed to read csv:", csv_file)
    print(e)
    sys.exit(1)

if not rows:
    print("empty csv")
    sys.exit(1)

cols = [c.strip() for c in rows[0].keys()]
required = getattr(plugin, "REQUIRED_COLUMNS", [])
missing = [c for c in required if c not in cols]

if missing:
    print("missing columns:", ", ".join(missing))
    print("found columns:", ", ".join(cols))
    sys.exit(1)

try:
    result = plugin.detect(rows)
    html = plugin.render(result)
except Exception as e:
    print("plugin failed:", plugin_name)
    print(e)
    sys.exit(1)

with open("graph.html", "w", encoding="utf-8") as f:
    f.write(html)

print("graph.html written")