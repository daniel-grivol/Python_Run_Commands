# HOWTO: Run Bulk Network Commands with Netmiko

This guide walks through the full workflow: **NetBox → devices.csv → Netmiko runner → logs**.

Logs are saved per device in outputs/host_mm-dd-YYYY__HH-MM-SS.log


---

## 0) Prerequisites
- Python 3.10+
- Network reachability (SSH) to device management IPs
- Optional: NetBox CSV export named `netbox_devices_2.csv`

---

## 1) Set up a virtual environment
**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

---

## 2) Install dependencies
```bash
pip install -r requirements.txt
```
This installs:
- `netmiko` (SSH to network devices)
- `pandas` (read/filter CSVs)
- `openpyxl` (optional Excel support)

---

## 3) Generate `devices.csv` from NetBox (optional)
If you have a NetBox export `netbox_full_exported_devices_.csv` in the same folder:
If you have a NetBox export `netbox_PEs_exported_devices.csv` in the same folder:

What does it do?
- Rads your netbox_exported_file.csv
- Filters devices (for example, by Manufacturer = “Arista” or Role = “Switch (Access)”)
- Exports a Netmiko-ready devices.csv (host, device_type, etc.)

```bash
python generate_devices_from_netbox.py --input netbox_full_exported_devices_.csv
#or
python generate_devices_from_netbox.py --input netbox_PEs_exported_devices.csv --output EVPN_devices.csv

```
- Output: `devices.csv` or `EVPN_devices.csv` with columns
  ```
  hostname,device_type,host,username,password,secret,port
  ```
- `hostname` ← NetBox `Name`
- `host` ← `IP Address` without `/mask`
- `device_type` inferred from `Manufacturer` (Cisco/Arista/Juniper/etc.)

> You can open `devices.csv` or `EVPN_devices.csv` in Excel to review and delete any devices you don’t want to touch.

---

## 4) Create your command list
**Show commands (`commands.txt`):**
```
terminal length 0
show version
show ip interface brief
show lldp neighbors
```
**Config commands (`config.txt`):**
The config.txt file is the list of configuration commands that the script will push to devices when you run it in --mode config. The script:
- SSHs into each device listed in devices.csv
- Enters configuration mode (for example conf t on Cisco IOS, or configure on Junos)
- Sends each line from config.txt as a command
- Exits configuration mode and saves the output to a per-device log file.

```bash
#1)Test (show) commands:
python run_commands_netmiko.py --devices devices.csv --commands commands.txt --mode show --ask

#2)Then apply config:
python run_commands_netmiko.py --devices devices.csv --commands config.txt --mode config --ask

#3)Verify after:
python run_commands_netmiko.py --devices devices.csv --commands verify.txt --mode show --ask
```

---

## 5) Run the tool

### Show mode (safe / read-only)
```bash
python run_commands_netmiko.py --devices devices.csv --commands commands.txt --mode show --ask
or
python run_commands_netmiko.py --devices EVPN_devices.csv --commands commands.txt --mode show --ask
```

---

## 6) Review outputs
Logs are written per-device into `outputs/` with the filename:
```
<hostname>_<ip>_<mm-dd-YYYY__HH-MM-SS>.log
```
Each file starts with a header and (in show mode) contains each command prefixed with `$ <command>` followed by output.


---

## 7) Supported Platforms (examples)
- Cisco IOS (`cisco_ios`)
- Arista EOS (`arista_eos`)
- Juniper Junos (`juniper_junos`)
- HP ProCurve (`hp_procurve`)
- Dell OS10 (`dell_os10`)
- Fortinet (`fortinet`)
- Palo Alto PAN-OS (`paloalto_panos`)
- Generic/other (`generic`) — will attempt SSH but features may be limited


---

## 8) 

Assuming all your .log files are in the same directory and you want to merge them all into a new file named merged_output.log

Run the Command:
```bash
Get-Content -Path *.log | Set-Content -Path merged_output.log
```

---

## Appendix: CLI Reference

```
usage: run_commands_netmiko.py [-h] --devices DEVICES --commands COMMANDS
                               [--mode {show,config}] [--threads THREADS]
                               [--out OUT] [--ask] [--use-keys]
                               [--key-file KEY_FILE] [--cmd-delay CMD_DELAY]
```

- `--devices`: path to `devices.csv`
- `--commands`: path to commands file (`commands.txt` or `config.txt`)
- `--mode`: `show` (default) or `config`
- `--threads`: concurrent sessions (default 20)
- `--out`: output folder (default `outputs`)
- `--ask`: prompt once for credentials/secret
- `--use-keys`: use SSH key auth
- `--key-file`: path to private key
- `--cmd-delay`: optional delay between commands (seconds)

