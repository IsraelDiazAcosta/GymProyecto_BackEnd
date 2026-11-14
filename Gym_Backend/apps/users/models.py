import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone

class CustomUserManager(BaseUserManager):
    """Gestor personalizado de usuarios con email como identificador único."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser debe tener is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser debe tener is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField('correo electrónico', unique=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    EXPERIENCE_CHOICES = [
        ('beginner', 'Principiante'),
        ('intermediate', 'Intermedio'),
        ('advanced', 'Avanzado'),
    ]
    experience_level = models.CharField(
        max_length=20, 
        choices=EXPERIENCE_CHOICES, 
        default='beginner',
        verbose_name='Nivel de experiencia'
    )
    current_weight = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='Peso actual (kg)'
    )
    height = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='Estatura (cm)'
    )
    TRAINING_GOAL_CHOICES = [
        ('hypertrophy', 'Hipertrofia / Ganancia muscular'),
        ('strength', 'Fuerza máxima'),
        ('weight_loss', 'Pérdida de grasa / Definición'),
        ('endurance', 'Resistencia / Recomposición'),
        ('general_fitness', 'Salud y condición general'),
    ]
    training_goal = models.CharField(
        max_length=30,
        choices=TRAINING_GOAL_CHOICES,
        default='hypertrophy',
        verbose_name='Objetivo de entrenamiento'
    )
    bio = models.TextField(blank=True, verbose_name='Biografía / Objetivos')

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.email


class BodyWeightLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='weight_logs',
        verbose_name='Usuario'
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Peso corporal (kg)'
    )
    date = models.DateField(default=timezone.localdate, verbose_name='Fecha de registro')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Registro de Peso Corporal'
        verbose_name_plural = 'Historial de Peso Corporal'
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.user.email} - {self.weight} kg ({self.date})"


