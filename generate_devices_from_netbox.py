#!/usr/bin/env python3
"""
Generate a Netmiko-ready devices.csv from a NetBox CSV export.

Usage:
    python generate_devices_from_netbox_v2.py --input <file.csv> [--output devices.csv]

Example:
    python generate_devices_from_netbox_v2.py --input netbox_devices_2.csv
"""

import argparse
import re
import pandas as pd
from pathlib import Path


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
    return re.sub(r"/.*$", "", ip.strip())


def sanitize_hostname(name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        return ""
    return " ".join(name.strip().split())


def main():
    parser = argparse.ArgumentParser(description="Convert NetBox CSV export to Netmiko devices.csv")
    parser.add_argument("--input", "-i", required=True, help="Path to NetBox CSV export file")
    parser.add_argument("--output", "-o", default="devices.csv", help="Output CSV file (default: devices.csv)")
    args = parser.parse_args()

    infile = Path(args.input)
    outfile = Path(args.output)

    if not infile.exists():
        raise FileNotFoundError(f"Input file not found: {infile}")

    df = pd.read_csv(infile)

    required_cols = ["Name", "Manufacturer", "IP Address"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    df = df[df["IP Address"].notna() & (df["IP Address"].astype(str).str.strip() != "")]
    df["hostname"] = df["Name"].apply(sanitize_hostname)
    df["host"] = df["IP Address"].astype(str).apply(normalize_ip)
    df["device_type"] = df["Manufacturer"].astype(str).apply(map_device_type)

    out = df[["hostname", "device_type", "host"]].copy()
    out["username"] = ""
    out["password"] = ""
    out["secret"] = ""
    out["port"] = "22"

    out = out[(out["host"].astype(str).str.strip() != "") & (out["hostname"].astype(str).str.strip() != "")]

    out.to_csv(outfile, index=False)
    print(f"✅ Exported {len(out)} devices to {outfile}")


if __name__ == "__main__":
    main()
