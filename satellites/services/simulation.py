"""Battery state of charge over a few orbits, stepped at a fixed interval."""

from . import orbit

STEP_S = 10
ORBIT_COUNT = 3
WARNING_PCT = 30.0
SECONDS_PER_HOUR = 3600


def simulate_battery(capacity_wh, generate_sunlit_w, consume_w, altitude_km, step_s=STEP_S, orbit_count=ORBIT_COUNT):
    """Return the time series plus min_battery_pct and an OK/WARNING/FAILED status."""
    period_s = orbit.orbital_period_s(altitude_km)
    fraction = orbit.eclipse_fraction(altitude_km)
    result = {
        "capacity_wh": capacity_wh,
        "generate_sunlit_w": round(generate_sunlit_w, 2),
        "consume_w": round(consume_w, 2),
        "period_min": round(period_s / 60, 2),
        "eclipse_fraction": round(fraction, 4),
    }

    if capacity_wh <= 0:
        return {
            **result,
            "series": [],
            "min_battery_pct": 0.0,
            "status": "FAILED",
            "reason": "ไม่มีแบตเตอรี่ ดาวเทียมไม่มีไฟใช้ระหว่างอยู่ในเงาโลก",
        }

    dt_h = step_s / SECONDS_PER_HOUR
    steps = int(orbit_count * period_s // step_s)
    energy = capacity_wh
    lowest = capacity_wh
    series = []

    for step in range(steps + 1):
        t_s = step * step_s
        shadow = orbit.in_eclipse(t_s, period_s, fraction)
        series.append(
            {
                "t_min": round(t_s / 60, 3),
                "battery_pct": round(energy / capacity_wh * 100, 2),
                "in_eclipse": shadow,
            }
        )
        net_w = -consume_w if shadow else generate_sunlit_w - consume_w
        energy = min(capacity_wh, max(0.0, energy + net_w * dt_h))
        lowest = min(lowest, energy)

    min_pct = round(lowest / capacity_wh * 100, 2)
    if lowest <= 0:
        status = "FAILED"
        reason = "แบตเตอรี่หมดระหว่างโคจร ระบบดับ"
    elif lowest / capacity_wh * 100 < WARNING_PCT:
        status = "WARNING"
        reason = f"แบตเตอรี่ต่ำกว่า {WARNING_PCT:.0f}% ระหว่างโคจร"
    else:
        status = "OK"
        reason = "แบตเตอรี่เพียงพอตลอดวงโคจร"

    return {**result, "series": series, "min_battery_pct": min_pct, "status": status, "reason": reason}
