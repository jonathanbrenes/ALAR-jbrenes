# Task 19 — fstab-impl.sh doesn't handle btrfs subvolumes (SLES 16)

- **Priority**: 4 (Low)
- **Type**: Enhancement
- **Script**: `src/action_implementation/fstab-impl.sh`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

SLES 16 uses btrfs with `@/` subvolumes. The root fstab entry looks like:

```
UUID=<uuid>  /  btrfs  subvol=/@/.snapshots/1/snapshot  0  0
```

`fstab-impl.sh` extracts the root line with `awk '/[[:space:]]+\/[[:space:]]+/ {print}'` (line 95), which will match the line. However, the script only handles UUID-to-device and device-to-UUID conversions — it does not preserve or reconstruct the `subvol=` mount option.

If fstab is rebuilt without the `subvol=` option, the root mount may fail on SLES 16 because btrfs needs to know which subvolume to mount.

## Affected lines

### fstab-impl.sh (lines 94-101)

```bash
if [[ ${isLVM} != "true" ]]; then
    fstab_root=$(awk '/[[:space:]]+\/[[:space:]]+/ {print}' ${fstab_org})
    if [[ "$fstab_root" =~ ^[[:space:]]*.*UUID.*  ]]; then
        echo "$fstab_root" >> /etc/fstab
    else
        fstab_root_dev=$(awk '{print $1}'<<< "$fstab_root")
        fstab_root_uuid=$(blkid -o value -s UUID $(awk '{print $1}'<<< "$fstab_root"))
        sed "s|$fstab_root_dev|UUID=$fstab_root_uuid|" <<< $fstab_root >> /etc/fstab
    fi
```

The UUID branch (line 97) echoes the whole line including `subvol=`, so if the original fstab had it, it's preserved. The bug only manifests if fstab was device-name based and the sed replacement loses mount options — but in practice SLES 16 uses UUID already.

## How to fix

For robustness, when rebuilding fstab on btrfs:

1. Detect btrfs: `lsblk -f -o FSTYPE $(findmnt / -o SOURCE -n) -n`
2. Get the current subvolume: `btrfs subvolume show / 2>/dev/null | grep 'Name:'`
3. Ensure `subvol=` option is preserved in the reconstructed line

```bash
if [[ "$root_fstype" == "btrfs" ]]; then
    current_subvol=$(findmnt / -o OPTIONS -n | grep -oP 'subvol=\S+')
    # Ensure subvol option is included in the fstab line
fi
```

## SLES 16 btrfs subvolume layout

```
@/                          # top-level subvolume
@/.snapshots/               # snapper snapshots
@/.snapshots/1/snapshot/    # default root snapshot (mounted as /)
@/boot/grub2/x86_64-efi/   # GRUB modules
@/opt/                      # /opt
@/srv/                      # /srv
@/usr/local/                # /usr/local
@/var/                      # /var
```
