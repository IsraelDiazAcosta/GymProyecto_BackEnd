from rest_framework import serializers
from apps.catalog.serializers import ExerciseListSerializer
from .models import Routine, RoutineDay, RoutineExercise, RoutineSet

class RoutineSetSerializer(serializers.ModelSerializer):
    set_type_display = serializers.CharField(source='get_set_type_display', read_only=True)

    class Meta:
        model = RoutineSet
        fields = ('id', 'set_number', 'set_type', 'set_type_display', 'min_reps', 'max_reps', 'target_rpe', 'target_rir', 'target_weight')


class RoutineExerciseSerializer(serializers.ModelSerializer):
    exercise_detail = ExerciseListSerializer(source='exercise', read_only=True)
    target_sets = RoutineSetSerializer(many=True, required=False)

    class Meta:
        model = RoutineExercise
        fields = ('id', 'exercise', 'exercise_detail', 'order', 'rest_seconds', 'tempo', 'notes', 'target_sets')

    def create(self, validated_data):
        target_sets_data = validated_data.pop('target_sets', [])
        routine_exercise = RoutineExercise.objects.create(**validated_data)
        for set_data in target_sets_data:
            RoutineSet.objects.create(routine_exercise=routine_exercise, **set_data)
        return routine_exercise


class RoutineDaySerializer(serializers.ModelSerializer):
    exercises = RoutineExerciseSerializer(many=True, required=False)

    class Meta:
        model = RoutineDay
        fields = ('id', 'routine', 'name', 'order', 'exercises')
        read_only_fields = ('routine',)

    def create(self, validated_data):
        exercises_data = validated_data.pop('exercises', [])
        routine_day = RoutineDay.objects.create(**validated_data)
        for exercise_data in exercises_data:
            sets_data = exercise_data.pop('target_sets', [])
            routine_exercise = RoutineExercise.objects.create(routine_day=routine_day, **exercise_data)
            for s in sets_data:
                RoutineSet.objects.create(routine_exercise=routine_exercise, **s)
        return routine_day


class RoutineListSerializer(serializers.ModelSerializer):
    days_count = serializers.IntegerField(source='days.count', read_only=True)

    class Meta:
        model = Routine
        fields = ('id', 'title', 'description', 'is_template', 'is_active', 'days_count', 'created_at')


class RoutineDetailSerializer(serializers.ModelSerializer):
    days = RoutineDaySerializer(many=True, read_only=True)

    class Meta:
        model = Routine
        fields = ('id', 'user', 'title', 'description', 'is_template', 'is_active', 'days', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)

