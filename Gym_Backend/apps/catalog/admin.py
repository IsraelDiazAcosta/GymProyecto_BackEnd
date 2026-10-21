from django.contrib import admin
from .models import Equipment, MuscleGroup, Exercise, ExerciseMuscle, ExerciseMedia

class ExerciseMuscleInline(admin.TabularInline):
    model = ExerciseMuscle
    extra = 1


class ExerciseMediaInline(admin.TabularInline):
    model = ExerciseMedia
    extra = 1


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'equipment_type', 'brand')
    list_filter = ('equipment_type', 'brand')
    search_fields = ('name', 'brand')


@admin.register(MuscleGroup)
class MuscleGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'body_part')
    list_filter = ('body_part',)
    search_fields = ('name',)


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('name', 'equipment', 'mechanics', 'difficulty', 'created_at')
    list_filter = ('mechanics', 'difficulty', 'equipment')
    search_fields = ('name', 'instructions')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ExerciseMuscleInline, ExerciseMediaInline]


@admin.register(ExerciseMedia)
class ExerciseMediaAdmin(admin.ModelAdmin):
    list_display = ('exercise', 'media_type', 'title', 'order')
    list_filter = ('media_type',)

