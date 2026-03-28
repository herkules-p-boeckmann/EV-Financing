# KFZ Vergleichsrechner

Wirtschaftlicher Vergleich zwischen einem bestehenden Verbrenner und neuen Fahrzeugen,
inkl. verschiedener Finanzierungs- und Leasingoptionen.

> **Hinweis:** Die App wurde von Dash zu [Streamlit](https://streamlit.io) migriert.

## Schnellstart

### Voraussetzungen
- Python 3.9+
- pip

### Installation

```bash
# Abhängigkeiten installieren
pip install -r requirements.txt

# App starten
streamlit run app.py
```

Danach öffnet sich der Browser automatisch, oder manuell: **http://localhost:8501**

### Oder mit einem Befehl:
```bash
pip install -r requirements.txt && streamlit run app.py
```

---

## Funktionen

### Verbrenner (Referenzfahrzeug)
- LPG/Benzin-Mischmodus mit einstellbarem Kraftstoffverhältnis
- Separate Einmalinvestitionen für Jahr 1 (TÜV, Reparaturen) und laufende Folgekosten
- Alle Kostenarten: Kraftstoff, Versicherung, KFZ-Steuer, Wartung

### Neue Fahrzeuge
- Beliebig viele Fahrzeuge hinzufügbar (EV, PHEV, ICE)
- Je Fahrzeug mehrere Ausstattungsvarianten / Finanzierungsoptionen
- **Quellen-Feld** pro Option (Autohaus, Online-Portal, Händler)

### Finanzierungsoptionen (je Fahrzeug)
| Typ | Parameter |
|-----|-----------|
| Finanzierung | Kaufpreis, Anzahlung %, Laufzeit, Zinssatz |
| Leasing | Listenpreis, Monatsrate, Laufzeit, Sonderzahlung, km-Limit |
| Barkauf | Kaufpreis |

Staatliche Förderung (z.B. E-Auto-Prämie) wird separat als Abzug vom Kaufpreis eingetragen.

### Auswertung
- Kumulativer Kostenvergleich über 10 Jahre (Liniendiagramm)
- Jährliche Kostenübersicht für den gewählten Zeitraum (Balkendiagramm)
- Break-Even-Analyse: Ab wann ist das neue Fahrzeug günstiger?
- Zusammenfassung mit absolutem Kostenvorteil/-nachteil je Option

### Datenpersistenz
Alle Eingaben werden automatisch in `data.json` gespeichert und
beim nächsten Start wiederhergestellt.

---

## Projektstruktur

```
kfz_vergleich/
├── app.py              # Streamlit-App (Layout und Logik)
├── calculations.py     # Berechnungslogik (Opex, Finanzierung, Break-Even)
├── data_store.py       # JSON-basierte Datenpersistenz
├── data.json           # Gespeicherte Eingaben (wird automatisch erstellt)
├── requirements.txt    # Python-Abhängigkeiten
├── .streamlit/
│   └── config.toml     # Streamlit-Theme (Dark Mode)
└── README.md
```
