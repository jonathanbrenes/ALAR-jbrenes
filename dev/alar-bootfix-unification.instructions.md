# ALAR Boot Fix Unification — AI Workflow Instructions

## Project Context

**Repository**: ALAR (Azure Linux Auto Recover)

For how ALAR works, environment variables, supported distros, and design rules,
see `dev/AI_WORKFLOW.md`. This document focuses on the bootfix unification project.

---

## Objective: Unify grubfix + efifix into a Single `bootfix` Action

### Goals

1. **Merge** `grubfix-impl.sh` (Gen1/BIOS) and `efifix-impl.sh` (Gen2/EFI) into a single `bootfix-impl.sh`.
2. **Auto-detect** Gen1 vs Gen2 at runtime (presence of EFI partition / `/boot/efi` mount).
3. **Add arm64 (aarch64) support** — currently only x86_64 grub targets are used.
4. **Fix os-prober contamination** — use `GRUB_DISABLE_OS_PROBER=true` on ALL `grub2-mkconfig` / `grub-mkconfig` calls across ALL distros (the rescue VM's Ubuntu gets added to grub otherwise).
5. **Handle GRUB BLS (Boot Loader Specification)** — newer distros may use `/boot/loader/entries/` instead of a monolithic `grub.cfg`. Detect and handle both modes.
6. **Propagate fixes** to `serialconsole-impl.sh`, `initrd-impl.sh`, `kernel-impl.sh`, and any other script calling `grub2-mkconfig`.

### Backward Compatibility

- Keep `grubfix` and `efifix` as recognized action names by rewriting them as thin wrappers that call the unified bootfix logic.
- Ensure the unified logic works when invoked standalone or as part of a comma-separated action list.

---

## Detailed Analysis of Current Code

### grubfix-impl.sh (Gen1 / BIOS boot)

| Distro | What it does |
|---|---|
| RedHat | `sgdisk -e`, `grub2-install --target i386-pc`, `GRUB_DISABLE_OS_PROBER=true grub2-mkconfig` |
| SUSE | `sgdisk -e`, `grub2-install`, `grub2-mkconfig` (**missing** `GRUB_DISABLE_OS_PROBER`) |
| Ubuntu | `sgdisk -e`, `grub-install`, `update-grub` (**missing** `GRUB_DISABLE_OS_PROBER`) |
| AzureLinux | `sgdisk -e`, `grub2-install --target i386-pc`, `grub2-mkconfig` (**missing** `GRUB_DISABLE_OS_PROBER`) |

**Bugs/Issues found**:
- `recover_ubuntu()` calls `resolve-pre` (typo — should be `resolv-pre`)
- SUSE `grub2-install` has a typo: `"{$RECOVER_DISK_PATH}"` (brace in wrong position)
- `GRUB_DISABLE_OS_PROBER=true` only set for RedHat, NOT for SUSE/Ubuntu/AzureLinux
- No arm64 support anywhere

### efifix-impl.sh (Gen2 / EFI boot)

| Distro | What it does |
|---|---|
| RedHat | Reformats EFI partition, reinstalls `grub2-efi-x64 shim-x64`, regenerates grub.cfg in two locations, updates fstab UUID |
| SUSE | Reformats EFI, reinstalls `grub2-x86_64-efi` + `shim`, writes bootstrap grub.cfg, updates fstab UUID |
| Ubuntu | Reformats EFI, reinstalls `grub-efi`, `grub-install --target=x86_64-efi`, `update-grub`, updates fstab UUID |
| AzureLinux | Reformats EFI, reinstalls `grub2-efi` + `shim`, writes bootstrap grub.cfg, calls `initrd-impl.sh`, updates fstab UUID |

**Bugs/Issues found**:
- `resolv-after()` has typo: `resolve.conf` instead of `resolv.conf`
- `recover_ubuntu()` calls `resolve-pre` (typo, plus function undefined — dupcliated from grubfix)
- `recover_ubuntu()` uses `$new_efi_uuid` but the variable is named `$new_uuid`
- Ubuntu doesn't check for EFI partition existence like other distros do
- Hardcoded `x86_64` everywhere — no arm64 targets
- `GRUB_DISABLE_OS_PROBER=true` only used in RedHat section

### serialconsole-impl.sh

- Uses `GRUB_DISABLE_OS_PROBER=true` for RedHat only
- Uses `GRUB_DISABLE_OS_PROBER=true` for the second `grub2-mkconfig` call (SUSE/AzureLinux share `serial_fix_suse_redhat`)
- Does NOT set it for the first `grub2-mkconfig` call when distro is RedHat (the EFI grub.cfg one)
  - Wait — actually it does set it for RedHat. But SUSE and AzureLinux also call `serial_fix_suse_redhat` which does set it. OK.
- Missing: does not handle arm64 grub targets

### initrd-impl.sh

- Calls `grub2-mkconfig` / `grub-mkconfig` without `GRUB_DISABLE_OS_PROBER=true` in ALL cases (RedHat, SUSE, Ubuntu, AzureLinux)
- No arm64 considerations

### kernel-impl.sh

- Uses `GRUB_DISABLE_OS_PROBER=true` for RedHat only
- SUSE and AzureLinux call `grub2-mkconfig` without it
- Ubuntu calls `update-grub` without it

---

## Implementation Plan

### Phase 1: Create Shared Helper Functions

Create or extend `helpers.sh` with reusable functions:

```bash
# Detect architecture: returns "x86_64" or "aarch64"
detect_arch() {
    uname -m
}

# Detect boot mode: returns "efi" or "bios"
# IMPORTANT: Inside a chroot on a rescue VM, /sys/firmware/efi reflects the
# RESCUE VM's boot mode, not the broken disk's. A Gen2 VM rescued by a Gen1
# Ubuntu would show bios. Use $efi_part_path (set by ALAR) as primary signal.
# Fallback to /sys/firmware/efi for standalone testing outside ALAR.
detect_boot_mode() {
    if [ -n "${efi_part_path}" ]; then
        echo "efi"
    elif [ -d /sys/firmware/efi ]; then
        echo "efi"
    else
        echo "bios"
    fi
}

# Detect if BLS (Boot Loader Spec) is in use
is_bls_enabled() {
    [ -d /boot/loader/entries ] && ls /boot/loader/entries/*.conf &>/dev/null
}

# Safe grub2-mkconfig wrapper: always disables os-prober
safe_grub2_mkconfig() {
    local output_path="$1"
    GRUB_DISABLE_OS_PROBER=true grub2-mkconfig -o "$output_path"
}

# Safe grub-mkconfig wrapper for Ubuntu/Debian
safe_update_grub() {
    GRUB_DISABLE_OS_PROBER=true update-grub
}

# Resolve the EFI vendor directory
# Real data shows: RHEL=redhat, AlmaLinux=almalinux, Debian=debian, Ubuntu=ubuntu,
# SUSE=BOOT (no vendor-specific dir), Azure Linux 3=BOOT only (no vendor dir at all)
get_efi_vendor_dir() {
    local vendor
    vendor=$(ls /boot/efi/EFI | grep -i -E "centos|redhat|almalinux|rocky|oracle|ubuntu|debian|sles|azurelinux|mariner" | head -1)
    if [ -z "$vendor" ] && [ -d /boot/efi/EFI/BOOT ]; then
        vendor="BOOT"
    fi
    echo "$vendor"
}

# Get grub target based on architecture and boot mode
get_grub_target() {
    local arch=$(detect_arch)
    local mode=$(detect_boot_mode)
    
    if [[ "$mode" == "efi" ]]; then
        case "$arch" in
            x86_64)  echo "x86_64-efi" ;;
            aarch64) echo "arm64-efi" ;;
        esac
    else
        case "$arch" in
            x86_64)  echo "i386-pc" ;;
            aarch64) echo "arm64-efi" ;; # arm64 is always EFI
        esac
    fi
}

# Get the grub EFI package names per distro and arch
get_grub_efi_packages_redhat() {
    local arch=$(detect_arch)
    case "$arch" in
        x86_64)  echo "grub2-efi-x64 shim-x64" ;;
        aarch64) echo "grub2-efi-aa64 shim-aa64" ;;
    esac
}

get_grub_efi_packages_suse() {
    local arch=$(detect_arch)
    case "$arch" in
        x86_64)  echo "grub2-x86_64-efi" ;;
        aarch64) echo "grub2-arm64-efi" ;;
    esac
}

get_grub_efi_packages_azurelinux() {
    # Azure Linux 3 uses non-arch-suffixed package names for both x86_64 and aarch64
    echo "grub2-efi-binary shim"
}

get_grub_efi_packages_debian() {
    local arch=$(detect_arch)
    case "$arch" in
        x86_64)  echo "grub-efi-amd64-signed" ;;
        aarch64) echo "grub-efi-arm64-signed" ;;
    esac
}

get_grub_efi_packages_ubuntu() {
    local arch=$(detect_arch)
    case "$arch" in
        x86_64)  echo "grub-efi-amd64-signed shim-signed" ;;
        aarch64) echo "grub-efi-arm64-signed shim-signed" ;;
    esac
}
```

### Phase 2: Create `bootfix-impl.sh`

The unified script must:

1. **Source helpers**: `. /tmp/action_implementation/helpers.sh`
2. **Detect boot mode** (EFI vs BIOS) automatically
3. **Detect architecture** (x86_64 vs aarch64)
4. **Detect BLS** (Boot Loader Specification) usage
5. **Enforce EFI grub.cfg as a redirect shim** (not a full standalone config)
6. **Branch by distro** (existing env vars: `isRedHat`, `isUbuntu`, etc.)
7. **Execute the appropriate recovery** per distro × boot-mode × arch

#### Critical: EFI grub.cfg Must Be a Redirect Shim

The EFI partition's `grub.cfg` (e.g., `/boot/efi/EFI/redhat/grub.cfg`) should be a **thin redirect** that loads the main `grub.cfg` from the boot filesystem. It should NOT be a full standalone config. The `configfile` command is supported by all GRUB2 versions (since 2.00, 2012).

**Correct EFI grub.cfg pattern (redirect shim) — varies by distro:**

RHEL (all versions):
```
search --no-floppy --set prefix --file /grub2/grub.cfg
set prefix=($prefix)/grub2
configfile $prefix/grub.cfg
```

Debian/Ubuntu:
```
search.fs_uuid <root-partition-UUID> root
set prefix=($root)'/boot/grub'
configfile $prefix/grub.cfg
```

SUSE 15+ (CRITICAL: uses `source`, NOT `configfile`):
```
search --no-floppy --set prefix --file /grub2/grub.cfg
set prefix=($prefix)/grub2
source "${prefix}/grub.cfg"
```

SLES 12 SP5 (uses `normal`, NOT `configfile` or `source`):
```
set btrfs_relative_path="yes"
search --fs-uuid --set=root <UUID>
set prefix=($root)//grub2
normal
```

Azure Linux 3 (no EFI vendor dir — grub.cfg at `/boot/efi/boot/grub2/grub.cfg`, no redirect shim):
- Has no vendor-specific EFI directory, only `BOOT/`
- The grub.cfg lives directly on the boot partition, not as an EFI redirect
- No separate EFI grub.cfg to write

RHEL 8+ arm64 (`bls_full_config_efi_only`):
- arm64 images have a full BLS-enabled grub.cfg directly in the EFI partition
- No separate `/boot/grub2/grub.cfg` exists — the EFI grub.cfg IS the only config
- Contains `blscfg` command plus menuentries (hybrid pattern)

**WARNING from real data**: SUSE uses `source` instead of `configfile` in the EFI grub.cfg.
The plan must NOT assume `configfile` is universal. The redirect shim must match the distro's own pattern.

**Broken state to detect and fix:** Two full standalone grub.cfg files (one in `/boot/grub2/` and another in `/boot/efi/EFI/<vendor>/`) that have diverged. The current `efifix-impl.sh` creates this problem for RedHat by running `grub2-mkconfig -o` to BOTH locations.

**Fix approach in bootfix:**
1. Generate the main grub.cfg ONLY to `/boot/grub2/grub.cfg` (or `/boot/grub/grub.cfg` for Ubuntu)
2. Write/overwrite the EFI grub.cfg as a redirect shim pointing to the boot partition by UUID
3. This ensures a single source of truth and prevents drift

#### Pseudocode Structure

```
bootfix-impl.sh
├── source helpers.sh
├── detect_arch()          → ARCH
├── detect_boot_mode()     → BOOT_MODE (efi|bios)
├── is_bls_enabled()       → BLS
├── resolv-pre()
├── if isRedHat
│   ├── if BOOT_MODE == bios → recover_redhat_bios()
│   └── if BOOT_MODE == efi  → recover_redhat_efi()
├── if isSuse
│   ├── if BOOT_MODE == bios → recover_suse_bios()
│   └── if BOOT_MODE == efi  → recover_suse_efi()
├── if isUbuntu || isDebian
│   ├── if BOOT_MODE == bios → recover_ubuntu_bios()
│   └── if BOOT_MODE == efi  → recover_ubuntu_efi()
├── if isAzureLinux
│   ├── if BOOT_MODE == bios → recover_azurelinux_bios()
│   └── if BOOT_MODE == efi  → recover_azurelinux_efi()
├── if BLS → update_bls_entries()
├── resolv-after()
└── exit 0
```

#### Key Implementation Rules

- **EVERY** call to `grub2-mkconfig` or `grub-mkconfig` MUST be prefixed with `GRUB_DISABLE_OS_PROBER=true` — this is critical because Gen2 VMs are often rescued using Gen1 Ubuntu rescue VMs, and os-prober will add the rescue VM's Ubuntu to the grub menu
- **EVERY** call to `update-grub` MUST be wrapped: `GRUB_DISABLE_OS_PROBER=true update-grub`
- **Boot mode detection inside chroot**: `/sys/firmware/efi` reflects the rescue VM, not the broken disk. Detect the broken disk's boot mode from the `efi_part_path` env var or partition type `EF00`
- Use `detect_arch()` to select the correct grub target (`i386-pc`, `x86_64-efi`, `arm64-efi`)
- Use `detect_arch()` to select the correct package names (`grub2-efi-x64` vs `grub2-efi-aa64`, `shim-x64` vs `shim-aa64`)
- arm64 VMs are **always Gen2 (EFI)** — there is no BIOS mode for arm64 in Azure. If `aarch64 + bios` is detected, error out.
- For **BLS-enabled** distros: after regenerating grub.cfg, also check `/boot/loader/entries/*.conf` and ensure they reference valid kernels and initramfs paths
- Fix all existing typos (`resolve-pre` → `resolv-pre`, `"{$VAR}"` → `"${VAR}"`, `resolve.conf` → `resolv.conf`, `$new_efi_uuid` variable naming)

### Phase 3: Backward-Compatible Wrappers (No Binary Changes)

All changes stay inside the shell scripts. The binary is NOT modified.

#### 3.1 Backward-compatible action names via the existing scripts

Rewrite `grubfix-impl.sh` and `efifix-impl.sh` as thin wrappers that source `helpers.sh` and call the unified logic:

```bash
#!/bin/bash
# grubfix-impl.sh — backward-compatible wrapper
. /tmp/action_implementation/helpers.sh
run_bootfix
```

```bash
#!/bin/bash
# efifix-impl.sh — backward-compatible wrapper
. /tmp/action_implementation/helpers.sh
run_bootfix
```

The binary already deploys ALL `*-impl.sh` files to `/tmp/action_implementation/` and routes by filename. By putting the unified logic in `helpers.sh` as a `run_bootfix` function, both `grubfix-impl.sh` and `efifix-impl.sh` resolve to the same code.

#### 3.2 Architecture detection in shell

Detect architecture inside the shell scripts:

```bash
ARCH=$(uname -m)
```

In Azure rescue VM scenarios, the rescue VM and the broken disk always share the same architecture, so `uname -m` is reliable.

### Phase 4: Fix `serialconsole-impl.sh`

1. Source `helpers.sh` for the shared functions
2. Replace all `grub2-mkconfig` calls with `safe_grub2_mkconfig`
3. Replace `update-grub` with `safe_update_grub`
4. Add arm64 EFI grub.cfg path handling (arm64 distros may have different EFI directory names)
5. Handle BLS entries if `/boot/loader/entries/` exists — serial console parameters must be added to each BLS entry's `options` line

### Phase 5: Fix `initrd-impl.sh`

1. Add `GRUB_DISABLE_OS_PROBER=true` to ALL `grub2-mkconfig` and `grub-mkconfig` calls
2. Handle arm64 kernel naming differences (e.g., `vmlinuz` vs `Image`, different `dracut` driver sets)
3. Handle Hyper-V driver inclusion: `hv_vmbus`, `hv_storvsc`, `hv_netvsc` are built-in (not .ko modules) on all Ubuntu 20.04-25.10 (x86 and arm64), all Azure Linux 3, and some SUSE x86 — 48/97 images total. Check `/lib/modules/$(uname -r)/modules.builtin` for `hv_vmbus` before adding drivers with `--add-drivers`
4. Handle BLS entries — `dracut` on BLS systems may regenerate `/boot/loader/entries/` automatically

### Phase 6: Fix `kernel-impl.sh`

1. Add `GRUB_DISABLE_OS_PROBER=true` to SUSE, Ubuntu, and AzureLinux `grub2-mkconfig`/`update-grub` calls (already done for RedHat)
2. Handle BLS entries for kernel rollback

---

## GRUB BLS (Boot Loader Specification) Handling

### Background

Newer RHEL-based distributions (RHEL 8+, AlmaLinux 8+) use BLS where:
- `/boot/loader/entries/*.conf` files define individual boot entries
- `grub2-mkconfig` may or may not manage these
- `grubby` or `kernel-install` manages BLS entries
- The `grub.cfg` may be a thin shim that reads BLS entries

### Detection

```bash
is_bls_enabled() {
    # Check for BLS entries directory
    if [[ -d /boot/loader/entries ]] && ls /boot/loader/entries/*.conf &>/dev/null 2>&1; then
        return 0
    fi
    # Also check grub default config for BLS hint
    if grep -q "GRUB_ENABLE_BLSCFG=true" /etc/default/grub 2>/dev/null; then
        return 0
    fi
    return 1
}
```

### What Needs to Change for BLS

- **Serial console**: Instead of only modifying `/etc/default/grub` and regenerating `grub.cfg`, also update each `/boot/loader/entries/*.conf` to include serial console kernel parameters in the `options` line.
- **Kernel rollback**: Use `grubby --set-default` instead of modifying `GRUB_DEFAULT` in `/etc/default/grub`.
- **grub2-mkconfig**: On BLS systems, running `grub2-mkconfig` still works but the generated `grub.cfg` is a thin loader. The real entries are in `/boot/loader/entries/`. So `GRUB_DISABLE_OS_PROBER=true` is still important to prevent the rescue VM's OS from appearing.

---

## arm64 (aarch64) Specifics for Azure

For the complete arm64 reference tables (package names, EFI binary names,
serial console TTY, Hyper-V driver status), see `dev/vm-reference-data.md`.

Key points for bootfix implementation:
- arm64 is **always EFI** — no BIOS mode exists in Azure for aarch64
- Use `uname -m` to detect architecture — returns `aarch64`
- GRUB target: `arm64-efi`
- Serial console: `ttyAMA0` (not `ttyS0`)
- Hyper-V drivers are built into arm64 kernels — skip `--add-drivers` (also built-in on all Ubuntu x86 and Azure Linux 3 x86)
- Azure Linux 3 arm64: No EFI vendor directory (BOOT only), uses `tdnf`/`dnf`, uses `dracut` for initramfs

---

## Testing Checklist

### Matrix: Distro × Generation × Architecture

Based on 97 Azure VM images in `vm-data-consolidated.json`.

| # | Publisher | Distro | Gen | Arch | Notes |
|---|---|---|---|---|---|
| 1 | almalinux | AlmaLinux 8.10 | Gen1 | x86_64 | BLS |
| 2 | almalinux | AlmaLinux 8.10 | Gen2 | x86_64 | BLS |
| 3 | almalinux | AlmaLinux 8.10 | Gen2 | aarch64 | BLS, arm64 |
| 4 | almalinux | AlmaLinux 9.7 | Gen1 | x86_64 | BLS |
| 5 | almalinux | AlmaLinux 9.7 | Gen2 | x86_64 | BLS |
| 6 | almalinux | AlmaLinux 9.7 | Gen2 | aarch64 | BLS, arm64 |
| 7 | almalinux | AlmaLinux 10.1 | Gen1 | x86_64 | BLS |
| 8 | almalinux | AlmaLinux 10.1 | Gen2 | x86_64 | BLS |
| 9 | almalinux | AlmaLinux 10.1 | Gen2 | aarch64 | BLS, arm64 |
| 10 | Canonical | Ubuntu 20.04 | Gen1 | x86_64 | |
| 11 | Canonical | Ubuntu 20.04 | Gen2 | x86_64 | |
| 12 | Canonical | Ubuntu 20.04 | Gen2 | aarch64 | arm64 |
| 13 | Canonical | Ubuntu 22.04 | Gen1 | x86_64 | |
| 14 | Canonical | Ubuntu 22.04 | Gen2 | x86_64 | |
| 15 | Canonical | Ubuntu 22.04 | Gen2 | aarch64 | arm64 |
| 16 | Canonical | Ubuntu 24.04 | Gen1 | x86_64 | |
| 17 | Canonical | Ubuntu 24.04 | Gen2 | x86_64 | |
| 18 | Canonical | Ubuntu 24.04 | Gen2 | aarch64 | arm64 |
| 19 | Canonical | Ubuntu 25.10 | Gen1 | x86_64 | sudo-rs |
| 20 | Canonical | Ubuntu 25.10 | Gen2 | x86_64 | sudo-rs |
| 21 | Canonical | Ubuntu 25.10 | Gen2 | aarch64 | sudo-rs, arm64 |
| 22 | Debian | Debian 11 | Gen1 | x86_64 | |
| 23 | Debian | Debian 11 | Gen2 | x86_64 | |
| 24 | Debian | Debian 12 | Gen1 | x86_64 | |
| 25 | Debian | Debian 12 | Gen2 | x86_64 | |
| 26 | Debian | Debian 12 | Gen2 | aarch64 | arm64 |
| 27 | Debian | Debian 13 | Gen1 | x86_64 | |
| 28 | Debian | Debian 13 | Gen2 | x86_64 | |
| 29 | Debian | Debian 13 | Gen2 | aarch64 | arm64 |
| 30 | MicrosoftCBLMariner | Azure Linux 3.0 | Gen1 | x86_64 | No EFI vendor dir, NVMe, separate /boot |
| 31 | MicrosoftCBLMariner | Azure Linux 3.0 | Gen2 | x86_64 | No EFI vendor dir, NVMe, separate /boot |
| 32 | MicrosoftCBLMariner | Azure Linux 3.0 | Gen2 | aarch64 | arm64, no EFI vendor dir |
| 33 | RedHat | RHEL 7.6 | Gen1 | x86_64 | No BLS, full standalone EFI grub.cfg (DIVERGED) |
| 34 | RedHat | RHEL 7.8 | Gen1 | x86_64 | No BLS, full standalone EFI grub.cfg (DIVERGED) |
| 35 | RedHat | RHEL 8.x | Gen1 | x86_64 | BLS |
| 36 | RedHat | RHEL 8.x | Gen2 | x86_64 | BLS |
| 37 | RedHat | RHEL 8.10 | Gen2 | aarch64 | BLS, arm64, bls_full_config_efi_only |
| 38 | RedHat | RHEL 9.x | Gen1 | x86_64 | BLS |
| 39 | RedHat | RHEL 9.x | Gen2 | x86_64 | BLS |
| 40 | RedHat | RHEL 9.7 | Gen2 | aarch64 | BLS, arm64 |
| 41 | RedHat | RHEL 10.1 | Gen1 | x86_64 | BLS |
| 42 | RedHat | RHEL 10.1 | Gen2 | x86_64 | BLS |
| 43 | RedHat | RHEL 10.1 | Gen2 | aarch64 | BLS, arm64 |
| 44 | RedHat | RHEL-HA 8.8 | Gen1 | x86_64 | BLS, LVM |
| 45 | RedHat | RHEL-SAP-HA 8.4 | Gen2 | x86_64 | BLS, LVM |
| 46 | RedHat | RHEL-SAP-HA 9.6 | Gen2 | x86_64 | BLS, LVM |
| 47 | RedHat | RHEL raw 8.x | Gen1 | x86_64 | BLS, no /boot partition |
| 48 | RedHat | RHEL raw 8.x | Gen2 | x86_64 | BLS |
| 49 | RedHat | RHEL raw 9.x | Gen1 | x86_64 | BLS |
| 50 | RedHat | RHEL raw 9.x | Gen2 | x86_64 | BLS |
| 51 | RedHat | RHEL raw 10.x | Gen1 | x86_64 | BLS |
| 52 | RedHat | RHEL raw 10.x | Gen2 | x86_64 | BLS |
| 53 | SUSE | SLES 12 SP5 | Gen2 | x86_64 | normal redirect, old GRUB 2.02 |
| 54 | SUSE | SLES 15 SP6 | Gen2 | x86_64 | source redirect |
| 55 | SUSE | SLES 15 SP7 | Gen1 | x86_64 | |
| 56 | SUSE | SLES 15 SP7 | Gen2 | x86_64 | source redirect |
| 57 | SUSE | SLES 15 SP7 | Gen2 | aarch64 | arm64, source redirect |
| 58 | SUSE | SLES 16.0 | Gen1 | x86_64 | btrfs subvolumes |
| 59 | SUSE | SLES 16.0 | Gen2 | x86_64 | btrfs, source redirect |
| 60 | SUSE | SLES SAP 15 SP7 | Gen1 | x86_64 | |
| 61 | SUSE | SLES SAP 15 SP7 | Gen2 | x86_64 | source redirect |

### Verification Points per Test

1. After bootfix: VM boots successfully
2. `grub.cfg` does NOT contain rescue VM Ubuntu entries
3. `/etc/fstab` EFI UUID is correct (EFI cases)
4. Correct GRUB target was used for the architecture
5. Serial console accessible (if serialconsole also run)
6. BLS entries in `/boot/loader/entries/` are valid (BLS cases)

### Additional Cross-Script Tests

| Test | Script | Verification |
|---|---|---|
| A | serialconsole | `grub.cfg` has no os-prober entries; BLS entries have console params |
| B | initrd | Regenerated `grub.cfg` has no os-prober entries |
| C | kernel | Kernel rollback works; `grub.cfg` has no os-prober entries |
| D | bootfix,serialconsole | Combo action works end-to-end |

---

## File Change Summary

| File | Action | Description |
|---|---|---|
| `src/action_implementation/helpers.sh` | **MODIFY** | Add arch/boot-mode/BLS detection, safe grub wrappers, `run_bootfix` function |
| `src/action_implementation/grubfix-impl.sh` | **REWRITE** | Thin wrapper: sources `helpers.sh`, calls `run_bootfix` |
| `src/action_implementation/efifix-impl.sh` | **REWRITE** | Thin wrapper: sources `helpers.sh`, calls `run_bootfix` |
| `src/action_implementation/serialconsole-impl.sh` | **MODIFY** | Use safe grub wrappers, add arm64 support, add BLS handling |
| `src/action_implementation/initrd-impl.sh` | **MODIFY** | Add `GRUB_DISABLE_OS_PROBER=true` everywhere, arm64 driver handling |
| `src/action_implementation/kernel-impl.sh` | **MODIFY** | Add `GRUB_DISABLE_OS_PROBER=true` for all distros, BLS handling |
| `dev/test-action.sh` | **CREATE** | Test harness to run any action script outside ALAR |

**No Rust files are modified.** All logic lives in the shell scripts.

---

## Known Bugs To Fix During Implementation

See `dev/backlog.md` for the complete tracked list. The bugs addressed by this
bootfix unification are items 1-3 (Critical) and 4-7 (High Priority):
- Item 1: Unify grubfix + efifix into bootfix
- Item 2: Missing `GRUB_DISABLE_OS_PROBER=true` across multiple scripts
- Item 3: Multiple typos in grubfix/efifix causing failures
- Item 4: No arm64 support in boot-related scripts
- Item 5: No BLS handling
- Item 6: EFI grub.cfg written as full standalone instead of redirect shim
- Item 7: SUSE uses `source` not `configfile` in EFI grub.cfg

---

## Security Considerations

- All scripts run inside a chroot as root — ensure no path injection via variables
- `$RECOVER_DISK_PATH` is validated before reaching the scripts; quote it in all shell usage
- `resolv-pre()` / `resolv-after()` must reliably restore `/etc/resolv.conf` even on script failure (consider `trap`)
- `mkfs.vfat -F16` destroys data on the EFI partition — this is intentional but must be logged clearly
- Package installation (`yum`, `dnf`, `apt-get`, `zypper`, `tdnf`) should use `-y` to avoid interactive prompts

---

## Findings From Real VM Data (56 hosts collected)

These findings were extracted from 56 actual Azure VMs across 3 regions,
covering RHEL 7-10, AlmaLinux 8-10, Debian 11-13, Ubuntu 24.04, SLES 12-16, and arm64 variants.
Full raw data is available in `dev/vm-data-consolidated.json`.
These findings MUST inform the implementation.

### 1. SUSE uses `source` not `configfile` in EFI grub.cfg
All SUSE images (SLES 15 SP6, SP7, 16, SAP) use `source "${prefix}/grub.cfg"` instead of `configfile`. The bootfix must NOT force a `configfile`-based redirect on SUSE — it must use `source` to match the distro's native pattern.

### 2. Gen1 (BIOS) VMs still have /boot/efi mounted
Debian 12 Gen1, RHEL 8.9 Gen1, RHEL 9.7 Gen1, and all other Gen1 images have `/boot/efi` mounted with EFI binaries present. Boot mode detection MUST use `/sys/firmware/efi` directory existence, NOT the presence of `/boot/efi` or EFI partition. The `detect_boot_mode()` function must be updated accordingly.

### 3. GRUB config paths differ between distro families
- **RHEL/SUSE**: `/boot/grub2/grub.cfg`
- **Debian/Ubuntu**: `/boot/grub/grub.cfg` (note: `grub` not `grub2`)
- Helper functions must account for this path difference.

### 4. Debian vendor directory is "debian"
The `get_efi_vendor_dir()` grep pattern was missing `debian`. Real data shows:
- RHEL → `redhat`, Debian → `debian`, Ubuntu → `ubuntu`, SUSE → `sles` (or `BOOT` only)

### 5. RHEL "raw" images have NO separate /boot partition
RHEL raw images (`rhel-raw-*`) report `boot_mount: none (boot on root)`. Boot files live in `/boot` on the root filesystem. There is no separate boot partition, so `$BOOT_PARTITION` and `$boot_part_path` will be empty. The bootfix must handle this gracefully.

### 6. resolv.conf is a symlink on Debian 12+, Ubuntu, and SUSE
- **Debian 12+/Ubuntu**: symlink → `../run/systemd/resolve/stub-resolv.conf` (DNS at `127.0.0.53` via systemd-resolved)
- **SUSE**: symlink → `/run/netconfig/resolv.conf` (DNS at `168.63.129.16`)
- **RHEL/Debian 11**: regular file (DNS at `168.63.129.16`)

The `resolv-pre()` function uses `mv` which preserves the symlink correctly, but inside a chroot, systemd-resolved is not running — so writing `nameserver 168.63.129.16` directly is the correct approach. The `resolv-after()` function must restore the original (symlink or file) exactly.

### 7. BLS is RHEL-family only (8, 9, 10)
All RHEL versions (including raw, SAP, HA variants) have genuine BLS entries in `/boot/loader/entries/`. Debian, Ubuntu, and SUSE have NO BLS entries at all. BLS handling only needs to trigger for `isRedHat=true`.

### 8. RHEL 8.x uses BLS with `grub_class kernel`, RHEL 9+/10 uses `grub_class rhel`
The BLS entry format differs slightly between RHEL 8 and 9+. Both are valid.

### 9. os-prober is installed on RHEL and Ubuntu, NOT on SUSE/Debian
`GRUB_DISABLE_OS_PROBER=true` is critical for RHEL and Ubuntu. SUSE doesn't even ship os-prober.

### 10. Hyper-V modules report as NOT FOUND but ARE loaded
All hosts (including arm64) show `hv_vmbus: NOT FOUND` from the module type check, but `lsmod` shows them loaded. On cloud kernels, these drivers are compiled in (not separate .ko files and not in `modules.builtin`). The `initrd-impl.sh` `--add-drivers` may fail to find them but dracut/initramfs-tools will still include what's built-in.

### 11. SLES 16 uses btrfs with subvolumes
SLES 16 has `SUSE_BTRFS_SNAPSHOT_BOOTING=true` and the root filesystem is btrfs with `@/` subvolumes. The fstab action and bootfix must not assume xfs/ext4 everywhere.

### 12. SLES 15 SP7 and 16 use btrfs with subvolumes
SLES 15 SP7 and SLES 16 have `SUSE_BTRFS_SNAPSHOT_BOOTING=true` and the root filesystem is btrfs with `@/` subvolumes. The fstab action and bootfix must not assume xfs/ext4 everywhere.

### 13. Duplicate sudo user detected on rhel-sap-ha-84-gen2
User `packer` appears in multiple sudoers files — confirms the sudo action's duplicate detection is needed.

### 14. Debian arm64 needs special kernel cmdline parameters
Debian 13 arm64 has `10_cloud_azure_arm64.cfg` with `initcall_blacklist=arm_pmu_acpi_init transparent_hugepage=madvise` and `earlycon=pl011,0xeffec000`. The serialconsole action must preserve these arm64-specific parameters.

### 15. SUSE grub.cfg is generated by grub2-mkconfig (not BLS)
SUSE's main `/boot/grub2/grub.cfg` is a full generated config (not a BLS shim). SUSE never uses BLS. The grub.cfg regeneration path for SUSE is always `grub2-mkconfig -o /boot/grub2/grub.cfg`.

### 16. NVMe is present on rhel-raw-9-gen2, sles-16-gen2, sles-15-sp7-basic-gen2, and debian-12-gen2
These hosts use `/dev/nvme0n1` as root disk. The partition separator is `p` (e.g., `nvme0n1p3`). The bootfix must handle the NVMe partition naming convention.

### 17. RHEL 7.6 has a FULL STANDALONE grub.cfg in EFI (not a redirect shim)
RHEL 7.x uses GRUB 2.02~beta2 and the EFI grub.cfg contains actual `menuentry` directives — it is NOT a redirect shim. This is the oldest supported RHEL and the only one with a full standalone EFI config. The bootfix should handle this by replacing it with a redirect shim when fixing.

### 18. SLES 12 SP5 EFI grub.cfg is also a full standalone (not a redirect)
SLES 12 SP5 uses GRUB 2.02 and its EFI grub.cfg sources directly from `(${root})//grub2`. It's not a standard redirect shim. The bootfix must detect and handle this older SUSE pattern.

### 19. BLS actual entries exist on ALL RHEL 8.x+ (not just 9.5+)
Third batch confirms: ALL RHEL 8.x, 9.x, and 10.x images have genuine BLS entries in `/boot/loader/entries/` — including RHEL 8.4 raw, RHEL 8.8 HA, RHEL 8.10 arm64, RHEL 8 Gen2. Only RHEL 7.x has NO BLS entries. The BLS detection must check for actual entry files, not just the config flag (Debian/SUSE/Ubuntu never have entries despite the flag).

### 20. Debian 11 Gen1 has a SEPARATE /boot partition (unusual for Debian)
Most Debian images have no separate /boot, but Debian 11 Gen1 does (`/dev/sdb2`, 494M). The bootfix cannot assume Debian always has boot on root.

### 21. SLES 12 SP5 uses a slower serial baud rate (38400)
SLES 12 SP5 GRUB serial config uses `--speed=38400` instead of the standard `--speed=115200`. The serialconsole action must not blindly overwrite existing serial settings without checking.

### 22. Debian 12 arm64 has no separate /boot partition
Debian 12 arm64 has boot files on root (`/dev/sda1`). Combined with the arm64 serial console being `ttyAMA0`, this means the boot path for Debian arm64 is: EFI-only, no separate /boot, grub at `/boot/grub/`, redirect shim with `configfile`, serial over `ttyAMA0`.

---

## How to Use This Document in a New AI Session

1. Open this file and provide it as context to the AI assistant
2. Ask: "Implement Phase N of the bootfix unification" (where N = 1-6)
3. Or ask: "Create the bootfix-impl.sh script following these instructions"
4. Or ask: "Fix the os-prober issue across all scripts"
5. The AI has all the architecture knowledge, bug list, file locations, and implementation plan needed to execute each phase

### Recommended Implementation Order

1. **Phase 1** — Extend `helpers.sh` with shared functions and `run_bootfix`
2. **Phase 2** — Test `run_bootfix` logic using `dev/test-action.sh` harness
3. **Phase 3** — Rewrite `grubfix-impl.sh` and `efifix-impl.sh` as thin wrappers
4. **Phase 4** — Fix `serialconsole-impl.sh`
5. **Phase 5** — Fix `initrd-impl.sh`
6. **Phase 6** — Fix `kernel-impl.sh`
7. **Testing** — Work through the test matrix using `dev/test-action.sh`

**No binary rebuild is needed** — changes are tested and deployed purely at the shell script level.
