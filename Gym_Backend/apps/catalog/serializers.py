from rest_framework import serializers
from .models import Equipment, MuscleGroup, Exercise, ExerciseMuscle, ExerciseMedia

class EquipmentSerializer(serializers.ModelSerializer):
    equipment_type_display = serializers.CharField(source='get_equipment_type_display', read_only=True)

    class Meta:
        model = Equipment
        fields = ('id', 'name', 'equipment_type', 'equipment_type_display', 'brand', 'image', 'description', 'setup_guide')


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
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Exercise
        fields = ('id', 'name', 'slug', 'difficulty', 'mechanics', 'equipment_name', 'primary_muscle', 'thumbnail')

    def get_primary_muscle(self, obj):
        primary = obj.exercise_muscles.filter(role='primary').first()
        return primary.muscle.name if primary else None

    def get_thumbnail(self, obj):
        media = obj.media.first()
        if media and media.thumbnail:
            request = self.context.get('request')
            return request.build_absolute_uri(media.thumbnail.url) if request else media.thumbnail.url
        return None


class ExerciseDetailSerializer(serializers.ModelSerializer):
    equipment = EquipmentSerializer(read_only=True)
    equipment_id = serializers.PrimaryKeyRelatedField(
        queryset=Equipment.objects.all(), source='equipment', write_only=True, required=False, allow_null=True
    )
    muscles = ExerciseMuscleSerializer(source='exercise_muscles', many=True, read_only=True)
    media = ExerciseMediaSerializer(many=True, read_only=True)

    class Meta:
        model = Exercise
        fields = (
            'id', 'name', 'slug', 'equipment', 'equipment_id', 'muscles', 
            'mechanics', 'difficulty', 'instructions', 'tips', 'media', 
            'created_at', 'updated_at'
        )

