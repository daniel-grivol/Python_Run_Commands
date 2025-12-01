#!/usr/bin/env python3
"""Netmiko bulk runner (v2) with hostname-aware logs and filenames.

- Reads devices from CSV with columns:
    required: host
    optional: hostname, device_type, username, password, secret, port
  (Backwards compatible: if 'hostname' is absent, it falls back to host/IP.)

- Example filename:
    FIHEL-LAN-3D-N_10.32.192.109_20251030-152200.log
"""
import argparse
import csv
import getpass
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from netmiko import ConnectHandler
from netmiko import NetmikoTimeoutException, NetmikoAuthenticationException


def load_devices(csv_path: Path) -> List[Dict[str, str]]:
    devices = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            device = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
            if not device.get("host"):  # require host/IP
                continue
            # ensure optional keys exist
            for k in ("hostname", "device_type", "username", "password", "secret", "port"):
                device.setdefault(k, "")
            devices.append(device)
    if not devices:
        raise ValueError(f"No devices found in {csv_path}")
    return devices


def safe_hostname(value: str) -> str:
    if not value:
        return "unknown"
    # Replace path-unfriendly chars; collapse whitespace
    v = " ".join(value.split())
    v = re.sub(r'[\\/<>:"|?*]', "-", v)  # Windows-forbidden
    v = v.replace(" ", "_")
    return v


def load_commands(cmd_path: Path) -> List[str]:
    with cmd_path.open(encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f]
    cmds = [ln for ln in lines if ln and not ln.lstrip().startswith(("#", "!"))]
    if not cmds:
        raise ValueError(f"No commands found in {cmd_path}")
    return cmds


def build_params(device_row: Dict[str, str],
                 global_user: Optional[str],
                 global_pass: Optional[str],
                 global_secret: Optional[str],
                 use_keys: bool,
                 key_file: Optional[str]) -> Dict:
    params = {
        "device_type": device_row.get("device_type") or "cisco_ios",
        "host": device_row["host"],
        "fast_cli": True,
    }
    params["username"] = device_row.get("username") or global_user
    params["password"] = device_row.get("password") or global_pass
    secret = device_row.get("secret") or global_secret
    if secret:
        params["secret"] = secret

    port = device_row.get("port")
    if port:
        try:
            params["port"] = int(port)
        except ValueError:
            pass

    if use_keys:
        params["use_keys"] = True
        if key_file:
            params["key_file"] = key_file

    return params


def run_on_device(device_row: Dict[str, str],
                  commands: List[str],
                  mode: str,
                  out_dir: Path,
                  global_user: Optional[str],
                  global_pass: Optional[str],
                  global_secret: Optional[str],
                  use_keys: bool,
                  key_file: Optional[str],
                  cmd_delay: float) -> Path:
    host = device_row["host"]
    hostname = device_row.get("hostname") or host  # fallback if missing
    params = build_params(device_row, global_user, global_pass, global_secret, use_keys, key_file)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    fname = f"{safe_hostname(hostname)}_{host}_{ts}.log"
    outfile = out_dir / fname

    header_lines = [
        f"==== DEVICE: {hostname} ({host}) ====",  # show both
        f"device_type: {params.get('device_type')}",
        f"mode: {mode}"
    ]
    if params.get("port"):
        header_lines.append(f"port: {params['port']}")
    header_txt = "\n".join(header_lines) + "\n\n"

    try:
        with ConnectHandler(**params) as conn:
            if params.get("secret"):
                try:
                    conn.enable()
                except Exception as e:
                    logging.warning("Enable failed on %s (%s): %s", hostname, host, e)

            if mode == "show":
                output_chunks = []
                for cmd in commands:
                    try:
                        out = conn.send_command(cmd, read_timeout=90)
                    except TypeError:
                        out = conn.send_command(cmd)
                    output_chunks.append(f"$ {cmd}\n{out}\n")
                output = header_txt + "\n".join(output_chunks)

            elif mode == "config":
                out = conn.send_config_set(commands, exit_config_mode=True)
                output = header_txt + out + "\n"
            else:
                raise ValueError("Unknown mode (use 'show' or 'config').")

        outfile.write_text(output, encoding="utf-8")
        logging.info("Success: %s (%s)", hostname, host)
        return outfile

    except NetmikoAuthenticationException as e:
        logging.error("AUTH FAIL %s (%s): %s", hostname, host, e)
        outfile.write_text(header_txt + f"AUTHENTICATION FAILED: {e}\n", encoding="utf-8")
        return outfile
    except NetmikoTimeoutException as e:
        logging.error("TIMEOUT %s (%s): %s", hostname, host, e)
        outfile.write_text(header_txt + f"TIMEOUT: {e}\n", encoding="utf-8")
        return outfile
    except Exception as e:
        logging.exception("ERROR %s (%s): %s", hostname, host, e)
        outfile.write_text(header_txt + f"ERROR: {e}\n", encoding="utf-8")
        return outfile


def main():
    parser = argparse.ArgumentParser(description="Run Netmiko commands on multiple devices (hostname-aware logs)." )
    parser.add_argument("--devices", "-d", required=True, type=Path, help="CSV with device inventory.")
    parser.add_argument("--commands", "-c", required=True, type=Path, help="Text file with commands (one per line)." )
    parser.add_argument("--mode", "-m", choices=["show", "config"], default="show", help="Treat commands as show or config." )
    parser.add_argument("--threads", "-t", type=int, default=20, help="Max concurrent SSH sessions." )
    parser.add_argument("--out", "-o", type=Path, default=Path("outputs"), help="Output directory." )
    parser.add_argument("--ask", action="store_true", help="Prompt once for username/password/enable if not given per-device." )
    parser.add_argument("--use-keys", action="store_true", help="Use SSH keys instead of password." )
    parser.add_argument("--key-file", type=str, default=None, help="Path to private key file (optional)." )
    parser.add_argument("--cmd-delay", type=float, default=0.0, help="Optional delay between commands (seconds)." )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S")

    devices = load_devices(args.devices)
    commands = load_commands(args.commands)

    g_user = g_pass = g_secret = None
    if args.ask and not args.use_keys:
        g_user = input("Username: ").strip()
        g_pass = getpass.getpass("Password: ")
        g_secret = getpass.getpass("Enable/secret (if any, Enter for none): ").strip() or None
    elif args.ask and args.use_keys:
        g_user = input("Username (for key auth): ").strip()
        g_secret = getpass.getpass("Enable/secret (if any, Enter for none): ").strip() or None

    args.out.mkdir(parents=True, exist_ok=True)

    futures = []
    results = []
    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        for dev in devices:
            futures.append(pool.submit(
                run_on_device, dev, commands, args.mode, args.out,
                g_user, g_pass, g_secret, args.use_keys, args.key_file, args.cmd_delay
            ))
        for f in as_completed(futures):
            results.append(f.result())

    print("\nAll done. Output files:")
    for p in results:
        print(f" - {p}")


if __name__ == "__main__":
    main()
