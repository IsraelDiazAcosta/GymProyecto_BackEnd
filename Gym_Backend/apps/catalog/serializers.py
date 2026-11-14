import base64
import binascii
import os
import uuid
from django.core.files.base import ContentFile
from rest_framework import serializers
from .models import Equipment, MuscleGroup, Exercise, ExerciseMuscle, ExerciseMedia, UserFavoriteEquipment, validate_image


class FlexibleImageField(serializers.ImageField):
    """Acepta archivos multipart estándar o imágenes codificadas en Base64 (Data URI, string puro o dict)."""

    def to_internal_value(self, data):
        raw_name = None
        if isinstance(data, dict) and 'base64' in data:
            raw_name = data.get('name')
            data = data.get('base64')

        if isinstance(data, str):
            stripped = data.strip()
            if not stripped:
                return None
            if ';base64,' in stripped:
                header, b64_str = stripped.split(';base64,', 1)
                ext = header.split('/')[-1].split(';')[0].lower() if '/' in header else 'jpg'
            else:
                b64_str = stripped
                ext = 'jpg'

            if ext == 'jpeg':
                ext = 'jpg'
            if ext not in ('jpg', 'png', 'webp'):
                ext = 'jpg'

            try:
                decoded = base64.b64decode(''.join(b64_str.split()), validate=True)
            except (ValueError, binascii.Error, TypeError):
                self.fail('invalid_image')

            if not decoded:
                self.fail('invalid_image')

            base_name = os.path.splitext(os.path.basename(raw_name))[0] if raw_name else f"upload_{uuid.uuid4().hex[:12]}"
            data = ContentFile(decoded, name=f"{base_name}.{ext}")

        return super().to_internal_value(data)


def _build_abs_url(request, file_field):
    if not file_field:
        return None
    return request.build_absolute_uri(file_field.url) if request else file_field.url


def _resolve_exercise_image_url(obj, request):
    if obj.image:
        return _build_abs_url(request, obj.image)
    if obj.equipment and obj.equipment.image:
        return _build_abs_url(request, obj.equipment.image)
    media = obj.media.first()
    if media and media.thumbnail:
        return _build_abs_url(request, media.thumbnail)
    return None


class EquipmentSerializer(serializers.ModelSerializer):
    equipment_type_display = serializers.CharField(source='get_equipment_type_display', read_only=True)
    is_favorite = serializers.BooleanField(read_only=True, default=False)
    image = FlexibleImageField(required=False, allow_null=True, validators=[validate_image])

    class Meta:
        model = Equipment
        fields = ('id', 'name', 'equipment_type', 'equipment_type_display', 'brand', 'image', 'is_favorite', 'description', 'setup_guide')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['image'] = _build_abs_url(self.context.get('request'), instance.image)
        return data


class MuscleGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = MuscleGroup
        fields = ('id', 'name', 'body_part')


class ExerciseMuscleSerializer(serializers.ModelSerializer):
    muscle_name = serializers.CharField(source='muscle.name', read_only=True)
    body_part = serializers.CharField(source='muscle.body_part', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = ExerciseMuscle
        fields = ('muscle', 'muscle_name', 'body_part', 'role', 'role_display')


class ExerciseMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExerciseMedia
        fields = ('id', 'media_type', 'title', 'file', 'external_url', 'thumbnail', 'order')


class ExerciseListSerializer(serializers.ModelSerializer):
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)
    primary_muscle = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Exercise
        fields = ('id', 'name', 'slug', 'difficulty', 'mechanics', 'equipment_name', 'primary_muscle', 'image', 'image_url', 'thumbnail')

    def get_primary_muscle(self, obj):
        primary = obj.exercise_muscles.filter(role='primary').first()
        return primary.muscle.name if primary else None

    def get_image(self, obj):
        return _resolve_exercise_image_url(obj, self.context.get('request'))

    def get_image_url(self, obj):
        return _resolve_exercise_image_url(obj, self.context.get('request'))

    def get_thumbnail(self, obj):
        return _resolve_exercise_image_url(obj, self.context.get('request'))


class ExerciseDetailSerializer(serializers.ModelSerializer):
    equipment = EquipmentSerializer(read_only=True)
    equipment_id = serializers.PrimaryKeyRelatedField(
        queryset=Equipment.objects.all(), source='equipment', write_only=True, required=False, allow_null=True
    )
    muscle_id = serializers.PrimaryKeyRelatedField(
        queryset=MuscleGroup.objects.all(), write_only=True, required=False, allow_null=True
    )
    video_url = serializers.URLField(write_only=True, required=False, allow_blank=True)
    image = FlexibleImageField(required=False, allow_null=True, validators=[validate_image])
    image_url = serializers.SerializerMethodField()
    muscles = ExerciseMuscleSerializer(source='exercise_muscles', many=True, read_only=True)
    media = ExerciseMediaSerializer(many=True, read_only=True)

    class Meta:
        model = Exercise
        fields = (
            'id', 'name', 'slug', 'image', 'image_url', 'equipment', 'equipment_id', 'muscle_id', 'video_url', 'muscles', 
            'mechanics', 'difficulty', 'instructions', 'tips', 'media', 
            'created_at', 'updated_at'
        )

    def get_image_url(self, obj):
        return _resolve_exercise_image_url(obj, self.context.get('request'))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['image'] = self.get_image_url(instance)
        return data

    def create(self, validated_data):
        video_url = validated_data.pop('video_url', None)
        muscle = validated_data.pop('muscle_id', None)
        exercise = Exercise.objects.create(**validated_data)

        if muscle:
            ExerciseMuscle.objects.create(exercise=exercise, muscle=muscle, role='primary')

        if video_url:
            ExerciseMedia.objects.create(
                exercise=exercise,
                media_type='video',
                external_url=video_url,
                title='Demostración en video'
            )

        return exercise

    def update(self, instance, validated_data):
        has_video = 'video_url' in validated_data
        video_url = validated_data.pop('video_url', None)
        has_muscle = 'muscle_id' in validated_data
        muscle = validated_data.pop('muscle_id', None)

        instance = super().update(instance, validated_data)

        if has_muscle:
            ExerciseMuscle.objects.filter(exercise=instance, role='primary').delete()
            if muscle:
                ExerciseMuscle.objects.update_or_create(
                    exercise=instance,
                    muscle=muscle,
                    defaults={'role': 'primary'},
                )

        if has_video:
            existing_video = instance.media.filter(media_type='video').first()
            if video_url:
                if existing_video:
                    existing_video.external_url = video_url
                    existing_video.save(update_fields=['external_url'])
                else:
                    ExerciseMedia.objects.create(
                        exercise=instance,
                        media_type='video',
                        external_url=video_url,
                        title='Demostración en video',
                    )
            elif existing_video:
                existing_video.delete()

        return instance

