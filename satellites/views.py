import json
from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import MAX_ALTITUDE_KM, MIN_ALTITUDE_KM, Design, Frame, Module
from .serializers import design_to_dict, frame_to_dict, module_to_dict, user_to_dict
from .services import evaluation, placements as placement_rules

MAX_DESIGN_NAME_LENGTH = Design._meta.get_field("name").max_length
MAX_USERNAME_LENGTH = get_user_model()._meta.get_field("username").max_length


class ApiError(Exception):
    def __init__(self, message, status=400, details=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.details = details


def json_errors(view):
    """Turn ApiError and 404s into JSON so the client always has a readable message."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except ApiError as error:
            body = {"error": error.message}
            if error.details:
                body["details"] = error.details
            return JsonResponse(body, status=error.status)
        except Http404:
            return JsonResponse({"error": "ไม่พบข้อมูลที่ต้องการ"}, status=404)

    return wrapper


def login_required_json(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise ApiError("กรุณาเข้าสู่ระบบก่อน", status=401)
        return view(request, *args, **kwargs)

    return wrapper


def parse_body(request):
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ApiError("เนื้อหาคำขอไม่ใช่ JSON ที่ถูกต้อง")
    if not isinstance(data, dict):
        raise ApiError("เนื้อหาคำขอต้องเป็น JSON object")
    return data


def catalogue():
    """All modules as plain dicts, keyed by slug, for the service layer."""
    return {module.slug: module_to_dict(module) for module in Module.objects.all()}


def clean_frame(value):
    if not placement_rules.is_int(value):
        raise ApiError("frame ต้องเป็น id ของโครง")
    frame = Frame.objects.filter(pk=value).first()
    if frame is None:
        raise ApiError(f"ไม่พบโครงหมายเลข {value}")
    return frame


def clean_mission(value):
    if value not in Design.MissionType.values:
        raise ApiError(f"mission_type ต้องเป็นหนึ่งใน {', '.join(Design.MissionType.values)}")
    return value


def clean_altitude(value):
    if not placement_rules.is_int(value) or not MIN_ALTITUDE_KM <= value <= MAX_ALTITUDE_KM:
        raise ApiError(f"altitude_km ต้องเป็นจำนวนเต็มระหว่าง {MIN_ALTITUDE_KM} ถึง {MAX_ALTITUDE_KM}")
    return value


def clean_placements(value, modules):
    clean, errors = placement_rules.check_schema(value, modules)
    if errors:
        raise ApiError("รูปแบบ placements ไม่ถูกต้อง", details=errors)
    return clean


def clean_name(value):
    if not isinstance(value, str) or not value.strip():
        raise ApiError("กรุณาตั้งชื่อแบบ")
    name = value.strip()
    if len(name) > MAX_DESIGN_NAME_LENGTH:
        raise ApiError(f"ชื่อแบบยาวได้ไม่เกิน {MAX_DESIGN_NAME_LENGTH} ตัวอักษร")
    return name


def clean_is_public(value):
    if not isinstance(value, bool):
        raise ApiError("is_public ต้องเป็น true หรือ false")
    return value


def summarize(design, modules):
    return evaluation.design_summary(
        frame_to_dict(design.frame),
        design.placements,
        modules,
        design.altitude_km,
        settings.SOLAR_ORIENTATION_FACTORS,
    )



VALIDATION_MESSAGES_TH = {
    "password_too_short": "รหัสผ่านสั้นเกินไป ต้องมีอย่างน้อย 8 ตัวอักษร",
    "password_too_common": "รหัสผ่านนี้พบได้บ่อยเกินไป",
    "password_entirely_numeric": "รหัสผ่านต้องไม่เป็นตัวเลขทั้งหมด",
    "password_too_similar": "รหัสผ่านคล้ายกับชื่อผู้ใช้หรืออีเมลมากเกินไป",
    "invalid": "ชื่อผู้ใช้หรืออีเมลมีรูปแบบไม่ถูกต้อง",
}


def thai_validation_messages(error):
    if hasattr(error, "error_dict"):
        errors = [item for items in error.error_dict.values() for item in items]
    else:
        errors = error.error_list
    return [VALIDATION_MESSAGES_TH.get(item.code, " ".join(item.messages)) for item in errors]


@require_http_methods(["GET"])
@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"detail": "CSRF cookie set"})


@require_http_methods(["POST"])
@json_errors
def register(request):
    data = parse_body(request)
    username = data.get("username")
    password = data.get("password")
    email = data.get("email", "")
    if not isinstance(username, str) or not username.strip():
        raise ApiError("กรุณากรอกชื่อผู้ใช้")
    if not isinstance(password, str) or not password:
        raise ApiError("กรุณากรอกรหัสผ่าน")
    if not isinstance(email, str):
        raise ApiError("อีเมลไม่ถูกต้อง")
    username = username.strip()
    if len(username) > MAX_USERNAME_LENGTH:
        raise ApiError(f"ชื่อผู้ใช้ยาวได้ไม่เกิน {MAX_USERNAME_LENGTH} ตัวอักษร")

    User = get_user_model()
    candidate = User(username=username, email=email.strip())
    try:
        candidate.clean_fields(exclude=["password"])
        validate_password(password, candidate)
    except ValidationError as error:
        raise ApiError("ข้อมูลสมัครสมาชิกไม่ถูกต้อง", details=thai_validation_messages(error))

    try:
        with transaction.atomic():
            user = User.objects.create_user(username=username, email=email.strip(), password=password)
    except IntegrityError:
        raise ApiError("ชื่อผู้ใช้นี้ถูกใช้แล้ว")

    login(request, user)
    return JsonResponse({"user": user_to_dict(user)}, status=201)


@require_http_methods(["POST"])
@json_errors
def login_view(request):
    data = parse_body(request)
    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        raise ApiError("กรุณากรอกชื่อผู้ใช้และรหัสผ่าน")
    user = authenticate(request, username=username.strip(), password=password)
    if user is None:
        raise ApiError("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", status=401)
    login(request, user)
    return JsonResponse({"user": user_to_dict(user)})


@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    return JsonResponse({"detail": "ออกจากระบบแล้ว"})


@require_http_methods(["GET"])
def me(request):
    user = user_to_dict(request.user) if request.user.is_authenticated else None
    return JsonResponse({"user": user})


# --- Catalogue ---------------------------------------------------------------


@require_http_methods(["GET"])
def frames(request):
    return JsonResponse({"frames": [frame_to_dict(frame) for frame in Frame.objects.all()]})


@require_http_methods(["GET"])
@json_errors
def modules(request):
    queryset = Module.objects.all()
    category = request.GET.get("category")
    if category:
        if category not in Module.Category.values:
            raise ApiError(f"category ต้องเป็นหนึ่งใน {', '.join(Module.Category.values)}")
        queryset = queryset.filter(category=category)

    items = [module_to_dict(module) for module in queryset]

    frame_size = request.GET.get("frame_size")
    if frame_size:
        if not frame_size.isdecimal():
            raise ApiError("frame_size ต้องเป็นตัวเลข")
        size = int(frame_size)
        items = [item for item in items if placement_rules.fits_frame(item, size)]

    return JsonResponse({"modules": items})


# --- Budget calculations -----------------------------------------------------


@require_http_methods(["POST"])
@json_errors
def evaluate(request):
    data = parse_body(request)
    frame = clean_frame(data.get("frame"))
    mission_type = clean_mission(data.get("mission_type"))
    altitude_km = clean_altitude(data.get("altitude_km", 500))
    modules_by_slug = catalogue()
    placement_doc = clean_placements(data.get("placements", {}), modules_by_slug)
    result = evaluation.evaluate_design(
        frame_to_dict(frame),
        placement_doc,
        modules_by_slug,
        mission_type,
        altitude_km,
        settings.SOLAR_ORIENTATION_FACTORS,
    )
    return JsonResponse(result)


@require_http_methods(["POST"])
@json_errors
def simulate(request):
    data = parse_body(request)
    altitude_km = clean_altitude(data.get("altitude_km", 500))
    modules_by_slug = catalogue()
    placement_doc = clean_placements(data.get("placements", {}), modules_by_slug)
    result = evaluation.simulate_design(
        placement_doc,
        modules_by_slug,
        altitude_km,
        settings.SOLAR_ORIENTATION_FACTORS,
    )
    return JsonResponse(result)


# --- Designs -----------------------------------------------------------------


def apply_design_fields(design, data, modules_by_slug):
    """Validate the supplied fields, falling back to the design's current values."""
    design.name = clean_name(data.get("name", design.name))
    if "frame" in data:
        design.frame = clean_frame(data["frame"])
    elif design.frame_id is None:
        raise ApiError("กรุณาเลือกโครง")
    design.mission_type = clean_mission(data.get("mission_type", design.mission_type))
    design.altitude_km = clean_altitude(data.get("altitude_km", design.altitude_km))
    design.is_public = clean_is_public(data.get("is_public", design.is_public))

    placement_doc = clean_placements(data.get("placements", design.placements), modules_by_slug)
    errors = evaluation.layout_errors(frame_to_dict(design.frame), placement_doc, modules_by_slug)
    if errors:
        raise ApiError("การจัดวางชิ้นส่วนไม่ถูกต้อง", details=errors)
    design.placements = placement_doc


@require_http_methods(["GET", "POST"])
@json_errors
@login_required_json
def designs(request):
    modules_by_slug = catalogue()
    if request.method == "GET":
        queryset = request.user.designs.select_related("frame", "owner")
        return JsonResponse(
            {"designs": [design_to_dict(design, summarize(design, modules_by_slug)) for design in queryset]}
        )

    design = Design(owner=request.user, name="", placements={})
    apply_design_fields(design, parse_body(request), modules_by_slug)
    design.save()
    return JsonResponse({"design": design_to_dict(design)}, status=201)


@require_http_methods(["GET", "PUT", "DELETE"])
@json_errors
@login_required_json
def design_detail(request, design_id):
    design = get_object_or_404(Design.objects.select_related("frame", "owner"), pk=design_id)
    if design.owner_id != request.user.id:
        raise ApiError("คุณไม่มีสิทธิ์เข้าถึงแบบนี้", status=403)

    if request.method == "DELETE":
        design.delete()
        return JsonResponse({"detail": "ลบแบบแล้ว"})

    if request.method == "PUT":
        apply_design_fields(design, parse_body(request), catalogue())
        design.save()

    return JsonResponse({"design": design_to_dict(design)})


@require_http_methods(["GET"])
def gallery(request):
    modules_by_slug = catalogue()
    queryset = Design.objects.filter(is_public=True).select_related("frame", "owner")
    return JsonResponse(
        {"designs": [design_to_dict(design, summarize(design, modules_by_slug)) for design in queryset]}
    )


@require_http_methods(["GET"])
@json_errors
def shared(request, share_slug):
    design = get_object_or_404(Design.objects.select_related("frame", "owner"), share_slug=share_slug)
    return JsonResponse({"design": design_to_dict(design)})
