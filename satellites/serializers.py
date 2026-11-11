"""Plain-Python serialization between models and the JSON API."""

from .services import placements as placement_rules

FRAME_SIZES = (1, 3, 6)


def frame_to_dict(frame):
    return {
        "id": frame.id,
        "name": frame.name,
        "size_u": frame.size_u,
        "length_mm": frame.length_mm,
        "width_mm": frame.width_mm,
        "height_mm": frame.height_mm,
        "mass_g": frame.mass_g,
        "max_mass_g": frame.max_mass_g,
        "slot_count": frame.slot_count,
    }


def module_to_dict(module):
    data = {
        "id": module.id,
        "name": module.name,
        "slug": module.slug,
        "category": module.category,
        "mount_type": module.mount_type,
        "slots": module.slots,
        "mass_g": module.mass_g,
        "power_consume_w": float(module.power_consume_w),
        "power_generate_w": float(module.power_generate_w),
        "battery_capacity_wh": float(module.battery_capacity_wh),
        "fits_frame_sizes": module.fits_frame_sizes,
        "price_usd": float(module.price_usd),
        "color": module.color,
        "model_url": module.model_file.url if module.model_file else None,
        "description": module.description,
    }
    data["allowed_faces"] = {str(size): placement_rules.allowed_faces(data, size) for size in FRAME_SIZES}
    return data


def design_to_dict(design, summary=None):
    data = {
        "id": design.id,
        "name": design.name,
        "owner": design.owner.username,
        "frame": frame_to_dict(design.frame),
        "mission_type": design.mission_type,
        "altitude_km": design.altitude_km,
        "placements": design.placements,
        "is_public": design.is_public,
        "share_slug": design.share_slug,
        "created_at": design.created_at.isoformat(),
        "updated_at": design.updated_at.isoformat(),
    }
    if summary is not None:
        data["summary"] = summary
    return data


def user_to_dict(user):
    return {"id": user.id, "username": user.username, "email": user.email}
