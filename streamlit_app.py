"""Dashboard interattiva del modello Athena."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from athena_model.config import Config
from athena_model.model import cashflow, scenario_summary, sensitivity, startup_total, unit_economics

st.set_page_config(page_title="Athena · Modello economico", page_icon="🏛️", layout="wide")
st.title("Athena · Modello economico")
st.caption("Server Arm senza GPU · SiPearl Athena1 · Linee da 16, 32 e 64 core")
st.info("I valori sono ipotesi da sostituire con preventivi reali. Il margine indicato è dopo la riserva garanzia, prima di costi operativi, imposte e finanziamenti.")
default = json.loads((Path(__file__).parent / "config/default.json").read_text(encoding="utf-8"))
with st.sidebar:
    st.header("Ipotesi")
    upload = st.file_uploader("Carica configurazione JSON", type="json")
    try:
        data = json.load(upload) if upload else default
        Config.from_dict(data)
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        st.error(f"Configurazione non valida: {exc}")
        st.stop()
    a = data["assumptions"]
    scenario = st.selectbox("Scenario", list(data["scenarios"]), index=list(data["scenarios"]).index("base") if "base" in data["scenarios"] else 0)
    years = st.slider("Anni della proiezione", 2, 15, 5)
    a["ram_eur_per_gb"] = st.number_input("RAM (€/GB)", min_value=0.0, value=float(a["ram_eur_per_gb"]))
    for key, label in [("warranty_reserve_pct", "Riserva garanzia (%)"), ("support_annual_pct", "Supporto annuo (% prezzo)"), ("support_margin_pct", "Margine supporto (%)")]:
        a[key] = st.number_input(label, min_value=0.0, max_value=100.0, value=float(a[key])*100)/100
    a["annual_unit_growth"] = st.number_input("Crescita annua volumi (%)", min_value=-100.0, value=float(a["annual_unit_growth"])*100)/100
    reprice = st.checkbox("Adegua i prezzi nella sensibilità")

with st.expander("Modifica prodotti e volumi", expanded=False):
    products = st.data_editor(pd.DataFrame(data["lines"]), hide_index=True, disabled=["name"], key="products")
    volumes = st.data_editor(pd.DataFrame([{"linea": n, "unità": u} for n, u in data["scenarios"][scenario].items()]), hide_index=True, disabled=["linea"], key=f"volumes_{scenario}")
    data["lines"] = products.to_dict("records")
    data["scenarios"][scenario] = {r["linea"]: int(r["unità"]) for r in volumes.to_dict("records")}
try:
    cfg = Config.from_dict(data)
    if any(line.other_bom < 0 or line.cores <= 0 for line in cfg.lines):
        raise ValueError("Costi negativi o numero di core non valido")
    result = scenario_summary(cfg, scenario)
except (ValueError, KeyError, TypeError, IndexError) as exc:
    st.error(f"Dati non validi: {exc}")
    st.stop()

def eur(value):
    return f"{value:,.0f} €".replace(",", ".")

cols = st.columns(4)
cols[0].metric("Ricavi annui a regime", eur(result["revenue"]))
cols[1].metric("Margine dopo garanzia", eur(result["net_margin"]))
cols[2].metric("Avvio: costo centrale", eur(startup_total(cfg)[1]))
cols[3].metric("Rientro semplice a regime", f"{result['payback_months']:.1f} mesi" if result["payback_months"] is not None else "n/d")
st.caption("Il rientro semplice divide il costo iniziale per il margine annuo a regime; non comprende il periodo prima delle vendite né il capitale circolante.")
st.write(f"Capitale circolante stimato: **{eur(result['working_capital_low'])} – {eur(result['working_capital_high'])}**")
tabs = st.tabs(["Prodotti", "Flusso di cassa", "Sensibilità"])
with tabs[0]:
    units = pd.DataFrame([unit_economics(line, cfg) for line in cfg.lines])
    st.dataframe(units, hide_index=True)
    st.download_button("Scarica prodotti CSV", units.to_csv(index=False), "athena_prodotti.csv", "text/csv")
with tabs[1]:
    flows = pd.DataFrame(cashflow(cfg, scenario, years))
    st.line_chart(flows.set_index("year")[["cumulative", "net_flow"]])
    st.dataframe(flows, hide_index=True)
    st.caption("Flusso semplificato: margini delle vendite e del supporto meno avvio; non include variazioni del circolante, costi operativi o imposte.")
    st.download_button("Scarica flusso CSV", flows.to_csv(index=False), "athena_flusso.csv", "text/csv")
with tabs[2]:
    grid = pd.DataFrame(sensitivity(cfg, scenario, reprice=reprice))
    st.write("Margine dopo garanzia al variare dei moltiplicatori del costo del chip e della RAM")
    st.dataframe(grid.pivot(index="chip_mult", columns="ram_mult", values="net_margin"))
    st.download_button("Scarica sensibilità CSV", grid.to_csv(index=False), "athena_sensibilita.csv", "text/csv")
st.download_button("Scarica configurazione JSON", json.dumps(data, ensure_ascii=False, indent=2), "athena_config.json", "application/json")
