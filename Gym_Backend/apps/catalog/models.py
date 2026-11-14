import os
import uuid
from io import BytesIO
from PIL import Image, ImageOps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.text import slugify


def validate_image(file):
    if hasattr(file, 'seek'):
        file.seek(0)
    max_size = 5 * 1024 * 1024  # 5 MB
    if file.size > max_size:
        raise ValidationError('El tamaño máximo de imagen permitido es 5 MB.')
    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp')
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError('Formato no válido. Usa imágenes JPG, PNG o WebP.')


def optimize_image(image_field):
    if not image_field:
        return
    try:
        if hasattr(image_field, 'seek'):
            image_field.seek(0)
        img = Image.open(image_field)
        img = ImageOps.exif_transpose(img)
        if img.mode == 'P':
            img = img.convert('RGBA' if 'transparency' in img.info else 'RGB')
        elif img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
        img.thumbnail((1080, 1080), Image.Resampling.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, format='WEBP', quality=75, optimize=True)
        base_name = os.path.splitext(os.path.basename(image_field.name))[0]
        new_name = f"{base_name}.webp"
        image_field.save(new_name, ContentFile(buffer.getvalue()), save=False)
    except Exception:
        if hasattr(image_field, 'seek'):
            try:
                image_field.seek(0)
            except Exception:
                pass


def delete_old_file_on_update(instance, model_class, field_name='image'):
    if not instance.pk:
        return False
    old_instance = model_class.objects.filter(pk=instance.pk).first()
    if not old_instance:
        return False
    old_file = getattr(old_instance, field_name)
    new_file = getattr(instance, field_name)
    if old_file and old_file != new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)
        return True
    return bool(new_file and not old_file)


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
    image = models.ImageField(upload_to='equipment/', null=True, blank=True, validators=[validate_image], verbose_name='Foto de la máquina')
    description = models.TextField(blank=True, verbose_name='Descripción')
    setup_guide = models.TextField(blank=True, verbose_name='Guía de ajuste (asiento, rodillos, pernos)')

    class Meta:
        verbose_name = 'Equipo / Máquina'
        verbose_name_plural = 'Equipos y Máquinas'
        ordering = ['name']

    def save(self, *args, **kwargs):
        is_new_image = not self.pk and bool(self.image)
        if self.pk:
            is_new_image = delete_old_file_on_update(self, Equipment, 'image')
        if is_new_image and self.image:
            optimize_image(self.image)
        super().save(*args, **kwargs)

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
    image = models.ImageField(upload_to='exercises/', null=True, blank=True, validators=[validate_image], verbose_name='Imagen del ejercicio')
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
        is_new_image = not self.pk and bool(self.image)
        if self.pk:
            is_new_image = delete_old_file_on_update(self, Exercise, 'image')
        if is_new_image and self.image:
            optimize_image(self.image)
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


class UserFavoriteEquipment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorite_equipment'
    )
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='favorited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Máquina Favorita'
        verbose_name_plural = 'Máquinas Favoritas'
        unique_together = ('user', 'equipment')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} -> {self.equipment.name}"


@receiver(post_delete, sender=Equipment)
@receiver(post_delete, sender=Exercise)
def auto_delete_image_on_delete(sender, instance, **kwargs):
    if instance.image and os.path.isfile(instance.image.path):
        os.remove(instance.image.path)


