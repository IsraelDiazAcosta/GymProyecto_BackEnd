from rest_framework import serializers
from apps.catalog.serializers import ExerciseListSerializer
from .models import WorkoutSession, WorkoutLogExercise, WorkoutSetLog, PersonalRecord

class WorkoutSetLogSerializer(serializers.ModelSerializer):
    estimated_1rm = serializers.FloatField(read_only=True)

    class Meta:
        model = WorkoutSetLog
        fields = (
            'id', 'log_exercise', 'set_number', 'set_type', 
            'weight', 'reps', 'rpe', 'rir', 'is_completed', 
            'estimated_1rm', 'logged_at'
        )
        read_only_fields = ('id', 'logged_at')


class WorkoutLogExerciseSerializer(serializers.ModelSerializer):
    exercise_detail = ExerciseListSerializer(source='exercise', read_only=True)
    logged_sets = WorkoutSetLogSerializer(many=True, read_only=True)

    class Meta:
        model = WorkoutLogExercise
        fields = ('id', 'session', 'exercise', 'exercise_detail', 'order', 'notes', 'logged_sets')
        read_only_fields = ('id',)


class WorkoutSessionListSerializer(serializers.ModelSerializer):
    exercises_count = serializers.IntegerField(source='logged_exercises.count', read_only=True)
    duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = WorkoutSession
        fields = (
            'id', 'title', 'start_time', 'end_time', 
            'is_completed', 'perceived_effort_rpe', 
            'exercises_count', 'duration_minutes'
        )

    def get_duration_minutes(self, obj):
        if obj.start_time and obj.end_time:
            diff = obj.end_time - obj.start_time
            return round(diff.total_seconds() / 60)
        return None


class WorkoutSessionDetailSerializer(serializers.ModelSerializer):
    logged_exercises = WorkoutLogExerciseSerializer(many=True, read_only=True)

    class Meta:
        model = WorkoutSession
        fields = (
            'id', 'user', 'routine_day', 'title', 
            'start_time', 'end_time', 'perceived_effort_rpe', 
            'notes', 'is_completed', 'logged_exercises'
        )
        read_only_fields = ('id', 'user')

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)


class PersonalRecordSerializer(serializers.ModelSerializer):
    exercise_name = serializers.CharField(source='exercise.name', read_only=True)

    class Meta:
        model = PersonalRecord
        fields = ('id', 'exercise', 'exercise_name', 'record_type', 'value', 'achieved_at')

