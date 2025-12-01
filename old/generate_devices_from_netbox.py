#!/usr/bin/env python3
"""Generate a Netmiko-ready devices.csv from a NetBox CSV export.

- Reads:  netbox_devices_2.csv  (must be in the same folder)
- Writes: devices.csv           (columns ordered for readability)

Columns produced:
  hostname, device_type, host, username, password, secret, port

Notes:
- 'hostname' comes from the NetBox 'Name' column.
- 'host' is the management IP with any subnet mask removed.
- 'device_type' is inferred from 'Manufacturer' with sensible defaults.
"""

import sys
import re
import pandas as pd
from pathlib import Path

INFILE = Path("netbox_devices_2.csv")
OUTFILE = Path("devices.csv")


def map_device_type(manufacturer: str) -> str:
    m = (manufacturer or "").lower()
    if "cisco" in m:
        return "cisco_ios"
    if "arista" in m:
        return "arista_eos"
    if "juniper" in m:
        return "juniper_junos"
    if "hp" in m or "hewlett" in m:
        return "hp_procurve"
    if "dell" in m:
        return "dell_os10"
    if "fortinet" in m:
        return "fortinet"
    if "palo" in m:
        return "paloalto_panos"
    if "linux" in m or "ubuntu" in m:
        return "linux"
    return "generic"


def normalize_ip(ip: str) -> str:
    if not isinstance(ip, str) or not ip.strip():
        return ""
    # Strip CIDR if present (e.g., 10.0.0.1/24 -> 10.0.0.1)
    return re.sub(r"/.*$", "", ip.strip())


def sanitize_hostname(name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        return ""
    # Trim spaces, collapse internal whitespace, remove illegal CSV-breaking chars
    cleaned = " ".join(name.strip().split())
    return cleaned


def main() -> int:
    if not INFILE.exists():
        print(f"❌ Input file not found: {INFILE}")
        return 1

    df = pd.read_csv(INFILE)

    # Basic column presence checks
    required_cols = ["Name", "Manufacturer", "IP Address"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"❌ Missing required column(s) in {INFILE}: {', '.join(missing)}")
        return 2

    # Drop rows without an IP
    df = df[df["IP Address"].notna() & (df["IP Address"].astype(str).str.strip() != "")]

    # Build fields
    df["hostname"] = df["Name"].apply(sanitize_hostname)
    df["host"] = df["IP Address"].astype(str).apply(normalize_ip)
    df["device_type"] = df["Manufacturer"].astype(str).apply(map_device_type)

    # Compose output in desired column order (hostname first for readability)
    out = df[["hostname", "device_type", "host"]].copy()
    out["username"] = ""
    out["password"] = ""
    out["secret"] = ""
    out["port"] = "22"

    # Drop any rows missing host or hostname after normalization
    out = out[(out["host"].astype(str).str.strip() != "") & (out["hostname"].astype(str).str.strip() != "")]

    out.to_csv(OUTFILE, index=False)
    print(f"✅ Exported {len(out)} devices to {OUTFILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
