import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


def sync_existing_sessions(apps, schema_editor):
    WorkoutSession = apps.get_model('tracking', 'WorkoutSession')
    WorkoutSession.objects.filter(is_completed=True).update(status='completed')
    WorkoutSession.objects.filter(
        title='Entrenamiento Móvil',
        is_completed=False,
        routine__isnull=True,
    ).update(status='cancelled')


class Migration(migrations.Migration):

    dependencies = [
        ('routines', '0002_initial'),
        ('tracking', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='workoutsession',
            name='routine',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='workout_sessions',
                to='routines.routine',
                verbose_name='Rutina',
            ),
        ),
        migrations.AddField(
            model_name='workoutsession',
            name='duration_seconds',
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name='Duración en segundos',
            ),
        ),
        migrations.AddField(
            model_name='workoutsession',
            name='status',
            field=models.CharField(
                choices=[
                    ('active', 'Activa'),
                    ('completed', 'Completada'),
                    ('cancelled', 'Cancelada'),
                ],
                default='active',
                max_length=20,
                verbose_name='Estado de la sesión',
            ),
        ),
        migrations.AlterField(
            model_name='workoutsession',
            name='start_time',
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                verbose_name='Hora de inicio',
            ),
        ),
        migrations.RunPython(sync_existing_sessions, migrations.RunPython.noop),
    ]

