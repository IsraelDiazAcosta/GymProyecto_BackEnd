from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'password', 'password_confirm', 'experience_level', 'current_weight', 'height')
        read_only_fields = ('id',)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'avatar', 'experience_level', 'current_weight', 'height', 'bio', 'is_staff', 'date_joined')
        read_only_fields = ('id', 'email', 'is_staff', 'date_joined')


class AdminUserListSerializer(serializers.ModelSerializer):
    """Serializer para que el administrador pueda auditar a todos los usuarios."""
    routines_count = serializers.IntegerField(source='routines.count', read_only=True)
    workouts_count = serializers.IntegerField(source='workout_sessions.count', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'experience_level', 
            'current_weight', 'height', 'is_staff', 'is_active', 
            'routines_count', 'workouts_count', 'date_joined'
        )


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': str(self.user.id),
            'email': self.user.email,
            'username': self.user.username,
            'experience_level': self.user.experience_level,
            'is_staff': self.user.is_staff,
        }
        return data

