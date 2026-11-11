"""Combines the individual budgets into the result returned by /api/evaluate/."""

from . import budget, missions, orbit, placements, simulation


def evaluate_design(frame, placement_doc, modules_by_slug, mission_type, altitude_km, factors=None):
    """Full budget report. `placement_doc` must already have passed placements.check_schema."""
    modules = placements.placed_modules(placement_doc, modules_by_slug)

    mass = budget.mass_budget(frame, modules)
    slots = budget.slot_budget(frame, placement_doc["internal"], modules_by_slug)
    power = budget.power_budget(modules, orbit.eclipse_fraction(altitude_km), factors)
    mission = missions.check_mission(mission_type, modules)

    errors = layout_errors(frame, placement_doc, modules_by_slug, slots)
    warnings = []

    if mass["status"] == "ERROR":
        errors.append(f"น้ำหนักรวม {mass['total_g']} g เกินขีดจำกัด {mass['max_g']} g")
    elif mass["status"] == "WARNING":
        warnings.append(f"น้ำหนักรวมเกิน 90% ของขีดจำกัด ({mass['pct']}%)")
    if power["status"] == "WARNING":
        warnings.append(
            f"กำลังผลิตเฉลี่ยทั้งวงโคจร {power['generate_avg_w']} W น้อยกว่ากำลังใช้ {power['consume_w']} W"
        )
    warnings.extend(mission["missing"])

    return {
        "mass": mass,
        "slots": slots,
        "power": power,
        "orbit": orbit.orbit_summary(altitude_km),
        "mission": mission,
        "cost_usd": budget.total_cost_usd(modules),
        "warnings": warnings,
        "errors": errors,
    }


def layout_errors(frame, placement_doc, modules_by_slug, slots=None):
    """Everything that makes a build physically impossible, as opposed to merely unwise."""
    if slots is None:
        slots = budget.slot_budget(frame, placement_doc["internal"], modules_by_slug)
    errors = placements.check_layout(frame, placement_doc, modules_by_slug)
    if slots["conflicts"]:
        errors.append(f"โมดูลซ้อนทับกันที่ช่อง {', '.join(str(slot) for slot in slots['conflicts'])}")
    if slots["out_of_range"]:
        errors.append(f"โมดูลล้นโครง (โครงนี้มี {slots['total']} ช่อง)")
    return errors


def simulate_design(placement_doc, modules_by_slug, altitude_km, factors=None):
    modules = placements.placed_modules(placement_doc, modules_by_slug)
    panels = [module for module in modules if module["power_generate_w"] > 0]
    return simulation.simulate_battery(
        capacity_wh=sum(module["battery_capacity_wh"] for module in modules),
        generate_sunlit_w=budget.sunlit_generation_w(panels, factors),
        consume_w=budget.total_consumption_w(modules),
        altitude_km=altitude_km,
    )


def design_summary(frame, placement_doc, modules_by_slug, altitude_km, factors=None):
    known = {
        "internal": [item for item in placement_doc.get("internal", []) if item.get("module") in modules_by_slug],
        "faces": [item for item in placement_doc.get("faces", []) if item.get("module") in modules_by_slug],
    }
    modules = placements.placed_modules(known, modules_by_slug)
    return {
        "module_count": len(modules),
        "mass_g": budget.mass_budget(frame, modules)["total_g"],
        "cost_usd": budget.total_cost_usd(modules),
        "battery_status": simulate_design(known, modules_by_slug, altitude_km, factors)["status"],
    }
