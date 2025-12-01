# Netmiko Bulk SSH Runner – How-To (Confluence Copy)

**Purpose**: Standardize and accelerate safe, parallel command execution across network devices (show or config).

---

## Overview
- Parallel SSH across many devices using Netmiko
- Inventory-driven (`devices.csv`)
- Per-device log files with hostname + IP in filename
- Supports show and config modes, password and key auth

---

## Prerequisites
- Python 3.10+
- SSH reachability to device management IPs
- Optional: NetBox CSV export (any filename)

---

## Setup

1. **Create a virtual environment**
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **macOS/Linux:**
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```

2. **Install packages**
   ```bash
   pip install -r requirements.txt
   ```

3. **Generate `devices.csv` from NetBox (optional)**
   ```bash
   python generate_devices_from_netbox.py --input <your_export>.csv --output devices.csv
   ```
   It produces columns:
   ```
   hostname,device_type,host,username,password,secret,port
   ```

---

## Usage

### Show Mode (Read-Only)
```bash
python run_commands_netmiko.py --devices devices.csv --commands commands.txt --mode show --ask
```

### Config Mode (Push Changes)
```bash
python run_commands_netmiko.py --devices devices.csv --commands config.txt --mode config --ask
```

### Key-Based Authentication
```bash
python run_commands_netmiko.py --devices devices.csv --commands commands.txt --mode show --use-keys --key-file ~/.ssh/id_rsa --ask
```

### Concurrency
- Default `--threads 20`
- Adjust based on device/jump-host limits

---

## Inventory Format (`devices.csv`)
| Column       | Required | Notes                                                            |
|--------------|----------|------------------------------------------------------------------|
| `hostname`   | no       | Recommended; appears in logs and filenames                       |
| `device_type`| yes      | Netmiko type (e.g., `cisco_ios`, `arista_eos`, `juniper_junos`)  |
| `host`       | yes      | SSH target (IP/DNS)                                              |
| `username`   | no       | Per-device override (otherwise prompted with `--ask`)            |
| `password`   | no       | Per-device override                                              |
| `secret`     | no       | Enable password (if applicable)                                  |
| `port`       | no       | SSH port; default `22`                                           |

---

## Outputs
- Directory: `outputs/`
- **Filename format:** `<hostname>_<ip>_<mm-dd-YYYY__HH-MM-SS>.log`
- Header includes hostname, IP, mode, and device type.

---

## Workflow with `config.txt` and `verify.txt`

1. **Test first:**
   ```bash
   python run_commands_netmiko.py --devices devices.csv --commands commands.txt --mode show --ask
   ```
2. **Apply configuration:**
   ```bash
   python run_commands_netmiko.py --devices devices.csv --commands config.txt --mode config --ask
   ```
3. **Verify results:**
   ```bash
   python run_commands_netmiko.py --devices devices.csv --commands verify.txt --mode show --ask
   ```

- `config.txt`: lines are configuration commands sent in config mode. Comments starting with `#` or `!` are ignored.
- `verify.txt`: read-only “show” commands to validate changes.

---

## Troubleshooting
- Activate the correct venv if packages aren’t found.
- Using Netmiko 4.x — exceptions import from `netmiko` (already handled).
- Windows filename issues are avoided via hostname sanitization.
- Reduce `--threads` for slow links or limited jump hosts.

---

## Governance & Safety
- Always validate in **show mode** before **config mode**.
- Use small batches for config pushes and have rollback steps ready.
- Protect `outputs/` and any config artifacts — they may contain sensitive data.


---

## Change Log
### 2025-10-31
- Updated log filename format to `mm-dd-YYYY__HH-MM-SS`
- Added workflow details for `config.txt` and `verify.txt`
- Synchronized HOWTO and Confluence documentation
