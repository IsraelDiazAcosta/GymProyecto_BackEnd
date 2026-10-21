from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoutineViewSet, RoutineDayViewSet, RoutineExerciseViewSet, RoutineSetViewSet

router = DefaultRouter()
router.register(r'routines', RoutineViewSet, basename='routines')
router.register(r'days', RoutineDayViewSet, basename='routine-days')
router.register(r'exercises', RoutineExerciseViewSet, basename='routine-exercises')
router.register(r'sets', RoutineSetViewSet, basename='routine-sets')

urlpatterns = [
    path('', include(router.urls)),
]

