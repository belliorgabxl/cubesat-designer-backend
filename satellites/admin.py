from django.contrib import admin

from .models import Design, Frame, Module


@admin.register(Frame)
class FrameAdmin(admin.ModelAdmin):
    list_display = ("name", "size_u", "mass_g", "max_mass_g", "slot_count")


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "mount_type", "slots", "mass_g", "price_usd")
    list_filter = ("category", "mount_type")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Design)
class DesignAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "frame", "mission_type", "altitude_km", "is_public", "updated_at")
    list_filter = ("mission_type", "is_public", "frame")
    search_fields = ("name", "owner__username", "share_slug")
    readonly_fields = ("share_slug", "created_at", "updated_at")
