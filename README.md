# polar_multi_hr

Records heart rate data from a large number of Polar H10 chest straps
simultaneously, displaying it live and saving it to a CSV file for
later analysis.

Most heart rate tools work by forming a dedicated Bluetooth connection
to each device — the same way your phone connects to headphones. This
limits you to a handful of devices at most. polar_multi_hr works
differently: the Polar H10 continuously broadcasts its heart rate as a
short radio advertisement, and this tool simply listens for those
broadcasts without ever connecting. Because there is no connection,
there is no limit on the number of devices — a single laptop can pick up
readings from dozens of sensors at once, as long as they are within
Bluetooth range. It also means no pairing or other setup is needed —
just switch the sensors on and they will be detected automatically.

## What it does

- Scans for nearby Polar H10 devices continuously
- Shows each device's heart rate in a live terminal display, with
  status indicators for lost signal, no skin contact, and low battery
- Appends every reading to a timestamped CSV file in the current
  directory
- Converts raw CSV output to a tidy second-by-second summary with one
  column per device via `get_second_by_second.py`

### Display status values

| Status | Meaning |
|--------|---------|
| `NNN bpm` | Current heart rate in beats per minute |
| `INVALID` | Heart rate value outside the plausible range (< 10 or > 250 bpm) |
| `NO CONTACT` | Sensor is not in contact with skin |
| `LOW BATTERY` | Device battery is low |
| `LOST` | No advertisement received from this device in the last 5 seconds |

### CSV output columns

| Column | Description |
|--------|-------------|
| timestamp | Unix timestamp (seconds, 6 decimal places) |
| mac | Bluetooth MAC address of the device |
| sensor_contact | 1 if the sensor is in contact with skin, 0 otherwise |
| frame_counter | Rolling counter (0–7) from the device advertisement |
| fast_avg_hr | Fast-averaging heart rate (beats per minute) |
| slow_avg_hr | Slow-averaging heart rate (beats per minute) |

## Labelling devices

When running a session with multiple participants, it helps to
physically label each Polar H10 with a sticker (e.g. "P01", "Alice",
"Subject 3") so you can tell them apart. You can then create a
`devices.csv` file in the same directory as the script to map each
device's Bluetooth MAC address to that label:

```
D4:3B:22:AA:BB:CC,P01
F0:12:34:56:78:9A,P02
```

If this file is present, the display will show the label instead of
the raw MAC address. Devices are listed in alphabetical order by
label, with any unlabelled devices appearing afterwards sorted by MAC
address. The MAC address is always used in the CSV output regardless.

To find a device's MAC address, run the script without `devices.csv`
and note the address shown for each device as it appears.

## Requirements

- Python 3.10 or later
- A Bluetooth adapter
- One or more Polar H10 heart rate monitors (worn and active)

## Setup

### 1. Create a virtual environment

A virtual environment keeps the dependencies for this project isolated
from the rest of your system.

```bash
python3 -m venv venv
```

### 2. Activate the virtual environment

On Linux/macOS:
```bash
source venv/bin/activate
```

On Windows:
```bash
venv\Scripts\activate
```

You should see `(venv)` appear at the start of your terminal prompt.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Running

Make sure the virtual environment is active (see step 2 above), then:

```bash
python polar_multi_hr.py
```

Press `Ctrl+C` to stop recording. The output CSV file is named
`result_YYYYMMDD_HHMM.csv`, where the `YYYYMMDD_HHMM` part is the
timestamp of when the recording started.

## Post-processing

`get_second_by_second.py` converts a raw results CSV into a tidy
second-by-second summary, with one column per device:

```bash
python get_second_by_second.py result_20260425_2049.csv
```

It requires a `devices.csv` file in the current directory and writes
`<input>_second_by_second.csv` alongside the input file. Each row
covers one integer second and has a `time` column (human-readable
datetime), a `unix_epoch` column, and one column per device containing
the latest `fast_avg_hr` sample received within that second, or left
empty if no sample was received.

## Notes

- On Linux, Bluetooth access may require running as root or granting
  your user the necessary permissions. If you get a Bluetooth
  permission error, try `sudo python polar_multi_hr.py`.
- The H10 must be worn (or the electrodes bridged with your fingers)
  for the sensor contact flag to be active and heart rate to be
  reported.
- If you deactivate the virtual environment and come back later, just
  run `source venv/bin/activate` again before running the script.
