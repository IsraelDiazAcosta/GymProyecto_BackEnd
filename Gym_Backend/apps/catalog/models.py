import uuid
from django.db import models
from django.utils.text import slugify

class Equipment(models.Model):
    EQUIPMENT_TYPES = [
        ('plate_loaded', 'Máquina de discos / palanca'),
        ('pin_selected', 'Máquina de placas / pines'),
        ('cable', 'Polea / Cable'),
        ('smith', 'Barra guiada / Multipower'),
        ('free_weight', 'Peso libre (Mancuernas / Barras)'),
        ('bodyweight', 'Peso corporal / Calistenia'),
        ('cardio', 'Cardio'),
        ('accessory', 'Accesorio / Banco'),
    ]

    name = models.CharField(max_length=120, unique=True, verbose_name='Nombre de la máquina / equipo')
    equipment_type = models.CharField(max_length=30, choices=EQUIPMENT_TYPES, default='plate_loaded', verbose_name='Tipo de equipo')
    brand = models.CharField(max_length=100, blank=True, verbose_name='Marca (ej. Hammer Strength, Life Fitness)')
    image = models.ImageField(upload_to='equipment/', null=True, blank=True, verbose_name='Foto de la máquina')
    description = models.TextField(blank=True, verbose_name='Descripción')
    setup_guide = models.TextField(blank=True, verbose_name='Guía de ajuste (asiento, rodillos, pernos)')

    class Meta:
        verbose_name = 'Equipo / Máquina'
        verbose_name_plural = 'Equipos y Máquinas'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_equipment_type_display()})"


class MuscleGroup(models.Model):
    name = models.CharField(max_length=80, unique=True, verbose_name='Grupo muscular')
    body_part = models.CharField(max_length=50, verbose_name='Zona anatómica (Torso, Pierna, Brazo, etc.)')

    class Meta:
        verbose_name = 'Grupo Muscular'
        verbose_name_plural = 'Grupos Musculares'
        ordering = ['body_part', 'name']

    def __str__(self):
        return f"{self.name} ({self.body_part})"


class Exercise(models.Model):
    MECHANICS_CHOICES = [
        ('compound', 'Multiarticular / Compuesto'),
        ('isolation', 'Monoarticular / Aislamiento'),
    ]
    DIFFICULTY_CHOICES = [
        ('beginner', 'Principiante'),
        ('intermediate', 'Intermedio'),
        ('advanced', 'Avanzado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, unique=True, verbose_name='Nombre del ejercicio')
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exercises',
        verbose_name='Máquina o equipo utilizado'
    )
    muscles = models.ManyToManyField(
        MuscleGroup,
        through='ExerciseMuscle',
        related_name='exercises',
        verbose_name='Músculos involucrados'
    )
    mechanics = models.CharField(max_length=20, choices=MECHANICS_CHOICES, default='compound', verbose_name='Mecánica')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='beginner', verbose_name='Dificultad')
    instructions = models.TextField(verbose_name='Instrucciones de ejecución paso a paso')
    tips = models.TextField(blank=True, verbose_name='Consejos técnicos y errores comunes')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ejercicio'
        verbose_name_plural = 'Ejercicios'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ExerciseMuscle(models.Model):
    ROLE_CHOICES = [
        ('primary', 'Agonista (Músculo Principal)'),
        ('secondary', 'Sinergista (Secundario)'),
        ('stabilizer', 'Estabilizador'),
    ]

    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='exercise_muscles')
    muscle = models.ForeignKey(MuscleGroup, on_delete=models.CASCADE, related_name='muscle_exercises')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='primary')

    class Meta:
        verbose_name = 'Músculo del Ejercicio'
        verbose_name_plural = 'Músculos del Ejercicio'
        unique_together = ('exercise', 'muscle')

    def __str__(self):
        return f"{self.exercise.name} - {self.muscle.name} ({self.get_role_display()})"


class ExerciseMedia(models.Model):
    MEDIA_TYPES = [
        ('image', 'Imagen / Foto'),
        ('video', 'Video demostrativo'),
        ('gif', 'GIF animado'),
    ]

    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='media')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES, default='video')
    title = models.CharField(max_length=100, blank=True, verbose_name='Título o vista (ej. Vista lateral)')
    file = models.FileField(upload_to='exercises/media/', null=True, blank=True, verbose_name='Archivo subido')
    external_url = models.URLField(blank=True, verbose_name='Enlace externo (YouTube, Vimeo, CDN)')
    thumbnail = models.ImageField(upload_to='exercises/thumbnails/', null=True, blank=True, verbose_name='Miniatura')
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')

    class Meta:
        verbose_name = 'Material Multimedia del Ejercicio'
        verbose_name_plural = 'Materiales Multimedia'
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.exercise.name} - {self.get_media_type_display()} ({self.title or 'Sin título'})"

