import copy
import json
from pathlib import Path

import pytest

from athena_model.config import Config
from athena_model.model import (cashflow, scenario_summary, sensitivity, startup_total,
                                unit_economics, with_multipliers)

CFG_PATH = Path(__file__).resolve().parent.parent / "config" / "default.json"


@pytest.fixture
def cfg():
    return Config.from_json(CFG_PATH)


def test_unit_economics_orders_of_magnitude(cfg):
    ue = {line.name: unit_economics(line, cfg) for line in cfg.lines}
    assert ue["Athena-16"]["bom"] == pytest.approx(4900, rel=0.01)
    assert ue["Athena-32"]["bom"] == pytest.approx(8300, rel=0.01)
    assert ue["Athena-64"]["bom"] == pytest.approx(15600, rel=0.01)
    assert ue["Athena-64"]["net_margin"] == pytest.approx(4390, rel=0.02)


def test_startup_total(cfg):
    assert startup_total(cfg) == (1_050_000, 1_400_000, 1_750_000)


def test_base_scenario(cfg):
    s = scenario_summary(cfg, "base")
    assert s["revenue"] == pytest.approx(6_200_000)
    assert s["net_margin"] == pytest.approx(1_360_000, rel=0.02)
    assert s["payback_months"] == pytest.approx(12.4, abs=0.5)
    assert 1.1e6 < s["working_capital_low"] < s["working_capital_high"] < 1.7e6


def test_scenarios_scale_linearly(cfg):
    base = scenario_summary(cfg, "base")["net_margin"]
    assert scenario_summary(cfg, "ottimistico")["net_margin"] == pytest.approx(2 * base)
    assert scenario_summary(cfg, "prudente")["net_margin"] == pytest.approx(base / 2)


def test_cashflow_starts_negative_and_recovers(cfg):
    rows = cashflow(cfg, "base", years=5)
    assert rows[0]["year"] == 2027 and rows[0]["net_flow"] < 0
    assert rows[1]["support_margin"] == 0   # nessun parco installato nel primo anno di vendite
    assert rows[-1]["cumulative"] > 0


def test_reprice_keeps_margin_pct(cfg):
    new = with_multipliers(cfg, chip_mult=1.5, ram_mult=2.0, reprice=True)
    for old_line, new_line in zip(cfg.lines, new.lines):
        a = unit_economics(old_line, cfg)["gross_margin_pct"]
        b = unit_economics(new_line, new)["gross_margin_pct"]
        assert a == pytest.approx(b)


def test_sensitivity_fixed_price_reduces_margin(cfg):
    rows = sensitivity(cfg, "base", chip_mults=(1.0, 1.5), ram_mults=(1.0,))
    assert rows[1]["net_margin"] < rows[0]["net_margin"]


def test_validation_rejects_unknown_line():
    d = copy.deepcopy(json.loads(CFG_PATH.read_text(encoding="utf-8")))
    d["scenarios"]["base"]["Athena-99"] = 10
    with pytest.raises(ValueError):
        Config.from_dict(d)
