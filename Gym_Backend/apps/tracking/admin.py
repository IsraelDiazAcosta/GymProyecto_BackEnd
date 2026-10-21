from django.contrib import admin
from .models import WorkoutSession, WorkoutLogExercise, WorkoutSetLog, PersonalRecord

class WorkoutSetLogInline(admin.TabularInline):
    model = WorkoutSetLog
    extra = 1


class WorkoutLogExerciseInline(admin.StackedInline):
    model = WorkoutLogExercise
    extra = 1


@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'start_time', 'end_time', 'is_completed', 'perceived_effort_rpe')
    list_filter = ('is_completed', 'start_time')
    search_fields = ('user__email', 'title')
    inlines = [WorkoutLogExerciseInline]


@admin.register(WorkoutSetLog)
class WorkoutSetLogAdmin(admin.ModelAdmin):
    list_display = ('log_exercise', 'set_number', 'set_type', 'weight', 'reps', 'rpe', 'is_completed')
    list_filter = ('set_type', 'is_completed')


@admin.register(PersonalRecord)
class PersonalRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'exercise', 'record_type', 'value', 'achieved_at')
    list_filter = ('record_type',)

