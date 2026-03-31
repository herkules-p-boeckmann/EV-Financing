import json, os

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")
ATTACHMENTS_DIR = os.path.join(os.path.dirname(__file__), "attachments")

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
            "uvp": 0.0,
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
                    "label": "Finanzierungsoption 1",
                    "type": "Finanzierung",
                    "source": "",
                    "date_of_entry": "",
                    "anmerkungen": "",
                    "price": 40000.0,
                    "anzahlung": 0.0,
                    "laufzeit": 48,
                    "effektiver_jahreszins": 0.0,
                    "monatliche_rate": 399.0,
                    "schlussrate": 0.0,
                    "gesamtbetrag": 0.0,
                    "attachment": None,
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


def save_attachment(opt_id: str, file_bytes: bytes, original_name: str, mime_type: str) -> dict:
    """Save an attachment file and return its metadata dict."""
    os.makedirs(ATTACHMENTS_DIR, exist_ok=True)
    ext = os.path.splitext(original_name)[1].lower()
    filename = f"{opt_id}{ext}"
    with open(os.path.join(ATTACHMENTS_DIR, filename), "wb") as f:
        f.write(file_bytes)
    return {"filename": filename, "original_name": original_name, "mime_type": mime_type}


def delete_attachment(filename: str) -> None:
    """Delete an attachment file if it exists."""
    if filename:
        filepath = os.path.join(ATTACHMENTS_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)


def load_attachment(filename: str) -> bytes | None:
    """Return the bytes of an attachment file, or None if not found."""
    if filename:
        filepath = os.path.join(ATTACHMENTS_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                return f.read()
    return None
