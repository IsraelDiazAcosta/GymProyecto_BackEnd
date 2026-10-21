from django.contrib import admin
from .models import Routine, RoutineDay, RoutineExercise, RoutineSet

class RoutineSetInline(admin.TabularInline):
    model = RoutineSet
    extra = 1


class RoutineExerciseInline(admin.StackedInline):
    model = RoutineExercise
    extra = 1


@admin.register(Routine)
class RoutineAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_template', 'is_active', 'created_at')
    list_filter = ('is_template', 'is_active')
    search_fields = ('title', 'description')


@admin.register(RoutineDay)
class RoutineDayAdmin(admin.ModelAdmin):
    list_display = ('name', 'routine', 'order')
    list_filter = ('routine',)
    inlines = [RoutineExerciseInline]


@admin.register(RoutineExercise)
class RoutineExerciseAdmin(admin.ModelAdmin):
    list_display = ('exercise', 'routine_day', 'order', 'rest_seconds')
    inlines = [RoutineSetInline]


@admin.register(RoutineSet)
class RoutineSetAdmin(admin.ModelAdmin):
    list_display = ('routine_exercise', 'set_number', 'set_type', 'min_reps', 'max_reps', 'target_rpe')

