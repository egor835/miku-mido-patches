#!/bin/bash
#
# SPDX-License-Identifier: Apache-2.0
#
# Apply the mido patches on top of a synced Miku UI Cinderella tree.
# Usage: scripts/apply.sh <android source root>

set -euo pipefail

TOP=$(realpath "${1:?usage: $0 <android source root>}")
HERE=$(dirname "$(realpath "$0")")/..

GIT_IDENT=(-c user.name="${GIT_AUTHOR_NAME:-mido-patches}" -c user.email="${GIT_AUTHOR_EMAIL:-mido-patches@localhost}")

# Patch directory name -> path in the source tree
declare -A PROJECTS=(
    [build_make]=build/make
    [device_qcom_sepolicy-legacy-um]=device/qcom/sepolicy-legacy-um
    [device_xiaomi_mido]=device/xiaomi/mido
    [frameworks_av]=frameworks/av
    [frameworks_native]=frameworks/native
    [kernel_xiaomi_mido]=kernel/xiaomi/mido
)

for dir in "${!PROJECTS[@]}"; do
    path="$TOP/${PROJECTS[$dir]}"
    echo "==> ${PROJECTS[$dir]}"
    git -C "$path" checkout -q -B mido-patches
    git "${GIT_IDENT[@]}" -C "$path" am -q --committer-date-is-author-date "$HERE/patches/$dir"/*.patch
done

echo "==> vendor/xiaomi/mido"
git -C "$TOP/vendor/xiaomi/mido" checkout -q -B mido-patches
git -C "$TOP/vendor/xiaomi/mido" apply "$HERE"/patches/vendor_xiaomi_mido/*.diff
python3 "$HERE/scripts/patch-camera-blobs.py" "$TOP"

echo "Done. Note: 'repo sync' detaches these branches; re-run on a fresh sync."
