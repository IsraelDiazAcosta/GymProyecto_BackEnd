from decimal import Decimal
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.catalog.models import validate_image
from apps.catalog.serializers import FlexibleImageField
from .models import User, BodyWeightLog

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)
    current_weight = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('1.00'),
        max_value=Decimal('500.00'),
        required=False,
        allow_null=True,
    )
    height = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0.50'),
        max_value=Decimal('300.00'),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'password', 'password_confirm', 'experience_level', 'training_goal', 'current_weight', 'height')
        read_only_fields = ('id',)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    avatar = FlexibleImageField(required=False, allow_null=True, validators=[validate_image])
    current_weight = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('1.00'),
        max_value=Decimal('500.00'),
        required=False,
        allow_null=True,
    )
    height = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0.50'),
        max_value=Decimal('300.00'),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'avatar', 'experience_level', 'training_goal', 'current_weight', 'height', 'bio', 'is_staff', 'date_joined')
        read_only_fields = ('id', 'email', 'is_staff', 'date_joined')


class BodyWeightLogSerializer(serializers.ModelSerializer):
    weight = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('1.00'),
        max_value=Decimal('500.00'),
    )

    class Meta:
        model = BodyWeightLog
        fields = ('id', 'weight', 'date', 'created_at')
        read_only_fields = ('id', 'created_at')


class AdminUserListSerializer(serializers.ModelSerializer):
    """Serializer allowing admins to audit all registered users."""
    routines_count = serializers.IntegerField(source='routines.count', read_only=True)
    workouts_count = serializers.IntegerField(source='workout_sessions.count', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'experience_level', 'training_goal',
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

