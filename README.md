# KFZ Vergleichsrechner

Wirtschaftlicher Vergleich zwischen einem bestehenden Verbrenner und neuen Fahrzeugen,
inkl. verschiedener Finanzierungs- und Leasingoptionen.

## Schnellstart

### Voraussetzungen
- Python 3.9+
- pip

### Installation

```bash
# Abhängigkeiten installieren
pip install -r requirements.txt

# App starten
python app.py
```

Danach im Browser öffnen: **http://localhost:8050**

### Oder mit einem Befehl:
```bash
pip install -r requirements.txt && python app.py
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
├── app.py            # Dash-App, Layout und Callbacks
├── calculations.py   # Berechnungslogik (Opex, Finanzierung, Break-Even)
├── data_store.py     # JSON-basierte Datenpersistenz
├── data.json         # Gespeicherte Eingaben (wird automatisch erstellt)
├── requirements.txt  # Python-Abhängigkeiten
└── README.md
```
