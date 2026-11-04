"""Single source of "now" for the services.

MySQL DATETIME columns in this schema have no fractional seconds, so a value
written with microseconds comes back truncated. Truncating before the write
keeps the value returned by a create call identical to the value read later.
"""

from datetime import datetime


def now() -> datetime:
    return datetime.now().replace(microsecond=0)
