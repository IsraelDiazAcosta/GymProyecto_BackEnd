import uuid
from django.db import models
from django.conf import settings
from apps.catalog.models import Exercise

class Routine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='routines',
        null=True,
        blank=True,
        verbose_name='Creator user'
    )
    title = models.CharField(max_length=150, verbose_name='Plan / routine title')
    description = models.TextField(blank=True, verbose_name='Description or goals')
    is_template = models.BooleanField(default=False, verbose_name='Is public / default template')
    is_active = models.BooleanField(default=True, verbose_name='Active routine')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Routine'
        verbose_name_plural = 'Routines'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class RoutineDay(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    routine = models.ForeignKey(Routine, on_delete=models.CASCADE, related_name='days')
    name = models.CharField(max_length=80, verbose_name='Day name (e.g. Day 1: Upper)')
    order = models.PositiveSmallIntegerField(default=1, verbose_name='Order in week')

    class Meta:
        verbose_name = 'Routine Day'
        verbose_name_plural = 'Routine Days'
        ordering = ['order']

    def __str__(self):
        return f"{self.routine.title} - {self.name}"


class RoutineExercise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    routine_day = models.ForeignKey(RoutineDay, on_delete=models.CASCADE, related_name='exercises')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='routine_placements')
    order = models.PositiveSmallIntegerField(default=1, verbose_name='Exercise order')
    rest_seconds = models.PositiveIntegerField(default=90, verbose_name='Recommended rest seconds')
    tempo = models.CharField(max_length=20, blank=True, verbose_name='Tempo (e.g. 3-1-1-0)')
    notes = models.TextField(blank=True, verbose_name='Notes / Technical cues')

    class Meta:
        verbose_name = 'Routine Exercise'
        verbose_name_plural = 'Routine Exercises'
        ordering = ['order']

    def __str__(self):
        return f"{self.routine_day.name} - #{self.order} {self.exercise.name}"


class RoutineSet(models.Model):
    SET_TYPES = [
        ('warmup', 'Warm-up'),
        ('feeder', 'Feeder'),
        ('working', 'Working set'),
        ('drop_set', 'Drop set'),
        ('to_failure', 'To failure'),
    ]

    routine_exercise = models.ForeignKey(RoutineExercise, on_delete=models.CASCADE, related_name='target_sets')
    set_number = models.PositiveSmallIntegerField(default=1, verbose_name='Set number')
    set_type = models.CharField(max_length=20, choices=SET_TYPES, default='working', verbose_name='Set type')
    min_reps = models.PositiveSmallIntegerField(default=8, verbose_name='Min reps')
    max_reps = models.PositiveSmallIntegerField(default=12, verbose_name='Max reps')
    target_rpe = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, verbose_name='Target RPE (1-10)')
    target_rir = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='Target RIR (reps in reserve)')
    target_weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='Suggested weight (kg)')

    class Meta:
        verbose_name = 'Target Set Configuration'
        verbose_name_plural = 'Target Set Configurations'
        ordering = ['set_number']

    def __str__(self):
        return f"Set {self.set_number} ({self.min_reps}-{self.max_reps} reps)"

