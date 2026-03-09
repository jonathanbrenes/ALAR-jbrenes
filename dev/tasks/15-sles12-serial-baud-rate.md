# Task 15 — SLES 12 SP5 slow serial baud rate (38400 vs 115200)

- **Priority**: 3 (Medium)
- **Type**: Design consideration
- **Script**: `src/action_implementation/serialconsole-impl.sh`
- **Repo**: https://github.com/jonathanbrenes/ALAR-jbrenes/tree/main/dev

`serialconsole-impl.sh` writes hardcoded serial settings including `115200` baud rate. SLES 12 SP5 uses `38400` by default. Blindly overwriting may cause issues if the customer's serial configuration was intentional.

## Affected lines

### serialconsole-impl.sh — `alter_serial_properties()` (lines 27-30)

```bash
echo 'GRUB_CMDLINE_LINUX="USE_BY_UUID_DEVICE_NAMES=1 rootdelay=300 multipath=off net.ifnames=0 console=ttyS0,115200n8 earlyprintk=ttyS0,115200 console=tty1 earlyprintk=ttyS1"' >> $grub_file
echo 'GRUB_SERIAL_COMMAND="serial --speed=9600 --unit=0 --word=8 --parity=no --stop=1"' >> $grub_file
```

Note: The `GRUB_SERIAL_COMMAND` uses `--speed=9600` while `GRUB_CMDLINE_LINUX` uses `115200` — these are inconsistent with each other.

### serialconsole-impl.sh — fallback template (lines 52-58)

```bash
GRUB_SERIAL_COMMAND="serial --speed=19600 --unit=0 --word=8 --parity=no --stop=1"
GRUB_CMDLINE_LINUX="... console=ttyS0,115200n8 ..."
```

Note: `--speed=19600` looks like a typo — should be `19200` or `9600`.

## How to fix

1. Preserve existing baud rate if already configured:
```bash
existing_speed=$(grep -oP 'console=ttyS0,\K[0-9]+' /etc/default/grub 2>/dev/null)
BAUD=${existing_speed:-115200}
```

2. Make `GRUB_SERIAL_COMMAND` and `GRUB_CMDLINE_LINUX` use the same speed
3. Fix the `19600` typo (line 56) — should be `19200` or `9600`
4. Consider using `115200` consistently as it's the Azure default

## Inconsistencies to resolve

| Setting | Line 29 | Line 56 | Correct |
|---|---|---|---|
| `GRUB_SERIAL_COMMAND --speed` | `9600` | `19600` (typo?) | Should match CMDLINE or use `115200` |
| `GRUB_CMDLINE_LINUX console` | `115200` | `115200` | OK |
