from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    Application,
    LecturerProfile,
    PortalRegistry,
    PortalTable,
    StaffProfile,
    UserProfile,
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    fk_name = "user"


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile)
admin.site.register(Application)
admin.site.register(StaffProfile)
admin.site.register(LecturerProfile)


class PortalTableInline(admin.TabularInline):
    model = PortalTable
    extra = 0
    fields = ("sort_order", "table_key", "table_name", "dashboard_route_name", "dashboard_path", "is_active")


@admin.register(PortalRegistry)
class PortalRegistryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "dashboard_route_name", "dashboard_path", "is_active")
    list_filter = ("is_active", "code")
    search_fields = ("name", "code", "description")
    inlines = (PortalTableInline,)


@admin.register(PortalTable)
class PortalTableAdmin(admin.ModelAdmin):
    list_display = ("table_name", "portal", "table_key", "dashboard_route_name", "dashboard_path", "sort_order", "is_active")
    list_filter = ("is_active", "portal__code")
    search_fields = ("table_name", "table_key", "portal__name", "portal__code")
