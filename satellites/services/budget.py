
MASS_WARNING_RATIO = 0.9

DEFAULT_ORIENTATION_FACTORS = {
    "SOLAR_BODY": 0.5,
    "SOLAR_DEPLOYABLE": 0.75,
}


def mass_budget(frame, modules):
    total = frame["mass_g"] + sum(module["mass_g"] for module in modules)
    maximum = frame["max_mass_g"]
    if total > maximum:
        status = "ERROR"
    elif total > maximum * MASS_WARNING_RATIO:
        status = "WARNING"
    else:
        status = "OK"
    return {
        "total_g": total,
        "max_g": maximum,
        "pct": round(total / maximum * 100, 1),
        "status": status,
    }


def slot_budget(frame, internal_placements, modules_by_slug):
    total = frame["slot_count"]
    owners = {}
    conflicts = set()
    out_of_range = set()

    for item in internal_placements:
        module = modules_by_slug[item["module"]]
        for slot in range(item["start_slot"], item["start_slot"] + module["slots"]):
            if slot >= total:
                out_of_range.add(slot)
            elif slot in owners:
                conflicts.add(slot)
            else:
                owners[slot] = item["module"]

    occupied = sorted(owners)
    return {
        "used": len(occupied),
        "total": total,
        "occupied": occupied,
        "free": [slot for slot in range(total) if slot not in owners],
        "conflicts": sorted(conflicts),
        "out_of_range": sorted(out_of_range),
    }


def sunlit_generation_w(panels, factors=None):
    """Mean output while in sunlight: sum of peak output x orientation factor."""
    factors = DEFAULT_ORIENTATION_FACTORS if factors is None else factors
    return sum(panel["power_generate_w"] * factors.get(panel["category"], 0) for panel in panels)


def total_consumption_w(modules):
    return sum(module["power_consume_w"] for module in modules)


def power_budget(modules, eclipse_fraction, factors=None):
    panels = [module for module in modules if module["power_generate_w"] > 0]
    sunlit = sunlit_generation_w(panels, factors)
    orbit_average = sunlit * (1 - eclipse_fraction)
    consume = total_consumption_w(modules)
    return {
        "generate_sunlit_w": round(sunlit, 2),
        "generate_avg_w": round(orbit_average, 2),
        "consume_w": round(consume, 2),
        "status": "WARNING" if orbit_average < consume else "OK",
    }


def total_cost_usd(modules):
    return round(sum(module["price_usd"] for module in modules), 2)
