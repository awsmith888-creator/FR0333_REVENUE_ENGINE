#!/usr/bin/env python3
"""FR-0333 on-demand read-only ADB inventory parser.

Reads saved text only. Never starts ADB, connects to a device, opens ports,
installs apps, pushes commands, monitors continuously or stores raw serials.
"""
import argparse
import json
import re
from pathlib import Path

ALLOWED={"device","offline","unauthorized","recovery","sideload","bootloader"}
MAX_LINES=1000
SERIAL_PATTERN=re.compile(r"^[A-Za-z0-9_.:-]{1,180}$")

def analyze(text):
    if not isinstance(text,str) or len(text)>262144:
        raise ValueError("invalid or oversized diagnostic")
    seen=set()
    counts={k:0 for k in sorted(ALLOWED)}
    found_header=False
    saw_row=False
    errors=[]
    lines=text.splitlines()
    if len(lines)>MAX_LINES:
        raise ValueError("diagnostic exceeds maximum lines")
    for line in lines:
        stripped=line.strip()
        if not stripped:
            continue
        if not found_header:
            if stripped=="List of devices attached":
                found_header=True
            elif stripped.startswith("* daemon") or stripped.startswith("adb server version"):
                continue
            else:
                errors.append("unrecognized content before ADB inventory header")
            continue
        if stripped.startswith("* daemon"):
            errors.append("unexpected daemon line after inventory header")
            continue
        fields=stripped.split()
        if len(fields)<2 or not SERIAL_PATTERN.fullmatch(fields[0]):
            errors.append("invalid device row")
            continue
        serial, state=fields[0],fields[1]
        if serial in seen:
            errors.append("duplicate device identifier")
            continue
        seen.add(serial)
        if state not in ALLOWED:
            errors.append("unknown or noncanonical ADB state")
            continue
        # Any trailing -l hardware info is intentionally ignored, never persisted.
        counts[state]+=1
        saw_row=True
    if not found_header:
        errors.append("missing ADB header")
    total=sum(counts.values())
    authorized=counts["device"]
    return {
     "identifier":"FR0333.MOBILE.FLEET.OFFLINE.INVENTORY.0001",
     "status":"F.6.REJECT" if errors else "T.20.PASS.READ_ONLY_SNAPSHOT",
     "inventory_records":total,
     "adb_debug_ready_count":authorized,
     "unauthorized_count":counts["unauthorized"],
     "offline_count":counts["offline"],
     "other_recognized_states":{k:v for k,v in counts.items() if k not in ("device","offline","unauthorized")},
     "debug_ready_ratio":round(authorized/total,6) if total else None,
     "malformed_input_errors":len(errors),
     "failure_reasons":list(dict.fromkeys(errors)),
     "snapshot_state":"DECLARED_LOCAL_ADB_TEXT_NOT_AUTHENTICATED_WITH_HARDWARE",
     "live_devices_read":"U.21.HOLD",
     "operator_authorization":"U.21.HOLD",
     "voltage_current_temperature_readings":"U.21.HOLD",
     "equipment_actions":0,
     "network_requests":0,
     "privacy":"NO_DEVICE_SERIALS_EMITTED",
     "traces_attested":"U.21.HOLD"
    }

if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--input",type=Path,required=True,help="Previously saved adb devices -l text file")
    cli.add_argument("--receipt",type=Path,default=None)
    a=cli.parse_args()
    try:
        report=analyze(a.input.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,ValueError) as exc:
        report={"status":"F.6.REJECT","error_class":type(exc).__name__,"equipment_actions":0,"network_requests":0}
    encoded=json.dumps(report,sort_keys=True,indent=2)+"\n"
    if a.receipt:
        a.receipt.write_text(encoded,encoding="utf-8")
    print(encoded,end="")
    raise SystemExit(0 if report.get("status")=="T.20.PASS.READ_ONLY_SNAPSHOT" else 1)
