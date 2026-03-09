# Task 06 — EFI grub.cfg written as full standalone instead of redirect shim

- **Priority**: 2 (High)
- **Type**: Bug
- **Script**: `src/action_implementation/efifix-impl.sh`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

> **Note**: This fix applies to efifix-impl.sh. Once Task 01 (bootfix unification) replaces efifix-impl.sh, this task will no longer be required.

## Problem

`efifix-impl.sh` `recover_redhat()` (lines 30-31) generates a full `grub.cfg` at the EFI vendor path AND at `/boot/grub2/grub.cfg`. This creates two independent configs that diverge over time. The correct pattern is a small redirect shim at the EFI path that points to the main grub.cfg.

RHEL 7.x already shows this divergence in the 97-VM data — two different full configs at `/boot/efi/EFI/redhat/grub.cfg` and `/boot/grub2/grub.cfg`.

## Affected lines

### efifix-impl.sh — `recover_redhat()` (lines 30-31)

```bash
# Current (lines 30-31)
GRUB_DISABLE_OS_PROBER=true grub2-mkconfig -o /boot/grub2/grub.cfg
GRUB_DISABLE_OS_PROBER=true grub2-mkconfig -o /boot/efi/EFI/$(ls /boot/efi/EFI | grep -i -E "centos|redhat")/grub.cfg
```

The second `grub2-mkconfig` writes a full config to the EFI path. It should instead write a redirect shim.

### efifix-impl.sh — `recover_suse()` (lines 61-64)

```bash
# Current (lines 61-64)
echo "search --no-floppy --fs-uuid --set=dev $boot_uuid" > /boot/efi/EFI/.../grub.cfg
echo 'set prefix=($dev)/grub2
export $prefix
configfile $prefix/grub.cfg' >> /boot/efi/EFI/.../grub.cfg
```

This writes a `configfile` redirect, but SUSE uses `source` instead of `configfile`.

## Correct redirect shim patterns (from 97-VM data)

### RHEL 8+ / AlmaLinux 8+ — `configfile`

```bash
vendor_dir=$(ls /boot/efi/EFI | grep -i -E "centos|redhat|almalinux")
boot_uuid=$(blkid -s UUID -o value $(findmnt /boot -o SOURCE -n))
cat > "/boot/efi/EFI/${vendor_dir}/grub.cfg" <<EOF
search --no-floppy --fs-uuid --set=dev ${boot_uuid}
set prefix=(\$dev)/grub2
export \$prefix
configfile \$prefix/grub.cfg
EOF
```

### SUSE 15+ — `source` (NOT configfile)

```bash
vendor_dir="BOOT"  # SUSE uses BOOT, not sles
boot_uuid=$(blkid -s UUID -o value $(findmnt /boot -o SOURCE -n))
cat > "/boot/efi/EFI/${vendor_dir}/grub.cfg" <<EOF
search --no-floppy --fs-uuid --set=dev ${boot_uuid}
set prefix=(\$dev)/grub2
source \$prefix/grub.cfg
EOF
```

### Debian / Ubuntu — `configfile`

```bash
vendor_dir=$(ls /boot/efi/EFI | grep -i -E "debian|ubuntu")
boot_uuid=$(blkid -s UUID -o value $(findmnt / -o SOURCE -n))
cat > "/boot/efi/EFI/${vendor_dir}/grub.cfg" <<EOF
search.fs_uuid ${boot_uuid} root
set prefix=(\$root)/boot/grub
configfile \$prefix/grub.cfg
EOF
```

### Azure Linux 3 — no vendor dir

Azure Linux 3 has no EFI vendor dir. Its grub.cfg lives at `/boot/efi/boot/grub2/grub.cfg` (lowercase `boot`). This is a redirect to `/boot/grub2/grub.cfg`.

## How to fix

1. Generate the main grub.cfg only at the standard path (`/boot/grub2/grub.cfg` or `/boot/grub/grub.cfg`)
2. Write the EFI grub.cfg as a distro-appropriate redirect shim
3. Detect the vendor directory dynamically (include `almalinux` and `debian` in the grep pattern)
