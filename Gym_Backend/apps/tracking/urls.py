from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WorkoutSessionViewSet,
    WorkoutLogExerciseViewSet,
    WorkoutSetLogViewSet,
    ExerciseProgressionView,
)

router = DefaultRouter()
router.register(r'sessions', WorkoutSessionViewSet, basename='workout-sessions')
router.register(r'exercises', WorkoutLogExerciseViewSet, basename='workout-exercises')
router.register(r'sets', WorkoutSetLogViewSet, basename='workout-sets')

urlpatterns = [
    path('', include(router.urls)),
    path('progression/<uuid:exercise_id>/', ExerciseProgressionView.as_view(), name='exercise-progression'),
]

