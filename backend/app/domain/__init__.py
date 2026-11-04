"""Pure business rules with no database or HTTP dependencies.

Everything here is deterministic and unit-testable in isolation. Services
orchestrate persistence around these rules; the simulator reuses them so the
synthetic factory obeys the same rules as the API.
"""
