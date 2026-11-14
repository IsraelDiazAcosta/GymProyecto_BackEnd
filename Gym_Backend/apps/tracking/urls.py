from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WorkoutSessionViewSet,
    WorkoutLogExerciseViewSet,
    WorkoutSetLogViewSet,
    ExerciseProgressionView,
    Weight1RMProgressView,
)

router = DefaultRouter()
router.register(r'sessions', WorkoutSessionViewSet, basename='workout-sessions')
router.register(r'exercises', WorkoutLogExerciseViewSet, basename='workout-exercises')
router.register(r'sets', WorkoutSetLogViewSet, basename='workout-sets')

urlpatterns = [
    path('sessions/finish/', WorkoutSessionViewSet.as_view({'post': 'finish_active'}), name='workout-sessions-finish-active'),
    path('', include(router.urls)),
    path('progression/<uuid:exercise_id>/', ExerciseProgressionView.as_view(), name='exercise-progression'),
    path('progress/weight-1rm/', Weight1RMProgressView.as_view(), name='weight-1rm-progress'),
]

