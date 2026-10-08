"""Offline FR0333 Living Manual vendor simulation; no external vendor connection."""
from dataclasses import dataclass
import hashlib
import json

VENDORS = ("META", "X.XAI", "GOOGLE", "MICROSOFT", "AMAZON", "SALESFORCE", "OPENAI")
TABS = {vendor: f"FR0333.TAB.AGENT.{i:02d}" for i, vendor in enumerate(VENDORS, 1)}
PIN = "FR0333.PIN.AGENT.0003.HUMANLOCK"
STEPS = ("SOURCE", "PIN", "TAB", "CAPABILITY", "ACCESS", "TEST", "RECEIPT", "DELTA", "STAY")

@dataclass(frozen=True)
class SimReceipt:
    vendor: str
    tab: str
    pin: str
    state: str
    operation: str
    digest: str

class ManualAgentSimulator:
    """A local contract simulator; not a real vendor API adapter."""
    def __init__(self, vendor):
        if vendor not in TABS:
            raise ValueError("unknown vendor")
        self.vendor = vendor
        self.tab = TABS[vendor]
        self.history = []

    def retrieve_pin(self):
        return PIN

    def route_tab(self):
        return self.tab

    def directions(self):
        return STEPS

    def execute(self, operation="READ.MANUAL", authorized=False):
        if operation != "READ.MANUAL" and not authorized:
            raise PermissionError("HUMANLOCK required")
        state = "T.20.SIMULATED" if operation == "READ.MANUAL" else "U.21.APPROVED.SIMULATION"
        payload = json.dumps({"vendor": self.vendor, "tab": self.tab, "pin": PIN,
                              "state": state, "operation": operation}, sort_keys=True)
        receipt = SimReceipt(self.vendor, self.tab, PIN, state, operation,
                             hashlib.sha256(payload.encode()).hexdigest())
        self.history.append(receipt)
        return receipt

    def snapshot(self):
        return [r.__dict__.copy() for r in self.history]

    def restore(self, snapshot):
        for item in snapshot:
            if item["vendor"] != self.vendor or item["tab"] != self.tab or item["pin"] != PIN:
                raise ValueError("invalid snapshot provenance")
            payload = json.dumps({key: item[key] for key in
                                  ("vendor", "tab", "pin", "state", "operation")}, sort_keys=True)
            if hashlib.sha256(payload.encode()).hexdigest() != item["digest"]:
                raise ValueError("snapshot integrity failure")
        self.history = [SimReceipt(**item) for item in snapshot]
