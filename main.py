import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ---------------------- Standarddaten ----------------------------------

HOURS = [6, 9, 12, 15, 18, 21]

PRODUCERS = [
    "Wind 1", #"Wind 2", "Wind 3",
    "PV 1", #"PV 2",
    "Wasser 1", #"Wasser 2",
    "Pumpspeicher 1",
    "Gas 1", "Gas 2",
    "Nuklear 1"
    ]

factor = 2.5

#---------------------- Nachfrageprofile ----------------------

demand_profiles = {
    "Normaler Tag": {6: 600, 9: 900, 12: 800, 15: 700, 18: 1200, 21: 700},
    "Wintertag": {6: 1500, 9: 2000, 12: 2500, 15: 2700, 18: 3500, 21: 2500},
    "Sommertag": {6: 500, 9: 700, 12: 700, 15: 500, 18: 1000, 21: 700},
    }

#---------------------- Kapazitäten ----------------------

capacity_profiles = {
    "Normaler Tag": {
        "Wind 1": [120, 80, 80, 150, 60, 90], #600
        "Wind 2": [120, 80, 80, 150, 60, 90],
        "Wind 3": [120, 80, 80, 150, 60, 90],
        "PV 1": [0, 90, 300, 150, 50, 0],
        "PV 2": [0, 90, 300, 150, 50, 0],
        "Wasser 1": [80, 100, 80, 120, 80, 120],
        "Wasser 2": [80, 100, 80, 120, 80, 120],
        "Pumpspeicher 1": [200, 200, 200, 200, 200, 200],
        "Gas 1": [999999] * 6,
        "Gas 2": [999999] * 6,
        "Nuklear 1": [100] * 6 ,
    },
    "Wintertag": {
        "Wind 1": [180, 140, 100, 200, 80, 120],
        "Wind 2": [180, 140, 100, 200, 80, 120],
        "Wind 3": [180, 140, 100, 200, 80, 120],
        "PV 1": [0, 200, 350, 300, 150, 5],
        "PV 2": [0, 200, 350, 300, 150, 5],
        "Wasser 1": [150, 150, 200, 200, 150, 150],
        "Wasser 2": [150, 150, 200, 200, 150, 150],
        "Pumpspeicher 1": [300, 300, 300, 300, 300, 300],
        "Gas 1": [999999] * 6,
        "Gas 2": [999999] * 6,
        "Nuklear 1": [500] * 6,
        },
    "Sommertag": {
        "Wind 1": [100, 70, 50, 40, 70, 80],
        "Wind 2": [100, 70, 50, 40, 70, 80],
        "Wind 3": [100, 70, 50, 40, 70, 80],
        "PV 1": [50, 250, 500, 400, 250, 50],
        "PV 2": [50, 250, 500, 400, 250, 50],
        "Wasser 1": [200, 100, 100, 100, 100, 100],
        "Wasser 2": [200, 100, 100, 100, 100, 100],
        "Pumpspeicher 1": [300, 300, 300, 300, 300, 300],
        "Gas 1": [999999] * 6,
        "Gas 2": [999999] * 6,
        "Nuklear 1": [500] * 6,
        },
    }

# ---------------------- Kosten & Farben ----------------------

cost_default = {
    "Wind 1": 0, "Wind 2": 0, "Wind 3": 0,
    "PV 1": 0, "PV 2": 0,
    "Wasser 1": 10, "Wasser 2": 10,
    "Pumpspeicher 1": 5,
    "Gas 1": 60, "Gas 2": 60,
    "Nuklear 1": 20
    }

colors = {
    "Wind 1": "green", "Wind 2": "limegreen", "Wind 3": "seagreen",
    "PV 1": "orange", "PV 2": "gold",
    "Wasser 1": "blue", "Wasser 2": "skyblue",
    "Pumpspeicher 1": "navy",
    "Gas 1": "gray", "Gas 2": "darkgray",
    "Nuklear 1": "violet"
    }

petrol_color = "#006C67"
max_storage = 500.0
# ---------------------- Session-States ---------------------------------

st.session_state.setdefault("profits", {p: 0.0 for p in PRODUCERS})
st.session_state.setdefault("storage_level", 250.0)
st.session_state.setdefault("day_type", "Normaler Tag")
st.session_state.setdefault("hour_index", 0)

# ---------------------- UI --------------------------------------------

def limit_pumpspeicher(qty, storage_level, max_storage):
    if qty < 0 and storage_level >= max_storage:
        st.info("Pumpspeicher voll – kann nicht laden!")
        return 0.0
    elif qty > 0 and storage_level <= 0:
        st.info("Pumpspeicher leer – kann nicht entladen!")
        return 0.0
    return qty

st.set_page_config(page_title="Merit Order Spiel", layout="wide")
st.title("🔌 Merit-Order-Spiel")

# Dropdown menu for day type
st.sidebar.subheader("Tagestyp auswählen")
day_type = st.sidebar.selectbox("Tagestyp", ["Normaler Tag", "Wintertag", "Sommertag"])
st.session_state.day_type = day_type

# Dropdown menu for hour selection
st.sidebar.subheader("Stunde auswählen")
hour = st.sidebar.selectbox("Stunde", HOURS, index=st.session_state.hour_index)
st.session_state.hour_index = HOURS.index(hour)

# Update demand and capacities based on day type
demand_default = demand_profiles[day_type]
caps_default = capacity_profiles[day_type]

col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("Nachfrage und maximale Erzeugung pro Stunde / MWh")

    current_hour = HOURS[st.session_state.hour_index]
    demand_series = pd.Series([demand_default[h] for h in HOURS], index=HOURS, name="Nachfrage")

    # Gruppen (Technologien) – Gas wird bewusst ausgelassen
    tech_groups = ["Wind", "PV", "Wasser", "Pumpspeicher", "Nuklear"]

    group_colors = {
        "Wind": "#3ca54c",
        "PV": "#f68b1f",
        "Wasser": "#1f77b4",
        "Pumpspeicher": "#006C67",  # Petrol
        "Nuklear": "#6a0dad"
    }

    # Aggregiere Kapazitäten über alle Anlagen derselben Technologie
    total_caps = {tech: np.zeros(len(HOURS)) for tech in tech_groups}
    for tech in tech_groups:
        relevant = [k for k in caps_default.keys() if k.startswith(tech)]
        if not relevant and tech in caps_default:
            relevant = [tech]
        for h_idx, h in enumerate(HOURS):
            total_caps[tech][h_idx] = sum(caps_default[r][h_idx] for r in relevant)

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(HOURS))
    width = 0.35

    # Nachfragebalken – aktuelle Stunde petrolfarben markieren
    demand_colors = [
        ("lightgray" if i != st.session_state.hour_index else group_colors["Pumpspeicher"])
        for i in range(len(HOURS))
    ]
    ax.bar(x - width / 2, demand_series.values, width, color=demand_colors, label="Nachfrage")

    # Gestapelte Erzeugungsbalken (ohne Gas)
    bottom = np.zeros(len(HOURS))
    for tech in tech_groups:
        cap_vals = total_caps[tech]
        ax.bar(x + width / 2, cap_vals, width, bottom=bottom,
               color=group_colors[tech], label=f"{tech} (gesamt)")
        bottom += cap_vals

    ax.set_xticks(x)
    ax.set_xticklabels(HOURS)
    ax.set_xlabel("Stunden")
    ax.set_ylabel("MWh")
    ax.set_title(f"Nachfrage (links) und Erzeugungskapazität (rechts, ohne Gas) — {day_type}")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    st.pyplot(fig)



with col2:
    st.write(f"**Aktuelle Stunde:** {hour} Uhr")
    storage_percent = st.session_state.storage_level / max_storage * 100
    st.write(
        f"**Pumpspeicher-Füllstand:** {st.session_state.storage_level:.1f} / {max_storage} MWh ({storage_percent:.0f}%)")
    st.progress(storage_percent / 100)

st.divider()
st.subheader("Gebote der Erzeuger")

# Linke Spalte: Geboteingabe | Rechte Spalte: Deckungsanzeige
col_bids, col_status = st.columns([3, 1])

bids = []
with col_bids:
    for p in PRODUCERS:
        maxcap = caps_default[p][st.session_state.hour_index] * factor
        cost = cost_default[p]

        col_a, col_b, col_c = st.columns([3, 2, 2])
        with col_a:
            st.write(f"**{p}** — Max: {maxcap if maxcap < 999999 else '∞'} MWh | Kosten: {cost} €/MWh")
        with col_b:
            price = st.number_input(
                f"Preis {p} / €/MWh",
                value=0.0,
                key=f"bids_price_{p}"
            )
        with col_c:
            qty = st.number_input(
                f"gebotene Energiemenge {p} / MWh",
                value=0.0,
                min_value=-float(maxcap) if p == "Pumpspeicher 1" else 0.0,
                max_value=float(abs(maxcap)),
                key=f"bids_qty_{p}"
            )

        if p == "Pumpspeicher 1":
            qty = limit_pumpspeicher(qty, st.session_state.storage_level, max_storage)

        bids.append({"Producer": p, "Price": price, "Qty": qty, "Cost": cost})

with col_status:
    st.markdown("**Deckung der Nachfrage**")
    demand_now = demand_default[hour]

    # Angebot (nur positive Mengen zählen als Erzeugung)
    supply_now = sum(max(0.0, b["Qty"]) for b in bids)

    # Pumpspeicher-Ladeleistung erhöht die Nachfrage
    pump_load = sum(-b["Qty"] for b in bids if b["Producer"] == "Pumpspeicher 1" and b["Qty"] < 0)

    # Immer berücksichtigen
    effective_demand = demand_now + pump_load

    target = max(effective_demand, 0.0)
    covered = min(supply_now, target)

    coverage = (covered / target) if target > 0 else 1.0
    coverage = float(max(0.0, min(coverage, 1.0)))

    st.metric("Effektive Nachfrage (akt. Stunde)", f"{effective_demand:.0f} MWh")
    st.metric("Angebot (positiv)", f"{supply_now:.0f} MWh")
    st.progress(coverage)

    if target == 0:
        st.info("Keine Nachfrage in dieser Stunde.")
    elif supply_now < target:
        st.warning(f"Noch offen: {(target - supply_now):.0f} MWh")
    else:
        st.success("Voll gedeckt")

# Nachfrage sicherstellen (Fallback auf Gas 1)
# Optional: nutze effective_demand statt demand_now, wenn du das Laden des Pumpspeichers abdecken willst
missing = demand_default[hour] - sum(max(0.0, b["Qty"]) for b in bids)
if missing > 0:
    for b in bids:
        if b["Producer"] == "Gas 1":
            b["Qty"] += missing
            break

# ---------------- Berechnung Merit Order ----------------

if st.button("Los! Merit Order berechnen"):
    bids_df = pd.DataFrame(bids).sort_values("Price").reset_index(drop=True)
    gen_df = bids_df[bids_df["Qty"] > 0].copy()
    cons_df = bids_df[bids_df["Qty"] < 0].copy()

    demand = demand_default[hour]
    pump_load = -cons_df["Qty"].sum() if not cons_df.empty else 0.0
    effective_demand = demand + pump_load

    gen_df["CumulQty"] = gen_df["Qty"].cumsum()
    if gen_df.empty:
        st.error("Keine Erzeugung vorhanden!")
    else:
        if gen_df["CumulQty"].iloc[-1] < effective_demand:
            clearing_price = gen_df["Price"].max()
            dispatched = gen_df["Qty"].copy()
        else:
            marginal_idx = gen_df[gen_df["CumulQty"] >= effective_demand].index[0]
            pos = gen_df.index.get_loc(marginal_idx)
            clearing_price = gen_df.loc[marginal_idx, "Price"]
            dispatched = gen_df["Qty"].copy()
            prev_cumul = gen_df["CumulQty"].iloc[pos - 1] if pos > 0 else 0.0
            needed = max(0.0, min(effective_demand - prev_cumul, dispatched.iloc[pos]))
            dispatched.iloc[pos] = needed
            dispatched.iloc[pos + 1:] = 0.0 if pos + 1 < len(dispatched) else dispatched.iloc[pos + 1:]

        gen_df["Dispatched"] = dispatched
        gen_df["Revenue"] = gen_df["Dispatched"] * clearing_price
        gen_df["Profit"] = gen_df["Dispatched"] * (clearing_price - gen_df["Cost"])

        if not cons_df.empty:
            cons_df["Revenue"] = cons_df["Qty"] * clearing_price
            cons_df["Profit"] = cons_df["Revenue"]

        # Gewinne aktualisieren
        for df in [gen_df, cons_df]:
            for _, r in df.iterrows():
                st.session_state.profits[r["Producer"]] += r.get("Profit", 0)

        # Pumpspeicher-Füllstand anpassen
        pump_action = sum(
            r["Qty"] for _, r in pd.concat([gen_df, cons_df]).iterrows() if r["Producer"] == "Pumpspeicher 1")
        st.session_state.storage_level = min(max(st.session_state.storage_level - pump_action, 0), max_storage)

        result = pd.concat([gen_df, cons_df], ignore_index=True).fillna(0)

        # ---------------- Plot Merit Order ----------------
        fig, ax = plt.subplots(figsize=(8, 5))
        cum = 0
        for _, r in gen_df.iterrows():
            x = [cum, cum + r["Qty"]]
            y = [r["Price"], r["Price"]]
            ax.step(x, y, where="post", color=colors[r["Producer"]],
                    linewidth=2, label=r["Producer"] if r["Producer"] not in [l.get_label() for l in ax.lines] else "")
            ax.fill_between(x, y, step="post", alpha=0.2, color=colors[r["Producer"]])
            cum += r["Qty"]

        ax.axvline(demand, color='red', linestyle='--', label='Nachfrage')
        if pump_load > 0:
            ax.axvline(effective_demand, color=petrol_color, linestyle='--',
                       label='Effektive Nachfrage (inkl. Pumpspeicher)')
        ax.axhline(clearing_price, color='green', linestyle=':', label=f'Clearingpreis {clearing_price:.2f} €/MWh')
        ax.set_xlabel('Erzeugte und nachgefragte Energie / MWh')
        ax.set_ylabel('Preis / €/MWh')
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        st.pyplot(fig)

        st.success(f"Clearingpreis: {clearing_price:.2f} €/MWh")
        st.dataframe(result.style.format(
            {"Price": "{:.2f}", "Qty": "{:.1f}", "Dispatched": "{:.1f}", "Revenue": "{:.2f}", "Profit": "{:.2f}"}))


st.divider()
st.subheader("Bisherige Gewinne / €")

profit_df = pd.DataFrame({
    "Erzeuger": list(st.session_state.profits.keys()),
    "Gewinn / €": list(st.session_state.profits.values())
})

# Für die Anzeige: keine Nachkommastellen und Punkt als Tausendertrennzeichen
display_df = profit_df.copy()
display_df["Gewinn / €"] = (
    display_df["Gewinn / €"]
    .round(0).astype(int)                       # keine Nachkommastellen
    .map(lambda v: f"{v:,}".replace(",", "."))  # 1.234.567
)

st.table(display_df)

if st.button("Neuer Tag starten"):
    st.session_state.profits = {p: 0.0 for p in PRODUCERS}
    st.session_state.storage_level = 250.0
    st.session_state.hour_index = 0
    st.info("Neuer Tag gestartet — Speicher und Gewinne zurückgesetzt.")
