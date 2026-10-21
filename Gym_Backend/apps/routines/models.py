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
        verbose_name='Usuario creador'
    )
    title = models.CharField(max_length=150, verbose_name='Nombre del plan / rutina')
    description = models.TextField(blank=True, verbose_name='Descripción u objetivos')
    is_template = models.BooleanField(default=False, verbose_name='Es plantilla pública / predeterminada')
    is_active = models.BooleanField(default=True, verbose_name='Rutina activa')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Rutina'
        verbose_name_plural = 'Rutinas'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class RoutineDay(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    routine = models.ForeignKey(Routine, on_delete=models.CASCADE, related_name='days')
    name = models.CharField(max_length=80, verbose_name='Nombre del día (ej. Día 1: Torso)')
    order = models.PositiveSmallIntegerField(default=1, verbose_name='Orden en la semana')

    class Meta:
        verbose_name = 'Día de Rutina'
        verbose_name_plural = 'Días de Rutina'
        ordering = ['order']

    def __str__(self):
        return f"{self.routine.title} - {self.name}"


class RoutineExercise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    routine_day = models.ForeignKey(RoutineDay, on_delete=models.CASCADE, related_name='exercises')
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT, related_name='routine_placements')
    order = models.PositiveSmallIntegerField(default=1, verbose_name='Orden del ejercicio')
    rest_seconds = models.PositiveIntegerField(default=90, verbose_name='Segundos de descanso recomendados')
    tempo = models.CharField(max_length=20, blank=True, verbose_name='Tempo (ej. 3-1-1-0)')
    notes = models.TextField(blank=True, verbose_name='Notas / Indicaciones técnicas')

    class Meta:
        verbose_name = 'Ejercicio en Rutina'
        verbose_name_plural = 'Ejercicios en Rutina'
        ordering = ['order']

    def __str__(self):
        return f"{self.routine_day.name} - #{self.order} {self.exercise.name}"


class RoutineSet(models.Model):
    SET_TYPES = [
        ('warmup', 'Calentamiento'),
        ('feeder', 'Aproximación'),
        ('working', 'Serie efectiva'),
        ('drop_set', 'Drop Set'),
        ('to_failure', 'Al fallo muscular'),
    ]

    routine_exercise = models.ForeignKey(RoutineExercise, on_delete=models.CASCADE, related_name='target_sets')
    set_number = models.PositiveSmallIntegerField(default=1, verbose_name='Número de serie')
    set_type = models.CharField(max_length=20, choices=SET_TYPES, default='working', verbose_name='Tipo de serie')
    min_reps = models.PositiveSmallIntegerField(default=8, verbose_name='Reps mínimas')
    max_reps = models.PositiveSmallIntegerField(default=12, verbose_name='Reps máximas')
    target_rpe = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, verbose_name='RPE objetivo (esfuerzo 1-10)')
    target_rir = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='RIR objetivo (reps en recámara)')
    target_weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='Peso sugerido (kg)')

    class Meta:
        verbose_name = 'Rango / Configuración de Serie'
        verbose_name_plural = 'Rangos / Configuración de Series'
        ordering = ['set_number']

    def __str__(self):
        return f"Serie {self.set_number} ({self.min_reps}-{self.max_reps} reps)"

