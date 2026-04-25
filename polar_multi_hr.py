#!/usr/bin/env python3

import asyncio
import csv
import curses
import os
import time
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

HR_SERVICE = "0000180d-0000-1000-8000-00805f9b34fb"
POLAR_MFR_ID = 0x006B

class PolarH10MfrAdv:
    def __init__(self, mfr):
       self.battery_status = 0 if mfr[0] & 0x01 == 0 else 1
       self.sensor_contact = 0 if mfr[0] & 0x02 == 0 else 1
       self.frame_counter = (mfr[0] >> 2) & 0x07
       self.broadcast_bit = 0 if mfr[0] & 0x20 == 0 else 1
       self.data_type = 0 if mfr[0] & 0x40 == 0 else 1
       self.status_flags = 0 if mfr[0] & 0x80 == 0 else 1
       self.khz_code = mfr[1]
       self.fast_avg_hr = mfr[2]
       self.slow_avg_hr = mfr[3]

def decode_polar10_mfr_adv(mfr):
    return PolarH10MfrAdv(mfr)

def process_advertisement(device: BLEDevice, adv: AdvertisementData) -> tuple[str, PolarH10MfrAdv] | None:
    if HR_SERVICE not in (adv.service_uuids or []):
        return None
    if POLAR_MFR_ID not in (adv.manufacturer_data or {}):
        return None
    if not (device.name or "").startswith("Polar H10 "):
        return None
    mfr_dec = decode_polar10_mfr_adv(adv.manufacturer_data[POLAR_MFR_ID])
    return (device.address, mfr_dec)

LOST_TIMEOUT = 5.0

class Display:
    COLOR_RED = 1

    def __init__(self, stdscr, names: dict[str, str]):
        self.stdscr = stdscr
        self.names = names
        self.last_mfr: dict[str, PolarH10MfrAdv | None] = {}
        self.last_seen: dict[str, float] = {}
        self._order: list[str] = sorted(names.keys(), key=self._sort_key)
        curses.start_color()
        curses.init_pair(self.COLOR_RED, curses.COLOR_RED, curses.COLOR_BLACK)
        stdscr.clear()
        self._render_all()

    def _sort_key(self, mac: str) -> tuple:
        if mac in self.names:
            return (0, self.names[mac].lower())
        return (1, mac)

    def update(self, mac: str, mfr: PolarH10MfrAdv) -> None:
        self.last_mfr[mac] = mfr
        self.last_seen[mac] = time.monotonic()
        new_order = sorted(set(self.last_mfr.keys()) | set(self.names.keys()), key=self._sort_key)
        if new_order != self._order:
            self._order = new_order
            self._render_all()
        else:
            self._render_row(self._order.index(mac), mac, mfr)
            self.stdscr.refresh()

    def tick(self) -> None:
        now = time.monotonic()
        changed = False
        for mac, last in self.last_seen.items():
            if now - last >= LOST_TIMEOUT and self.last_mfr[mac] is not None:
                self.last_mfr[mac] = None
                self._render_row(self._order.index(mac), mac, None)
                changed = True
        if changed:
            self.stdscr.refresh()

    def _render_row(self, row: int, mac: str, mfr: PolarH10MfrAdv | None) -> None:
        max_rows, _ = self.stdscr.getmaxyx()
        if row >= max_rows - 2:
            return
        if mac not in self.last_seen:
            status, attr = "", curses.A_NORMAL
        elif mfr is None:
            status, attr = "LOST", curses.color_pair(self.COLOR_RED)
        elif not mfr.sensor_contact:
            status, attr = "NO CONTACT", curses.color_pair(self.COLOR_RED)
        elif not mfr.battery_status:
            status, attr = "LOW BATTERY", curses.color_pair(self.COLOR_RED)
        elif not (10 <= mfr.fast_avg_hr <= 250):
            status, attr = "INVALID", curses.color_pair(self.COLOR_RED)
        else:
            status, attr = f"{mfr.fast_avg_hr} bpm", curses.A_NORMAL
        label = self.names.get(mac, mac)
        self.stdscr.addstr(row, 0,  f"[{row+1:03d}]")
        self.stdscr.addstr(row, 6,  f"{label:<20}")
        self.stdscr.addstr(row, 26, f"{status:<15}", attr)

    def _render_all(self) -> None:
        max_rows, _ = self.stdscr.getmaxyx()
        for row in range(max_rows - 2):
            if row < len(self._order):
                mac = self._order[row]
                self._render_row(row, mac, self.last_mfr.get(mac))
            else:
                self.stdscr.move(row, 0)
                self.stdscr.clrtoeol()
        hidden = max(0, len(self._order) - (max_rows - 2))
        if hidden:
            self.stdscr.addstr(max_rows - 2, 0, f"[{hidden} more devices]")
        else:
            self.stdscr.move(max_rows - 2, 0)
            self.stdscr.clrtoeol()
        self._render_status_bar()
        self.stdscr.refresh()

    def _render_status_bar(self) -> None:
        max_rows, max_cols = self.stdscr.getmaxyx()
        msg = "Polar H10 Heart Rate Recorder --- Press Control-C to exit."
        bar = msg[:max_cols].ljust(max_cols)
        try:
            self.stdscr.addstr(max_rows - 1, 0, bar, curses.A_REVERSE)
        except curses.error:
            pass

async def tick_loop(display: Display) -> None:
    while True:
        await asyncio.sleep(1)
        display.tick()

def load_device_names(path: str = "devices.csv") -> dict[str, str]:
    names = {}
    if os.path.exists(path):
        with open(path, newline="") as f:
            for mac, name in csv.reader(f):
                names[mac.strip()] = name.strip()
    return names

async def main(stdscr) -> None:
    display = Display(stdscr, load_device_names())
    asyncio.create_task(tick_loop(display))
    filename = time.strftime("result_%Y%m%d_%H%M.csv")
    with open(filename, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        async with BleakScanner() as scanner:
            async for device, adv in scanner.advertisement_data():
                if result := process_advertisement(device, adv):
                    mac, mfr_dec = result
                    display.update(mac, mfr_dec)
                    writer.writerow([
                        f"{time.time():.6f}",
                        mac,
                        mfr_dec.sensor_contact,
                        mfr_dec.frame_counter,
                        mfr_dec.fast_avg_hr,
                        mfr_dec.slow_avg_hr,
                    ])

if __name__ == "__main__":
    try:
        curses.wrapper(lambda stdscr: asyncio.run(main(stdscr)))
    except KeyboardInterrupt:
        pass
