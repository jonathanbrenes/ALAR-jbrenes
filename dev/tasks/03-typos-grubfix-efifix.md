# Task 03 — Multiple typos in grubfix/efifix causing failures

- **Priority**: 1 (Critical)
- **Type**: Bug
- **Scripts**: `src/action_implementation/grubfix-impl.sh`, `src/action_implementation/efifix-impl.sh`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

> **Note**: All typos in this task are in grubfix-impl.sh and efifix-impl.sh. Once Task 01 (bootfix unification) replaces both scripts, these fixes will no longer be required.

## Problem: undefined function calls, wrong file paths, and undefined variable references.

## Affected lines and fixes

### grubfix-impl.sh

**Line 49** — `recover_ubuntu()`: calls `resolve-pre` but the function is `resolv-pre`
```bash
# Current (line 49)
    resolve-pre
# Fix
    resolv-pre
```

**Line 42** — `recover_suse()`: misplaced `$` in variable expansion
```bash
# Current (line 42)
    grub2-install "{$RECOVER_DISK_PATH}"
# Fix
    grub2-install "${RECOVER_DISK_PATH}"
```

### efifix-impl.sh

**Line 10** — `resolv-after()`: wrong filename
```bash
# Current (line 10)
    mv /etc/resolv.conf.org /etc/resolve.conf
# Fix
    mv /etc/resolv.conf.org /etc/resolv.conf
```

**Line 135** — `recover_ubuntu()`: calls `resolve-pre` but the function is `resolv-pre`
```bash
# Current (line 135)
    resolve-pre
# Fix
    resolv-pre
```

**Line 143** — `recover_ubuntu()`: uses `$new_efi_uuid` but the variable defined on line 142 is `$new_uuid`
```bash
# Current (lines 141-143)
    read -ra EFI_DISK <<<$(blkid $efi_part_path)
    new_uuid=$(for i in "${EFI_DISK[@]}"; do grep ^UUID= <<<$i; done)
    sed -i "s/$uuid_to_be_replaced/UUID=$new_efi_uuid/" /etc/fstab
# Fix — use $new_uuid consistently
    read -ra EFI_DISK <<<$(blkid $efi_part_path)
    new_uuid=$(for i in "${EFI_DISK[@]}"; do grep ^UUID= <<<$i; done)
    sed -i "s/$uuid_to_be_replaced/$new_uuid/" /etc/fstab
```

**Lines 134-146** — `recover_ubuntu()`: no EFI partition existence check (unlike all other distro functions which check `findmnt -n -o SOURCE /boot/efi`)
```bash
# Fix — add check at function start, matching the pattern from recover_redhat()
recover_ubuntu() {
    resolv-pre

    efi_part_path=$(findmnt -n -o SOURCE /boot/efi)
    if [[ -z ${efi_part_path} ]]; then
        echo "No EFI partition found"
        echo "Aborting! Are you running it on a GEN1 image?"
        exit 1
    fi
    # ... rest of function
```

## Impact

- `resolve-pre` typo: function not found → script aborts on Ubuntu (both grubfix and efifix)
- `"{$RECOVER_DISK_PATH}"` typo: grub2-install receives literal `{/dev/sdc}` → fails on SUSE
- `resolve.conf` typo: resolv.conf not restored after efifix → DNS breaks on recovered VM
- `$new_efi_uuid` typo: undefined variable → fstab UUID replacement is empty → fstab corrupted
- Missing EFI check: `recover_ubuntu()` proceeds without EFI partition → mkfs on wrong device
