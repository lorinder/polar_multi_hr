#!/usr/bin/env python3

import csv
import sys
import datetime

Device = tuple[str, str]          # (mac, label)
Reading = tuple[float, str, int]  # (timestamp, mac, fast_hr)

def load_results(path: str) -> tuple[list[Device], list[Reading]]:
    devices_seen: dict[str, str] = {}
    rows = []
    with open(path, newline="") as f:
        for row in csv.reader(f):
            timestamp, mac, label, _contact, _frame, fast_hr, _slow_hr = row
            mac = mac.strip()
            label = label.strip()
            if mac not in devices_seen:
                devices_seen[mac] = label
            rows.append((float(timestamp), mac, int(fast_hr)))

    def sort_key(item):
        mac, label = item
        return (0, label.lower()) if label else (1, mac)

    devices = sorted(devices_seen.items(), key=sort_key)
    return devices, rows

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <results.csv>", file=sys.stderr)
        sys.exit(1)

    devices, rows = load_results(sys.argv[1])
    if not rows:
        print("No data in results file.", file=sys.stderr)
        sys.exit(1)

    macs = [mac for mac, _ in devices]
    labels = [label or mac for mac, label in devices]

    min_sec = int(min(ts for ts, _, _ in rows))
    max_sec = int(max(ts for ts, _, _ in rows))

    # For each (second, mac), keep the latest sample's fast_hr
    latest: dict[tuple[int, str], tuple[float, int]] = {}
    for ts, mac, fast_hr in rows:
        sec = int(ts)
        key = (sec, mac)
        if key not in latest or ts > latest[key][0]:
            latest[key] = (ts, fast_hr)

    out_path = sys.argv[1].replace(".csv", "_second_by_second.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time", "unix_epoch"] + labels)
        for sec in range(min_sec, max_sec + 1):
            dt = datetime.datetime.fromtimestamp(sec).strftime("%Y-%m-%d %H:%M:%S")
            hr_values = []
            for mac in macs:
                entry = latest.get((sec, mac))
                hr_values.append(entry[1] if entry is not None else "")
            writer.writerow([dt, sec] + hr_values)

    print(f"Written to {out_path}")

if __name__ == "__main__":
    main()
