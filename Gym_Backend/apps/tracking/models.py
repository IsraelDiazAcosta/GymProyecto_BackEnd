import uuid
from django.db import models
from django.conf import settings
from apps.catalog.models import Exercise
from apps.routines.models import RoutineDay

class WorkoutSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workout_sessions',
        verbose_name='Usuario'
    )
    routine_day = models.ForeignKey(
        RoutineDay,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workout_sessions',
        verbose_name='Día de rutina base'
    )
    title = models.CharField(max_length=150, blank=True, verbose_name='Título de la sesión')
    start_time = models.DateTimeField(verbose_name='Hora de inicio')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='Hora de finalización')
    perceived_effort_rpe = models.DecimalField(
        max_digits=3, 
        decimal_places=1, 
        null=True, 
        blank=True, 
        verbose_name='Esfuerzo global de la sesión (RPE 1-10)'
    )
    notes = models.TextField(blank=True, verbose_name='Sensaciones y notas del entrenamiento')
    is_completed = models.BooleanField(default=False, verbose_name='Sesión completada')

    class Meta:
        verbose_name = 'Sesión de Entrenamiento'
        verbose_name_plural = 'Sesiones de Entrenamiento'
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.user.email} - {self.title or 'Sesión'} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"


class WorkoutLogExercise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(WorkoutSession, on_delete=models.CASCADE, related_name='logged_exercises')
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT, related_name='logged_workouts')
    order = models.PositiveSmallIntegerField(default=1, verbose_name='Orden en la sesión')
    notes = models.TextField(blank=True, verbose_name='Notas del ejercicio')

    class Meta:
        verbose_name = 'Ejercicio Realizado'
        verbose_name_plural = 'Ejercicios Realizados'
        ordering = ['order']

    def __str__(self):
        return f"{self.exercise.name} (Sesión {self.session.id})"


class WorkoutSetLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    log_exercise = models.ForeignKey(WorkoutLogExercise, on_delete=models.CASCADE, related_name='logged_sets')
    set_number = models.PositiveSmallIntegerField(default=1, verbose_name='Número de serie')
    set_type = models.CharField(max_length=20, default='working', verbose_name='Tipo de serie')
    weight = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Peso utilizado (kg)')
    reps = models.PositiveSmallIntegerField(verbose_name='Repeticiones logradas')
    rpe = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, verbose_name='RPE')
    rir = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='Reps en reserva (RIR)')
    is_completed = models.BooleanField(default=True, verbose_name='Completada')
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Serie Registrada'
        verbose_name_plural = 'Series Registradas'
        ordering = ['set_number']

    @property
    def estimated_1rm(self):
        """Fórmula de Brzycki: peso * (36 / (37 - reps))"""
        if self.reps > 0 and self.reps < 37:
            return round(float(self.weight) * (36 / (37 - self.reps)), 2)
        return float(self.weight)

    def __str__(self):
        return f"Serie {self.set_number}: {self.weight}kg x {self.reps} reps"


class PersonalRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='records')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='user_records')
    record_type = models.CharField(max_length=30, verbose_name='Tipo de récord (ej. max_weight, 1rm)')
    value = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='Valor récord')
    achieved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Récord Personal (PR)'
        verbose_name_plural = 'Récords Personales (PRs)'
        unique_together = ('user', 'exercise', 'record_type')

    def __str__(self):
        return f"{self.user.email} - {self.exercise.name}: {self.value} ({self.record_type})"

