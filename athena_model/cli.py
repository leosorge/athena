"""Interfaccia a riga di comando del modello Athena."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .config import Config
from .model import cashflow, scenario_summary, sensitivity, startup_total, unit_economics


def eur(x: float | None) -> str:
    if x is None:
        return "n/d"
    return f"{x:,.0f}".replace(",", ".") + " €"


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="athena_model", description=__doc__)
    p.add_argument("--config", default="config/default.json", help="file JSON delle ipotesi")
    p.add_argument("--scenario", help="nome dello scenario (default: tutti)")
    p.add_argument("--years", type=int, default=5, help="anni del flusso di cassa")
    p.add_argument("--sensitivity", action="store_true", help="stampa la griglia di sensibilità")
    p.add_argument("--reprice", action="store_true", help="nella sensibilità, adegua il prezzo al costo")
    p.add_argument("--export", metavar="DIR", help="esporta i risultati in CSV")
    args = p.parse_args(argv)

    cfg = Config.from_json(args.config)
    scenarios = [args.scenario] if args.scenario else list(cfg.scenarios)

    print("== Unit economics per unità ==")
    ue_rows = [unit_economics(line, cfg) for line in cfg.lines]
    for r in ue_rows:
        print(f"{r['line']:<11} BOM {eur(r['bom']):>10}  prezzo {eur(r['price']):>10}  "
              f"margine netto {eur(r['net_margin']):>9}  ({r['gross_margin_pct']:.1%} lordo)")

    lo, mid, hi = startup_total(cfg)
    print(f"\n== Costi di avvio ({cfg.startup_year}) ==\n{eur(lo)} - {eur(hi)} (centrale {eur(mid)})")

    summaries, flows = [], []
    for s in scenarios:
        r = scenario_summary(cfg, s)
        summaries.append({k: v for k, v in r.items() if k != "lines"})
        pb = f"{r['payback_months']:.1f} mesi" if r["payback_months"] else "n/d"
        print(f"\n== Scenario: {s} ==")
        print(f"Ricavi {eur(r['revenue'])} | componenti {eur(r['component_cost'])} | "
              f"margine netto {eur(r['net_margin'])} | supporto/anno {eur(r['support_margin_per_year'])}")
        print(f"Circolante {eur(r['working_capital_low'])} - {eur(r['working_capital_high'])} | rientro {pb}")
        for row in cashflow(cfg, s, args.years):
            flows.append({"scenario": s, **row})
        if args.sensitivity:
            print("  sensibilità (chip x, RAM x -> margine netto, rientro):")
            for row in sensitivity(cfg, s, reprice=args.reprice):
                pbm = f"{row['payback_months']:.0f} m" if row["payback_months"] else "n/d"
                print(f"   {row['chip_mult']:.1f}x {row['ram_mult']:.1f}x -> {eur(row['net_margin']):>12} {pbm:>6}")

    print("\n== Flusso di cassa cumulato ==")
    for s in scenarios:
        line = " | ".join(f"{r['year']}: {eur(r['cumulative'])}" for r in flows if r["scenario"] == s)
        print(f"{s:<12}{line}")

    if args.export:
        out = Path(args.export)
        out.mkdir(parents=True, exist_ok=True)
        _write_csv(out / "unit_economics.csv", ue_rows)
        _write_csv(out / "scenari.csv", summaries)
        _write_csv(out / "flusso_di_cassa.csv", flows)
        if args.sensitivity:
            _write_csv(out / "sensibilita.csv", [{"scenario": s, **r}
                       for s in scenarios for r in sensitivity(cfg, s, reprice=args.reprice)])
        print(f"\nCSV salvati in {out}/")
    return 0
