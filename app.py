import uuid

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from calculations import calc_cumulative, calc_financing, calc_yearly, find_break_even
from data_store import load_data, save_data

st.set_page_config(
    page_title="KFZ Vergleichsrechner",
    page_icon="🚗",
    layout="wide",
)

PLOT_COLORS = ["#1D9E75", "#378ADD", "#7F77DD", "#D85A30", "#BA7517", "#0F6E56", "#185FA5", "#5DCAA5"]
COLOR_VERBRENNER = "#a09e95"

# ── Initialize session state ──────────────────────────────────────────────
if "data" not in st.session_state:
    st.session_state.data = load_data()

data = st.session_state.data

# ── Header ────────────────────────────────────────────────────────────────
st.title("🚗 KFZ Vergleichsrechner")
st.caption(
    "Wirtschaftlicher Vergleich zwischen einem bestehenden Verbrenner und neuen Fahrzeugen, "
    "inkl. verschiedener Finanzierungs- und Leasingoptionen."
)
st.divider()

# ── VERBRENNER SECTION ────────────────────────────────────────────────────
st.subheader("⛽ Aktuelles Fahrzeug (Verbrenner)")

v = data["verbrenner"]

with st.container(border=True):
    c1, c2 = st.columns([3, 1])
    with c1:
        v["name"] = st.text_input(
            "Modellbezeichnung",
            value=v.get("name", ""),
            placeholder="z.B. VW Golf 1.4 TSI LPG",
            key="v_name",
        )
    with c2:
        v["km"] = st.number_input(
            "Jährl. Fahrleistung (km/Jahr)",
            value=int(v.get("km", 12500)),
            min_value=1000,
            max_value=100000,
            step=500,
            key="v_km",
        )

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        v["lpg_mix"] = st.slider(
            "Kraftstoffmix (% LPG)",
            min_value=0,
            max_value=100,
            step=5,
            value=int(v.get("lpg_mix", 70)),
            key="v_lpg_mix",
            help="0% = nur Benzin, 100% = nur LPG",
        )
    with c2:
        v["ben_cons"] = st.number_input(
            "Benzinverbrauch (L/100km)",
            value=float(v.get("ben_cons", 5.0)),
            min_value=3.0,
            max_value=25.0,
            step=0.1,
            key="v_ben_cons",
        )
    with c3:
        v["lpg_cons"] = st.number_input(
            "LPG-Verbrauch (L/100km)",
            value=float(v.get("lpg_cons", 7.5)),
            min_value=4.0,
            max_value=30.0,
            step=0.1,
            key="v_lpg_cons",
        )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        v["ben_price"] = st.number_input(
            "Benzinpreis (€/L)",
            value=float(v.get("ben_price", 2.07)),
            min_value=1.0,
            max_value=4.0,
            step=0.01,
            key="v_ben_price",
        )
    with c2:
        v["lpg_price"] = st.number_input(
            "LPG-Preis (€/L)",
            value=float(v.get("lpg_price", 1.03)),
            min_value=0.50,
            max_value=2.50,
            step=0.01,
            key="v_lpg_price",
        )
    with c3:
        v["insurance"] = st.number_input(
            "Versicherung (€/Jahr)",
            value=int(v.get("insurance", 750)),
            min_value=0,
            step=10,
            key="v_insurance",
        )
    with c4:
        v["tax"] = st.number_input(
            "KFZ-Steuer (€/Jahr)",
            value=int(v.get("tax", 102)),
            min_value=0,
            step=5,
            key="v_tax",
        )
    with c5:
        v["repair_y1"] = st.number_input(
            "Rep./Wartung Jahr 1 (€)",
            value=int(v.get("repair_y1", 2500)),
            min_value=0,
            step=50,
            key="v_repair_y1",
            help="TÜV, Kupplung, Inspektion …",
        )
    with c6:
        v["repair_follow"] = st.number_input(
            "Rep./Wartung Folgejahre (€/J)",
            value=int(v.get("repair_follow", 800)),
            min_value=0,
            step=50,
            key="v_repair_follow",
        )

# ── VEHICLES SECTION ──────────────────────────────────────────────────────
st.divider()
st.subheader("🔌 Neue Fahrzeuge & Angebote")

# Collect mutations during rendering; apply after the loop to avoid list-mutation issues
_vehicle_to_delete = None
_option_to_delete = None   # (vid, oid)
_add_option_to = None      # vid
_add_vehicle = False

_VTYPE_OPTS = ["EV", "PHEV", "ICE"]
_VTYPE_LABELS = {"EV": "Elektro (BEV)", "PHEV": "Plug-in Hybrid (PHEV)", "ICE": "Verbrenner (ICE)"}
_FIN_OPTS = ["Finanzierung", "Händlerfinanzierung", "Leasing", "Barkauf"]
_TODAY = __import__("datetime").date.today().isoformat()

for veh_idx, vehicle in enumerate(data["vehicles"]):
    vid = vehicle["id"]
    vtype = vehicle.get("type", "EV")
    badge = {"EV": "🟢", "PHEV": "🟡", "ICE": "⚪"}.get(vtype, "🔵")
    label = vehicle.get("name") or f"Fahrzeug {veh_idx + 1}"

    with st.expander(f"{badge} {label}", expanded=True):
        # Delete vehicle
        _, del_col = st.columns([11, 1])
        with del_col:
            if st.button("🗑️", key=f"del_v_{vid}", help="Fahrzeug löschen"):
                _vehicle_to_delete = vid

        c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
        with c1:
            vehicle["name"] = st.text_input(
                "Bezeichnung / Ausstattungsvariante",
                value=vehicle.get("name", ""),
                placeholder="z.B. KIA EV3 81kWh Long Range",
                key=f"veh_name_{vid}",
            )
        with c2:
            vtype_idx = _VTYPE_OPTS.index(vtype) if vtype in _VTYPE_OPTS else 0
            vehicle["type"] = st.selectbox(
                "Fahrzeugtyp",
                options=_VTYPE_OPTS,
                format_func=lambda x: _VTYPE_LABELS.get(x, x),
                index=vtype_idx,
                key=f"veh_type_{vid}",
            )
        with c3:
            vehicle["uvp"] = st.number_input(
                "UVP (€)",
                value=float(vehicle.get("uvp", 0)),
                min_value=0.0,
                step=500.0,
                key=f"veh_uvp_{vid}",
                help="Unverbindliche Preisempfehlung des Herstellers",
            )
        with c4:
            vehicle["insurance"] = st.number_input(
                "Versicherung (€/J)",
                value=int(vehicle.get("insurance", 1100)),
                min_value=0,
                step=10,
                key=f"veh_ins_{vid}",
            )
        with c5:
            vehicle["tax"] = st.number_input(
                "KFZ-Steuer (€/J)",
                value=int(vehicle.get("tax", 0)),
                min_value=0,
                step=5,
                key=f"veh_tax_{vid}",
            )

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            vehicle["consumption"] = st.number_input(
                "Verbrauch (kWh/100km)",
                value=float(vehicle.get("consumption", 18.0)),
                min_value=5.0,
                max_value=50.0,
                step=0.5,
                key=f"veh_cons_{vid}",
            )
        with c2:
            vehicle["strom_price"] = st.number_input(
                "Strompreis (ct/kWh)",
                value=float(vehicle.get("strom_price", 28.06)),
                min_value=5.0,
                max_value=80.0,
                step=0.5,
                key=f"veh_strom_{vid}",
            )
        with c3:
            vehicle["charge_loss"] = st.number_input(
                "Ladeverlust (%)",
                value=int(vehicle.get("charge_loss", 15)),
                min_value=0,
                max_value=40,
                step=1,
                key=f"veh_loss_{vid}",
            )
        with c4:
            vehicle["service"] = st.number_input(
                "Service/Wartung (€/J)",
                value=int(vehicle.get("service", 300)),
                min_value=0,
                step=50,
                key=f"veh_service_{vid}",
            )
        with c5:
            vehicle["foerder"] = st.number_input(
                "Staatl. Förderung (€)",
                value=int(vehicle.get("foerder", 0)),
                min_value=0,
                step=500,
                key=f"veh_foerder_{vid}",
                help="Wird vom Kaufpreis abgezogen",
            )

        # ── Financing options ──
        st.markdown("**Finanzierungs- / Leasingoptionen**")

        for opt in vehicle.get("financing_options", []):
            oid = opt["id"]
            with st.container(border=True):
                # ── Row 1: General information ──────────────────────────────
                c1, c2, c3, c4, del_col = st.columns([3, 1.5, 2, 1.5, 1])
                with c1:
                    opt["label"] = st.text_input(
                        "Bezeichnung",
                        value=opt.get("label", ""),
                        placeholder="Finanzierungsoption 1",
                        key=f"opt_label_{vid}_{oid}",
                    )
                with c2:
                    type_idx = _FIN_OPTS.index(opt.get("type", "Finanzierung")) if opt.get("type") in _FIN_OPTS else 0
                    opt["type"] = st.selectbox(
                        "Typ",
                        options=_FIN_OPTS,
                        index=type_idx,
                        key=f"opt_type_{vid}_{oid}",
                    )
                with c3:
                    opt["source"] = st.text_input(
                        "Quelle",
                        value=opt.get("source", ""),
                        placeholder="Online, Autohaus …",
                        key=f"opt_source_{vid}_{oid}",
                    )
                with c4:
                    if not opt.get("date_of_entry"):
                        opt["date_of_entry"] = _TODAY
                    st.text_input(
                        "Erfassungsdatum",
                        value=opt["date_of_entry"],
                        disabled=True,
                        key=f"opt_date_{vid}_{oid}",
                    )
                with del_col:
                    st.write("")
                    if st.button("🗑️", key=f"del_opt_{vid}_{oid}", help="Option löschen"):
                        _option_to_delete = (vid, oid)

                # ── Row 2: Financial information ────────────────────────────
                fin_type = opt["type"]
                is_leasing = fin_type == "Leasing"
                is_barkauf = fin_type == "Barkauf"

                if is_barkauf:
                    c1, c2 = st.columns([1, 3])
                    with c1:
                        opt["price"] = st.number_input(
                            "Kaufpreis (€)",
                            value=float(opt.get("price", 0.0)),
                            min_value=0.0,
                            step=500.0,
                            key=f"opt_price_{vid}_{oid}",
                        )
                    with c2:
                        st.info(
                            "Kein Kredit – Kaufpreis wird im ersten Jahr vollständig angesetzt.",
                            icon="ℹ️",
                        )
                else:
                    c1, c2, c3, c4, c5 = st.columns(5)
                    with c1:
                        opt["price"] = st.number_input(
                            "Kaufpreis (€)" + (" *(optional)*" if is_leasing else ""),
                            value=float(opt.get("price", 0.0)),
                            min_value=0.0,
                            step=500.0,
                            key=f"opt_price_{vid}_{oid}",
                            help="Optional bei Leasing" if is_leasing else None,
                        )
                    with c2:
                        opt["anzahlung"] = st.number_input(
                            "Anzahlung (€)",
                            value=float(opt.get("anzahlung", 0.0)),
                            min_value=0.0,
                            step=500.0,
                            key=f"opt_anzahlung_{vid}_{oid}",
                        )
                    with c3:
                        opt["laufzeit"] = int(st.number_input(
                            "Laufzeit (Monate)",
                            value=int(opt.get("laufzeit", 48)),
                            min_value=1,
                            max_value=120,
                            step=6,
                            key=f"opt_laufzeit_{vid}_{oid}",
                        ))
                    with c4:
                        opt["effektiver_jahreszins"] = st.number_input(
                            "Eff. Jahreszins (%)",
                            value=float(opt.get("effektiver_jahreszins", 0.0)),
                            min_value=0.0,
                            max_value=30.0,
                            step=0.01,
                            format="%.2f",
                            key=f"opt_zins_{vid}_{oid}",
                        )
                    with c5:
                        opt["monatliche_rate"] = st.number_input(
                            "Monatliche Rate (€)",
                            value=float(opt.get("monatliche_rate", 0.0)),
                            min_value=0.0,
                            step=10.0,
                            key=f"opt_rate_{vid}_{oid}",
                        )

                    # ── Row 3: Schlussrate, Gesamtbetrag ────────────────────
                    c1, c2, c3 = st.columns([1, 1, 2])
                    with c1:
                        opt["schlussrate"] = st.number_input(
                            "Schlussrate (€)",
                            value=float(opt.get("schlussrate", 0.0)),
                            min_value=0.0,
                            step=500.0,
                            key=f"opt_schluss_{vid}_{oid}",
                            help="Restschuld / Ballonrate am Ende der Laufzeit (0 = keine)",
                        )
                    with c2:
                        opt["gesamtbetrag"] = st.number_input(
                            "Gesamtbetrag (€)",
                            value=float(opt.get("gesamtbetrag", 0.0)),
                            min_value=0.0,
                            step=100.0,
                            key=f"opt_gesamt_{vid}_{oid}",
                            help="Laut Vertrag – falls abweichend vom berechneten Wert",
                        )
                    with c3:
                        _laufzeit = int(opt.get("laufzeit", 48))
                        _anz = float(opt.get("anzahlung", 0.0))
                        _rate = float(opt.get("monatliche_rate", 0.0))
                        _schluss = float(opt.get("schlussrate", 0.0))
                        _calc_total = _anz + _rate * _laufzeit + _schluss
                        _stated = float(opt.get("gesamtbetrag", 0.0))
                        _delta = f"{_calc_total - _stated:+,.0f} €".replace(",", ".") if _stated > 0 else None
                        st.metric(
                            "Berechneter Gesamtbetrag",
                            f"{_calc_total:,.0f} €".replace(",", "."),
                            delta=_delta,
                            delta_color="off",
                            help="Anzahlung + Monatsraten × Laufzeit + Schlussrate",
                        )

                # ── Row 4: Anmerkungen ───────────────────────────────────────
                opt["anmerkungen"] = st.text_area(
                    "Anmerkungen",
                    value=opt.get("anmerkungen", ""),
                    placeholder="Zusätzliche Informationen oder Kommentare …",
                    height=68,
                    key=f"opt_notes_{vid}_{oid}",
                )

        if st.button(f"➕ Option hinzufügen", key=f"add_opt_{vid}"):
            _add_option_to = vid

st.divider()
if st.button("➕ Fahrzeug hinzufügen", type="secondary"):
    _add_vehicle = True

# ── Apply mutations ───────────────────────────────────────────────────────
_mutated = False

if _vehicle_to_delete:
    data["vehicles"] = [veh for veh in data["vehicles"] if veh["id"] != _vehicle_to_delete]
    _mutated = True

if _option_to_delete:
    del_vid, del_oid = _option_to_delete
    for veh in data["vehicles"]:
        if veh["id"] == del_vid:
            veh["financing_options"] = [o for o in veh["financing_options"] if o["id"] != del_oid]
    _mutated = True

if _add_option_to:
    for veh in data["vehicles"]:
        if veh["id"] == _add_option_to:
            veh["financing_options"].append({
                "id": str(uuid.uuid4())[:8],
                "label": "",
                "type": "Finanzierung",
                "source": "",
                "date_of_entry": _TODAY,
                "anmerkungen": "",
                "price": 0.0,
                "anzahlung": 0.0,
                "laufzeit": 48,
                "effektiver_jahreszins": 0.0,
                "monatliche_rate": 0.0,
                "schlussrate": 0.0,
                "gesamtbetrag": 0.0,
            })
    _mutated = True

if _add_vehicle:
    data["vehicles"].append({
        "id": str(uuid.uuid4())[:8],
        "name": "",
        "type": "EV",
        "uvp": 0.0,
        "insurance": 1100,
        "tax": 0,
        "consumption": 18.0,
        "strom_price": 28.06,
        "charge_loss": 15,
        "service": 300,
        "foerder": 0,
        "financing_options": [],
    })
    _mutated = True

# Persist current state after every render (captures form field edits too)
save_data(data)

if _mutated:
    st.rerun()

# ── COMPARISON / RESULTS SECTION ──────────────────────────────────────────
st.divider()
st.subheader("📊 Vergleich")

c_radio, c_btn = st.columns([3, 1])
with c_radio:
    _horizon_default = data.get("horizon", 5)
    horizon = st.radio(
        "Betrachtungszeitraum",
        options=[2, 5, 10],
        format_func=lambda x: f"{x} Jahre",
        index=[2, 5, 10].index(_horizon_default) if _horizon_default in [2, 5, 10] else 1,
        horizontal=True,
        key="horizon_radio",
    )
with c_btn:
    st.write("")
    st.button("🔄 Vergleich aktualisieren", type="primary", width="stretch")

data["horizon"] = horizon

# ── Build comparison series ───────────────────────────────────────────────
km = data["verbrenner"].get("km", 12500)
v_data = data["verbrenner"]

series = []
v_yearly = [calc_yearly(v_data, y, km, mode="verbrenner") for y in range(1, 11)]
series.append({
    "label": v_data.get("name", "Verbrenner") or "Verbrenner (Behalten)",
    "is_verbrenner": True,
    "cum10": calc_cumulative(v_yearly),
    "yearly10": v_yearly,
    "fin_summary": None,
    "source": "",
})

for vehicle in data.get("vehicles", []):
    for opt in vehicle.get("financing_options", []):
        fin = calc_financing(opt, vehicle.get("foerder", 0))
        ev_opex = [calc_yearly(vehicle, y, km, mode="ev") for y in range(1, 11)]
        total_yearly = [ev_opex[y - 1] + fin["year_cost"](y) for y in range(1, 11)]
        vname = vehicle.get("name", "") or "Fahrzeug"
        oname = opt.get("label", "") or opt.get("type", "")
        series.append({
            "label": f"{vname} · {oname}",
            "is_verbrenner": False,
            "cum10": calc_cumulative(total_yearly),
            "yearly10": total_yearly,
            "fin_summary": fin["summary"],
            "source": opt.get("source", ""),
        })

if len(series) < 2:
    st.info(
        "Füge mindestens ein Fahrzeug mit einer Finanzierungsoption hinzu, "
        "um den Vergleich zu sehen.",
        icon="ℹ️",
    )
else:
    # Assign colors
    ci, colors = 0, []
    for s in series:
        if s["is_verbrenner"]:
            colors.append(COLOR_VERBRENNER)
        else:
            colors.append(PLOT_COLORS[ci % len(PLOT_COLORS)])
            ci += 1

    # ── Summary metric cards ──
    v_total = sum(series[0]["yearly10"][:horizon])
    st.markdown(f"**Ergebnis – {horizon}-Jahres-Betrachtung**")
    cols = st.columns(len(series))
    for i, (s, col) in enumerate(zip(series, cols)):
        total = sum(s["yearly10"][:horizon])
        diff = total - v_total
        is_v = s["is_verbrenner"]
        with col:
            st.markdown(
                f'<div style="height:4px;background:{colors[i]};'
                f'border-radius:4px 4px 0 0;margin-bottom:4px"></div>',
                unsafe_allow_html=True,
            )
            with st.container(border=True):
                st.caption(s["label"])
                st.metric(
                    label="Gesamtkosten",
                    value=f"{total:,.0f} €".replace(",", "."),
                    delta=None if is_v else f"{diff:+,.0f} €".replace(",", "."),
                    delta_color="off" if is_v else "inverse",
                )
                if s.get("fin_summary"):
                    st.caption(s["fin_summary"])
                if s.get("source"):
                    st.caption(f"Quelle: {s['source']}")

    # ── Break-Even table ──
    st.markdown("**Break-Even gegenüber Verbrenner**")
    v_cum = series[0]["cum10"]
    be_rows = []
    for i, s in enumerate(series[1:], start=1):
        be = find_break_even(v_cum, s["cum10"])
        be_rows.append({
            "Fahrzeug / Option": s["label"],
            "Break-Even": f"Jahr {be}" if be else "> 10 Jahre",
        })
    if be_rows:
        st.dataframe(pd.DataFrame(be_rows), width="stretch", hide_index=True)
    else:
        st.caption("Keine Vergleichsfahrzeuge.")

    # ── Financing details comparison table ──
    _fin_detail_rows = []
    for vehicle in data.get("vehicles", []):
        for opt in vehicle.get("financing_options", []):
            vname = vehicle.get("name", "") or "Fahrzeug"
            _laufzeit = int(opt.get("laufzeit", 48))
            _anz = float(opt.get("anzahlung", 0.0))
            _rate = float(opt.get("monatliche_rate", 0.0))
            _schluss = float(opt.get("schlussrate", 0.0))
            _gesamt_entered = float(opt.get("gesamtbetrag", 0.0))
            _gesamt_calc = _anz + _rate * _laufzeit + _schluss
            _gesamt_display = _gesamt_entered if _gesamt_entered > 0 else _gesamt_calc
            _price = float(opt.get("price", 0.0))
            _fin_detail_rows.append({
                "Fahrzeug": vname,
                "Option": opt.get("label", "") or opt.get("type", ""),
                "Typ": opt.get("type", ""),
                "Quelle": opt.get("source", ""),
                "Datum": opt.get("date_of_entry", ""),
                "Kaufpreis": f"{_price:,.0f} €".replace(",", ".") if _price > 0 else "–",
                "Anzahlung": f"{_anz:,.0f} €".replace(",", "."),
                "Laufzeit": f"{_laufzeit} Monate",
                "Eff. Jahreszins": f"{float(opt.get('effektiver_jahreszins', 0.0)):.2f} %",
                "Monatl. Rate": f"{_rate:,.0f} €".replace(",", "."),
                "Schlussrate": f"{_schluss:,.0f} €".replace(",", ".") if _schluss > 0 else "–",
                "Gesamtbetrag": f"{_gesamt_display:,.0f} €".replace(",", "."),
                "Anmerkungen": opt.get("anmerkungen", ""),
            })
    if _fin_detail_rows:
        st.markdown("**Finanzierungsoptionen im Detail**")
        st.dataframe(
            pd.DataFrame(_fin_detail_rows),
            hide_index=True,
            use_container_width=True,
        )

    # ── Cumulative cost chart ──
    years = list(range(1, 11))
    fig_cum = go.Figure()
    for i, s in enumerate(series):
        fig_cum.add_trace(go.Scatter(
            x=years,
            y=s["cum10"],
            name=s["label"],
            line=dict(color=colors[i], width=2.5, dash="dot" if s["is_verbrenner"] else "solid"),
            mode="lines+markers",
            marker=dict(size=5),
            hovertemplate="%{y:,.0f} €<extra>" + s["label"] + "</extra>",
        ))
    fig_cum.update_layout(
        xaxis=dict(title="Jahr", tickvals=years, ticktext=[f"J.{y}" for y in years], gridcolor="#444"),
        yaxis=dict(title="Kumulierte Kosten (€)", tickformat=",.0f", gridcolor="#444"),
        legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="left", x=0, font=dict(size=11)),
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=30, b=10, l=60, r=20),
        height=400,
        title=dict(text="Kumulative Gesamtkosten über 10 Jahre", font=dict(size=14)),
    )
    st.plotly_chart(fig_cum, width="stretch")

    # ── Annual cost bar chart ──
    bar_labels = [f"J.{y}" for y in range(1, horizon + 1)]
    fig_bar = go.Figure()
    for i, s in enumerate(series):
        fig_bar.add_trace(go.Bar(
            name=s["label"],
            x=bar_labels,
            y=[round(s["yearly10"][y - 1]) for y in range(1, horizon + 1)],
            marker_color=colors[i],
            hovertemplate="%{y:,.0f} €/Jahr<extra>" + s["label"] + "</extra>",
        ))
    fig_bar.update_layout(
        barmode="group",
        xaxis=dict(gridcolor="#444"),
        yaxis=dict(title="€/Jahr", tickformat=",.0f", gridcolor="#444"),
        legend=dict(orientation="h", yanchor="top", y=-0.28, xanchor="left", x=0, font=dict(size=11)),
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=30, b=10, l=60, r=20),
        height=350,
        title=dict(text=f"Jährliche Kosten – {horizon} Jahre", font=dict(size=14)),
    )
    st.plotly_chart(fig_bar, width="stretch")
