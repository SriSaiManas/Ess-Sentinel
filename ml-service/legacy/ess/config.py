"""Versioned, inspectable engineering policy; defaults are illustrative only."""
from dataclasses import dataclass, asdict
import json
from pathlib import Path

@dataclass(frozen=True)
class Policy:
    safety_fraction: float = .85
    robust_z: float = 3.5
    temporal_z: float = 3.5
    if_percentile: float = 95.0
    minimum_peers: int = 8
    scale_floor_fraction: float = .001
    watch_score: float = 20
    high_score: float = 45
    critical_score: float = 75
    population_weight: float = 30
    drift_weight: float = 25
    prediction_weight: float = 25
    proximity_weight: float = 10
    isolation_weight: float = 10
    def validate(self):
        vals = asdict(self)
        import math
        if any(not math.isfinite(v) for v in vals.values()):
            raise ValueError('Policy values must be finite.')
        if not 0 < self.safety_fraction <= 1 or self.robust_z <= 0 or self.temporal_z <= 0:
            raise ValueError('Safety fraction must be in (0,1]; Z thresholds must be positive.')
        if not 50 <= self.if_percentile < 100 or self.minimum_peers < 3 or self.scale_floor_fraction <= 0:
            raise ValueError('Invalid Isolation Forest percentile, peer count, or scale floor.')
        if not 0 <= self.watch_score < self.high_score < self.critical_score <= 100:
            raise ValueError('Risk cutoffs must increase between 0 and 100.')
        weights = [v for k,v in vals.items() if k.endswith('_weight')]
        if min(weights) < 0 or abs(sum(weights)-100)>1e-8:
            raise ValueError('Nonnegative risk weights must sum to 100.')
        return self
    def save(self, path):
        Path(path).write_text(json.dumps(asdict(self), indent=2))
