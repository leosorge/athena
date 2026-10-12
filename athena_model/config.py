"""Caricamento e validazione della configurazione del modello."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProductLine:
    name: str
    cores: int
    chip_cost: float             # costo del chip (ipotesi, non pubblico)
    ram_gb: int
    other_bom: float             # scheda, chassis, rete, NVMe
    price_to_distributor: float


@dataclass
class Config:
    ram_eur_per_gb: float
    warranty_reserve_pct: float
    support_annual_pct: float    # % annua del prezzo di vendita
    support_margin_pct: float    # margine sul servizio di supporto
    working_capital_days: tuple[int, int]
    startup_year: int
    first_sales_year: int
    annual_unit_growth: float
    startup_costs: dict[str, tuple[float, float]]
    lines: list[ProductLine]
    scenarios: dict[str, dict[str, int]]

    @classmethod
    def from_dict(cls, d: dict) -> "Config":
        a = d["assumptions"]
        cfg = cls(
            ram_eur_per_gb=float(a["ram_eur_per_gb"]),
            warranty_reserve_pct=float(a["warranty_reserve_pct"]),
            support_annual_pct=float(a["support_annual_pct"]),
            support_margin_pct=float(a["support_margin_pct"]),
            working_capital_days=(int(a["working_capital_days"][0]), int(a["working_capital_days"][1])),
            startup_year=int(a["startup_year"]),
            first_sales_year=int(a["first_sales_year"]),
            annual_unit_growth=float(a["annual_unit_growth"]),
            startup_costs={k: (float(v[0]), float(v[1])) for k, v in d["startup_costs"].items()},
            lines=[ProductLine(**line) for line in d["lines"]],
            scenarios={k: {n: int(u) for n, u in v.items()} for k, v in d["scenarios"].items()},
        )
        cfg.validate()
        return cfg

    @classmethod
    def from_json(cls, path: str | Path) -> "Config":
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def validate(self) -> None:
        for name in ("warranty_reserve_pct", "support_annual_pct", "support_margin_pct"):
            if not 0 <= getattr(self, name) <= 1:
                raise ValueError(f"{name} deve essere tra 0 e 1")
        if self.ram_eur_per_gb < 0:
            raise ValueError("ram_eur_per_gb non può essere negativo")
        lo, hi = self.working_capital_days
        if lo < 0 or lo > hi:
            raise ValueError("working_capital_days deve essere [min, max] con min <= max")
        if self.first_sales_year < self.startup_year:
            raise ValueError("first_sales_year non può precedere startup_year")
        for k, (lo_c, hi_c) in self.startup_costs.items():
            if lo_c < 0 or lo_c > hi_c:
                raise ValueError(f"startup_costs[{k}] deve essere [min, max] con min <= max")
        names = [line.name for line in self.lines]
        if len(set(names)) != len(names):
            raise ValueError("i nomi delle linee di prodotto devono essere unici")
        for line in self.lines:
            if line.price_to_distributor <= 0 or line.ram_gb < 0 or line.chip_cost < 0:
                raise ValueError(f"valori non validi per la linea {line.name}")
        for scen, units in self.scenarios.items():
            for n, u in units.items():
                if n not in names:
                    raise ValueError(f"scenario '{scen}': linea sconosciuta '{n}'")
                if u < 0:
                    raise ValueError(f"scenario '{scen}': unità negative per '{n}'")
