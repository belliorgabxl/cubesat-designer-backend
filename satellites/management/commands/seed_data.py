"""Idempotent sample data: frames, modules and three public demo designs."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from satellites.models import Design, Frame, Module

DEMO_USERNAME = "demo"

FRAMES = [
    {"name": "CubeSat 1U", "size_u": 1, "length_mm": 114, "width_mm": 100, "height_mm": 100,
     "mass_g": 180, "max_mass_g": 2000, "slot_count": 4},
    {"name": "CubeSat 3U", "size_u": 3, "length_mm": 341, "width_mm": 100, "height_mm": 100,
     "mass_g": 450, "max_mass_g": 6000, "slot_count": 12},
    {"name": "CubeSat 6U", "size_u": 6, "length_mm": 366, "width_mm": 226, "height_mm": 100,
     "mass_g": 1000, "max_mass_g": 12000, "slot_count": 24},
]


def _internal(name, slug, category, slots, mass_g, consume, price, color, description, battery=0):
    return {
        "name": name, "slug": slug, "category": category, "mount_type": Module.MountType.INTERNAL,
        "slots": slots, "mass_g": mass_g, "power_consume_w": Decimal(str(consume)),
        "power_generate_w": Decimal("0"), "battery_capacity_wh": Decimal(str(battery)),
        "fits_frame_sizes": [], "price_usd": Decimal(str(price)), "color": color, "description": description,
    }


def _panel(name, slug, category, mount, mass_g, generate, sizes, price, description):
    return {
        "name": name, "slug": slug, "category": category, "mount_type": mount, "slots": 0, "mass_g": mass_g,
        "power_consume_w": Decimal("0"), "power_generate_w": Decimal(str(generate)),
        "battery_capacity_wh": Decimal("0"), "fits_frame_sizes": sizes, "price_usd": Decimal(str(price)),
        "color": "#14264f", "description": description,
    }


C = Module.Category
FACE = Module.MountType.FACE
DEPLOYABLE = Module.MountType.DEPLOYABLE

MODULES = [
    _internal("OBC Basic", "obc-basic", C.OBC, 1, 70, 0.4, 4500, "#2fa66a",
              "คอมพิวเตอร์ควบคุมพื้นฐาน เหมาะกับภารกิจที่ประมวลผลไม่มาก"),
    _internal("OBC Advanced", "obc-advanced", C.OBC, 1, 110, 1.1, 9500, "#1f8f8a",
              "คอมพิวเตอร์สมรรถนะสูง ประมวลผลภาพบนดาวเทียมได้ แต่ใช้ไฟมากกว่า"),
    _internal("Battery 20Wh", "battery-20wh", C.EPS_BATTERY, 1, 150, 0.1, 2200, "#c98a2b",
              "แบตเตอรี่ลิเธียมไอออนขนาดเล็ก พร้อมวงจรจ่ายไฟ", battery=20),
    _internal("Battery 40Wh", "battery-40wh", C.EPS_BATTERY, 1, 260, 0.1, 3800, "#d9962c",
              "แบตเตอรี่ขนาดกลาง สมดุลระหว่างน้ำหนักและความจุ", battery=40),
    _internal("Battery 80Wh", "battery-80wh", C.EPS_BATTERY, 2, 500, 0.1, 6900, "#e8a62f",
              "แบตเตอรี่ความจุสูงสำหรับภารกิจที่ใช้ไฟมาก", battery=80),
    _internal("UHF Radio", "uhf-radio", C.COMMS, 1, 90, 1.2, 5200, "#3c7bd9",
              "วิทยุ UHF สำหรับ telemetry และคำสั่งจากภาคพื้นดิน อัตราข้อมูลต่ำ"),
    _internal("S-Band Transmitter", "s-band-transmitter", C.COMMS, 1, 130, 4.0, 14500, "#5563e0",
              "เครื่องส่ง S-Band อัตราข้อมูลสูง สำหรับส่งภาพและข้อมูลภารกิจ"),
    _internal("X-Band Transmitter", "x-band-transmitter", C.COMMS, 2, 240, 6.5, 26000, "#7a56d8",
              "เครื่องส่ง X-Band อัตราข้อมูลสูงมาก ใช้ไฟมากและต้องชี้ทิศแม่นยำ"),
    _internal("Magnetorquer", "magnetorquer", C.ADCS, 1, 180, 0.5, 6000, "#c2526b",
              "ขดลวดแม่เหล็กควบคุมท่าทาง ใช้สนามแม่เหล็กโลก แรงบิดต่ำแต่ประหยัดไฟ"),
    _internal("Reaction Wheels", "reaction-wheels", C.ADCS, 2, 650, 1.8, 21000, "#d6455f",
              "ล้อปฏิกิริยา 3 แกน ควบคุมท่าทางได้แม่นยำสำหรับการถ่ายภาพ"),
    _internal("Star Tracker", "star-tracker", C.ADCS, 1, 120, 0.9, 18000, "#e0668a",
              "กล้องดาวสำหรับระบุท่าทางของดาวเทียมอย่างแม่นยำ"),
    _internal("Camera Small", "camera-small", C.PAYLOAD, 2, 300, 1.5, 12000, "#9a6ad6",
              "กล้องถ่ายภาพโลกขนาดเล็ก ความละเอียดปานกลาง"),
    _internal("Camera HD", "camera-hd", C.PAYLOAD, 4, 900, 3.5, 38000, "#b57bee",
              "กล้องความละเอียดสูง กินพื้นที่ 1U ใช้ไฟและน้ำหนักมาก"),
    _internal("Science Sensor", "science-sensor", C.PAYLOAD, 1, 120, 0.6, 8000, "#38b6c4",
              "ชุดเซนเซอร์วัดรังสีและสนามแม่เหล็กสำหรับงานวิทยาศาสตร์"),
    _panel("Body Panel 1U", "solar-body-1u", C.SOLAR_BODY, FACE, 50, 2.3, [1, 3, 6], 1500,
           "แผงโซลาร์ขนาด 1U ติดด้านใดก็ได้ของโครง 1U หรือด้านปลายของโครง 3U/6U"),
    _panel("Body Panel 3U", "solar-body-3u", C.SOLAR_BODY, FACE, 140, 7, [3], 4000,
           "แผงโซลาร์ติดผิวด้านยาวของโครง 3U"),
    _panel("Body Panel 6U", "solar-body-6u", C.SOLAR_BODY, FACE, 280, 14, [6], 7500,
           "แผงโซลาร์ติดผิวด้านยาวของโครง 6U"),
    _panel("Deployable 3U", "solar-deploy-3u", C.SOLAR_DEPLOYABLE, DEPLOYABLE, 280, 14, [3], 9000,
           "แผงกางออกจากบานพับด้านยาวของโครง 3U รับแสงได้ดีกว่าแผงติดผิว"),
    _panel("Deployable 6U", "solar-deploy-6u", C.SOLAR_DEPLOYABLE, DEPLOYABLE, 550, 28, [6], 16500,
           "แผงกางออกขนาดใหญ่สำหรับโครง 6U ให้กำลังไฟสูงสุดในคลัง"),
]

DESIGNS = [
    {
        "name": "Siam-EO 3U (ถ่ายภาพโลก)",
        "frame": 3,
        "mission_type": Design.MissionType.EARTH_OBSERVATION,
        "altitude_km": 500,
        "placements": {
            "internal": [
                {"module": "obc-basic", "start_slot": 0},
                {"module": "battery-80wh", "start_slot": 1},
                {"module": "s-band-transmitter", "start_slot": 3},
                {"module": "reaction-wheels", "start_slot": 4},
                {"module": "camera-small", "start_slot": 6},
            ],
            "faces": [
                {"module": "solar-deploy-3u", "face": "+X"},
                {"module": "solar-deploy-3u", "face": "-X"},
                {"module": "solar-body-3u", "face": "+Y"},
            ],
        },
    },
    {
        "name": "Relay-1 1U (สื่อสาร)",
        "frame": 1,
        "mission_type": Design.MissionType.COMMUNICATION,
        "altitude_km": 650,
        "placements": {
            "internal": [
                {"module": "obc-basic", "start_slot": 0},
                {"module": "battery-20wh", "start_slot": 1},
                {"module": "uhf-radio", "start_slot": 2},
            ],
            "faces": [
                {"module": "solar-body-1u", "face": "+X"},
                {"module": "solar-body-1u", "face": "-X"},
                {"module": "solar-body-1u", "face": "+Y"},
                {"module": "solar-body-1u", "face": "-Y"},
            ],
        },
    },
    {
        # Deliberately underpowered: the 20 Wh battery runs flat during the demo.
        "name": "Blackout-3U (ตัวอย่างแบบที่ล้มเหลว)",
        "frame": 3,
        "mission_type": Design.MissionType.EARTH_OBSERVATION,
        "altitude_km": 500,
        "placements": {
            "internal": [
                {"module": "obc-basic", "start_slot": 0},
                {"module": "battery-20wh", "start_slot": 1},
                {"module": "s-band-transmitter", "start_slot": 2},
                {"module": "reaction-wheels", "start_slot": 3},
                {"module": "camera-hd", "start_slot": 5},
            ],
            "faces": [
                {"module": "solar-body-3u", "face": "+X"},
            ],
        },
    },
]


class Command(BaseCommand):
    help = "Create or refresh the sample frames, modules and public demo designs."

    @transaction.atomic
    def handle(self, *args, **options):
        frames = {}
        for data in FRAMES:
            frame, _ = Frame.objects.update_or_create(size_u=data["size_u"], defaults=data)
            frames[frame.size_u] = frame

        for data in MODULES:
            Module.objects.update_or_create(slug=data["slug"], defaults=data)

        User = get_user_model()
        demo, created = User.objects.get_or_create(username=DEMO_USERNAME)
        if created:
            # Owns the demo designs only; nobody can log in as this account.
            demo.set_unusable_password()
            demo.save()

        for data in DESIGNS:
            Design.objects.update_or_create(
                owner=demo,
                name=data["name"],
                defaults={
                    "frame": frames[data["frame"]],
                    "mission_type": data["mission_type"],
                    "altitude_km": data["altitude_km"],
                    "placements": data["placements"],
                    "is_public": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {len(FRAMES)} frames, {len(MODULES)} modules, {len(DESIGNS)} public designs.")
        )
