import json, os

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")

DEFAULT_DATA = {
    "horizon": 5,
    "verbrenner": {
        "name": "LPG/Benzin-Hybrid",
        "km": 12500,
        "lpg_mix": 70,
        "ben_cons": 5.0,
        "lpg_cons": 7.5,
        "ben_price": 2.07,
        "lpg_price": 1.03,
        "insurance": 750,
        "tax": 102,
        "repair_y1": 2500,
        "repair_follow": 800,
    },
    "vehicles": [
        {
            "id": "kia-ev3",
            "name": "KIA EV3 81,4 kWh",
            "type": "EV",
            "insurance": 1100,
            "tax": 0,
            "consumption": 18.0,
            "strom_price": 28.06,
            "charge_loss": 15,
            "service": 300,
            "foerder": 3000,
            "financing_options": [
                {
                    "id": "opt-1",
                    "label": "Teilfinanzierung 50%",
                    "type": "Finanzierung",
                    "source": "",
                    "price": 40000,
                    "down_pct": 50,
                    "years": 5,
                    "rate": 5.5,
                    "lease_rate": 399,
                    "lease_months": 48,
                    "lease_down": 0,
                    "lease_residual": 0,
                    "lease_km": 15000,
                }
            ]
        }
    ]
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                pass
    return json.loads(json.dumps(DEFAULT_DATA))

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
