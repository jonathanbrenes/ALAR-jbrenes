# Task 16 — Ubuntu 25.10 uses sudo-rs via alternatives symlink chain

- **Priority**: 3 (Medium)
- **Type**: Enhancement
- **Script**: `src/action_implementation/sudo-impl.sh`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev replaced traditional `sudo` with `sudo-rs` (Rust implementation). The binary path is a symlink chain:

```
/usr/bin/sudo → /etc/alternatives/sudo → /usr/lib/cargo/bin/sudo
```

`sudo-impl.sh` calls `fixPerm $(which sudo) 4755` (line 120), which resolves to `/usr/bin/sudo` — a symlink. `chmod` on a symlink changes the **target** file's permissions, which works, but:

1. `stat -c "%a"` in `checkPerm()` follows symlinks, so checks are correct
2. However, if the symlink is broken or the chain changes, the fix fails silently

The `collect-vm-info.yml` playbook had a similar issue with `find -type f` missing symlinks — already fixed with `( -type f -o -type l )` + `readlink -f`.

## Affected lines

### sudo-impl.sh (lines 119-121)

```bash
if [[ "$OSFAM" == "fedora" ]]; then
    fixPerm $(which sudo) 4111
else
    fixPerm $(which sudo) 4755
fi
```

## How to fix

Resolve symlinks before `chmod`:

```bash
SUDO_BIN=$(readlink -f "$(which sudo)")
if [[ "$OSFAM" == "fedora" ]]; then
    fixPerm "$SUDO_BIN" 4111
else
    fixPerm "$SUDO_BIN" 4755
fi
fixOwner "$SUDO_BIN" root:root
```

Also confirm the symlink target exists:

```bash
SUDO_BIN=$(readlink -f "$(which sudo)" 2>/dev/null)
if [[ -z "$SUDO_BIN" || ! -f "$SUDO_BIN" ]]; then
    echo "ERR: sudo binary not found or broken symlink"
    exit 1
fi
```

## Impact

- Ubuntu 25.10 uses `sudo-rs` at `/usr/lib/cargo/bin/sudo` with permissions `4755`
- All other Ubuntu versions use traditional sudo at `/usr/bin/sudo` with `4755`
- RHEL/AlmaLinux use traditional sudo with `4111`
