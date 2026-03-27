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
    """Returns financing metadata and a year_cost(y) function."""
    fin_type = opt.get("type", "Finanzierung")
    price = opt.get("price", 40000)
    net = max(price - foerder, 0)

    if fin_type == "Leasing":
        rate = opt.get("lease_rate", 399)
        months = opt.get("lease_months", 48)
        down = opt.get("lease_down", 0)
        years = months / 12
        annual_rate = rate * 12

        def year_cost(y):
            if y == 1:
                return down + annual_rate
            elif y <= years:
                return annual_rate
            else:
                return 0

        total_lease = down + rate * months
        summary = (f"Leasing: {rate:.0f} €/Monat · {months} Monate · "
                   f"Sonderzahlung {down:,.0f} € · Gesamt {total_lease:,.0f} €".replace(",","."))
        return {"year_cost": year_cost, "summary": summary, "down": down,
                "loan": rate * months, "interest": 0, "type": "Leasing"}

    elif fin_type == "Barkauf":
        def year_cost(y):
            return net if y == 1 else 0

        summary = f"Barkauf: {net:,.0f} € (nach Förderung)".replace(",",".")
        return {"year_cost": year_cost, "summary": summary, "down": net,
                "loan": 0, "interest": 0, "type": "Barkauf"}

    else:  # Finanzierung
        down_pct = opt.get("down_pct", 50) / 100
        years = opt.get("years", 5)
        rate_annual = opt.get("rate", 5.5) / 100
        down = net * down_pct
        loan = net - down
        r = rate_annual / 12
        n = years * 12

        if r > 0:
            monthly = (loan * r * (1 + r) ** n) / ((1 + r) ** n - 1)
        else:
            monthly = loan / n if n > 0 else 0

        annual_payment = monthly * 12
        total_interest = annual_payment * years - loan

        def year_cost(y):
            if y == 1:
                return down + annual_payment
            elif y <= years:
                return annual_payment
            else:
                return 0

        summary = (f"Finanzierung: {down:,.0f} € Anzahlung · "
                   f"{monthly:,.0f} €/Monat · {years} Jahre · "
                   f"Zinsen gesamt {total_interest:,.0f} €".replace(",","."))
        return {"year_cost": year_cost, "summary": summary, "down": down,
                "loan": loan, "interest": total_interest, "type": "Finanzierung"}


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
