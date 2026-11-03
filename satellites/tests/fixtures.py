"""Small in-memory frames and modules for the pure-function service tests."""

FRAME_3U = {"size_u": 3, "mass_g": 450, "max_mass_g": 6000, "slot_count": 12}
FRAME_1U = {"size_u": 1, "mass_g": 180, "max_mass_g": 2000, "slot_count": 4}


def module(slug, category="OBC", mount_type="INTERNAL", slots=1, mass_g=100, consume=0.0, generate=0.0,
           battery=0.0, price=100.0, sizes=None):
    return {
        "name": slug,
        "slug": slug,
        "category": category,
        "mount_type": mount_type,
        "slots": slots,
        "mass_g": mass_g,
        "power_consume_w": consume,
        "power_generate_w": generate,
        "battery_capacity_wh": battery,
        "fits_frame_sizes": sizes or [],
        "price_usd": price,
    }


CATALOGUE = {
    item["slug"]: item
    for item in [
        module("obc", "OBC", consume=0.4),
        module("battery", "EPS_BATTERY", consume=0.1, battery=40.0, mass_g=260),
        module("uhf", "COMMS", consume=1.2),
        module("wheels", "ADCS", slots=2, consume=1.8, mass_g=650),
        module("camera-small", "PAYLOAD", slots=2, consume=1.5, mass_g=300),
        module("sensor", "PAYLOAD", consume=0.6),
        module("body-1u", "SOLAR_BODY", "FACE", slots=0, generate=2.3, sizes=[1, 3, 6]),
        module("body-3u", "SOLAR_BODY", "FACE", slots=0, generate=7.0, sizes=[3]),
        module("deploy-3u", "SOLAR_DEPLOYABLE", "DEPLOYABLE", slots=0, generate=14.0, sizes=[3]),
    ]
}


def placements(internal=(), faces=()):
    return {
        "internal": [{"module": slug, "start_slot": slot} for slug, slot in internal],
        "faces": [{"module": slug, "face": face} for slug, face in faces],
    }
