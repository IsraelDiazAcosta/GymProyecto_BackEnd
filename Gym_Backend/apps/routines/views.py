from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Routine, RoutineDay, RoutineExercise, RoutineSet
from .serializers import (
    RoutineListSerializer,
    RoutineDetailSerializer,
    RoutineDaySerializer,
    RoutineExerciseSerializer,
    RoutineSetSerializer,
)

class RoutineViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return RoutineListSerializer
        return RoutineDetailSerializer

    def get_queryset(self):
        user = self.request.user
        # Muestra rutinas del usuario y plantillas públicas
        return Routine.objects.filter(
            Q(user=user) | Q(is_template=True)
        ).prefetch_related('days__exercises__target_sets', 'days__exercises__exercise')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='clone')
    def clone_routine(self, request, pk=None):
        """Permite a un usuario clonar una plantilla a su cuenta personal."""
        original = self.get_object()
        new_routine = Routine.objects.create(
            user=request.user,
            title=f"{original.title} (Mi copia)",
            description=original.description,
            is_template=False,
            is_active=True,
        )

        for day in original.days.all():
            new_day = RoutineDay.objects.create(
                routine=new_routine,
                name=day.name,
                order=day.order
            )
            for ex in day.exercises.all():
                new_ex = RoutineExercise.objects.create(
                    routine_day=new_day,
                    exercise=ex.exercise,
                    order=ex.order,
                    rest_seconds=ex.rest_seconds,
                    tempo=ex.tempo,
                    notes=ex.notes
                )
                for s in ex.target_sets.all():
                    RoutineSet.objects.create(
                        routine_exercise=new_ex,
                        set_number=s.set_number,
                        set_type=s.set_type,
                        min_reps=s.min_reps,
                        max_reps=s.max_reps,
                        target_rpe=s.target_rpe,
                        target_rir=s.target_rir,
                        target_weight=s.target_weight,
                    )

        serializer = RoutineDetailSerializer(new_routine, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RoutineDayViewSet(viewsets.ModelViewSet):
    serializer_class = RoutineDaySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RoutineDay.objects.filter(routine__user=self.request.user)


class RoutineExerciseViewSet(viewsets.ModelViewSet):
    serializer_class = RoutineExerciseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RoutineExercise.objects.filter(routine_day__routine__user=self.request.user)


class RoutineSetViewSet(viewsets.ModelViewSet):
    serializer_class = RoutineSetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RoutineSet.objects.filter(routine_exercise__routine_day__routine__user=self.request.user)

