import csv
import importlib
import sys
from pathlib import Path


PLUGINS_DIR = Path(__file__).parent / "plugins"


def list_plugins():
    return sorted(
        p.stem for p in PLUGINS_DIR.glob("*.py")
        if p.name != "__init__.py"
    )


def load_csv(path):
    meta = {}
    data_lines = []

    with open(path, encoding="utf-8-sig", newline="") as f:
        for line in f:
            if line.startswith("#"):
                line = line[1:].strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    meta[k.strip()] = v.strip()
            else:
                data_lines.append(line)

    rows = list(csv.DictReader(data_lines))

    for r in rows:
        r["_capture_start"] = meta.get("capture_start", "")
        r["_capture_end"] = meta.get("capture_end", "")

    return rows


def print_usage_and_plugins():
    print("usage: python3 tcpdiag.py <plugin> <file.csv>")
    print("Available plugins:")
    for plugin_name in list_plugins():
        print(f" - {plugin_name}")


def main():
    if len(sys.argv) == 1:
        print_usage_and_plugins()
        sys.exit(0)

    if len(sys.argv) != 3:
        print("usage: python3 tcpdiag.py <plugin> <file.csv>")
        sys.exit(1)

    plugin_name = sys.argv[1]
    csv_file = sys.argv[2]

    if plugin_name not in list_plugins():
        print(f"plugin not found: {plugin_name}")
        print_usage_and_plugins()
        sys.exit(1)

    try:
        plugin = importlib.import_module(f"plugins.{plugin_name}")
    except Exception as e:
        print(f"failed to load plugin: {plugin_name}")
        print(e)
        sys.exit(1)

    try:
        rows = load_csv(csv_file)
    except Exception as e:
        print(f"failed to read csv: {csv_file}")
        print(e)
        sys.exit(1)

    if not rows:
        print("empty csv")
        sys.exit(1)

    cols = [c.strip() for c in rows[0].keys() if c is not None]
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
        print(f"plugin failed: {plugin_name}")
        print(e)
        sys.exit(1)

    with open("graph.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"graph.html written using plugin: {plugin_name}")


if __name__ == "__main__":
    main()