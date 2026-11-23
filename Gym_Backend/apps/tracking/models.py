import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.catalog.models import Exercise
from apps.routines.models import Routine, RoutineDay

class WorkoutSession(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workout_sessions',
        verbose_name='User'
    )
    routine = models.ForeignKey(
        Routine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workout_sessions',
        verbose_name='Routine'
    )
    routine_day = models.ForeignKey(
        RoutineDay,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workout_sessions',
        verbose_name='Base routine day'
    )
    title = models.CharField(max_length=150, blank=True, verbose_name='Session title')
    start_time = models.DateTimeField(default=timezone.now, verbose_name='Start time')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='End time')
    duration_seconds = models.PositiveIntegerField(null=True, blank=True, verbose_name='Duration in seconds')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='Session status'
    )
    perceived_effort_rpe = models.DecimalField(
        max_digits=3, 
        decimal_places=1, 
        null=True, 
        blank=True, 
        verbose_name='Overall session RPE (1-10)'
    )
    notes = models.TextField(blank=True, verbose_name='Session notes and feedback')
    is_completed = models.BooleanField(default=False, verbose_name='Completed session')

    @property
    def started_at(self):
        return self.start_time

    @started_at.setter
    def started_at(self, value):
        self.start_time = value

    @property
    def ended_at(self):
        return self.end_time

    @ended_at.setter
    def ended_at(self, value):
        self.end_time = value

    class Meta:
        verbose_name = 'Workout Session'
        verbose_name_plural = 'Workout Sessions'
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.user.email} - {self.title or 'Session'} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"


class WorkoutLogExercise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(WorkoutSession, on_delete=models.CASCADE, related_name='logged_exercises')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='logged_workouts')
    order = models.PositiveSmallIntegerField(default=1, verbose_name='Session order')
    notes = models.TextField(blank=True, verbose_name='Exercise notes')

    class Meta:
        verbose_name = 'Logged Exercise'
        verbose_name_plural = 'Logged Exercises'
        ordering = ['order']

    def __str__(self):
        return f"{self.exercise.name} (Session {self.session.id})"


class WorkoutSetLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    log_exercise = models.ForeignKey(WorkoutLogExercise, on_delete=models.CASCADE, related_name='logged_sets')
    set_number = models.PositiveSmallIntegerField(default=1, verbose_name='Set number')
    set_type = models.CharField(max_length=20, default='working', verbose_name='Set type')
    weight = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Weight used (kg)')
    reps = models.PositiveSmallIntegerField(verbose_name='Reps completed')
    rpe = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, verbose_name='RPE')
    rir = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='Reps in reserve (RIR)')
    is_completed = models.BooleanField(default=True, verbose_name='Completed')
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Logged Set'
        verbose_name_plural = 'Logged Sets'
        ordering = ['set_number']

    @property
    def estimated_1rm(self):
        """Brzycki formula: weight * (36 / (37 - reps))"""
        if self.reps > 0 and self.reps < 37:
            return round(float(self.weight) * (36 / (37 - self.reps)), 2)
        return float(self.weight)

    def __str__(self):
        return f"Set {self.set_number}: {self.weight}kg x {self.reps} reps"


class PersonalRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='records')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='user_records')
    record_type = models.CharField(max_length=30, verbose_name='Record type (e.g. max_weight, 1rm)')
    value = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='Record value')
    achieved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Personal Record (PR)'
        verbose_name_plural = 'Personal Records (PRs)'
        unique_together = ('user', 'exercise', 'record_type')

    def __str__(self):
        return f"{self.user.email} - {self.exercise.name}: {self.value} ({self.record_type})"

