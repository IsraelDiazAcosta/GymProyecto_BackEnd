from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, BodyWeightLog, UserSettings

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'username', 'experience_level')


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ('email', 'username', 'experience_level', 'current_weight', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'experience_level')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('username', 'avatar', 'bio', 'experience_level', 'current_weight', 'height')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'experience_level', 'is_staff', 'is_superuser'),
        }),
    )
    
    search_fields = ('email', 'username')
    ordering = ('email',)


@admin.register(BodyWeightLog)
class BodyWeightLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'weight', 'date', 'created_at')
    list_filter = ('date',)
    search_fields = ('user__email',)


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'theme_mode', 'accent_color', 'language', 'updated_at')
    list_filter = ('theme_mode', 'accent_color', 'language')
    search_fields = ('user__email',)
