#!/usr/bin/env python3
#
# SPDX-License-Identifier: Apache-2.0
#
# Apply the mido camera fixes to the Xiaomi blobs in vendor/xiaomi/mido
# (Evolution-X `cnb`), so that no modified proprietary binaries have to be
# redistributed. Mirrors the blob_fixups added to extract-files.py.
#
#  - libmmcamera2_sensor_modules.so
#      * sensor_init_xml_probe: don't skip modules whose EEPROM module ID isn't
#        recognized (bne -> nop); the kernel still matches sensor ID/address.
#      * port_sensor_create: treat a PDAF init failure as "no PDAF" instead of
#        failing the stream (bgt.w -> b.w).
#  - mm-qcamera-daemon: add libpdafshim.so to DT_NEEDED.
#
# Usage: patch-camera-blobs.py <android source root>

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

SENSOR_MODULES = 'vendor/xiaomi/mido/proprietary/vendor/lib/libmmcamera2_sensor_modules.so'
DAEMON = 'vendor/xiaomi/mido/proprietary/vendor/bin/mm-qcamera-daemon'

SENSOR_MODULES_ORIG = '143caf50b1872023053a53f425789d219504131e3e3037292a588a75de35fc8c'
SENSOR_MODULES_NEW = '8818d7ba0209f6ab27bf487db04a1ae099c1bc54c07488e95ffb82bcd16e759b'
DAEMON_ORIG = '567bb936ecb457f3c67d492ec10fe26b1649d906d98e18b1a176941f3804edf8'

SENSOR_PATCHES = [
    (bytes.fromhex('002876d1d9f80000'), bytes.fromhex('002800bfd9f80000')),
    (bytes.fromhex('ff3f00f3f885dff87c04'), bytes.fromhex('ff3f00f0f8bddff87c04')),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def patch_sensor_modules(top: Path) -> None:
    path = top / SENSOR_MODULES
    digest = sha256(path)
    if digest == SENSOR_MODULES_NEW:
        print(f'{path.name}: already patched')
        return
    if digest != SENSOR_MODULES_ORIG:
        sys.exit(f'{path}: unexpected sha256 {digest}, refusing to patch')

    data = path.read_bytes()
    for old, new in SENSOR_PATCHES:
        if data.count(old) != 1:
            sys.exit(f'{path}: pattern {old.hex()} not found exactly once')
        data = data.replace(old, new)
    path.write_bytes(data)

    if sha256(path) != SENSOR_MODULES_NEW:
        sys.exit(f'{path}: result sha256 mismatch')
    print(f'{path.name}: patched')


def find_patchelf(top: Path) -> str:
    bundled = sorted((top / 'prebuilts/extract-tools/linux-x86/bin').glob('patchelf-*'))
    if bundled:
        return str(bundled[-1])
    found = shutil.which('patchelf')
    if not found:
        sys.exit('patchelf not found')
    return found


def patch_daemon(top: Path) -> None:
    path = top / DAEMON
    patchelf = find_patchelf(top)
    needed = subprocess.run([patchelf, '--print-needed', str(path)],
                            check=True, capture_output=True, text=True).stdout.split()
    if 'libpdafshim.so' in needed:
        print(f'{path.name}: already patched')
        return
    digest = sha256(path)
    if digest != DAEMON_ORIG:
        sys.exit(f'{path}: unexpected sha256 {digest}, refusing to patch')
    subprocess.run([patchelf, '--add-needed', 'libpdafshim.so', str(path)], check=True)
    print(f'{path.name}: patched')


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(f'usage: {sys.argv[0]} <android source root>')
    top = Path(sys.argv[1]).resolve()
    patch_sensor_modules(top)
    patch_daemon(top)


if __name__ == '__main__':
    main()
