# Miku UI Cinderella (Android 17) for Redmi Note 4 / 4X (mido)

Patches to build [Miku UI](https://github.com/Miku-UI/manifesto) **Cinderella**
(`android-17.0.0_r1`) for the Xiaomi Redmi Note 4 Snapdragon (`mido`, MSM8953),
using the Evolution-X `cnb` device/vendor/kernel trees (kernel 4.19).

> Unofficial and for personal use. Miku UI asks that builds from unsupported
> device configurations are not published.

## Status

| Works | Notes |
|---|---|
| Boot, encryption (FBE), dynamic partitions (retrofit) | |
| RIL: calls, SMS, LTE data | VoLTE untested |
| Wi-Fi 2.4/5 GHz, Bluetooth, audio (speaker, earpiece, wired headset) | |
| Sensors, OTG, fingerprint (FPC and Goodix) | |
| Rear and front camera, 13 MP stills, video, AF | PDAF disabled when the module's EEPROM calibration isn't available (contrast AF) |

No setup wizard: Miku UI without GApps only ships AOSP `Provision`.

## Base revisions

| Path | Source | Base |
|---|---|---|
| Miku UI | `Miku-UI/manifesto` `Cinderella` | `521b67b` |
| `device/xiaomi/mido` | `Evolution-X-Devices/device_xiaomi_mido` `cnb` | `4cae883` |
| `vendor/xiaomi/mido` | `Evolution-X-Devices/vendor_xiaomi_mido` `cnb` | `36bc2ae` |
| `kernel/xiaomi/mido` | `Evolution-X-Devices/kernel_xiaomi_mido` `cnb` | `0a495a07e` |
| `hardware/xiaomi`, `hardware/qcom-caf/msm8953/*` | LineageOS `lineage-24.0[-caf-msm8953]` | |

## Usage

```sh
repo init -u https://github.com/Miku-UI/manifesto -b Cinderella --git-lfs
mkdir -p .repo/local_manifests
cp /path/to/this/repo/local_manifests/mido.xml .repo/local_manifests/
repo sync -c --force-sync --no-clone-bundle --no-tags

/path/to/this/repo/scripts/apply.sh .

. build/envsetup.sh
lunch miku_mido-cp2a-userdebug
make diva
```

`repo sync` resets the patched projects to their manifest revisions, so re-run
`apply.sh` after every sync.

Building needs a lot of RAM: Soong analysis alone takes ~20 GB. With 32 GB RAM
plus swap, `-j8` works; `-j12` ran out of memory.

## Installing

The Android 17 `update-binary` needs `MADV_WIPEONFORK` (kernel ≥ 4.14), so
recoveries with older kernels (e.g. OrangeFox with 4.9) abort right away.
Use the recovery from the build instead:

1. Flash `out/target/product/mido/recovery.img` to the `recovery` partition.
2. Boot into recovery, choose *Apply update from ADB*, then
   `adb sideload MikuUI-Cinderella-mido-*.zip`.
3. On first install, wipe data (*Wipe data/factory reset*).

The OTA flashes `super_dummy.img` over the stock `system`/`cust` partitions to
set up retrofit dynamic partitions. Back up `persist`, `modemst1/2` and `fsg`
before the first install.

## What the patches do

### Miku UI (generic, needed for any legacy QCOM device)

- **frameworks/native**: restore the gralloc 2/3 fallback in `libui`. Android 17
  only allows mapper 4+ (`require_gralloc4_or_newer`), which aborts composer
  and surfaceflinger on mapper 2.x devices.
- **build/make**: `update_dynamic_partitions` with one argument. The releasetools
  pass `unsparse_super_empty.img` (a LineageOS updater extension), which the AOSP
  updater in `bootable/deprecated-ota` rejects.
- **device/qcom/sepolicy-legacy-um**: declare the missing
  `vendor_persist_camera_prop`, use Miku's `device/miku/sepolicy/qcom` instead of
  Lineage's, keep the `icmp_socket` rule off core domains (Android 17's
  `pcc_component` neverallow), and drop a property label Miku already defines.
- **local manifest**: `hardware/qcom-caf/msm8953` namespace guards
  (`os_pickup_qssi.bp`), which Miku's manifest only creates for msm8996 and newer.

### device/xiaomi/mido

- Miku product makefile, FCM target level 7 plus the Lineage HAL framework
  matrix (Android 17 dropped FCM 6), Treble labeling checks as warnings.
- sepolicy: Miku sepolicy instead of `device/lineage/sepolicy`, with the Lineage
  bits mido needs (health, livedisplay, AIDL touch).
- fstab: `/dev/block/by-name` (Miku's init doesn't create
  `/dev/block/bootdevice`, so recovery couldn't find partitions).
- releasetools: ship `flash_super_dummy.sh` in the OTA and run it via `sh`
  (no `set_metadata` in the AOSP updater).
- USB: Lineage's AIDL basic USB HAL. The HIDL 1.3 one isn't labeled by Miku's
  sepolicy (so `UsbService` blocked boot on "Phone is starting"), and it reports
  a permanently connected port with unknown data status, which shows
  "Charging this device via USB" forever.
- Bluetooth: `bluetooth.core.le.vendor_capabilities.enabled=false`. Pronto
  (WCN36xx) answers `LE_ADV_FILTER` with a truncated opcode and the gd stack
  aborts.
- Camera: `libpdafshim`, plus blob fixups in `extract-files.py` (see below).

### Camera blobs

The mido camera blobs never attach EEPROM calibration data to rear modules
(the PDAF calibration pointer arrives as `NULL + 0x11f84`), and Xiaomi's sensor
module skips modules whose EEPROM module ID it doesn't recognize. Rear modules
from donor or swapped boards (blank EEPROM, or an ov13855 whose ID these blobs
can't decode) either weren't detected or crashed `mm-qcamera-daemon` on
full-resolution streams.

- `libmmcamera2_sensor_modules.so`: `bne -> nop` in `sensor_init_xml_probe`
  (stop skipping unknown modules; the kernel still matches sensor ID and I2C
  address), `bgt.w -> b.w` in `port_sensor_create` (a PDAF init failure means
  "no PDAF" instead of failing the stream).
- `libpdafshim` (linked into `mm-qcamera-daemon`): returns `NULL` from
  `PDAF_PhaseDetection_init` when there is no calibration data.

Modified Xiaomi binaries aren't included here. `scripts/patch-camera-blobs.py`
applies the same changes to the blobs in your `vendor/xiaomi/mido`, and checks
their hashes before and after.

## Layout

```
local_manifests/mido.xml       extra projects for .repo/local_manifests
patches/<project>/*.patch      git am series, one directory per project
patches/vendor_xiaomi_mido/    Android.bp change (applied with git apply)
scripts/apply.sh               applies everything to a synced tree
scripts/patch-camera-blobs.py  patches the camera blobs in place
```
