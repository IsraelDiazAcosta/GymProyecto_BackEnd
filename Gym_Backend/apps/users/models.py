import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone

class CustomUserManager(BaseUserManager):
    """Custom user manager using email as the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
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
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField('email address', unique=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    EXPERIENCE_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    experience_level = models.CharField(
        max_length=20, 
        choices=EXPERIENCE_CHOICES, 
        default='beginner',
        verbose_name='Experience level'
    )
    current_weight = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='Current weight (kg)'
    )
    height = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='Height (cm)'
    )
    TRAINING_GOAL_CHOICES = [
        ('hypertrophy', 'Hypertrophy / Muscle gain'),
        ('strength', 'Maximum strength'),
        ('weight_loss', 'Fat loss / Cutting'),
        ('endurance', 'Endurance / Recomposition'),
        ('general_fitness', 'General fitness & health'),
    ]
    training_goal = models.CharField(
        max_length=30,
        choices=TRAINING_GOAL_CHOICES,
        default='hypertrophy',
        verbose_name='Training goal'
    )
    bio = models.TextField(blank=True, verbose_name='Bio / Goals')

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email


class BodyWeightLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='weight_logs',
        verbose_name='User'
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Body weight (kg)'
    )
    date = models.DateField(default=timezone.localdate, verbose_name='Log date')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Body Weight Log'
        verbose_name_plural = 'Body Weight History'
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.user.email} - {self.weight} kg ({self.date})"


class UserSettings(models.Model):
    """Stores persistent UI appearance and language preferences per user."""

    THEME_MODE_CHOICES = [
        ('dark', 'Dark'),
        ('light', 'Light'),
        ('system', 'System'),
    ]
    ACCENT_COLOR_CHOICES = [
        ('emerald', 'Emerald'),
        ('ocean', 'Ocean Blue'),
        ('amber', 'Energy Amber'),
        ('violet', 'Electric Violet'),
        ('crimson', 'Crimson Red'),
    ]
    LANGUAGE_CHOICES = [
        ('es', 'Spanish'),
        ('en', 'English'),
        ('system', 'System'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='settings',
        verbose_name='User',
    )
    theme_mode = models.CharField(
        max_length=10,
        choices=THEME_MODE_CHOICES,
        default='dark',
        verbose_name='Theme mode',
    )
    accent_color = models.CharField(
        max_length=20,
        choices=ACCENT_COLOR_CHOICES,
        default='emerald',
        verbose_name='Accent color',
    )
    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='es',
        verbose_name='Language',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Settings'
        verbose_name_plural = 'User Settings'

    def __str__(self):
        return f"{self.user.email} ({self.theme_mode}/{self.accent_color}/{self.language})"


