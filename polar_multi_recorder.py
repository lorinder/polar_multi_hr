#!/usr/bin/env python3

import asyncio
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
    def get_dict(self):
        d = dict([
              ('battery_status',    self.battery_status),
              ('sensor_contact',    self.sensor_contact),
              ('frame_counter',     self.frame_counter),
              ('broadcast_bit',     self.broadcast_bit),
              ('data_type',         self.data_type),
              ('status_flags',      self.status_flags),
              ('khz_code',          self.khz_code),
              ('fast_avg_hr',       self.fast_avg_hr),
              ('slow_avg_hr',       self.slow_avg_hr),
            ])
        return d

def decode_polar10_mfr_adv(mfr):
    return PolarH10MfrAdv(mfr)

def callback(device: BLEDevice, adv: AdvertisementData) -> None:
    if HR_SERVICE not in (adv.service_uuids or []):
        return
    if POLAR_MFR_ID not in (adv.manufacturer_data or {}):
        return
    if not (device.name or "").startswith("Polar H10 "):
        return
    mfr = adv.manufacturer_data[POLAR_MFR_ID]
    mfr_dec = decode_polar10_mfr_adv(mfr)
    print(f"{device.address}  {mfr_dec.get_dict()}")

async def main() -> None:
    async with BleakScanner(callback):
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
