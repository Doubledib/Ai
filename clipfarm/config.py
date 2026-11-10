"""Config: which sources we may clip, and which brand/accounts each clip goes to."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# The only bases on which the pipeline will touch someone's footage.
#   own               - footage you (or a player you pay) recorded
#   clipping_program  - streamer/agency runs a clipping campaign you have joined
#   written_permission- you hold an email/contract from the rights holder
ALLOWED_LICENSES = {"own", "clipping_program", "written_permission"}


class LicenseError(RuntimeError):
    pass


@dataclass
class Source:
    name: str
    channel_id: str = ""          # YouTube channel id (UC...) for the watcher
    license: str = "none"
    license_ref: str = ""         # campaign URL / email / contract id proving it
    brand: str = ""               # which brand gets this source's clips
    credit: str = ""              # on-screen credit, e.g. "@streamer"

    def require_license(self) -> None:
        if self.license not in ALLOWED_LICENSES:
            raise LicenseError(
                f"source '{self.name}' has license='{self.license}'. "
                f"Refusing to ingest: set one of {sorted(ALLOWED_LICENSES)} and a license_ref."
            )
        if self.license != "own" and not self.license_ref:
            raise LicenseError(f"source '{self.name}' needs license_ref (proof of permission).")


@dataclass
class Brand:
    name: str
    angle: str = ""                               # editorial angle, used in AI titling
    accounts: dict[str, str] = field(default_factory=dict)  # platform -> handle
    daily_cap: int = 4                            # posts per platform per day


@dataclass
class Config:
    sources: dict[str, Source]
    brands: dict[str, Brand]

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        raw = json.loads(Path(path).read_text())
        sources = {s["name"]: Source(**s) for s in raw.get("sources", [])}
        brands = {b["name"]: Brand(**b) for b in raw.get("brands", [])}
        for s in sources.values():
            if s.brand and s.brand not in brands:
                raise ValueError(f"source '{s.name}' points at unknown brand '{s.brand}'")
        return cls(sources, brands)
