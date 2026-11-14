from django.db import transaction
from rest_framework import serializers
from apps.catalog.serializers import ExerciseListSerializer
from .models import Routine, RoutineDay, RoutineExercise, RoutineSet

class RoutineSetSerializer(serializers.ModelSerializer):
    set_type_display = serializers.CharField(source='get_set_type_display', read_only=True)
    min_reps = serializers.IntegerField(min_value=1)
    max_reps = serializers.IntegerField(min_value=1)

    class Meta:
        model = RoutineSet
        fields = ('id', 'set_number', 'set_type', 'set_type_display', 'min_reps', 'max_reps', 'target_rpe', 'target_rir', 'target_weight')

    def validate(self, attrs):
        min_r = attrs.get('min_reps', getattr(self.instance, 'min_reps', 1))
        max_r = attrs.get('max_reps', getattr(self.instance, 'max_reps', 1))
        if min_r > max_r:
            raise serializers.ValidationError({'min_reps': 'min_reps no puede ser mayor que max_reps.'})
        return attrs


class RoutineExerciseSerializer(serializers.ModelSerializer):
    exercise_detail = ExerciseListSerializer(source='exercise', read_only=True)
    target_sets = RoutineSetSerializer(many=True, required=False)
    sets_count = serializers.IntegerField(write_only=True, required=False, min_value=1)
    min_reps = serializers.IntegerField(write_only=True, required=False, min_value=1)
    max_reps = serializers.IntegerField(write_only=True, required=False, min_value=1)

    class Meta:
        model = RoutineExercise
        fields = (
            'id', 'exercise', 'exercise_detail', 'order', 'rest_seconds',
            'tempo', 'notes', 'target_sets', 'sets_count', 'min_reps', 'max_reps'
        )

    def validate(self, attrs):
        min_r = attrs.get('min_reps')
        max_r = attrs.get('max_reps')
        if min_r is not None and max_r is not None and min_r > max_r:
            raise serializers.ValidationError({'min_reps': 'min_reps no puede ser mayor que max_reps.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        sets_count = validated_data.pop('sets_count', None)
        min_reps = validated_data.pop('min_reps', None)
        max_reps = validated_data.pop('max_reps', None)
        target_sets_data = validated_data.pop('target_sets', [])
        routine_exercise = RoutineExercise.objects.create(**validated_data)

        if target_sets_data:
            for idx, set_data in enumerate(target_sets_data, start=1):
                set_data.setdefault('set_number', idx)
                RoutineSet.objects.create(routine_exercise=routine_exercise, **set_data)
        elif any(v is not None for v in (sets_count, min_reps, max_reps)):
            final_sets = sets_count or 3
            final_min = min_reps or 8
            final_max = max_reps or max(final_min, 12)
            for s in range(1, final_sets + 1):
                RoutineSet.objects.create(
                    routine_exercise=routine_exercise,
                    set_number=s,
                    min_reps=final_min,
                    max_reps=final_max
                )
        return routine_exercise

    @transaction.atomic
    def update(self, instance, validated_data):
        sets_count = validated_data.pop('sets_count', None)
        min_reps = validated_data.pop('min_reps', None)
        max_reps = validated_data.pop('max_reps', None)
        target_sets_data = validated_data.pop('target_sets', None)

        instance = super().update(instance, validated_data)
        existing_sets = list(instance.target_sets.order_by('set_number', 'id'))

        if target_sets_data is not None:
            common_len = min(len(existing_sets), len(target_sets_data))
            for idx in range(common_len):
                s_obj = existing_sets[idx]
                s_data = target_sets_data[idx]
                s_obj.set_number = s_data.get('set_number', idx + 1)
                for field in ('set_type', 'min_reps', 'max_reps', 'target_rpe', 'target_rir', 'target_weight'):
                    if field in s_data:
                        setattr(s_obj, field, s_data[field])
                s_obj.save()
            if len(target_sets_data) > len(existing_sets):
                for idx in range(len(existing_sets), len(target_sets_data)):
                    s_data = dict(target_sets_data[idx])
                    s_data.setdefault('set_number', idx + 1)
                    RoutineSet.objects.create(routine_exercise=instance, **s_data)
            elif len(target_sets_data) < len(existing_sets):
                ids_to_delete = [s.id for s in existing_sets[len(target_sets_data):]]
                instance.target_sets.filter(id__in=ids_to_delete).delete()

        elif any(v is not None for v in (sets_count, min_reps, max_reps)):
            ref_set = existing_sets[-1] if existing_sets else None
            final_sets = sets_count if sets_count is not None else (len(existing_sets) or 3)
            final_min = min_reps if min_reps is not None else (ref_set.min_reps if ref_set else 8)
            final_max = max_reps if max_reps is not None else (ref_set.max_reps if ref_set else final_min)
            if final_min > final_max:
                raise serializers.ValidationError({'min_reps': 'min_reps no puede ser mayor que max_reps.'})

            common_len = min(len(existing_sets), final_sets)
            for idx in range(common_len):
                s_obj = existing_sets[idx]
                s_obj.set_number = idx + 1
                if min_reps is not None:
                    s_obj.min_reps = final_min
                if max_reps is not None:
                    s_obj.max_reps = final_max
                if s_obj.min_reps > s_obj.max_reps:
                    raise serializers.ValidationError({'min_reps': 'min_reps no puede ser mayor que max_reps.'})
                s_obj.save()

            if final_sets > len(existing_sets):
                for s_num in range(len(existing_sets) + 1, final_sets + 1):
                    RoutineSet.objects.create(
                        routine_exercise=instance,
                        set_number=s_num,
                        set_type=ref_set.set_type if ref_set else 'working',
                        min_reps=final_min,
                        max_reps=final_max,
                        target_rpe=ref_set.target_rpe if ref_set else None,
                        target_rir=ref_set.target_rir if ref_set else None,
                        target_weight=ref_set.target_weight if ref_set else None,
                    )
            elif final_sets < len(existing_sets):
                ids_to_delete = [s.id for s in existing_sets[final_sets:]]
                instance.target_sets.filter(id__in=ids_to_delete).delete()

        return instance


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
            exercise_data.pop('sets_count', None)
            exercise_data.pop('min_reps', None)
            exercise_data.pop('max_reps', None)
            sets_data = exercise_data.pop('target_sets', [])
            routine_exercise = RoutineExercise.objects.create(routine_day=routine_day, **exercise_data)
            for s in sets_data:
                RoutineSet.objects.create(routine_exercise=routine_exercise, **s)
        return routine_day


class RoutineListSerializer(serializers.ModelSerializer):
    days_count = serializers.IntegerField(source='days.count', read_only=True)
    days = RoutineDaySerializer(many=True, read_only=True)

    class Meta:
        model = Routine
        fields = ('id', 'title', 'description', 'is_template', 'is_active', 'days_count', 'days', 'created_at')


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

