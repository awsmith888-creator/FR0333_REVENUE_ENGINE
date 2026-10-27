# FR-0333 Mobile Fleet Control Evolution — 0.13

## Why
A user-shared Facebook reel shows a dark rear panel with apparent RJ45 and USB connections and text suggesting uniform control of multiple phones. **No accessible transcript, label or exact device identity was verified.** The product category is consistent with phone-farm control racks, not unique to any brand or particular board.

## Public source comparator
- Phones Farm's *particular* advertised 20-device chassis: **20 ports**, **5 V**, **40 A**, **200 W**, **3 fans**, with Ethernet on some configurations. These are vendor ratings, not bench-tested values, universal operating thresholds or confirmed values of the video device.
- The separate Phone Farm Shop manual documents multi-device control software concepts.
- Android Developers documents ADB multi-device enumeration, device serial selection and RSA debugging authorization. This is a platform capability, **not authorization to access someone else's devices**.
- Google Firebase Test Lab operates authorized app-test fleets; no Test Lab integration is claimed.
- USB-IF overcurrent conformance methods are a **test reference**, not evidence this unknown box has passed.

## Active + passive separation
10 append-only **MATRIX** facts M01–M10 and 10 paired **ACTIVE METRIC DEFINITIONS** A01–A10. All actual physical-sensor measurements, active hardware connection, port-current distribution, thermal thresholds and provider receipt fields remain null/HOLD. No motherboard access or physical port interrogation.

## Local executable gate
`fr0333_mobile_fleet_inventory_0001.py` is a Python parser for **saved text** from `adb devices -l`. It never runs `adb` or sends commands. It rejects unknown/duplicate states and malformed data; counts ready, unauthorized and offline states; omits physical serials from receipts. Output identities are not stable across runs by design. `device` means a debugging-ready state, **not consent to execute actions**.

```bash
python3 RavenCloudTaskbar/validate_mobile_fleet_evolution_0001.py
python3 RavenCloudTaskbar/test_fr0333_mobile_fleet_inventory_0001.py
python3 RavenCloudTaskbar/fr0333_mobile_fleet_inventory_0001.py --input saved_adb_device_list.txt --receipt inventory_receipt.json
```

## Boundary
The structure gate and synthetic parser tests do not establish hardware compatibility, thermal performance, electrical safety, live USB connection, device ownership, Android Enterprise authorization, or any live FR-0333 phone integration. Unauthorized bulk engagement, ad clicks, view manipulation and account farming are explicitly rejected.

The chain appends candidate 0.13 **after 0.12**; no prior entry is renumbered. HumanLock remains HOLD. No recurring tasks, merges, external actions or automatic device control.

`DOCUMENTED != CONNECTED != CONTROLLED != SAFETY_VERIFIED`.
