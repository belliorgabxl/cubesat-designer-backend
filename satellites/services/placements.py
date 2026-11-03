"""Validation of the Design.placements JSON document.

`check_schema` covers malformed input, which is always rejected with HTTP 400.
`check_layout` covers well-formed documents that describe an impossible build;
/evaluate/ reports those as errors so the builder can show them, /designs/ refuses to save them.
"""

END_FACES = ("+Z", "-Z")
LONG_FACES = ("+X", "-X", "+Y", "-Y")
ALL_FACES = LONG_FACES + END_FACES

INTERNAL = "INTERNAL"
DEPLOYABLE = "DEPLOYABLE"
SURFACE_MOUNTS = ("FACE", "DEPLOYABLE")


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def fits_frame(module, size_u):
    sizes = module["fits_frame_sizes"]
    return not sizes or size_u in sizes


def allowed_faces(module, size_u):
    """Faces a surface-mounted module may occupy on a frame of the given size.

    End faces of a 3U/6U frame are small, so they take end-size panels (those
    that also fit a 1U frame) and long faces take the full-length ones.
    """
    if module["mount_type"] not in SURFACE_MOUNTS or not fits_frame(module, size_u):
        return []
    if module["mount_type"] == DEPLOYABLE:
        return list(LONG_FACES)
    if size_u == 1:
        return list(ALL_FACES)
    return list(END_FACES) if 1 in module["fits_frame_sizes"] else list(LONG_FACES)


def _resolve_module(slug, modules_by_slug):
    return modules_by_slug.get(slug) if isinstance(slug, str) else None


def check_schema(placements, modules_by_slug):
    """Return (normalized, errors). `normalized` is None when there are errors."""
    if not isinstance(placements, dict):
        return None, ["placements ต้องเป็น object ที่มี internal และ faces"]

    errors = []
    internal = placements.get("internal", [])
    faces = placements.get("faces", [])
    unknown_keys = set(placements) - {"internal", "faces"}
    if unknown_keys:
        errors.append(f"placements มีคีย์ที่ไม่รู้จัก: {', '.join(sorted(unknown_keys))}")
    if not isinstance(internal, list):
        errors.append("placements.internal ต้องเป็น list")
        internal = []
    if not isinstance(faces, list):
        errors.append("placements.faces ต้องเป็น list")
        faces = []

    clean_internal = []
    for index, item in enumerate(internal):
        where = f"internal[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{where} ต้องเป็น object")
            continue
        slug = item.get("module")
        start_slot = item.get("start_slot")
        module = _resolve_module(slug, modules_by_slug)
        if module is None:
            errors.append(f"{where}: ไม่พบโมดูล '{slug}'")
        elif module["mount_type"] != INTERNAL:
            errors.append(f"{where}: {module['name']} ไม่ใช่โมดูลภายใน ต้องติดที่ผิวโครง")
        if not is_int(start_slot) or start_slot < 0:
            errors.append(f"{where}: start_slot ต้องเป็นจำนวนเต็มตั้งแต่ 0 ขึ้นไป")
        clean_internal.append({"module": slug, "start_slot": start_slot})

    clean_faces = []
    for index, item in enumerate(faces):
        where = f"faces[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{where} ต้องเป็น object")
            continue
        slug = item.get("module")
        face = item.get("face")
        module = _resolve_module(slug, modules_by_slug)
        if module is None:
            errors.append(f"{where}: ไม่พบโมดูล '{slug}'")
        elif module["mount_type"] not in SURFACE_MOUNTS:
            errors.append(f"{where}: {module['name']} เป็นโมดูลภายใน ติดที่ผิวโครงไม่ได้")
        if not isinstance(face, str) or face not in ALL_FACES:
            errors.append(f"{where}: face ต้องเป็นหนึ่งใน {', '.join(ALL_FACES)}")
        clean_faces.append({"module": slug, "face": face})

    if errors:
        return None, errors
    return {"internal": clean_internal, "faces": clean_faces}, []


def check_layout(frame, placements, modules_by_slug):
    """Frame-compatibility rules. Slot overlap is reported by budget.slot_budget."""
    errors = []
    size_u = frame["size_u"]

    for item in placements["internal"]:
        module = modules_by_slug[item["module"]]
        if not fits_frame(module, size_u):
            errors.append(f"{module['name']} ใช้กับโครง {size_u}U ไม่ได้")

    used_faces = set()
    for item in placements["faces"]:
        module = modules_by_slug[item["module"]]
        face = item["face"]
        if not fits_frame(module, size_u):
            errors.append(f"{module['name']} ใช้กับโครง {size_u}U ไม่ได้")
        elif face not in allowed_faces(module, size_u):
            errors.append(f"{module['name']} ติดที่ด้าน {face} ของโครง {size_u}U ไม่ได้")
        if face in used_faces:
            errors.append(f"ด้าน {face} มีแผงติดอยู่แล้ว หนึ่งด้านติดได้หนึ่งแผง")
        used_faces.add(face)

    return errors


def placed_modules(placements, modules_by_slug):
    """Flat list of module dicts for every placement."""
    items = placements["internal"] + placements["faces"]
    return [modules_by_slug[item["module"]] for item in items]
