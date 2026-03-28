def calc_yearly(vehicle_or_verbrenner, year, km, mode="verbrenner"):
    """Calculates annual operating costs (OPEX only, no capital)."""
    v = vehicle_or_verbrenner
    if mode == "verbrenner":
        lpg_mix = (v.get("lpg_mix", 70)) / 100
        ben_share = 1 - lpg_mix
        fuel = km / 100 * (
            ben_share * v.get("ben_cons", 5.0) * v.get("ben_price", 2.07)
            + lpg_mix * v.get("lpg_cons", 7.5) * v.get("lpg_price", 1.03)
        )
        repair = v.get("repair_y1", 2500) if year == 1 else v.get("repair_follow", 800)
        return fuel + v.get("insurance", 750) + v.get("tax", 102) + repair
    else:
        cons = v.get("consumption", 18.0)
        loss = 1 + v.get("charge_loss", 15) / 100
        strom = v.get("strom_price", 28.06) / 100  # ct → €
        fuel = km / 100 * cons * loss * strom
        return fuel + v.get("insurance", 1100) + v.get("tax", 0) + v.get("service", 300)


def calc_financing(opt, foerder=0):
    """Returns financing metadata and a year_cost(y) function.

    Uses directly-entered contract data: anzahlung, laufzeit (months),
    monatliche_rate, schlussrate, and optionally gesamtbetrag.
    Barkauf is handled as a special case (full price in year 1).
    """
    fin_type = opt.get("type", "Finanzierung")

    if fin_type == "Barkauf":
        price = float(opt.get("price", 0.0))
        net = max(price - foerder, 0)

        def year_cost(y):
            return net if y == 1 else 0.0

        summary = f"Barkauf: {net:,.0f} € (nach Förderung)".replace(",", ".")
        return {"year_cost": year_cost, "summary": summary, "down": net,
                "loan": 0, "interest": 0, "type": "Barkauf"}

    anzahlung = float(opt.get("anzahlung", 0.0))
    laufzeit = max(int(opt.get("laufzeit", 48)), 1)
    monatliche_rate = float(opt.get("monatliche_rate", 0.0))
    schlussrate = float(opt.get("schlussrate", 0.0))

    gesamtbetrag_entered = float(opt.get("gesamtbetrag", 0.0))
    gesamtbetrag_calc = anzahlung + monatliche_rate * laufzeit + schlussrate
    gesamtbetrag = gesamtbetrag_entered if gesamtbetrag_entered > 0 else gesamtbetrag_calc

    last_year = (laufzeit + 11) // 12

    def year_cost(y, _a=anzahlung, _m=monatliche_rate, _lt=laufzeit,
                  _s=schlussrate, _ly=last_year):
        if y > _ly:
            return 0.0
        months_this_year = min(y * 12, _lt) - (y - 1) * 12
        cost = months_this_year * _m
        if y == 1:
            cost += _a
        if y == _ly:
            cost += _s
        return cost

    summary = (
        f"{fin_type}: {anzahlung:,.0f} € Anzahlung · "
        f"{monatliche_rate:,.0f} €/Monat · {laufzeit} Monate · "
        f"Gesamt {gesamtbetrag:,.0f} €"
    ).replace(",", ".")

    price = float(opt.get("price", 0.0))
    return {
        "year_cost": year_cost,
        "summary": summary,
        "down": anzahlung,
        "loan": monatliche_rate * laufzeit + schlussrate,
        "interest": max(gesamtbetrag - price, 0) if price > 0 else 0,
        "type": fin_type,
    }


def calc_cumulative(yearly_list):
    cumul = []
    total = 0
    for y in yearly_list:
        total += y
        cumul.append(round(total))
    return cumul


def find_break_even(v_cum, ev_cum):
    for i in range(min(len(v_cum), len(ev_cum))):
        if ev_cum[i] <= v_cum[i]:
            return i + 1
    return None
