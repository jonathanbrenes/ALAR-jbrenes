# Task 09 — Azure Linux 3: NVMe native boot with separate /boot partition

- **Priority**: 2 (High)
- **Type**: Design consideration
- **Scripts**: Rust binary (partition detection), mount logic
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

## Problem

Azure Linux 3 is the only distro that boots natively from NVMe (`/dev/nvme0n1`) with a 3-partition layout:

| Partition | Size | Filesystem | Mount point |
|:------|:------|:------|:------|
| p1 | 64 MB | vfat | /boot/efi |
| p2 | 500 MB | ext4 | /boot |
| p3 | remaining | ext4 | / |

All other distros either:
- Use SCSI (`/dev/sda`) natively, or
- Use NVMe but with 2 partitions (EFI + root, no separate `/boot`)

When ALAR attaches the broken disk to the rescue VM, the NVMe disk appears as **SCSI** (`/dev/sdX`). The partition layout is preserved, but the device names change.

## Impact

1. The ALAR binary's partition detection must handle the 3-partition layout (separate `/boot`)
2. The mount logic must mount `/boot` separately before `/boot/efi`
3. Scripts that reference `$boot_part_path` must handle it being non-empty
4. `fstab-impl.sh` must preserve the separate `/boot` entry

## Current handling

The ALAR binary already exports `$boot_part_path` (non-empty when `/boot` is separate). Review needed:

- `fstab-impl.sh` `boot_efi_mnt()` (lines 33-82): handles `/boot` and `/boot/efi` — should work if `$boot_part_path` and `efi_part_path` are set correctly
- Boot scripts: assume `/boot` is on the root partition unless calling `findmnt /boot`

## What to verify

1. Confirm the Rust binary correctly detects 3-partition NVMe layout when re-attached as SCSI
2. Confirm `$boot_part_path` is set to the correct device for the separate `/boot`
3. Test `fstab-impl.sh` on an Azure Linux 3 VM — does it preserve the separate `/boot` entry?
4. Test `initrd-impl.sh` `recover_azurelinux()` — does it find kernels/initramfs in the mounted `/boot`?

## Related tasks

- Task 08 (Azure Linux EFI vendor dir)
- Task 17 (Azure Linux GRUB commands)
