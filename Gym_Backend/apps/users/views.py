from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, BodyWeightLog
from .serializers import (
    UserRegistrationSerializer,
    UserProfileSerializer,
    BodyWeightLogSerializer,
    AdminUserListSerializer,
    CustomTokenObtainPairSerializer,
)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class AdminUserListView(generics.ListAPIView):
    """Permite al administrador ver la lista de todos los usuarios registrados y sus métricas."""
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = AdminUserListSerializer
    permission_classes = [permissions.IsAdminUser]


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generar tokens automáticamente al registrarse
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserProfileSerializer(user, context={'request': request}).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class BodyWeightLogListCreateView(generics.ListCreateAPIView):
    serializer_class = BodyWeightLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BodyWeightLog.objects.filter(user=self.request.user).order_by('-date', '-id')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        latest = BodyWeightLog.objects.filter(user=self.request.user).order_by('-date', '-id').first()
        if latest:
            self.request.user.current_weight = latest.weight
            self.request.user.save(update_fields=['current_weight'])


