# Netmiko Bulk SSH Runner

This repository automates running commands (show/config) across multiple network devices in parallel via Netmiko.

---

## Quick Start

### 1. Create & activate a virtual environment
**Windows:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Generate `devices.csv` (optional)
```bash
python generate_devices_from_netbox_v2.py --input netbox_devices.csv
```

### 4. Run show or config mode
```bash
python run_commands_netmiko.py --devices devices.csv --commands commands.txt --mode show --ask
python run_commands_netmiko.py --devices devices.csv --commands config.txt --mode config --ask
```

---

## Outputs
- Logs saved per device in `outputs/` as:
  ```
  <hostname>_<ip>_<mm-dd-YYYY__HH-MM-SS>.log
  ```

---

## Files
- `run_commands_netmiko.py` — main runner
- `generate_devices_from_netbox_v2.py` — build devices.csv from NetBox export
- `config.txt` — configuration commands to apply
- `verify.txt` — validation commands after config
- `requirements.txt` — dependencies

---

## Change Log
### 2025-10-31
- Updated log filename format to `mm-dd-YYYY__HH-MM-SS`
- Added documentation for `config.txt` and `verify.txt`
- Updated HOWTO and Confluence documentation accordingly
