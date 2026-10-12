"""Calcoli del modello: unit economics, scenari, avvio, rientro, circolante, sensibilità."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from .config import Config, ProductLine


def unit_economics(line: ProductLine, cfg: Config) -> dict:
    """Costi e margini per singola unità venduta al distributore."""
    ram = line.ram_gb * cfg.ram_eur_per_gb
    bom = line.chip_cost + ram + line.other_bom
    price = line.price_to_distributor
    gross = price - bom
    reserve = price * cfg.warranty_reserve_pct
    return {
        "line": line.name,
        "cores": line.cores,
        "chip": line.chip_cost,
        "ram": ram,
        "other_bom": line.other_bom,
        "bom": bom,
        "price": price,
        "gross_margin": gross,
        "gross_margin_pct": gross / price,
        "warranty_reserve": reserve,
        "net_margin": gross - reserve,
        "support_margin_per_year": price * cfg.support_annual_pct * cfg.support_margin_pct,
    }


def startup_total(cfg: Config) -> tuple[float, float, float]:
    """Costi di avvio: (minimo, centrale, massimo)."""
    low = sum(v[0] for v in cfg.startup_costs.values())
    high = sum(v[1] for v in cfg.startup_costs.values())
    return low, (low + high) / 2, high


def scenario_summary(cfg: Config, scenario: str) -> dict:
    """Risultati annui di uno scenario di volumi (a regime, senza crescita)."""
    units = cfg.scenarios[scenario]
    revenue = component_cost = gross = net = support = 0.0
    rows = []
    for line in cfg.lines:
        n = units.get(line.name, 0)
        ue = unit_economics(line, cfg)
        rows.append({"line": line.name, "units": n, "revenue": n * ue["price"],
                     "net_margin": n * ue["net_margin"]})
        revenue += n * ue["price"]
        component_cost += n * ue["bom"]
        gross += n * ue["gross_margin"]
        net += n * ue["net_margin"]
        support += n * ue["support_margin_per_year"]
    d_lo, d_hi = cfg.working_capital_days
    _, start_mid, _ = startup_total(cfg)
    return {
        "scenario": scenario,
        "lines": rows,
        "revenue": revenue,
        "component_cost": component_cost,
        "gross_margin": gross,
        "net_margin": net,                       # dopo riserva garanzia
        "support_margin_per_year": support,      # ricorrente, dall'anno dopo
        "working_capital_low": component_cost * d_lo / 365,
        "working_capital_high": component_cost * d_hi / 365,
        "payback_months": (start_mid / net * 12) if net > 0 else None,
    }


def cashflow(cfg: Config, scenario: str, years: int = 5) -> list[dict]:
    """Flusso annuale semplificato: avvio, vendite, supporto sul parco installato."""
    _, start_mid, _ = startup_total(cfg)
    units = cfg.scenarios[scenario]
    ue = {line.name: unit_economics(line, cfg) for line in cfg.lines}
    out, installed_revenue, cumulative = [], 0.0, 0.0
    for i in range(years):
        year = cfg.startup_year + i
        if year >= cfg.first_sales_year:
            factor = (1 + cfg.annual_unit_growth) ** (year - cfg.first_sales_year)
        else:
            factor = 0.0
        revenue = net = 0.0
        for name, n in units.items():
            sold = round(n * factor)
            revenue += sold * ue[name]["price"]
            net += sold * ue[name]["net_margin"]
        support = installed_revenue * cfg.support_annual_pct * cfg.support_margin_pct
        startup = start_mid if year == cfg.startup_year else 0.0
        flow = net + support - startup
        cumulative += flow
        out.append({"year": year, "revenue": revenue, "net_margin": net,
                    "support_margin": support, "startup_cost": startup,
                    "net_flow": flow, "cumulative": cumulative})
        installed_revenue += revenue
    return out


def with_multipliers(cfg: Config, chip_mult: float = 1.0, ram_mult: float = 1.0,
                     reprice: bool = False) -> Config:
    """Copia della config con chip e RAM scalati. Se reprice=True il prezzo di vendita
    segue il costo mantenendo costante la percentuale di margine lordo."""
    new = deepcopy(cfg)
    new.ram_eur_per_gb = cfg.ram_eur_per_gb * ram_mult
    new_lines = []
    for line in cfg.lines:
        base = unit_economics(line, cfg)
        changed = replace(line, chip_cost=line.chip_cost * chip_mult)
        if reprice:
            bom_new = unit_economics(changed, new)["bom"]
            price = bom_new / (1 - base["gross_margin_pct"])
            changed = replace(changed, price_to_distributor=price)
        new_lines.append(changed)
    new.lines = new_lines
    return new


def sensitivity(cfg: Config, scenario: str,
                chip_mults=(0.8, 1.0, 1.2, 1.5), ram_mults=(0.8, 1.0, 1.5, 2.0),
                reprice: bool = False) -> list[dict]:
    """Griglia di sensibilità su prezzo del chip e della RAM."""
    rows = []
    for c in chip_mults:
        for r in ram_mults:
            s = scenario_summary(with_multipliers(cfg, c, r, reprice), scenario)
            rows.append({"chip_mult": c, "ram_mult": r, "revenue": s["revenue"],
                         "net_margin": s["net_margin"], "payback_months": s["payback_months"]})
    return rows
