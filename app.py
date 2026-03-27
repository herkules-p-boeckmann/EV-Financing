import dash
from dash import dcc, html, Input, Output, State, ALL, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import json, uuid

from data_store import load_data, save_data
from calculations import calc_yearly, calc_financing, calc_cumulative, find_break_even

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY, dbc.icons.BOOTSTRAP],
    title="KFZ Vergleichsrechner",
    suppress_callback_exceptions=True,
)

PLOT_COLORS = ["#1D9E75","#378ADD","#7F77DD","#D85A30","#BA7517","#0F6E56","#185FA5","#5DCAA5"]
COLOR_VERBRENNER = "#a09e95"


# ════════════════════════════════════════════════════════════════════════════
#  UI HELPERS
# ════════════════════════════════════════════════════════════════════════════

def labeled(label, component, extra=None):
    children = [html.Label(label, className="form-label small text-muted mb-1")]
    children.append(component)
    if extra:
        children.append(html.Small(extra, className="text-muted"))
    return html.Div(children, className="mb-2")


def make_option_fields(vid, oid, opt):
    fin_type = opt.get("type", "Finanzierung")

    # Always render ALL field IDs (hidden when not relevant) to avoid pattern-matching errors
    fin_fields = html.Div([
        dbc.Row([
            dbc.Col(labeled("Kaufpreis (€)", dbc.Input(id={"type":"opt-price","vid":vid,"oid":oid}, type="number", value=opt.get("price",40000), min=0, step=500, size="sm")), md=2),
            dbc.Col(labeled("Anzahlung (%)", dbc.Input(id={"type":"opt-down-pct","vid":vid,"oid":oid}, type="number", value=opt.get("down_pct",50), min=0, max=100, step=5, size="sm")), md=2),
            dbc.Col(labeled("Laufzeit (Jahre)", dbc.Input(id={"type":"opt-years","vid":vid,"oid":oid}, type="number", value=opt.get("years",5), min=1, max=10, step=1, size="sm")), md=2),
            dbc.Col(labeled("Zinssatz (%/Jahr)", dbc.Input(id={"type":"opt-rate","vid":vid,"oid":oid}, type="number", value=opt.get("rate",5.5), min=0, max=20, step=0.25, size="sm")), md=2),
        ])
    ], style={"display": "block" if fin_type == "Finanzierung" else "none"})

    barkauf_fields = html.Div([
        dbc.Row([
            dbc.Col(labeled("Kaufpreis (€)", dbc.Input(id={"type":"opt-price-bk","vid":vid,"oid":oid}, type="number", value=opt.get("price",40000), min=0, step=500, size="sm")), md=3),
            dbc.Col(html.P("Kein Kredit – Kaufpreis wird im ersten Jahr vollständig angesetzt.", className="small text-muted mt-4"), md=9),
        ])
    ], style={"display": "block" if fin_type == "Barkauf" else "none"})

    lease_fields = html.Div([
        dbc.Row([
            dbc.Col(labeled("Listenpreis (€)", dbc.Input(id={"type":"opt-price-ls","vid":vid,"oid":oid}, type="number", value=opt.get("price",40000), min=0, step=500, size="sm")), md=2),
            dbc.Col(labeled("Rate (€/Monat)", dbc.Input(id={"type":"opt-lease-rate","vid":vid,"oid":oid}, type="number", value=opt.get("lease_rate",399), min=0, step=10, size="sm")), md=2),
            dbc.Col(labeled("Laufzeit (Monate)", dbc.Input(id={"type":"opt-lease-months","vid":vid,"oid":oid}, type="number", value=opt.get("lease_months",48), min=12, max=96, step=6, size="sm")), md=2),
            dbc.Col(labeled("Sonderzahlung (€)", dbc.Input(id={"type":"opt-lease-down","vid":vid,"oid":oid}, type="number", value=opt.get("lease_down",0), min=0, step=500, size="sm")), md=2),
            dbc.Col(labeled("km-Limit/Jahr", dbc.Input(id={"type":"opt-lease-km","vid":vid,"oid":oid}, type="number", value=opt.get("lease_km",15000), min=5000, max=60000, step=1000, size="sm")), md=2),
        ])
    ], style={"display": "block" if fin_type == "Leasing" else "none"})

    return html.Div([fin_fields, barkauf_fields, lease_fields])


def make_option_row(vid, opt, idx):
    oid = opt["id"]
    src = opt.get("source", "")
    return dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col(dbc.Input(id={"type":"opt-label","vid":vid,"oid":oid}, value=opt.get("label",""),
                                  placeholder="Bezeichnung (z.B. Händlerangebot A)", size="sm"), md=3),
                dbc.Col(dbc.Select(id={"type":"opt-type","vid":vid,"oid":oid},
                                   options=[{"label":"Finanzierung","value":"Finanzierung"},
                                            {"label":"Leasing","value":"Leasing"},
                                            {"label":"Barkauf","value":"Barkauf"}],
                                   value=opt.get("type","Finanzierung"), size="sm"), md=2),
                dbc.Col(dbc.Input(id={"type":"opt-source","vid":vid,"oid":oid}, value=src,
                                  placeholder="Quelle / Autohaus / Portal", size="sm"), md=4),
                dbc.Col(dbc.Button(html.I(className="bi bi-trash3"),
                                   id={"type":"delete-option","vid":vid,"oid":oid},
                                   color="light", size="sm", className="text-danger border-0"), md=1),
            ], align="center", className="mb-2"),
            html.Div(id={"type":"opt-fields-container","vid":vid,"oid":oid},
                     children=make_option_fields(vid, oid, opt)),
        ], className="py-2 px-3"),
        className="mb-2 border-start border-success border-2",
        style={"background":"#2b2b2b"}
    )


def make_vehicle_card(vehicle, index):
    vid = vehicle["id"]
    options = vehicle.get("financing_options", [])
    vtype = vehicle.get("type", "EV")
    badge_color = {"EV":"success","PHEV":"warning","ICE":"secondary"}.get(vtype, "secondary")

    return dbc.Card([
        dbc.CardHeader(dbc.Row([
            dbc.Col([
                html.I(className="bi bi-ev-station me-2 text-success"),
                html.Strong(vehicle.get("name", f"Fahrzeug {index+1}") or f"Fahrzeug {index+1}"),
                dbc.Badge(vtype, color=badge_color, className="ms-2"),
            ]),
            dbc.Col(
                dbc.Button(html.I(className="bi bi-trash3"),
                           id={"type":"delete-vehicle","index":vid},
                           color="light", size="sm", className="float-end text-danger border-0"),
                width="auto"
            ),
        ], align="center")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(labeled("Bezeichnung / Ausstattungsvariante",
                                dbc.Input(id={"type":"veh-name","index":vid}, value=vehicle.get("name",""),
                                          placeholder="z.B. KIA EV3 81kWh Long Range", size="sm")), md=5),
                dbc.Col(labeled("Fahrzeugtyp",
                                dbc.Select(id={"type":"veh-type","index":vid},
                                           options=[{"label":"Elektro (BEV)","value":"EV"},
                                                    {"label":"Plug-in Hybrid (PHEV)","value":"PHEV"},
                                                    {"label":"Verbrenner (ICE)","value":"ICE"}],
                                           value=vtype, size="sm")), md=3),
                dbc.Col(labeled("Versicherung (€/Jahr)",
                                dbc.Input(id={"type":"veh-insurance","index":vid}, type="number",
                                          value=vehicle.get("insurance",1100), min=0, step=10, size="sm")), md=2),
                dbc.Col(labeled("KFZ-Steuer (€/Jahr)",
                                dbc.Input(id={"type":"veh-tax","index":vid}, type="number",
                                          value=vehicle.get("tax",0), min=0, step=5, size="sm")), md=2),
            ]),
            dbc.Row([
                dbc.Col(labeled("Verbrauch (kWh/100km)",
                                dbc.Input(id={"type":"veh-cons","index":vid}, type="number",
                                          value=vehicle.get("consumption",18.0), min=5, max=50, step=0.5, size="sm")), md=2),
                dbc.Col(labeled("Strompreis (ct/kWh)",
                                dbc.Input(id={"type":"veh-strom","index":vid}, type="number",
                                          value=vehicle.get("strom_price",28.06), min=5, max=80, step=0.5, size="sm")), md=2),
                dbc.Col(labeled("Ladeverlust (%)",
                                dbc.Input(id={"type":"veh-loss","index":vid}, type="number",
                                          value=vehicle.get("charge_loss",15), min=0, max=40, step=1, size="sm")), md=2),
                dbc.Col(labeled("Service/Wartung (€/Jahr)",
                                dbc.Input(id={"type":"veh-service","index":vid}, type="number",
                                          value=vehicle.get("service",300), min=0, step=50, size="sm")), md=2),
                dbc.Col(labeled("Staatl. Förderung (€)",
                                dbc.Input(id={"type":"veh-foerder","index":vid}, type="number",
                                          value=vehicle.get("foerder",0), min=0, step=500, size="sm"),
                                extra="wird vom Kaufpreis abgezogen"), md=2),
            ]),
            html.Hr(className="my-2"),
            dbc.Row([
                dbc.Col(html.P("Finanzierungs- / Leasingoptionen", className="small fw-bold mb-0")),
                dbc.Col(
                    dbc.Button([html.I(className="bi bi-plus-circle me-1"), "Option hinzufügen"],
                               id={"type":"add-option","index":vid}, color="light", size="sm", className="float-end border"),
                    width="auto"
                ),
            ], align="center", className="mb-2"),
            html.Div(
                [make_option_row(vid, opt, i) for i, opt in enumerate(options)],
                id={"type":"options-container","index":vid}
            ),
        ])
    ], className="mb-4 shadow-sm")


def make_verbrenner_card(data):
    v = data.get("verbrenner", {})
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-fuel-pump me-2 text-secondary"),
            html.Strong("Aktueller Verbrenner"),
            dbc.Badge("Behalten", color="secondary", className="ms-2")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(labeled("Modellbezeichnung",
                                dbc.Input(id="v-name", value=v.get("name",""), placeholder="z.B. VW Golf 1.4 TSI LPG", size="sm")), md=6),
                dbc.Col(labeled("Jährl. Fahrleistung (km/Jahr)",
                                dbc.Input(id="v-km", type="number", value=v.get("km",12500), min=1000, max=100000, step=500, size="sm")), md=3),
            ]),
            dbc.Row([
                dbc.Col([
                    html.Label("Kraftstoffmix (% LPG)", className="form-label small text-muted"),
                    dcc.Slider(id="v-lpg-mix", min=0, max=100, step=5, value=v.get("lpg_mix",70),
                               marks={0:"0% (nur Benzin)", 50:"50/50", 100:"100% LPG"},
                               tooltip={"placement":"bottom","always_visible":True}),
                ], md=6),
                dbc.Col(labeled("Benzinverbrauch (L/100km)",
                                dbc.Input(id="v-ben-cons", type="number", value=v.get("ben_cons",5.0), min=3, max=25, step=0.1, size="sm")), md=3),
                dbc.Col(labeled("LPG-Verbrauch (L/100km)",
                                dbc.Input(id="v-lpg-cons", type="number", value=v.get("lpg_cons",7.5), min=4, max=30, step=0.1, size="sm")), md=3),
            ], className="mb-2"),
            dbc.Row([
                dbc.Col(labeled("Benzinpreis (€/L)", dbc.Input(id="v-ben-price", type="number", value=v.get("ben_price",2.07), min=1.0, max=4.0, step=0.01, size="sm")), md=2),
                dbc.Col(labeled("LPG-Preis (€/L)", dbc.Input(id="v-lpg-price", type="number", value=v.get("lpg_price",1.03), min=0.50, max=2.50, step=0.01, size="sm")), md=2),
                dbc.Col(labeled("Versicherung (€/Jahr)", dbc.Input(id="v-insurance", type="number", value=v.get("insurance",750), min=0, step=10, size="sm")), md=2),
                dbc.Col(labeled("KFZ-Steuer (€/Jahr)", dbc.Input(id="v-tax", type="number", value=v.get("tax",102), min=0, step=5, size="sm")), md=2),
                dbc.Col(labeled("Rep./Wartung Jahr 1 (€)", dbc.Input(id="v-repair-y1", type="number", value=v.get("repair_y1",2500), min=0, step=50, size="sm"),
                                extra="TÜV, Kupplung, Inspektion …"), md=2),
                dbc.Col(labeled("Rep./Wartung Folgejahre (€/J)", dbc.Input(id="v-repair-follow", type="number", value=v.get("repair_follow",800), min=0, step=50, size="sm")), md=2),
            ]),
        ])
    ], className="mb-4 shadow-sm")


# ════════════════════════════════════════════════════════════════════════════
#  LAYOUT
# ════════════════════════════════════════════════════════════════════════════

def build_layout(data):
    vehicles = data.get("vehicles", [])
    horizon = data.get("horizon", 5)
    return html.Div([
        dbc.Navbar(dbc.Container([
            html.Span([html.I(className="bi bi-car-front me-2"), "KFZ Vergleichsrechner"],
                      className="navbar-brand fw-bold fs-5"),
        ], fluid=True), color="dark", dark=True, className="border-bottom mb-4 shadow-sm", sticky="top"),

        dbc.Container([
            html.H6("Aktuelles Fahrzeug", className="text-uppercase text-muted mb-3 mt-2"),
            make_verbrenner_card(data),

            html.H6("Neue Fahrzeuge & Angebote", className="text-uppercase text-muted mb-3"),
            html.Div(id="vehicles-container",
                     children=[make_vehicle_card(v, i) for i, v in enumerate(vehicles)]),
            dbc.Button([html.I(className="bi bi-plus-circle me-2"), "Fahrzeug hinzufügen"],
                       id="add-vehicle-btn", color="success", outline=True, size="sm", className="mb-4"),

            html.Hr(),
            dbc.Row([
                dbc.Col([
                    html.H6("Vergleich", className="text-uppercase text-muted mb-2"),
                    dbc.RadioItems(id="horizon-radio",
                                  options=[{"label":"2 Jahre","value":2},
                                           {"label":"5 Jahre","value":5},
                                           {"label":"10 Jahre","value":10}],
                                  value=horizon, inline=True),
                ], md=8),
                dbc.Col(
                    dbc.Button([html.I(className="bi bi-arrow-clockwise me-2"), "Vergleich aktualisieren"],
                               id="calc-btn", color="primary", className="float-end mt-1"),
                    md=4, className="d-flex align-items-center justify-content-end"
                ),
            ], className="mb-4"),

            html.Div(id="results-area"),
        ], fluid=False, className="pb-5"),
    ])


app.layout = html.Div([
    dcc.Store(id="store", storage_type="session"),
    html.Div(id="page-content", children=build_layout(load_data()))
])


# ════════════════════════════════════════════════════════════════════════════
#  CALLBACKS
# ════════════════════════════════════════════════════════════════════════════

@app.callback(
    Output("vehicles-container", "children"),
    Output("store", "data"),
    Input("add-vehicle-btn", "n_clicks"),
    Input({"type":"delete-vehicle","index":ALL}, "n_clicks"),
    State("store", "data"),
    prevent_initial_call=True
)
def manage_vehicles(add_clicks, del_clicks, _store):
    data = load_data()
    triggered = ctx.triggered_id
    if triggered == "add-vehicle-btn":
        new_id = str(uuid.uuid4())[:8]
        data["vehicles"].append({
            "id": new_id, "name": "", "type": "EV",
            "insurance": 1100, "tax": 0, "consumption": 18.0,
            "strom_price": 28.06, "charge_loss": 15, "service": 300,
            "foerder": 0, "financing_options": []
        })
    elif isinstance(triggered, dict) and triggered.get("type") == "delete-vehicle":
        vid = triggered["index"]
        data["vehicles"] = [v for v in data["vehicles"] if v["id"] != vid]
    save_data(data)
    return [make_vehicle_card(v, i) for i, v in enumerate(data["vehicles"])], {}


@app.callback(
    Output({"type":"options-container","index":ALL}, "children"),
    Input({"type":"add-option","index":ALL}, "n_clicks"),
    Input({"type":"delete-option","vid":ALL,"oid":ALL}, "n_clicks"),
    State({"type":"options-container","index":ALL}, "id"),
    prevent_initial_call=True
)
def manage_options(add_clicks, del_clicks, container_ids):
    data = load_data()
    triggered = ctx.triggered_id
    if isinstance(triggered, dict) and triggered.get("type") == "add-option":
        vid = triggered["index"]
        for v in data["vehicles"]:
            if v["id"] == vid:
                v["financing_options"].append({
                    "id": str(uuid.uuid4())[:8],
                    "label": "", "type": "Finanzierung", "source": "",
                    "price": 40000, "down_pct": 50, "years": 5, "rate": 5.5,
                    "lease_rate": 399, "lease_months": 48, "lease_down": 0,
                    "lease_residual": 0, "lease_km": 15000,
                })
    elif isinstance(triggered, dict) and triggered.get("type") == "delete-option":
        vid, oid = triggered["vid"], triggered["oid"]
        for v in data["vehicles"]:
            if v["id"] == vid:
                v["financing_options"] = [o for o in v["financing_options"] if o["id"] != oid]
    save_data(data)
    result = []
    for cid in container_ids:
        vid = cid["index"]
        vehicle = next((v for v in data["vehicles"] if v["id"] == vid), None)
        opts = vehicle.get("financing_options", []) if vehicle else []
        result.append([make_option_row(vid, o, i) for i, o in enumerate(opts)])
    return result


@app.callback(
    Output("store", "data", allow_duplicate=True),
    Input("v-name","value"), Input("v-km","value"), Input("v-lpg-mix","value"),
    Input("v-ben-cons","value"), Input("v-lpg-cons","value"),
    Input("v-ben-price","value"), Input("v-lpg-price","value"),
    Input("v-insurance","value"), Input("v-tax","value"),
    Input("v-repair-y1","value"), Input("v-repair-follow","value"),
    prevent_initial_call=True
)
def save_verbrenner(name, km, lpg_mix, ben_cons, lpg_cons, ben_price, lpg_price,
                    insurance, tax, repair_y1, repair_follow):
    data = load_data()
    data["verbrenner"] = {
        "name": name or "", "km": km or 12500,
        "lpg_mix": lpg_mix or 70, "ben_cons": ben_cons or 5.0, "lpg_cons": lpg_cons or 7.5,
        "ben_price": ben_price or 2.07, "lpg_price": lpg_price or 1.03,
        "insurance": insurance or 750, "tax": tax or 102,
        "repair_y1": repair_y1 or 2500, "repair_follow": repair_follow or 800,
    }
    save_data(data)
    return {}


@app.callback(
    Output("store", "data", allow_duplicate=True),
    Input({"type":"veh-name","index":ALL}, "value"),
    Input({"type":"veh-type","index":ALL}, "value"),
    Input({"type":"veh-insurance","index":ALL}, "value"),
    Input({"type":"veh-tax","index":ALL}, "value"),
    Input({"type":"veh-cons","index":ALL}, "value"),
    Input({"type":"veh-strom","index":ALL}, "value"),
    Input({"type":"veh-loss","index":ALL}, "value"),
    Input({"type":"veh-service","index":ALL}, "value"),
    Input({"type":"veh-foerder","index":ALL}, "value"),
    State({"type":"veh-name","index":ALL}, "id"),
    prevent_initial_call=True
)
def save_vehicles(names, types, insurances, taxes, conss, stroms, losses, services, foeders, ids):
    data = load_data()
    for i, id_dict in enumerate(ids):
        vid = id_dict["index"]
        for v in data["vehicles"]:
            if v["id"] == vid:
                v.update({
                    "name": names[i] or "", "type": types[i] or "EV",
                    "insurance": insurances[i] or 1100, "tax": taxes[i] or 0,
                    "consumption": conss[i] or 18.0, "strom_price": stroms[i] or 28.06,
                    "charge_loss": losses[i] or 15, "service": services[i] or 300,
                    "foerder": foeders[i] or 0,
                })
    save_data(data)
    return {}


@app.callback(
    Output("store", "data", allow_duplicate=True),
    Input({"type":"opt-label","vid":ALL,"oid":ALL}, "value"),
    Input({"type":"opt-type","vid":ALL,"oid":ALL}, "value"),
    Input({"type":"opt-source","vid":ALL,"oid":ALL}, "value"),
    Input({"type":"opt-price","vid":ALL,"oid":ALL}, "value"),
    Input({"type":"opt-price-bk","vid":ALL,"oid":ALL}, "value"),
    Input({"type":"opt-price-ls","vid":ALL,"oid":ALL}, "value"),
    Input({"type":"opt-down-pct","vid":ALL,"oid":ALL}, "value"),
    Input({"type":"opt-years","vid":ALL,"oid":ALL}, "value"),
    Input({"type":"opt-rate","vid":ALL,"oid":ALL}, "value"),
    Input({"type":"opt-lease-rate","vid":ALL,"oid":ALL}, "value"),
    Input({"type":"opt-lease-months","vid":ALL,"oid":ALL}, "value"),
    Input({"type":"opt-lease-down","vid":ALL,"oid":ALL}, "value"),
    Input({"type":"opt-lease-km","vid":ALL,"oid":ALL}, "value"),
    State({"type":"opt-label","vid":ALL,"oid":ALL}, "id"),
    prevent_initial_call=True
)
def save_options(labels, types, sources, prices_fin, prices_bk, prices_ls,
                 down_pcts, years_list, rates, lease_rates, lease_months_list,
                 lease_downs, lease_kms, ids):
    data = load_data()
    for i, id_dict in enumerate(ids):
        vid, oid = id_dict["vid"], id_dict["oid"]
        t = types[i] or "Finanzierung"
        price = (prices_bk[i] if t == "Barkauf" else prices_ls[i] if t == "Leasing" else prices_fin[i]) or 40000
        for v in data["vehicles"]:
            if v["id"] == vid:
                for opt in v["financing_options"]:
                    if opt["id"] == oid:
                        opt.update({
                            "label": labels[i] or "", "type": t,
                            "source": sources[i] or "", "price": price,
                            "down_pct": down_pcts[i] or 50,
                            "years": years_list[i] or 5, "rate": rates[i] or 0,
                            "lease_rate": lease_rates[i] or 0,
                            "lease_months": lease_months_list[i] or 48,
                            "lease_down": lease_downs[i] or 0,
                            "lease_km": lease_kms[i] or 15000,
                        })
    save_data(data)
    return {}


@app.callback(
    Output("results-area", "children"),
    Output("store", "data", allow_duplicate=True),
    Input("calc-btn", "n_clicks"),
    Input("horizon-radio", "value"),
    prevent_initial_call=True
)
def update_results(n_clicks, horizon):
    data = load_data()
    data["horizon"] = horizon
    save_data(data)

    v = data.get("verbrenner", {})
    km = v.get("km", 12500)

    # ── Build series ──────────────────────────────────────────────────────
    series = []

    # Verbrenner baseline
    v_yearly = [calc_yearly(v, y, km, mode="verbrenner") for y in range(1, 11)]
    series.append({
        "label": v.get("name","Verbrenner") or "Verbrenner (Behalten)",
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
            total_yearly = [ev_opex[y-1] + fin["year_cost"](y) for y in range(1, 11)]
            vname = vehicle.get("name","") or "Fahrzeug"
            oname = opt.get("label","") or opt.get("type","")
            src = opt.get("source","")
            label = f"{vname} · {oname}"
            series.append({
                "label": label,
                "is_verbrenner": False,
                "cum10": calc_cumulative(total_yearly),
                "yearly10": total_yearly,
                "fin_summary": fin["summary"],
                "source": src,
            })

    if len(series) < 2:
        return dbc.Alert([
            html.I(className="bi bi-info-circle me-2"),
            "Füge mindestens ein Fahrzeug mit einer Finanzierungsoption hinzu und klicke 'Vergleich aktualisieren'."
        ], color="info", className="mt-2"), {}

    # Color assignment
    def get_color(s, ci):
        return COLOR_VERBRENNER if s["is_verbrenner"] else PLOT_COLORS[ci % len(PLOT_COLORS)]

    colors, ci = [], 0
    for s in series:
        colors.append(get_color(s, ci))
        if not s["is_verbrenner"]:
            ci += 1

    # ── Summary cards ─────────────────────────────────────────────────────
    v_total = sum(series[0]["yearly10"][:horizon])
    summary_cards = []
    for i, s in enumerate(series):
        total = sum(s["yearly10"][:horizon])
        diff = total - v_total
        is_v = s["is_verbrenner"]
        badge = dbc.Badge("Referenz", color="secondary") if is_v else (
            html.Span([html.I(className=f"bi bi-arrow-{'down' if diff<0 else 'up'}-circle me-1"),
                       f"{'−' if diff<0 else '+'} {abs(diff):,.0f} €".replace(",",".")],
                      className=f"small text-{'success' if diff<0 else 'danger'}"))
        summary_cards.append(
            dbc.Col(dbc.Card([
                html.Div(style={"height":"4px","background":colors[i],"borderRadius":"4px 4px 0 0"}),
                dbc.CardBody([
                    html.P(s["label"], className="small text-muted mb-1", style={"fontSize":"11px","lineHeight":"1.3"}),
                    html.H5(f"{total:,.0f} €".replace(",","."), className="mb-1"),
                    badge,
                    html.Div(html.Small(s.get("fin_summary",""), className="text-muted d-block mt-1"),
                             style={"fontSize":"10px","lineHeight":"1.3"}),
                    html.Small(f"Quelle: {s['source']}" if s.get("source") else "", className="text-muted"),
                ])
            ], className="h-100 shadow-sm"), md=True, className="mb-3")
        )

    # ── Break-Even table ──────────────────────────────────────────────────
    v_cum = series[0]["cum10"]
    be_rows = []
    for i, s in enumerate(series[1:], start=1):
        be = find_break_even(v_cum, s["cum10"])
        be_rows.append(html.Tr([
            html.Td(html.Span("■ ", style={"color":colors[i]}), style={"width":"20px"}),
            html.Td(s["label"], className="small"),
            html.Td(f"Jahr {be}" if be else "> 10 Jahre",
                    className=f"small fw-bold text-{'success' if be else 'warning'}"),
        ]))

    # ── Cumulative chart ──────────────────────────────────────────────────
    years = list(range(1, 11))
    fig_cum = go.Figure()
    for i, s in enumerate(series):
        fig_cum.add_trace(go.Scatter(
            x=years, y=s["cum10"],
            name=s["label"],
            line=dict(color=colors[i], width=2.5, dash="dot" if s["is_verbrenner"] else "solid"),
            mode="lines+markers", marker=dict(size=5),
            hovertemplate="%{y:,.0f} €<extra>" + s["label"] + "</extra>"
        ))
    fig_cum.update_layout(
        xaxis=dict(title="Jahr", tickvals=years, ticktext=[f"J.{y}" for y in years], gridcolor="#444"),
        yaxis=dict(title="Kumulierte Kosten (€)", tickformat=",.0f", gridcolor="#444"),
        legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="left", x=0, font=dict(size=11)),
        template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=10, l=60, r=20), height=360,
        title=dict(text="Kumulative Gesamtkosten über 10 Jahre", font=dict(size=13))
    )

    # ── Bar chart ─────────────────────────────────────────────────────────
    bar_labels = [f"J.{y}" for y in range(1, horizon+1)]
    fig_bar = go.Figure()
    for i, s in enumerate(series):
        fig_bar.add_trace(go.Bar(
            name=s["label"],
            x=bar_labels,
            y=[round(s["yearly10"][y-1]) for y in range(1, horizon+1)],
            marker_color=colors[i],
            hovertemplate="%{y:,.0f} €/Jahr<extra>" + s["label"] + "</extra>"
        ))
    fig_bar.update_layout(
        barmode="group",
        xaxis=dict(gridcolor="#444"),
        yaxis=dict(title="€/Jahr", tickformat=",.0f", gridcolor="#444"),
        legend=dict(orientation="h", yanchor="top", y=-0.28, xanchor="left", x=0, font=dict(size=11)),
        template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=10, l=60, r=20), height=320,
        title=dict(text=f"Jährliche Kosten – {horizon} Jahre", font=dict(size=13))
    )

    return [
        html.H6(f"Ergebnis – {horizon}-Jahres-Betrachtung", className="text-uppercase text-muted mb-3"),
        dbc.Row(summary_cards, className="mb-2"),
        dbc.Card([
            dbc.CardHeader("Break-Even gegenüber Verbrenner"),
            dbc.CardBody(
                dbc.Table([html.Tbody(be_rows)], bordered=False, hover=True, size="sm", className="mb-0")
                if be_rows else html.P("Keine Vergleichsfahrzeuge.", className="small text-muted mb-0")
            )
        ], className="mb-4 shadow-sm"),
        dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_cum, config={"displayModeBar":False})), className="mb-4 shadow-sm"),
        dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_bar, config={"displayModeBar":False})), className="mb-4 shadow-sm"),
    ], {}


if __name__ == "__main__":
    app.run(debug=True, port=8050)
