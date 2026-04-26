#!/usr/bin/env python3

import csv
import sys
import datetime

def load_devices(path: str = "devices.csv") -> list[tuple[str, str]]:
    devices = []
    with open(path, newline="") as f:
        for mac, name in csv.reader(f):
            devices.append((mac.strip(), name.strip()))
    return devices

def load_results(path: str) -> list[tuple[float, str, int]]:
    rows = []
    with open(path, newline="") as f:
        for row in csv.reader(f):
            timestamp, mac, _contact, _frame, fast_hr, _slow_hr = row
            rows.append((float(timestamp), mac.strip(), int(fast_hr)))
    return rows

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <results.csv>", file=sys.stderr)
        sys.exit(1)

    devices = load_devices("devices.csv")
    macs = [mac for mac, _ in devices]
    labels = [name for _, name in devices]

    rows = load_results(sys.argv[1])
    if not rows:
        print("No data in results file.", file=sys.stderr)
        sys.exit(1)

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
