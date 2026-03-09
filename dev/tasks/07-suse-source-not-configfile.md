# Task 07 — SUSE uses `source` not `configfile` in EFI grub.cfg

- **Priority**: 2 (High)
- **Type**: Bug / Design consideration
- **Script**: `src/action_implementation/efifix-impl.sh`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

> **Note**: This fix applies to efifix-impl.sh. Once Task 01 (bootfix unification) replaces efifix-impl.sh, this task will no longer be required.

## Problem

The SUSE EFI grub.cfg redirect must use the `source` command, not `configfile`. Using `configfile` starts a completely new configuration context (environment variables are reset), while `source` preserves the current context. SUSE's boot chain depends on variables set before the redirect.

## Affected lines

### efifix-impl.sh — `recover_suse()` (lines 61-64)

```bash
# Current
echo "search --no-floppy --fs-uuid --set=dev $boot_uuid" >  /boot/efi/EFI/$(ls /boot/efi/EFI | grep -i -E "sles")/grub.cfg
echo 'set prefix=($dev)/grub2
export $prefix
configfile $prefix/grub.cfg' >>  /boot/efi/EFI/$(ls /boot/efi/EFI | grep -i -E "sles")/grub.cfg
```

Two problems:
1. Uses `configfile` — should be `source`
2. Greps for `sles` — SUSE EFI vendor dir is actually `BOOT` (uppercase), not `sles`

## Evidence from 97-VM data

All SUSE 15+ images (SP4, SP5, SP6, SP7, SUSE 16) use the `BOOT` directory:
- `/boot/efi/EFI/BOOT/grub.cfg`

SUSE 12 SP5 uses a `normal` redirect:
```
normal
```

SUSE 15+ uses:
```
search --no-floppy --fs-uuid --set=dev <boot_uuid>
set prefix=($dev)/grub2
source $prefix/grub.cfg
```

## How to fix

```bash
# Detect the correct EFI vendor dir for SUSE (it's BOOT, not sles)
vendor_dir="BOOT"
boot_uuid=$(blkid -s UUID -o value $(findmnt /boot -o SOURCE -n))

cat > "/boot/efi/EFI/${vendor_dir}/grub.cfg" <<EOF
search --no-floppy --fs-uuid --set=dev ${boot_uuid}
set prefix=(\$dev)/grub2
source \$prefix/grub.cfg
EOF
```

## Related tasks

- Task 06 (EFI redirect shim) — this is the SUSE-specific aspect of the same problem
- Task 01 (bootfix unification) — the unified script must handle per-distro redirect methods
