# Task 25 — fstab-impl.sh LVM branch fails on RHEL 9/10 (UUID-based fstab)

- **Priority**: 1 (Critical)
- **Type**: Bug
- **Script**: `src/action_implementation/fstab-impl.sh`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

## Problem

The LVM branch in `fstab-impl.sh` (lines 93-99) rebuilds fstab by grepping for `rootvg-rootlv`, `rootvg-homelv`, etc. This works on RHEL 8 LVM images where fstab uses `/dev/mapper/rootvg-*` device paths, but **fails on RHEL 9 and RHEL 10** where fstab uses UUIDs.

When the patterns don't match, the rebuilt fstab is **empty** (no root, no /home, no /var, etc.) — the VM cannot boot.

## Evidence from 97-VM data

### RHEL 8 LVM (works)

```
/dev/mapper/rootvg-rootlv /                       xfs     defaults        0 0
/dev/mapper/rootvg-homelv /home                   xfs     defaults        0 0
/dev/mapper/rootvg-tmplv /tmp                    xfs     defaults        0 0
/dev/mapper/rootvg-usrlv /usr                    xfs     defaults        0 0
/dev/mapper/rootvg-varlv /var                    xfs     defaults        0 0
```

The awk pattern `/rootvg-rootlv/` matches. Fstab rebuilt correctly.

### RHEL 9 LVM (broken)

```
UUID=4c2f0acf-d447-42ee-9da4-1b473e4c1bf6     /       xfs     defaults       0 0
UUID=c7c02474-a41f-456c-89cd-e178584e3a8b     /boot   xfs     defaults       0 0
UUID=cca1b6e9-6127-42dc-8159-fdc9142bc8a9     /home   xfs     defaults       0 0
UUID=090cc21f-a27a-43f6-b4bc-a21fb44dd4a1     /tmp    xfs     defaults       0 0
UUID=4e9347bb-aac1-4cc1-b566-bb07e7b66b90     /usr    xfs     defaults       0 0
UUID=e24a79d3-29cc-4dd3-b0e7-3f20e85523ff     /var    xfs     defaults       0 0
```

The awk pattern `/rootvg-rootlv/` matches **nothing**. Fstab is empty.

### RHEL 10 LVM (broken)

Same as RHEL 9 — all UUID-based. Same failure.

## Affected lines

### fstab-impl.sh (lines 92-99)

```bash
else
    awk '/rootvg-rootlv/ {print}' ${fstab_org} >>/etc/fstab
    boot_efi_mnt
    awk '/rootvg-homelv/ {print}' ${fstab_org} >>/etc/fstab
    awk '/rootvg-optlv/ {print}' ${fstab_org} >>/etc/fstab
    awk '/rootvg-tmplv/ {print}' ${fstab_org} >>/etc/fstab
    awk '/rootvg-usrlv/ {print}' ${fstab_org} >>/etc/fstab
    awk '/rootvg-varlv/ {print}' ${fstab_org} >>/etc/fstab
fi
```

## How to fix

Match by **mount point** instead of device name. This works for both `/dev/mapper/rootvg-*` and `UUID=` formats:

```bash
else
    # LVM: match by mount point, not device name
    # Works for both /dev/mapper/rootvg-* (RHEL 8) and UUID= (RHEL 9/10)
    awk '/[[:space:]]+\/[[:space:]]+/ {print}'           ${fstab_org} >> /etc/fstab
    boot_efi_mnt
    awk '/[[:space:]]+\/home[[:space:]]+/ {print}'       ${fstab_org} >> /etc/fstab
    awk '/[[:space:]]+\/opt[[:space:]]+/ {print}'        ${fstab_org} >> /etc/fstab
    awk '/[[:space:]]+\/tmp[[:space:]]+/ {print}'        ${fstab_org} >> /etc/fstab
    awk '/[[:space:]]+\/usr[[:space:]]+/ {print}'        ${fstab_org} >> /etc/fstab
    awk '/[[:space:]]+\/var[[:space:]]+/ {print}'        ${fstab_org} >> /etc/fstab
fi
```

The `[[:space:]]+/home[[:space:]]+` pattern avoids matching `/home` inside longer paths like `/home2`.

## Impact

- **Without fix**: fstab action on RHEL 9/10 LVM images produces an empty fstab — VM fails to boot
- **With fix**: mount-point matching works on all RHEL LVM versions (8, 9, 10)

## Oracle Linux confirmation

All Oracle Linux 8.10/9.x/10.x LVM images use UUID-based fstab (same as RHEL 9/10). The same fix applies. OL VMs also have `/var/crash` as an additional LVM mount point (`rootvg-crashlv`). The mount-point matching approach handles this correctly — add an awk rule for `/var/crash` if needed, or rely on the existing catch-all.
