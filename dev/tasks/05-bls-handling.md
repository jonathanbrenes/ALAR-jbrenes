# Task 05 — No BLS (Boot Loader Specification) handling

- **Priority**: 2 (High)
- **Type**: Enhancement
- **Scripts**: `serialconsole-impl.sh`, `kernel-impl.sh`, `grubfix-impl.sh`, `efifix-impl.sh`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

## Problem

RHEL 8+, Oracle Linux 8.10+, and AlmaLinux 8+ use BLS entries in `/boot/loader/entries/`. The current scripts modify `/etc/default/grub` and regenerate `grub.cfg`, but don't update BLS entries. On BLS systems, boot parameters in `grub.cfg` are overridden by each BLS entry's `options` line.

All 34 RHEL 8+/AlmaLinux 8+ images and 14 Oracle Linux 8.10+ images in the 148-VM dataset use BLS (`GRUB_ENABLE_BLSCFG=true` in `/etc/default/grub`). All have `grubby` available. OL 7.9 and 8.2 do NOT use BLS.

## Affected lines

### serialconsole-impl.sh

- **Lines 27-30**: `alter_serial_properties()` appends to `/etc/default/grub` — on BLS systems, `GRUB_CMDLINE_LINUX` changes are reflected in new entries but NOT in existing BLS entries
- **Lines 63-69**: `serial_fix_suse_redhat()` — regenerates `grub.cfg` but doesn't update existing BLS entry `options` lines

**Fix**: After modifying `/etc/default/grub`, also run:
```bash
if [[ -d /boot/loader/entries ]]; then
    for entry in /boot/loader/entries/*.conf; do
        grubby --update-kernel=ALL --args="console=ttyS0,115200n8 earlyprintk=ttyS0,115200"
    done
fi
```

### kernel-impl.sh

- **Lines 12-21**: `isRedHat` section uses `GRUB_DEFAULT=1` in `/etc/default/grub` — on BLS systems this is unreliable
- **Fix**: Use `grubby --set-default` instead:
```bash
if [[ -d /boot/loader/entries ]]; then
    prev_kernel=$(grubby --info=ALL | grep ^kernel | head -2 | tail -1 | cut -d= -f2)
    grubby --set-default="$prev_kernel"
fi
```

### grubfix-impl.sh / efifix-impl.sh (via Task 01)

- When BLS entries exist, `grub2-mkconfig` preserves them via `blscfg` command in grub.cfg
- If `/boot/loader/entries/` was deleted, entries must be regenerated (see Task 10)

## How to detect BLS

```bash
# Check if BLS is enabled (do NOT check the directory — it may have been deleted)
if grep -q 'GRUB_ENABLE_BLSCFG=true' /etc/default/grub 2>/dev/null; then
    if [[ -d /boot/loader/entries ]] && ls /boot/loader/entries/*.conf &>/dev/null; then
        # BLS enabled, entries exist — update them
    else
        # BLS enabled, entries MISSING — recreate (Task 10 recovery)
    fi
fi
```

## Distros that use BLS

| Distro | BLS | grubby available |
|:------|:------|:------|
| RHEL 8-10 (x86_64 + arm64) | Yes | Yes |
| Oracle Linux 8.10-10 (x86_64 + arm64) | Yes | Yes |
| AlmaLinux 8-10 (x86_64 + arm64) | Yes | Yes |
| Oracle Linux 7.9, 8.2 | No | Yes (but no BLS) |
| RHEL 7 | No | Yes (but no BLS) |
| All other distros | No | No |
