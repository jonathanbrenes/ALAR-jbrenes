# Task 21 — Kernel rollback on BLS systems should use grubby --set-default

- **Priority**: 4 (Low)
- **Type**: Enhancement
- **Script**: `src/action_implementation/kernel-impl.sh`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

`kernel-impl.sh` rolls back the kernel by setting `GRUB_DEFAULT=1` (or `"1>2"`) in `/etc/default/grub`, then regenerating `grub.cfg`. On BLS systems (RHEL 8+, AlmaLinux 8+), this is unreliable because:

1. The boot order depends on BLS entries in `/boot/loader/entries/`, not `GRUB_DEFAULT` index
2. `GRUB_DEFAULT=1` selects by index, which may change after grub.cfg regeneration
3. `grubby` is the proper tool for BLS kernel selection

## Affected lines

### kernel-impl.sh — RedHat section (lines 9-22)

```bash
if [[ ${isRedHat} == "true" ]]; then
    grep -q 'GRUB_DEFAULT=.*' /etc/default/grub || echo 'GRUB_DEFAULT=saved' >>/etc/default/grub
    sed -i -e 's/GRUB_DEFAULT=.*/GRUB_DEFAULT=1/' /etc/default/grub

    cp /boot/efi/EFI/$(ls /boot/efi/EFI | grep -i -E "centos|redhat")/grub.cfg ...
    GRUB_DISABLE_OS_PROBER=true grub2-mkconfig -o /boot/efi/EFI/.../grub.cfg
    GRUB_DISABLE_OS_PROBER=true grub2-mkconfig -o /boot/grub2/grub.cfg

    echo "kernel.sysrq = 1" >>/etc/sysctl.conf
fi
```

## How to fix

On BLS systems, use `grubby` for kernel rollback:

```bash
if [[ ${isRedHat} == "true" ]]; then
    if [[ -d /boot/loader/entries ]] && grep -q 'GRUB_ENABLE_BLSCFG=true' /etc/default/grub; then
        # BLS system — use grubby
        current=$(grubby --default-kernel)
        # Get the previous kernel (second in the sorted list)
        prev_kernel=$(grubby --info=ALL | grep ^kernel= | head -2 | tail -1 | cut -d= -f2)
        if [[ -n "$prev_kernel" && "$prev_kernel" != "$current" ]]; then
            grubby --set-default="$prev_kernel"
            echo "Rolled back to $prev_kernel (was $current)"
        else
            echo "No previous kernel found for rollback"
            exit 1
        fi
    else
        # Non-BLS (RHEL 7) — use GRUB_DEFAULT
        grep -q 'GRUB_DEFAULT=.*' /etc/default/grub || echo 'GRUB_DEFAULT=saved' >>/etc/default/grub
        sed -i -e 's/GRUB_DEFAULT=.*/GRUB_DEFAULT=1/' /etc/default/grub
        GRUB_DISABLE_OS_PROBER=true grub2-mkconfig -o /boot/grub2/grub.cfg
    fi
fi
```

## Additional issues in current code

- **Line 19**: `grep -i -E "centos|redhat"` — missing `almalinux` (see Task 13)
- **Line 22**: `echo "kernel.sysrq = 1" >>/etc/sysctl.conf` — appends without checking if already present; on RedHat should use `/etc/sysctl.d/` (see serialconsole-impl.sh line 12 which does this correctly)

## Related tasks

- Task 05 (BLS handling)
- Task 13 (grep pattern for vendor dir)
