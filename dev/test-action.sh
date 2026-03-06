#!/bin/bash
# =============================================================================
# ALAR Action Script Test Harness
# =============================================================================
# Simulates the environment that the ALAR Rust binary sets up before running
# action scripts inside chroot. Use this to test individual action scripts
# on a live VM without needing the full ALAR binary.
#
# Usage:
#   sudo ./test-action.sh <action> [options]
#
# Examples:
#   sudo ./test-action.sh grubfix
#   sudo ./test-action.sh efifix
#   sudo ./test-action.sh serialconsole
#   sudo ./test-action.sh initrd
#   sudo ./test-action.sh kernel
#   sudo ./test-action.sh grubfix --dry-run
#   sudo ./test-action.sh grubfix --script-dir /path/to/custom/scripts
#
# The script auto-detects the distro, sets the same environment variables
# the Rust binary would set, and then runs the action script directly
# (no chroot — runs on the live system for testing purposes).
#
# WARNING: These scripts modify boot configuration. Run on test VMs only.
# =============================================================================

set -euo pipefail

# ─── Defaults ────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")/../src/action_implementation" && pwd)"
DRY_RUN=false
ACTION=""

# ─── Usage ───────────────────────────────────────────────────────────────────
usage() {
    cat <<EOF
Usage: sudo $0 <action> [options]

Actions:
  grubfix          Run grubfix-impl.sh
  efifix           Run efifix-impl.sh
  serialconsole    Run serialconsole-impl.sh
  initrd           Run initrd-impl.sh
  kernel           Run kernel-impl.sh
  fstab            Run fstab-impl.sh
  auditd           Run auditd-impl.sh
  sudo             Run sudo-impl.sh
  test             Run test-impl.sh
  <any>            Run <any>-impl.sh if it exists

Options:
  --dry-run           Print the environment and action script path, but don't execute
  --script-dir DIR    Path to the action_implementation directory
                      (default: ../src/action_implementation relative to this script)
  --disk PATH         Override RECOVER_DISK_PATH (default: auto-detect root disk)
  -h, --help          Show this help

Environment variables that will be set (matching ALAR Rust binary):
  isRedHat, isUbuntu, isSuse, isAzureLinux, isDebian  (boolean: "true"/"")
  DISTRONAME         Distro pretty name from os-release
  DISTROVERSION      VERSION_ID from os-release
  DISTROSUBTYPE      CentOS, AlmaLinux, RockyLinux, OracleLinux, or None
  RECOVER_DISK_PATH  Root disk device path
  efi_part_path      EFI partition device path (if present)
  boot_part_path     Boot partition device path (if present)
  EFI_PARTITION      EFI partition number (if present)
  BOOT_PARTITION     Boot partition number (if present)
  OS_PARTITION       OS/root partition number
  isLVM              "true" if LVM detected

EOF
    exit 0
}

# ─── Parse arguments ─────────────────────────────────────────────────────────
CUSTOM_DISK=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage ;;
        --dry-run) DRY_RUN=true; shift ;;
        --script-dir) SCRIPT_DIR="$2"; shift 2 ;;
        --disk) CUSTOM_DISK="$2"; shift 2 ;;
        -*)
            echo "Unknown option: $1"
            usage
            ;;
        *)
            if [[ -z "$ACTION" ]]; then
                ACTION="$1"
            else
                echo "Error: Multiple actions specified. Use one action at a time."
                exit 1
            fi
            shift
            ;;
    esac
done

if [[ -z "$ACTION" ]]; then
    echo "Error: No action specified."
    usage
fi

# ─── Must be root ────────────────────────────────────────────────────────────
if [[ $(id -u) -ne 0 ]]; then
    echo "Error: This script must be run as root (sudo)."
    exit 1
fi

# ─── Validate script directory ───────────────────────────────────────────────
IMPL_FILE="${SCRIPT_DIR}/${ACTION}-impl.sh"

if [[ ! -f "$IMPL_FILE" ]]; then
    echo "Error: Action script not found: ${IMPL_FILE}"
    echo "Available actions in ${SCRIPT_DIR}:"
    ls "${SCRIPT_DIR}"/*-impl.sh 2>/dev/null | sed 's/.*\//  /; s/-impl\.sh//' || echo "  (none)"
    exit 1
fi

# ─── Auto-detect distro from /etc/os-release ────────────────────────────────
detect_distro() {
    local name="" version_id="" pretty_name=""

    if [[ -f /etc/os-release ]]; then
        name=$(grep '^NAME=' /etc/os-release | cut -d'=' -f2 | tr -d '"')
        version_id=$(grep '^VERSION_ID=' /etc/os-release | cut -d'=' -f2 | tr -d '"')
        pretty_name=$(grep '^PRETTY_NAME=' /etc/os-release | cut -d'=' -f2 | tr -d '"')
    else
        echo "Error: /etc/os-release not found. Cannot detect distro."
        exit 1
    fi

    export DISTRONAME="'${pretty_name}'"
    export DISTROVERSION="${version_id}"

    # Reset all distro flags
    export isRedHat=""
    export isUbuntu=""
    export isSuse=""
    export isAzureLinux=""
    export isDebian=""
    export DISTROSUBTYPE="None"

    case "$name" in
        *"Red Hat"*|*"RHEL"*)
            export isRedHat="true"
            ;;
        *"CentOS"*)
            export isRedHat="true"
            export DISTROSUBTYPE="CentOS"
            ;;
        *"AlmaLinux"*)
            export isRedHat="true"
            export DISTROSUBTYPE="AlmaLinux"
            ;;
        *"Rocky"*)
            export isRedHat="true"
            export DISTROSUBTYPE="RockyLinux"
            ;;
        *"Oracle"*)
            export isRedHat="true"
            export DISTROSUBTYPE="OracleLinux"
            ;;
        *"Ubuntu"*)
            export isUbuntu="true"
            ;;
        *"Debian"*)
            export isDebian="true"
            ;;
        *"SLES"*|*"SUSE"*|*"openSUSE"*)
            export isSuse="true"
            ;;
        *"Azure Linux"*|*"CBL-Mariner"*|*"Linux Mariner"*)
            export isAzureLinux="true"
            ;;
        *)
            echo "Warning: Unrecognized distro '${name}'. No distro flag set."
            ;;
    esac
}

# ─── Auto-detect disk layout ─────────────────────────────────────────────────
detect_disk_layout() {
    # Root disk
    local root_source
    root_source=$(findmnt -n -o SOURCE /)

    if [[ -n "$CUSTOM_DISK" ]]; then
        export RECOVER_DISK_PATH="$CUSTOM_DISK"
    else
        local root_disk
        root_disk=$(lsblk -ndo PKNAME "$root_source" 2>/dev/null || echo "")
        if [[ -n "$root_disk" ]]; then
            export RECOVER_DISK_PATH="/dev/${root_disk}"
        else
            export RECOVER_DISK_PATH=""
            echo "Warning: Could not determine root disk path."
        fi
    fi

    # Determine partition separator (NVMe uses 'p', SCSI doesn't)
    local part_sep=""
    if [[ "$RECOVER_DISK_PATH" == *nvme* ]]; then
        part_sep="p"
    fi

    # OS partition
    local os_part_num
    os_part_num=$(echo "$root_source" | grep -oE '[0-9]+$' || echo "")
    export OS_PARTITION="${os_part_num}"

    # LVM detection
    if pvs 2>/dev/null | grep -q "${RECOVER_DISK_PATH}"; then
        export isLVM="true"
    else
        export isLVM="false"
    fi

    # Boot partition
    if findmnt -n /boot &>/dev/null; then
        local boot_source
        boot_source=$(findmnt -n -o SOURCE /boot)
        local boot_part_num
        boot_part_num=$(echo "$boot_source" | grep -oE '[0-9]+$' || echo "")
        export BOOT_PARTITION="${boot_part_num}"
        export boot_part_path="${RECOVER_DISK_PATH}${part_sep}${boot_part_num}"
    else
        export BOOT_PARTITION=""
        export boot_part_path=""
    fi

    # EFI partition
    if findmnt -n /boot/efi &>/dev/null; then
        local efi_source
        efi_source=$(findmnt -n -o SOURCE /boot/efi)
        local efi_part_num
        efi_part_num=$(echo "$efi_source" | grep -oE '[0-9]+$' || echo "")
        export EFI_PARTITION="${efi_part_num}"
        export efi_part_path="${RECOVER_DISK_PATH}${part_sep}${efi_part_num}"
    else
        export EFI_PARTITION=""
        export efi_part_path=""
    fi
}

# ─── Deploy helpers.sh to /tmp for scripts that source it ────────────────────
deploy_helpers() {
    local target_dir="/tmp/action_implementation"
    mkdir -p "$target_dir"

    # Copy helpers.sh so scripts that source it from /tmp can find it
    if [[ -f "${SCRIPT_DIR}/helpers.sh" ]]; then
        cp "${SCRIPT_DIR}/helpers.sh" "${target_dir}/helpers.sh"
        chmod 500 "${target_dir}/helpers.sh"
    fi

    # Copy the action script itself (some scripts source others, e.g. efifix calls initrd)
    for f in "${SCRIPT_DIR}"/*-impl.sh "${SCRIPT_DIR}"/*.sh "${SCRIPT_DIR}"/*.awk; do
        [[ -f "$f" ]] || continue
        cp "$f" "${target_dir}/$(basename "$f")"
        chmod 500 "${target_dir}/$(basename "$f")"
    done
}

# ─── Remove SUDO_COMMAND (matches Rust behavior) ─────────────────────────────
unset SUDO_COMMAND

# ─── Run detection ───────────────────────────────────────────────────────────
detect_distro
detect_disk_layout
deploy_helpers

# ─── Print environment summary ───────────────────────────────────────────────
echo "============================================================"
echo "ALAR Test Harness — Environment Summary"
echo "============================================================"
echo "Action:           ${ACTION}"
echo "Script:           ${IMPL_FILE}"
echo "------------------------------------------------------------"
echo "DISTRONAME:       ${DISTRONAME}"
echo "DISTROVERSION:    ${DISTROVERSION}"
echo "DISTROSUBTYPE:    ${DISTROSUBTYPE}"
echo "------------------------------------------------------------"
echo "isRedHat:         ${isRedHat:-false}"
echo "isUbuntu:         ${isUbuntu:-false}"
echo "isSuse:           ${isSuse:-false}"
echo "isAzureLinux:     ${isAzureLinux:-false}"
echo "isDebian:         ${isDebian:-false}"
echo "------------------------------------------------------------"
echo "RECOVER_DISK_PATH: ${RECOVER_DISK_PATH}"
echo "OS_PARTITION:      ${OS_PARTITION}"
echo "BOOT_PARTITION:    ${BOOT_PARTITION:-none}"
echo "boot_part_path:    ${boot_part_path:-none}"
echo "EFI_PARTITION:     ${EFI_PARTITION:-none}"
echo "efi_part_path:     ${efi_part_path:-none}"
echo "isLVM:             ${isLVM}"
echo "------------------------------------------------------------"
echo "Architecture:      $(uname -m)"
echo "Kernel:            $(uname -r)"
echo "Boot mode:         $([ -d /sys/firmware/efi ] && echo 'EFI' || echo 'BIOS')"
echo "============================================================"

if [[ "$DRY_RUN" == "true" ]]; then
    echo ""
    echo "[DRY RUN] Would execute: bash ${IMPL_FILE}"
    echo "[DRY RUN] Exiting without running the action script."
    exit 0
fi

echo ""
echo ">>> Running action: ${ACTION}"
echo "============================================================"

# ─── Execute the action script ───────────────────────────────────────────────
chmod 500 "$IMPL_FILE"
bash "$IMPL_FILE"
exit_code=$?

echo "============================================================"
echo ">>> Action '${ACTION}' completed with exit code: ${exit_code}"
echo "============================================================"

exit $exit_code
