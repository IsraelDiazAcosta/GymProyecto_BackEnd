from django.db import transaction
from django.db.models import Exists, OuterRef, Value, BooleanField, Prefetch
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from .models import Equipment, MuscleGroup, Exercise, ExerciseMedia, UserFavoriteEquipment
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
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'brand', 'equipment_type']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = getattr(self.request, 'user', None)
        if user and user.is_authenticated:
            queryset = queryset.annotate(
                is_favorite=Exists(
                    UserFavoriteEquipment.objects.filter(user=user, equipment=OuterRef('pk'))
                )
            )
        else:
            queryset = queryset.annotate(
                is_favorite=Value(False, output_field=BooleanField())
            )
        equipment_type = self.request.query_params.get('type')
        if equipment_type:
            queryset = queryset.filter(equipment_type=equipment_type)
        return queryset

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='favorite')
    def toggle_favorite(self, request, pk=None):
        equipment = self.get_object()
        fav, created = UserFavoriteEquipment.objects.get_or_create(
            user=request.user,
            equipment=equipment
        )
        if not created:
            fav.delete()
            return Response({'is_favorite': False, 'equipment_id': equipment.id})
        return Response({'is_favorite': True, 'equipment_id': equipment.id}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated], url_path='favorites')
    def list_favorites(self, request):
        queryset = self.get_queryset().filter(favorited_by__user=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


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
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'equipment__name', 'muscles__name']

    def get_serializer_class(self):
        if self.action == 'list':
            return ExerciseListSerializer
        return ExerciseDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = getattr(self.request, 'user', None)
        if user and user.is_authenticated:
            eq_qs = Equipment.objects.annotate(
                is_favorite=Exists(
                    UserFavoriteEquipment.objects.filter(user=user, equipment=OuterRef('pk'))
                )
            )
            queryset = queryset.prefetch_related(Prefetch('equipment', queryset=eq_qs))
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

    def perform_destroy(self, instance):
        with transaction.atomic():
            instance.routine_placements.all().delete()
            instance.logged_workouts.all().delete()
            instance.delete()


class ExerciseMediaViewSet(viewsets.ModelViewSet):
    queryset = ExerciseMedia.objects.all()
    serializer_class = ExerciseMediaSerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        queryset = super().get_queryset()
        exercise_id = self.request.query_params.get('exercise')
        if exercise_id:
            queryset = queryset.filter(exercise_id=exercise_id)
        return queryset

