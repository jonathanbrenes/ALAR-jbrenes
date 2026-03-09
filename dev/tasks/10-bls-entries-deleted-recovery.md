# Task 10 — Recovery when /boot/loader/entries/ is deleted on BLS systems

- **Priority**: 2 (High)
- **Type**: Enhancement
- **Scripts**: `grubfix-impl.sh`, `efifix-impl.sh`, planned bootfix
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

RHEL 8+ and AlmaLinux 8+ use BLS (`GRUB_ENABLE_BLSCFG=true`). Boot entries are stored as individual `.conf` files in `/boot/loader/entries/`. If this directory or its contents are deleted, GRUB finds no boot entries and the VM fails to boot.

All 34 BLS-enabled images in the 97-VM dataset have `grubby` available.

## Detection

```bash
# BLS is enabled but entries are missing
if grep -q 'GRUB_ENABLE_BLSCFG=true' /etc/default/grub 2>/dev/null; then
    if [[ ! -d /boot/loader/entries ]] || [[ -z "$(ls /boot/loader/entries/*.conf 2>/dev/null)" ]]; then
        echo "BLS entries missing — need to regenerate"
    fi
fi
```

## Recovery approach

### Step 1: Recreate the directory

```bash
mkdir -p /boot/loader/entries
```

### Step 2: Regenerate BLS entries for each installed kernel

```bash
for kver in $(ls /lib/modules/); do
    if [[ -f /boot/vmlinuz-${kver} ]]; then
        kernel-install add "${kver}" "/boot/vmlinuz-${kver}"
    fi
done
```

### Step 3: Set the default kernel

```bash
# Use the latest kernel
latest=$(ls -t /boot/vmlinuz-* | head -1 | sed 's|/boot/vmlinuz-||')
grubby --set-default="/boot/vmlinuz-${latest}"
```

### Step 4: Verify entries

```bash
grubby --info=ALL
```

### Step 5: Regenerate grub.cfg

```bash
GRUB_DISABLE_OS_PROBER=true grub2-mkconfig -o /boot/grub2/grub.cfg
```

If EFI, also write the redirect shim (not a full config — see Task 06).

## BLS entry format (reference)

A typical `/boot/loader/entries/<machine-id>-<kver>.conf`:

```
title Red Hat Enterprise Linux (5.14.0-503.40.1.el9_5.x86_64) 9.5 (Plow)
version 5.14.0-503.40.1.el9_5.x86_64
linux /vmlinuz-5.14.0-503.40.1.el9_5.x86_64
initrd /initramfs-5.14.0-503.40.1.el9_5.x86_64.img
options root=/dev/mapper/rootvg-rootlv ro crashkernel=1G-4G:192M,4G-64G:256M,64G-:512M resume=/dev/mapper/rootvg-swaplv rd.lvm.lv=rootvg/rootlv rd.lvm.lv=rootvg/swaplv console=tty1 console=ttyS0 earlyprintk=ttyS0 rootdelay=300
grub_users $grub_users
grub_arg --unrestricted
grub_class rhel
```

## Integration with bootfix

This recovery logic should be part of the unified bootfix (Task 01):
1. After reinstalling GRUB, check if BLS is enabled
2. If enabled and entries are missing, regenerate them
3. Set the default kernel
4. Then regenerate grub.cfg

## Distros affected

| Distro | BLS | kernel-install available | grubby available |
|:------|:------|:------|:------|
| RHEL 8-10 | Yes | Yes | Yes |
| AlmaLinux 8-10 | Yes | Yes | Yes |
| All others | No | N/A | N/A |

## Related tasks

- Task 05 (BLS handling)
- Task 01 (bootfix unification)
- Task 21 (kernel rollback on BLS)
