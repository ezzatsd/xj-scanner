"""Read-only OBD-II data sources used by the Polo scanner.

The first implementation is deliberately vehicle-free: ``DemoSource``
generates plausible engine speed and coolant temperature values.  A real
OBD-II/CAN source can later implement the same ``read_param`` method without
changing the user interface or CSV logger.
"""

from dataclasses import dataclass
import math
import time


PID_COOLANT_TEMP = 0x05
PID_ENGINE_RPM = 0x0C


class LinkError(Exception):
    """The selected data source could not provide a value."""


@dataclass(frozen=True)
class Param:
    pid: int
    name: str
    unit: str

    @property
    def label(self):
        return f"{self.name} ({self.unit})" if self.unit else self.name


PARAMS = [
    Param(PID_ENGINE_RPM, "Régime moteur", "tr/min"),
    Param(PID_COOLANT_TEMP, "Température liquide de refroidissement", "°C"),
]
PARAMS_BY_PID = {param.pid: param for param in PARAMS}


class DemoSource:
    """Generate two plausible readings without connecting to a vehicle."""

    def __init__(self):
        self._started_at = time.monotonic()
        self._closed = False

    def read_param(self, pid):
        if self._closed:
            raise LinkError("La source simulée est fermée.")

        elapsed = time.monotonic() - self._started_at
        if pid == PID_ENGINE_RPM:
            # A warm-idle-like value that moves gently instead of staying fixed.
            return round(800 + 35 * math.sin(elapsed * 1.4))
        if pid == PID_COOLANT_TEMP:
            # Start cold and warm up faster than a real car for an easy demo.
            return round(min(90.0, 20.0 + elapsed * 0.5), 1)
        raise LinkError(f"PID simulé non pris en charge : {pid:02X}")

    def close(self):
        self._closed = True
