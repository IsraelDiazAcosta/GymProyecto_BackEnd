from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EquipmentViewSet, MuscleGroupViewSet, ExerciseViewSet, ExerciseMediaViewSet

router = DefaultRouter()
router.register(r'equipment', EquipmentViewSet, basename='equipment')
router.register(r'muscles', MuscleGroupViewSet, basename='muscles')
router.register(r'exercises', ExerciseViewSet, basename='exercises')
router.register(r'media', ExerciseMediaViewSet, basename='media')

urlpatterns = [
    path('', include(router.urls)),
]

