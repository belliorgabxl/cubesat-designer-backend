import secrets

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

MIN_ALTITUDE_KM = 300
MAX_ALTITUDE_KM = 800
SHARE_SLUG_BYTES = 8


def generate_share_slug():
    return secrets.token_urlsafe(SHARE_SLUG_BYTES)


class Frame(models.Model):
    name = models.CharField(max_length=64)
    size_u = models.PositiveSmallIntegerField(unique=True)
    length_mm = models.PositiveIntegerField(help_text="Along the deployer rail (Z axis)")
    width_mm = models.PositiveIntegerField(help_text="X axis")
    height_mm = models.PositiveIntegerField(help_text="Y axis")
    mass_g = models.PositiveIntegerField()
    max_mass_g = models.PositiveIntegerField()
    slot_count = models.PositiveSmallIntegerField(help_text="1U = 4 slots of 0.25U each")

    class Meta:
        ordering = ["size_u"]

    def __str__(self):
        return self.name


class Module(models.Model):
    class Category(models.TextChoices):
        OBC = "OBC", "On-Board Computer"
        EPS_BATTERY = "EPS_BATTERY", "EPS / Battery"
        COMMS = "COMMS", "Communications"
        ADCS = "ADCS", "Attitude Control"
        PAYLOAD = "PAYLOAD", "Payload"
        SOLAR_BODY = "SOLAR_BODY", "Body-mounted solar panel"
        SOLAR_DEPLOYABLE = "SOLAR_DEPLOYABLE", "Deployable solar panel"

    class MountType(models.TextChoices):
        INTERNAL = "INTERNAL", "Internal slot"
        FACE = "FACE", "Face mounted"
        DEPLOYABLE = "DEPLOYABLE", "Deployable"

    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=64, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    mount_type = models.CharField(max_length=12, choices=MountType.choices)
    slots = models.PositiveSmallIntegerField(default=0, help_text="INTERNAL only; 1 slot = 0.25U")
    mass_g = models.PositiveIntegerField()
    power_consume_w = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    power_generate_w = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    battery_capacity_wh = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    fits_frame_sizes = models.JSONField(default=list, blank=True, help_text="Empty list = fits every frame")
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    color = models.CharField(max_length=7, default="#8899aa")
    model_file = models.FileField(upload_to="modules/", null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["category", "mass_g"]

    def __str__(self):
        return self.name


class Design(models.Model):
    class MissionType(models.TextChoices):
        EARTH_OBSERVATION = "EARTH_OBSERVATION", "Earth Observation"
        COMMUNICATION = "COMMUNICATION", "Communication"
        SCIENCE = "SCIENCE", "Science"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="designs")
    name = models.CharField(max_length=100)
    frame = models.ForeignKey(Frame, on_delete=models.PROTECT, related_name="designs")
    mission_type = models.CharField(max_length=20, choices=MissionType.choices)
    altitude_km = models.PositiveIntegerField(
        default=500,
        validators=[MinValueValidator(MIN_ALTITUDE_KM), MaxValueValidator(MAX_ALTITUDE_KM)],
    )
    placements = models.JSONField(default=dict)
    is_public = models.BooleanField(default=False)
    share_slug = models.CharField(max_length=32, unique=True, default=generate_share_slug, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name
