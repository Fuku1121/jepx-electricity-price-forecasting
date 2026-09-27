"""Hypothetical grid-side battery, with energy stored internally in MWh."""
from dataclasses import dataclass, asdict
import math
import numpy as np

DELTA_HOURS = 0.5
KWH_PER_MWH = 1000.0
FEASIBILITY_TOL = 1e-6

@dataclass(frozen=True)
class BatteryConfig:
    capacity_mwh: float = 1.0
    charge_power_mw: float = 0.5
    discharge_power_mw: float = 0.5
    initial_soc_fraction: float = 0.5
    min_soc_fraction: float = 0.1
    max_soc_fraction: float = 0.9
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    degradation_jpy_per_kwh: float = 0.0

    def __post_init__(self):
        if not all(math.isfinite(v) for v in asdict(self).values()):
            raise ValueError("Battery parameters must be finite")
        if min(self.capacity_mwh, self.charge_power_mw, self.discharge_power_mw) <= 0:
            raise ValueError("Capacity and power limits must be positive")
        if not 0 <= self.min_soc_fraction <= self.initial_soc_fraction <= self.max_soc_fraction <= 1:
            raise ValueError("Invalid SOC fractions")
        if self.min_soc_fraction == self.max_soc_fraction:
            raise ValueError("SOC range must be nonempty")
        if not 0 < self.charge_efficiency <= 1 or not 0 < self.discharge_efficiency <= 1:
            raise ValueError("Efficiencies must lie in (0, 1]")
        if self.degradation_jpy_per_kwh < 0:
            raise ValueError("Throughput cost cannot be negative")

    @property
    def initial_mwh(self):
        return self.capacity_mwh * self.initial_soc_fraction

    @property
    def round_trip_efficiency(self):
        return self.charge_efficiency * self.discharge_efficiency


def prices48(prices):
    values = np.asarray(prices, dtype=float)
    if values.shape != (48,) or not np.isfinite(values).all():
        raise ValueError("Expected 48 finite JPY/kWh prices")
    return values.copy()


@dataclass(frozen=True)
class BatterySchedule:
    # Tuples freeze the decision boundary; actual prices cannot mutate a plan.
    charge_mw: tuple[float, ...]
    discharge_mw: tuple[float, ...]
    soc_mwh: tuple[float, ...]
    config: BatteryConfig
    solver_gap: float = 0.0

    def __post_init__(self):
        for name in ("charge_mw", "discharge_mw", "soc_mwh"):
            object.__setattr__(self, name, tuple(float(v) for v in getattr(self, name)))
        self.validate()

    def validate(self):
        c, d, s = map(np.asarray, (self.charge_mw, self.discharge_mw, self.soc_mwh))
        b, t = self.config, FEASIBILITY_TOL
        if c.shape != (48,) or d.shape != (48,) or s.shape != (49,):
            raise ValueError("Invalid schedule dimensions")
        if not all(np.isfinite(v).all() for v in (c, d, s)):
            raise ValueError("Nonfinite schedule")
        if (c < -t).any() or (d < -t).any() or (c > b.charge_power_mw+t).any() or (d > b.discharge_power_mw+t).any():
            raise ValueError("Power constraint violation")
        if ((c > t) & (d > t)).any():
            raise ValueError("Simultaneous charging and discharging")
        if (s < b.capacity_mwh*b.min_soc_fraction-t).any() or (s > b.capacity_mwh*b.max_soc_fraction+t).any():
            raise ValueError("SOC bound violation")
        if abs(s[0]-b.initial_mwh) > t or abs(s[-1]-b.initial_mwh) > t:
            raise ValueError("Initial/terminal SOC violation")
        expected = b.charge_efficiency*c*DELTA_HOURS-d*DELTA_HOURS/b.discharge_efficiency
        if not np.allclose(np.diff(s), expected, atol=t, rtol=0):
            raise ValueError("SOC dynamics violation")


def no_operation(config=BatteryConfig()):
    return BatterySchedule((0.,)*48, (0.,)*48, (config.initial_mwh,)*49, config)
