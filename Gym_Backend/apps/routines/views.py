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
        routine = serializer.save(user=self.request.user)
        day = RoutineDay.objects.create(routine=routine, name='Día 1', order=1)

        exercise_ids = self.request.data.get('exercise_ids', [])
        sets_count = int(self.request.data.get('sets_count', 3))
        min_reps = int(self.request.data.get('min_reps', 8))
        max_reps = int(self.request.data.get('max_reps', 12))
        rest_seconds = int(self.request.data.get('rest_seconds', 90))

        if exercise_ids:
            from apps.catalog.models import Exercise
            for idx, ex_id in enumerate(exercise_ids, start=1):
                try:
                    exercise = Exercise.objects.get(pk=ex_id)
                    routine_ex = RoutineExercise.objects.create(
                        routine_day=day,
                        exercise=exercise,
                        order=idx,
                        rest_seconds=rest_seconds
                    )
                    for s in range(1, sets_count + 1):
                        RoutineSet.objects.create(
                            routine_exercise=routine_ex,
                            set_number=s,
                            min_reps=min_reps,
                            max_reps=max_reps
                        )
                except Exercise.DoesNotExist:
                    continue

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        routine = serializer.instance
        routine.refresh_from_db()
        detail_serializer = RoutineDetailSerializer(routine, context={'request': request})
        headers = self.get_success_headers(detail_serializer.data)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'], url_path='add-exercise')
    def add_exercise(self, request, pk=None):
        """Agrega uno o varios ejercicios del catálogo a la rutina con sus series y repeticiones objetivo."""
        from django.shortcuts import get_object_or_404
        from apps.catalog.models import Exercise

        routine = self.get_object()
        exercise_ids = request.data.get('exercise_ids')
        exercise_id = request.data.get('exercise_id')

        if not exercise_ids:
            if exercise_id:
                exercise_ids = [exercise_id]
            else:
                return Response(
                    {'detail': 'Se requiere exercise_id o exercise_ids.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        sets_count = int(request.data.get('sets_count', 3))
        min_reps = int(request.data.get('min_reps', 8))
        max_reps = int(request.data.get('max_reps', 12))
        rest_seconds = int(request.data.get('rest_seconds', 90))
        notes = request.data.get('notes', '')

        day = routine.days.first()
        if not day:
            day = RoutineDay.objects.create(routine=routine, name='Día 1', order=1)

        for ex_id in exercise_ids:
            try:
                exercise = Exercise.objects.get(pk=ex_id)
                if RoutineExercise.objects.filter(routine_day=day, exercise=exercise).exists():
                    continue

                next_order = day.exercises.count() + 1
                routine_ex = RoutineExercise.objects.create(
                    routine_day=day,
                    exercise=exercise,
                    order=next_order,
                    rest_seconds=rest_seconds,
                    notes=notes
                )

                for s in range(1, sets_count + 1):
                    RoutineSet.objects.create(
                        routine_exercise=routine_ex,
                        set_number=s,
                        min_reps=min_reps,
                        max_reps=max_reps
                    )
            except Exercise.DoesNotExist:
                continue

        routine.refresh_from_db()
        return Response(RoutineDetailSerializer(routine, context={'request': request}).data, status=status.HTTP_201_CREATED)

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

