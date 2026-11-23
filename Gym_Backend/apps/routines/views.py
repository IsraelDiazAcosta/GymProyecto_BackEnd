import uuid
from django.db import transaction
from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from apps.catalog.models import Exercise
from .models import Routine, RoutineDay, RoutineExercise, RoutineSet
from .serializers import (
    RoutineListSerializer,
    RoutineDetailSerializer,
    RoutineDaySerializer,
    RoutineExerciseSerializer,
    RoutineSetSerializer,
)


class IsRoutineOwnerOrReadOnlyTemplate(permissions.BasePermission):
    """Allows reading or cloning public templates, while only the owner or an admin can modify or delete them."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS or getattr(view, 'action', None) == 'clone_routine':
            return True
        return bool(obj.user_id == request.user.id or request.user.is_staff)


class RoutineViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsRoutineOwnerOrReadOnlyTemplate]

    def get_serializer_class(self):
        if self.action == 'list':
            return RoutineListSerializer
        return RoutineDetailSerializer

    def get_queryset(self):
        user = self.request.user
        # Show routines owned by the user as well as public templates
        return Routine.objects.filter(
            Q(user=user) | Q(is_template=True)
        ).prefetch_related('days__exercises__target_sets', 'days__exercises__exercise')

    @staticmethod
    def _extract_exercise_ids(data):
        """Extracts the list of exercise UUIDs from exercise_ids, exercise_id, or exercise."""
        raw_ids = data.get('exercise_ids')
        single_id = data.get('exercise_id') or data.get('exercise')
        if isinstance(raw_ids, list) and raw_ids:
            return [eid for eid in raw_ids if eid]
        if single_id:
            return [single_id]
        return []

    @staticmethod
    def _safe_pos_int(raw, default, max_val=None):
        try:
            val = int(raw)
            if val < 1:
                return default
            return min(val, max_val) if max_val is not None else val
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _add_exercises_to_day(day, ids_to_add, data):
        """Creates RoutineExercise and RoutineSet entries for the given exercises in a routine day."""
        sets_count = RoutineViewSet._safe_pos_int(data.get('sets_count'), 4, max_val=30)
        min_reps = RoutineViewSet._safe_pos_int(data.get('min_reps'), 8, max_val=1000)
        max_reps = max(min_reps, RoutineViewSet._safe_pos_int(data.get('max_reps'), 12, max_val=1000))
        rest_seconds = RoutineViewSet._safe_pos_int(data.get('rest_seconds'), 90, max_val=3600)
        notes = data.get('notes', '') or ''
        next_order = day.exercises.count() + 1

        for eid in ids_to_add:
            try:
                parsed_eid = uuid.UUID(str(eid))
            except (TypeError, ValueError):
                raise ValidationError({'exercise_ids': f'Invalid exercise ID: {eid}'})
            exercise = Exercise.objects.filter(pk=parsed_eid).first()
            if not exercise:
                raise ValidationError({'exercise_ids': f'Exercise not found: {eid}'})
            routine_ex = RoutineExercise.objects.create(
                routine_day=day,
                exercise=exercise,
                order=next_order,
                rest_seconds=rest_seconds,
                notes=notes,
            )
            next_order += 1
            for s in range(1, sets_count + 1):
                RoutineSet.objects.create(
                    routine_exercise=routine_ex,
                    set_number=s,
                    min_reps=min_reps,
                    max_reps=max_reps,
                )

    def perform_create(self, serializer):
        with transaction.atomic():
            routine = serializer.save(user=self.request.user)
            day = RoutineDay.objects.create(routine=routine, name='Day 1', order=1)
            ids_to_add = self._extract_exercise_ids(self.request.data)
            if ids_to_add:
                self._add_exercises_to_day(day, ids_to_add, self.request.data)

    @action(detail=True, methods=['post'], url_path='add-exercise')
    def add_exercise(self, request, pk=None):
        """Adds one or more catalog exercises to the routine with their target sets and rep ranges."""
        ids_to_add = self._extract_exercise_ids(request.data)
        if not ids_to_add:
            return Response(
                {'detail': 'You must select at least one exercise.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            routine = self.get_object()
            day = routine.days.first()
            if not day:
                day = RoutineDay.objects.create(routine=routine, name='Day 1', order=1)

            self._add_exercises_to_day(day, ids_to_add, request.data)

        routine = self.get_queryset().get(pk=routine.pk)
        return Response(RoutineDetailSerializer(routine, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='clone')
    def clone_routine(self, request, pk=None):
        """Allows a user to clone a template into their personal account."""
        original = self.get_object()
        new_routine = Routine.objects.create(
            user=request.user,
            title=f"{original.title} (My copy)",
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


class IsRoutineExerciseOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.routine_day.routine.user_id == request.user.id


class RoutineExerciseViewSet(viewsets.ModelViewSet):
    serializer_class = RoutineExerciseSerializer
    permission_classes = [permissions.IsAuthenticated, IsRoutineExerciseOwner]

    def get_queryset(self):
        return RoutineExercise.objects.filter(
            routine_day__routine__user=self.request.user
        ).select_related('exercise', 'routine_day__routine').prefetch_related('target_sets')


class RoutineSetViewSet(viewsets.ModelViewSet):
    serializer_class = RoutineSetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RoutineSet.objects.filter(routine_exercise__routine_day__routine__user=self.request.user)

