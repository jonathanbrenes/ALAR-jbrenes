# Task 14 — Boot mode detection using /boot/efi presence instead of /sys/firmware/efi

- **Priority**: 3 (Medium)
- **Type**: Bug (in planned helpers.sh)
- **Script**: Planned `helpers.sh` / bootfix
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

## Problem

Some code paths (planned and existing) detect EFI mode by checking if `/boot/efi` is mounted. Gen1 BIOS VMs can still have `/boot/efi` mounted (it's just empty or unused), which leads to false EFI detection.

The ALAR binary already sets `$efi_part_path` (non-empty = EFI), which is the primary signal. However, if scripts need a secondary check, `/sys/firmware/efi` is the correct path — but with a caveat: inside chroot, `/sys/firmware/efi` reflects the **rescue VM** (BIOS), not the broken disk.

## Current detection patterns

### efifix-impl.sh — `recover_redhat()` (line 16)

```bash
efi_part_path=$(findmnt -n -o SOURCE /boot/efi)
if [[ -z ${efi_part_path} ]]; then
    echo "No EFI partition found"
    exit 1
fi
```

This pattern is acceptable inside efifix (which should only run on EFI systems), but would be wrong as a general boot mode detector.

## Correct approach

1. **Primary signal**: `$efi_part_path` environment variable (set by the ALAR binary)
2. **Inside scripts**: `[[ -n "$efi_part_path" ]]` → EFI mode
3. **Do NOT use**: `[[ -d /sys/firmware/efi ]]` inside chroot — it reflects the rescue VM
4. **Do NOT use**: `findmnt /boot/efi` as a mode detector — Gen1 VMs may have it mounted

## How to fix

Document this and ensure all boot mode branching uses `$efi_part_path`:

```bash
if [[ -n "$efi_part_path" ]]; then
    # EFI mode
    ...
else
    # BIOS mode
    ...
fi
```

This is the pattern that the unified bootfix (Task 01) should use for auto-detecting boot mode.
