# Task 11 — resolv-pre() / resolv-after() fragile on symlink systems

- **Priority**: 3 (Medium)
- **Type**: Enhancement
- **Scripts**: `grubfix-impl.sh` (lines 3-11), `efifix-impl.sh` (lines 3-11), `fstab-impl.sh` (lines 8-16)
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

## Problem

`resolv-pre()` uses `mv` to replace `/etc/resolv.conf` with a static nameserver. On Debian 12+, Ubuntu, and SUSE, `/etc/resolv.conf` is a symlink (to `/run/systemd/resolve/stub-resolv.conf` or similar). The `mv` breaks the symlink, and `resolv-after()` restores the file but not the symlink.

Additionally, there is no `trap` for cleanup — if the script fails between `resolv-pre()` and `resolv-after()`, DNS is left with the Azure resolver and the original is lost.

The functions are also duplicated across three scripts.

## Affected lines

### grubfix-impl.sh (lines 3-11)
```bash
resolv-pre() {
    mv /etc/resolv.conf /etc/resolv.conf.org
    echo "nameserver 168.63.129.16" >/etc/resolv.conf
}
resolv-after() {
    mv /etc/resolv.conf.org /etc/resolv.conf
}
```

### efifix-impl.sh (lines 3-11)
```bash
resolv-pre() {
    mv /etc/resolv.conf /etc/resolv.conf.org
    echo "nameserver 168.63.129.16" >/etc/resolv.conf
}
resolv-after() {
    mv /etc/resolv.conf.org /etc/resolve.conf  # TYPO: resolve → resolv (Task 03)
}
```

### fstab-impl.sh (lines 8-16)
```bash
resolv-pre() {
    mv /etc/resolv.conf /etc/resolv.conf.org
    echo "nameserver 168.63.129.16" >/etc/resolv.conf
}
resolv-after() {
    mv /etc/resolv.conf.org /etc/resolv.conf
}
```

## How to fix

1. Move `resolv-pre()` / `resolv-after()` to `helpers.sh` (eliminate duplication)
2. Handle symlinks: save and restore the symlink target
3. Add `trap` for automatic cleanup on exit

```bash
resolv-pre() {
    if [[ -L /etc/resolv.conf ]]; then
        RESOLV_LINK_TARGET=$(readlink /etc/resolv.conf)
        rm /etc/resolv.conf
    else
        mv /etc/resolv.conf /etc/resolv.conf.org
    fi
    echo "nameserver 168.63.129.16" > /etc/resolv.conf
}

resolv-after() {
    rm -f /etc/resolv.conf
    if [[ -n "${RESOLV_LINK_TARGET:-}" ]]; then
        ln -s "$RESOLV_LINK_TARGET" /etc/resolv.conf
    else
        mv /etc/resolv.conf.org /etc/resolv.conf
    fi
}

# Add trap in each script that uses these functions:
trap resolv-after EXIT
```

## Impact

- Without fix: symlink-based resolv.conf systems (Debian 12+, Ubuntu, SUSE) lose their DNS resolver symlink after recovery
- With fix: symlink is preserved, cleanup happens even on script failure
