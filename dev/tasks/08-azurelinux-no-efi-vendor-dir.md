# Task 08 — Azure Linux 3: No EFI vendor directory

- **Priority**: 2 (High)
- **Type**: Bug
- **Script**: `src/action_implementation/efifix-impl.sh`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev has no vendor-specific EFI directory (no `redhat`, `ubuntu`, etc. under `/boot/efi/EFI/`). It only has the fallback `BOOT/` directory. The grub.cfg lives at an unusual path: `/boot/efi/boot/grub2/grub.cfg` (lowercase `boot`, not inside `EFI/BOOT/`).

The current `efifix-impl.sh` `recover_azurelinux()` (lines 78-132) already handles this correctly by writing to `/boot/efi/boot/grub2/grub.cfg`. However, any common helper (like `get_efi_vendor_dir()`) must handle this special case.

## Evidence from 97-VM data

All 6 Azure Linux 3 images show:
- EFI directory: `/boot/efi/EFI/BOOT/` (only the fallback)
- grub.cfg location: `/boot/efi/boot/grub2/grub.cfg`
- EFI grub.cfg status: `no_efi_grubcfg` (no vendor-specific redirect)

## Affected lines

### efifix-impl.sh — `recover_azurelinux()` (lines 113-120)

```bash
# Current code (works for Azure Linux 3)
mkdir -p /boot/efi/boot/grub2
cd /boot/efi/boot/grub2

boot_uuid=$(blkid -s UUID -o value $(findmnt /boot -o SOURCE -n))
echo "search -n -u $boot_uuid -s" >  grub.cfg
echo 'set prefix=($root)/grub2
export $prefix
configfile $prefix/grub.cfg' >>  grub.cfg
```

This is correct. The task is to ensure future refactoring (Task 01, Task 13) doesn't break this pattern.

## What to ensure

1. `get_efi_vendor_dir()` must return failure (non-zero) for Azure Linux 3
2. The bootfix must have a dedicated Azure Linux path that writes to `/boot/efi/boot/grub2/grub.cfg`
3. Do not try to create a vendor dir for Azure Linux — this is by design

## Related tasks

- Task 13 (EFI vendor dir detection)
- Task 17 (Azure Linux GRUB commands and packages)
- Task 01 (bootfix unification must handle this)
