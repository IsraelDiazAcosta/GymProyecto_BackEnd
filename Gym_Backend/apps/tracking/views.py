from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from .models import WorkoutSession, WorkoutLogExercise, WorkoutSetLog, PersonalRecord
from .serializers import (
    WorkoutSessionListSerializer,
    WorkoutSessionDetailSerializer,
    WorkoutLogExerciseSerializer,
    WorkoutSetLogSerializer,
    PersonalRecordSerializer,
)

class WorkoutSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkoutSessionListSerializer
        return WorkoutSessionDetailSerializer

    def get_queryset(self):
        return WorkoutSession.objects.filter(user=self.request.user).prefetch_related(
            'logged_exercises__logged_sets',
            'logged_exercises__exercise'
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='finish')
    def finish_session(self, request, pk=None):
        """Finaliza la sesión actual de entrenamiento."""
        session = self.get_object()
        session.end_time = timezone.now()
        session.is_completed = True
        session.perceived_effort_rpe = request.data.get('perceived_effort_rpe', session.perceived_effort_rpe)
        session.notes = request.data.get('notes', session.notes)
        session.save()
        return Response(WorkoutSessionDetailSerializer(session).data)


class WorkoutLogExerciseViewSet(viewsets.ModelViewSet):
    serializer_class = WorkoutLogExerciseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WorkoutLogExercise.objects.filter(session__user=self.request.user)


class WorkoutSetLogViewSet(viewsets.ModelViewSet):
    serializer_class = WorkoutSetLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WorkoutSetLog.objects.filter(log_exercise__session__user=self.request.user)

    def perform_create(self, serializer):
        set_log = serializer.save()
        # Verificar y actualizar récord personal (PR)
        exercise = set_log.log_exercise.exercise
        user = self.request.user

        # Máximo peso levantado
        current_max = PersonalRecord.objects.filter(
            user=user, exercise=exercise, record_type='max_weight'
        ).first()

        if not current_max or set_log.weight > current_max.value:
            PersonalRecord.objects.update_or_create(
                user=user,
                exercise=exercise,
                record_type='max_weight',
                defaults={'value': set_log.weight, 'achieved_at': timezone.now()}
            )


class ExerciseProgressionView(APIView):
    """Retorna el historial cronológico de pesos y repeticiones de un ejercicio para graficar."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, exercise_id):
        sets = WorkoutSetLog.objects.filter(
            log_exercise__session__user=request.user,
            log_exercise__exercise_id=exercise_id,
            is_completed=True
        ).order_by('logged_at').values(
            'logged_at', 'weight', 'reps', 'rpe', 'set_type'
        )

        prs = PersonalRecord.objects.filter(
            user=request.user,
            exercise_id=exercise_id
        )

        return Response({
            'exercise_id': exercise_id,
            'history': list(sets),
            'records': PersonalRecordSerializer(prs, many=True).data
        })

