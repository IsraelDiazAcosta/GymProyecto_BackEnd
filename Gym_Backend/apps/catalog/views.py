from rest_framework import viewsets, permissions, filters
from .models import Equipment, MuscleGroup, Exercise, ExerciseMedia
from .permissions import IsAdminOrReadOnly
from .serializers import (
    EquipmentSerializer,
    MuscleGroupSerializer,
    ExerciseListSerializer,
    ExerciseDetailSerializer,
    ExerciseMediaSerializer,
)

class EquipmentViewSet(viewsets.ModelViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'brand', 'equipment_type']

    def get_queryset(self):
        queryset = super().get_queryset()
        equipment_type = self.request.query_params.get('type')
        if equipment_type:
            queryset = queryset.filter(equipment_type=equipment_type)
        return queryset


class MuscleGroupViewSet(viewsets.ModelViewSet):
    queryset = MuscleGroup.objects.all()
    serializer_class = MuscleGroupSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'body_part']

    def get_queryset(self):
        queryset = super().get_queryset()
        body_part = self.request.query_params.get('body_part')
        if body_part:
            queryset = queryset.filter(body_part__iexact=body_part)
        return queryset


class ExerciseViewSet(viewsets.ModelViewSet):
    queryset = Exercise.objects.prefetch_related('exercise_muscles__muscle', 'media').select_related('equipment').all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'equipment__name', 'muscles__name']

    def get_serializer_class(self):
        if self.action == 'list':
            return ExerciseListSerializer
        return ExerciseDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        equipment_id = self.request.query_params.get('equipment')
        muscle_id = self.request.query_params.get('muscle')
        difficulty = self.request.query_params.get('difficulty')

        if equipment_id:
            queryset = queryset.filter(equipment_id=equipment_id)
        if muscle_id:
            queryset = queryset.filter(muscles__id=muscle_id)
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        return queryset.distinct()


class ExerciseMediaViewSet(viewsets.ModelViewSet):
    queryset = ExerciseMedia.objects.all()
    serializer_class = ExerciseMediaSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        exercise_id = self.request.query_params.get('exercise')
        if exercise_id:
            queryset = queryset.filter(exercise_id=exercise_id)
        return queryset

