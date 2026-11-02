#!/usr/bin/env python3
"""Offline fixtures only. No ADB daemon, USB interface or internet is accessed."""
import json
from fr0333_mobile_fleet_inventory_0001 import analyze

baseline="""List of devices attached
emulator-5554  device product:sdk model:Generic device:emu transport_id:1
012345ABCDEF unauthorized usb:1-2 transport_id:3
RAVEN_03 offline transport_id:4
"""
r=analyze(baseline)
assert r["status"]=="T.20.PASS.READ_ONLY_SNAPSHOT",r
assert r["inventory_records"]==3 and r["adb_debug_ready_count"]==1
assert r["unauthorized_count"]==1 and r["offline_count"]==1
assert r["debug_ready_ratio"]==0.333333
assert "012345ABCDEF" not in json.dumps(r)
assert "emulator-5554" not in json.dumps(r)
assert r["equipment_actions"]==0 and r["network_requests"]==0
empty=analyze("List of devices attached\n\n")
assert empty["status"]=="T.20.PASS.READ_ONLY_SNAPSHOT" and empty["inventory_records"]==0
assert empty["debug_ready_ratio"] is None
bad=[
 ("missing header","RAVEN_01 device"),
 ("duplicate","List of devices attached\nA device\nA device\n"),
 ("unknown","List of devices attached\nA active\n"),
 ("missing status","List of devices attached\nA\n"),
 ("invalid serial","List of devices attached\n../../bad device\n"),
 ("oversized","X"*262145),
 ("unexpected daemon","List of devices attached\n* daemon launched\n"),
 ("untrusted extra header","fake prefix\nList of devices attached\n"),
]
for name,payload in bad:
 try:
    result=analyze(payload)
 except ValueError:
    continue
 assert result["status"]=="F.6.REJECT",(name,result)
print(json.dumps({"state":"T.20.PASS.SYNTHETIC_ONLY","valid_fixture_count":2,
  "negative_cases_rejected":len(bad),"serials_emitted":0,"real_connected_devices":0,"adb_commands_executed":0}))
