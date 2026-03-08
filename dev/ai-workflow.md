# ALAR2 — AI Workflow Guide

Use this file as mandatory guidance for any AI session working on ALAR.
Load `dev/vm-data-consolidated.json` for complete context from 97 Azure VM images.
Known bugs and enhancements are tracked in `dev/backlog.md`.

### How to load this in a new AI session

Use this as the first message in Copilot Chat (or any AI agent):

```text
Use `dev/ai-workflow.md` as mandatory guidance for this session.
Also load `dev/vm-data-consolidated.json` for full VM reference data.
Check `dev/backlog.md` before making any changes.
```

---

## What is ALAR?

ALAR (Azure Linux Auto Recover) recovers non-bootable Azure Linux VMs by running
repair actions inside a chroot on the broken VM's disk.

### How it works

1. A rescue VM (typically Gen1 Ubuntu) is created via `az vm repair create`
2. The broken VM's OS disk is attached as a **data disk** to the rescue VM
3. ALAR detects the distro, mounts partitions, prepares a chroot at `/srv/rescue-root/`
4. Environment variables are set (distro flags, disk paths, partition numbers)
5. Action scripts from `src/action_implementation/` are executed inside the chroot
6. After recovery, the disk is detached and reattached to the original VM

### Rescue VM implications

- The rescue VM is Gen1 Ubuntu — `/sys/firmware/efi` inside chroot reflects the rescue VM (BIOS), NOT the broken disk
- `os-prober` on the rescue VM detects its Ubuntu — `GRUB_DISABLE_OS_PROBER=true` is mandatory on ALL grub regeneration calls
- The broken disk appears as SCSI even if the original VM used NVMe
- Architecture always matches (x86_64 rescue for x86_64, arm64 for arm64)
- If both rescue and broken disk use LVM `rootvg`, ALAR renames the broken disk's VG to `oldvg`

---

## Repository Structure

```
src/action_implementation/   # Shell scripts — the actual recovery logic
  grubfix-impl.sh            # Gen1/BIOS boot repair
  efifix-impl.sh             # Gen2/EFI boot repair
  serialconsole-impl.sh      # Serial console configuration
  initrd-impl.sh             # Initramfs/initrd rebuild
  kernel-impl.sh             # Kernel rollback
  fstab-impl.sh              # fstab repair
  auditd-impl.sh             # Auditd HALT rule fix + disk space
  sudo-impl.sh               # Sudoers permissions fix
  helpers.sh                 # Shared utility functions (backup, checkPerm, etc.)
dev/                         # Development tools and reference data
  backlog.md                 # ← KNOWN BUGS AND ENHANCEMENTS (23 items)
  vm-data-consolidated.json  # ← RAW DATA FROM 97 VMs (load for full context)
  vm-reference-data.md       # Extended reference tables
  alar-bootfix-unification.instructions.md  # Bootfix project plan
  collect-vm-info.yml        # Ansible playbook to collect VM data (sanitizes inline)
  merge-vm-data.py           # Merge new results into vm-data-consolidated.json
  test-action.sh             # Test harness for running action scripts
```

---

## Environment Variables Available to Action Scripts

Set by the binary before script execution inside chroot:

| Variable | Description |
|---|---|
| `isRedHat` | `"true"` if RHEL, CentOS, Alma, Rocky, Oracle |
| `isUbuntu` | `"true"` if Ubuntu |
| `isDebian` | `"true"` if Debian |
| `isSuse` | `"true"` if SLES/openSUSE |
| `isAzureLinux` | `"true"` if Azure Linux / Mariner |
| `DISTRONAME` | Pretty name (e.g., `'Red Hat Enterprise Linux'`) |
| `DISTROVERSION` | VERSION_ID (e.g., `9.7`) |
| `DISTROSUBTYPE` | `CentOS`, `AlmaLinux`, `RockyLinux`, `OracleLinux`, or `None` |
| `RECOVER_DISK_PATH` | Device path of the broken disk (e.g., `/dev/sdc`) |
| `efi_part_path` | EFI partition device (e.g., `/dev/sdc1`) — **empty if no EFI** |
| `boot_part_path` | Boot partition device — **empty if boot is on root** |
| `EFI_PARTITION` | EFI partition number |
| `BOOT_PARTITION` | Boot partition number |
| `OS_PARTITION` | OS/root partition number |
| `isLVM` | `"true"` if LVM detected |

Architecture is NOT exported — detect with `uname -m` (returns `x86_64` or `aarch64`).
Boot mode: use `$efi_part_path` (non-empty = EFI) as primary signal, `/sys/firmware/efi` as fallback.

---

## Distro Quick Reference (from 97 VMs)

### GRUB Commands and Paths

| Distro | grub-install | grub-mkconfig | GRUB path | Vendor EFI dir |
|---|---|---|---|---|
| RHEL 7-10 | `grub2-install` | `grub2-mkconfig` | `/boot/grub2/` | `redhat` |
| AlmaLinux 8-10 | `grub2-install` | `grub2-mkconfig` | `/boot/grub2/` | `almalinux` |
| Debian 11-13 | `grub-install` | `update-grub` | `/boot/grub/` | `debian` |
| Ubuntu 20.04-25.10 | `grub-install` | `update-grub` | `/boot/grub/` | `ubuntu` |
| Azure Linux 3 | `grub2-install` | `grub2-mkconfig` | `/boot/grub2/` | **none** (BOOT only) |
| SUSE 12-16 | `grub2-install` | `grub2-mkconfig` | `/boot/grub2/` | `BOOT` |

### EFI grub.cfg Redirect

| Distro | Method | Note |
|---|---|---|
| RHEL 8+ | `configfile` | Redirect shim to `/boot/grub2/grub.cfg` |
| AlmaLinux 8-10 | `configfile` | Same as RHEL 8+ (vendor dir is `almalinux`) |
| RHEL 7.x | Full standalone | **DIVERGED** — two different full configs |
| Debian/Ubuntu | `configfile` | Redirect shim to `/boot/grub/grub.cfg` |
| SUSE 15+ | `source` | **NOT configfile** — must use `source` for SUSE |
| SUSE 12 | `normal` | Minimal redirect pattern |
| Azure Linux 3 | None | **No EFI grub.cfg** — no vendor dir, grub.cfg at `/boot/efi/boot/grub2/grub.cfg` |

### BLS, Packages, and Serial TTY

| Distro | BLS entries | EFI packages (x86_64) | EFI packages (arm64) | Serial TTY |
|---|---|---|---|---|
| RHEL 7 | No | `grub2-efi-x64 shim-x64` | N/A | `ttyS0` |
| RHEL 8-10 | Yes | `grub2-efi-x64 shim-x64` | `grub2-efi-aa64 shim-aa64` | `ttyS0` / `ttyAMA0` |
| AlmaLinux 8-10 | Yes | `grub2-efi-x64 shim-x64` | `grub2-efi-aa64 shim-aa64` | `ttyS0` / `ttyAMA0` |
| Debian | No | `grub-efi-amd64-signed` | `grub-efi-arm64-signed` | `ttyS0` / `ttyAMA0` |
| Ubuntu | No | `grub-efi-amd64-signed shim-signed` | `grub-efi-arm64-signed shim-signed` | `ttyS0` / `ttyAMA0` |
| Azure Linux 3 | No | `grub2-efi-binary shim` | `grub2-efi-binary shim` | `ttyS0` / `ttyAMA0` |
| SUSE | No | `grub2-x86_64-efi` | `grub2-arm64-efi` | `ttyS0` / `ttyAMA0` |

### Other Distro-Specific Facts

| Distro | Package mgr | Root FS | sudo bits | os-prober installed |
|---|---|---|---|---|
| RHEL 7 | `yum` | xfs | `4111` | Yes — **critical** |
| RHEL 8+ | `dnf` | xfs | `4111` | Yes — **critical** |
| AlmaLinux 8-10 | `dnf` | xfs | `4111` | Yes — **critical** |
| Debian 11-13 | `apt-get` | ext4 | `4755` | No |
| Ubuntu 20.04-22.04 | `apt-get` | ext4 | `4755` | x86 server/minimal/Pro: Yes; arm64: No |
| Ubuntu 24.04 | `apt-get` | ext4 | `4755` | Server/Pro: Yes; Minimal: No |
| Ubuntu 25.10 | `apt-get` | ext4 | `4755` (sudo-rs via symlink) | Server: Yes; Minimal: No |
| Azure Linux 3 | `tdnf`/`dnf` | ext4 | `4755` | No |
| SUSE 12-15 | `zypper` | xfs | `4755` | No |
| SUSE 16 | `zypper` | **btrfs** (subvols) | `4755` | No |

---

## Critical Design Rules

1. **ALWAYS** prefix `grub2-mkconfig` and `update-grub` with `GRUB_DISABLE_OS_PROBER=true`
2. **Boot mode detection**: Use `$efi_part_path` (primary) — `/sys/firmware/efi` reflects the rescue VM, not the broken disk
3. **arm64 is always EFI** — no BIOS mode for aarch64 in Azure
4. **EFI grub.cfg must be a redirect shim** — `configfile` for RHEL/Debian/Ubuntu, `source` for SUSE
5. **GRUB path**: `/boot/grub2/` for RHEL/SUSE, `/boot/grub/` for Debian/Ubuntu
6. **BLS handling** only for RHEL 8+ — check `/boot/loader/entries/` for actual entries
7. **Serial TTY**: `ttyS0` for x86_64, `ttyAMA0` for aarch64 (all arm64 images confirmed)
8. **Hyper-V drivers**: Skip `--add-drivers` when modules are built-in (all Ubuntu 20.04-25.10, all Azure Linux 3, all aarch64, some SUSE x86); check `modules.builtin` at runtime
9. **SLES 16 uses btrfs** with `@/` subvolumes — fstab must preserve them
10. **sudo bits**: RHEL = `4111`, Debian/Ubuntu/SUSE/AzureLinux = `4755` (Ubuntu 25.10 uses a symlinked sudo)
11. **Azure Linux 3**: Uses `grub2-*` commands, `/boot/grub2/`, `tdnf`/`dnf`, dracut, no EFI vendor dir, NVMe-native with separate `/boot`

---

## Working on ALAR — Guidance by Task

### Modifying any action script
1. Read the script from `src/action_implementation/<name>-impl.sh`
2. Check `dev/backlog.md` for known bugs related to that script
3. Use the distro tables above for correct commands/paths
4. Test with `dev/test-action.sh --dry-run` on a matching VM

### Working on boot actions (grubfix, efifix, serialconsole, initrd, kernel)
- Read `dev/alar-bootfix-unification.instructions.md` for the bootfix project plan
- The plan covers unifying grubfix + efifix, adding arm64, BLS, and os-prober fixes

### Adding support for a new distro or image
1. Run `dev/collect-vm-info.yml` against the new VM (output is pre-sanitized)
2. Merge with `python dev/merge-vm-data.py results.json -o dev/vm-data-consolidated.json`
3. Update tables above and `dev/backlog.md` if new issues found

### Checking known bugs
- Read `dev/backlog.md` — 23 items: Critical (3), High (7), Medium (7), Low (6)
- Items 1-3 are most impactful: bootfix unification, missing `GRUB_DISABLE_OS_PROBER`, typos
- Item #23: BLS entries deleted — recovery when `/boot/loader/entries/` is missing on RHEL 8+
- Items 17-22 are from the 97-VM analysis: sudo-rs symlink, Azure Linux 3 EFI/NVMe/packages, os-prober patterns, Hyper-V built-in scope

### Testing changes
1. Deploy a test VM matching target distro/arch/generation
2. `sudo ./dev/test-action.sh <action> --script-dir /path/to/scripts --dry-run`
3. Verify environment, then run without `--dry-run`
4. Reboot VM and verify it boots

---

## Session Rules

- Before any commit, run `git diff --stat` to review changes, then show the exact proposed commit message and ask for approval
- After approval and commit, ask separately whether to push
- Update `dev/README.md` only for major behavior/workflow changes
- When outputting markdown content for commits or pull requests, present it inside a fenced `text` code block
