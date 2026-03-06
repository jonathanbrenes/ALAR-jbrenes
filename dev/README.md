# dev/ — Development & Testing Tools

This directory contains tools for validating and testing ALAR action scripts
outside the full ALAR Rust binary. Use these to develop new features, debug
fixes, or verify behavior across different distro/arch/generation combinations
without needing to compile or deploy the ALAR binary.

## Files

### test-action.sh

**Test harness for running individual action scripts on a live VM.**

Replicates the environment that the ALAR binary sets up before invoking
action scripts inside chroot. It auto-detects the distro, disk layout,
partition numbering, and LVM state, then exports the same environment
variables the binary would provide.

```bash
# Inspect the environment without executing (safe)
sudo ./dev/test-action.sh grubfix --dry-run

# Run an action script on the live VM
sudo ./dev/test-action.sh serialconsole

# Point to a custom script directory
sudo ./dev/test-action.sh efifix --script-dir /path/to/modified/scripts

# Override the disk path
sudo ./dev/test-action.sh grubfix --disk /dev/sdc
```

**Environment variables set** (matching ALAR binary):

| Variable | Description |
|---|---|
| `isRedHat`, `isUbuntu`, `isSuse`, `isAzureLinux`, `isDebian` | Distro boolean flags |
| `DISTRONAME` | Pretty name from `/etc/os-release` |
| `DISTROVERSION` | `VERSION_ID` from `/etc/os-release` |
| `DISTROSUBTYPE` | `CentOS`, `AlmaLinux`, `RockyLinux`, `OracleLinux`, or `None` |
| `RECOVER_DISK_PATH` | Root disk device path |
| `efi_part_path` | EFI partition device path (if present) |
| `boot_part_path` | Boot partition device path (if present) |
| `EFI_PARTITION` | EFI partition number |
| `BOOT_PARTITION` | Boot partition number |
| `OS_PARTITION` | OS/root partition number |
| `isLVM` | `true` if LVM detected on the disk |

> **Warning**: Action scripts modify boot configuration. Only run on test VMs.

---

### collect-vm-info.yml

**Ansible playbook that collects system details from multiple VMs in parallel.**

Gathers everything needed to understand each VM's boot process, disk layout,
security configuration, and system state — covering all ALAR action scripts:
bootfix, serialconsole, initrd, kernel, fstab, auditd, and sudo.

Outputs a single JSON to `/var/www/html/results.json` on the Ansible controller.

```bash
ansible-playbook -i inventory dev/collect-vm-info.yml
```

**What it collects** (27 sections per host):

#### Boot & GRUB (bootfix, serialconsole, initrd, kernel actions)

| Section | Why it matters |
|---|---|
| IMDS image reference | Maps VM to exact publisher:offer:sku:version |
| Architecture (`uname -m`) | x86_64 vs aarch64 branching |
| Boot mode (BIOS/EFI) | Gen1 vs Gen2 detection |
| Disk layout, NVMe, LVM | Partition path construction |
| GRUB packages & binaries | Correct install/reinstall commands per distro |
| `/etc/default/grub` + grub.d | Existing GRUB settings |
| grub.cfg files + type classification | Full vs BLS shim vs redirect detection |
| **EFI grub.cfg redirect analysis** | Detects diverged configs (broken state) |
| BLS entries (`/boot/loader/`) | Whether BLS-aware handling is needed |
| EFI directory tree + vendor dirs | EFI binary paths per distro |
| Kernel/initramfs files | Naming conventions per distro |
| Dracut / initramfs-tools config | Driver inclusion requirements |
| dracut-hyperv package | Whether Hyper-V dracut module is installed |
| Hyper-V modules (built-in vs module) | arm64 has built-in, x86_64 needs modules |
| Serial console (TTY, cmdline, getty) | `ttyS0` (x64) vs `ttyAMA0` (arm64) |
| Package manager | yum/dnf/tdnf/zypper/apt-get availability |
| os-prober | Whether `GRUB_DISABLE_OS_PROBER` is critical |
| Default boot kernel (`grubby`, `GRUB_DEFAULT`) | Kernel rollback target |

#### Filesystem & Disk (fstab action)

| Section | Why it matters |
|---|---|
| `/etc/fstab` | Current fstab content |
| `blkid` (all UUID mappings) | UUID↔device mapping for fstab rebuild |
| `/etc/mtab` (current mounts) | Runtime mount state vs fstab |
| Resource disk / BEK entries | Azure ephemeral disk and ADE encryption entries |
| LVM logical volume details | LV names and paths for LVM-based fstab rebuild |

#### Audit (auditd action)

| Section | Why it matters |
|---|---|
| `/etc/audit/auditd.conf` | Full auditd configuration |
| HALT/SUSPEND rules | Detects shutdown-on-failure rules that block boot |
| Disk usage (`df -h`) | Identifies full filesystems causing audit failures |
| VG free space | Whether LVM expansion is possible for full audit volumes |

#### Sudo & Permissions (sudo action)

| Section | Why it matters |
|---|---|
| sudoers file permissions & ownership | Detects broken 440/root:root requirements |
| sudo binary setuid bits | Detects missing setuid (4755 or 4111) |
| `/etc` directory perms & ownership | Signals larger permission corruption |
| `targetpw` flag in sudoers | SUSE-specific sudo lockout issue |
| Duplicate sudo users across files | vmaccess/waagent duplicate entry detection |
| `/etc/sudoers.d/waagent` content | Most common duplicate source from Azure password resets |

#### General Azure Context

| Section | Why it matters |
|---|---|
| waagent version & config | Azure Linux Agent state and provisioning settings |
| cloud-init version | Cloud-init availability for provisioning |
| `/etc/resolv.conf` | DNS resolver state (scripts modify this during recovery) |
| Secure boot & shim state | Affects EFI recovery approach |

---

## Typical Workflow

1. **Deploy test VMs** from the image catalog using ARM templates
2. **Run the collector** to gather baseline info:
   ```bash
   ansible-playbook -i inventory dev/collect-vm-info.yml
   ```
3. **Review** the JSON output to understand each image's boot layout
4. **Develop/modify** action scripts in `src/action_implementation/`
5. **Test** changes on individual VMs:
   ```bash
   # Dry run first
   sudo ./dev/test-action.sh grubfix --dry-run

   # Then execute
   sudo ./dev/test-action.sh grubfix
   ```
6. **Re-run the collector** to verify the boot state is correct after the fix
7. **Reboot** the VM to confirm it boots successfully

---

## Reference Documents

### ai-workflow.md

**Start here.** Complete AI workflow guide for any agent working on ALAR.
Covers how ALAR works, repository structure, environment variables, supported
distros, critical design rules, rescue VM context, reference data locations,
prompts for common tasks, and how to test changes. This is the single entry
point document for a new AI session.

### alar-bootfix-unification.instructions.md

AI workflow instructions for the bootfix unification project. Contains the
full implementation plan, phase-by-phase instructions, real VM data findings,
and test matrix. Use this as context when asking an AI assistant to implement
any bootfix-related changes.

### vm-reference-data.md

Consolidated reference of boot process details across 45 Azure VM images
(RHEL 7-10, Debian 11-13, Ubuntu 24.04, SLES 12-16, arm64 variants).
Provides quick-lookup tables for grub paths, package names, EFI patterns,
BLS status, serial console TTY, and other distro-specific facts. Use this
as context for any AI agent working on ALAR action scripts.

### backlog.md

Tracks all known bugs, enhancements, and technical debt items for the ALAR
action scripts. Organized by priority and action script.

### vm-data-consolidated.json

Raw collected data from 45 Azure VM images in a single JSON file (sanitized).
Generated using `sanitize-results.py` from multiple `results.json` files
produced by `collect-vm-info.yml` runs across different VM groups and regions.

Contains the full output for every host — GRUB configs, EFI analysis, BLS
entries, fstab, disk layout, kernel/initramfs inventory, serial console,
Hyper-V modules, sudo permissions, auditd config, and more.

**Sensitive data removed**: Azure subscription IDs, resource IDs, VM IDs,
resource group names, public SSH keys, internal DNS domain names, blkid UUIDs,
and mtab entries have been sanitized. IMDS data is limited to
publisher/offer/sku/osType/vmSize/location.

To regenerate from new collection runs:
```bash
python dev/sanitize-results.py results1.json results2.json -o dev/vm-data-consolidated.json
```

Use this file as context for any AI agent that needs to understand the actual
system configuration details of specific Azure VM images across all ALAR actions.
