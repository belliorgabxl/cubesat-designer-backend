
MISSION_REQUIREMENTS = {
    "EARTH_OBSERVATION": [
        {"category": "PAYLOAD", "slug_contains": "camera", "label": "กล้องถ่ายภาพ (PAYLOAD)"},
        {"category": "ADCS", "label": "ระบบควบคุมท่าทาง (ADCS)"},
        {"category": "COMMS", "label": "ระบบสื่อสาร (COMMS)"},
        {"category": "EPS_BATTERY", "label": "แบตเตอรี่ (EPS)"},
        {"category": "OBC", "label": "คอมพิวเตอร์ควบคุม (OBC)"},
    ],
    "COMMUNICATION": [
        {"category": "COMMS", "label": "ระบบสื่อสาร (COMMS) อย่างน้อย 1 ชุด"},
        {"category": "EPS_BATTERY", "label": "แบตเตอรี่ (EPS)"},
        {"category": "OBC", "label": "คอมพิวเตอร์ควบคุม (OBC)"},
    ],
    "SCIENCE": [
        {"category": "PAYLOAD", "label": "อุปกรณ์วิทยาศาสตร์ (PAYLOAD)"},
        {"category": "EPS_BATTERY", "label": "แบตเตอรี่ (EPS)"},
        {"category": "OBC", "label": "คอมพิวเตอร์ควบคุม (OBC)"},
    ],
}


def _satisfies(module, requirement):
    if module["category"] != requirement["category"]:
        return False
    fragment = requirement.get("slug_contains")
    return fragment is None or fragment in module["slug"]


def check_mission(mission_type, modules):
    """Return the mission type and a Thai message for every missing requirement."""
    missing = [
        f"ภารกิจนี้ต้องมี{requirement['label']}"
        for requirement in MISSION_REQUIREMENTS[mission_type]
        if not any(_satisfies(module, requirement) for module in modules)
    ]
    return {"type": mission_type, "missing": missing}
