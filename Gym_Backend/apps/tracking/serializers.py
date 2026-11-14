from django.utils import timezone
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


class _WorkoutSessionCommonMixin(serializers.ModelSerializer):
    routine_id = serializers.SerializerMethodField()
    routine_title = serializers.SerializerMethodField()
    routine_detail = serializers.SerializerMethodField()
    started_at = serializers.DateTimeField(source='start_time', read_only=True)
    ended_at = serializers.DateTimeField(source='end_time', read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()

    def _resolve_routine(self, obj):
        if obj.routine:
            return obj.routine
        if obj.routine_day and obj.routine_day.routine:
            return obj.routine_day.routine
        return None

    def _get_planned_exercises_count(self, obj):
        routine = self._resolve_routine(obj)
        if not routine:
            return 0
        count = 0
        for day in routine.days.all():
            count += len(list(day.exercises.all()))
        return count

    def get_routine_id(self, obj):
        if obj.routine_id:
            return str(obj.routine_id)
        if obj.routine_day_id and obj.routine_day.routine_id:
            return str(obj.routine_day.routine_id)
        return None

    def get_routine_title(self, obj):
        routine = self._resolve_routine(obj)
        if routine:
            return routine.title
        return obj.title or 'Rutina'

    def get_routine_detail(self, obj):
        routine = self._resolve_routine(obj)
        if not routine:
            return None
        return {
            'id': str(routine.id),
            'name': routine.title,
            'title': routine.title,
        }

    def get_duration_seconds(self, obj):
        if obj.duration_seconds is not None:
            return obj.duration_seconds
        if obj.start_time and obj.end_time:
            return max(0, int((obj.end_time - obj.start_time).total_seconds()))
        return None

    def get_date(self, obj):
        ref_dt = obj.end_time or obj.start_time
        if ref_dt:
            return timezone.localtime(ref_dt).date().isoformat()
        return None


class WorkoutSessionListSerializer(_WorkoutSessionCommonMixin):
    exercises_count = serializers.IntegerField(source='logged_exercises.count', read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    total_exercises = serializers.SerializerMethodField()
    total_sets = serializers.SerializerMethodField()
    total_volume = serializers.SerializerMethodField()

    class Meta:
        model = WorkoutSession
        fields = (
            'id', 'routine', 'routine_id', 'routine_title', 'routine_detail', 'title',
            'start_time', 'end_time', 'started_at', 'ended_at',
            'duration_seconds', 'status', 'date',
            'is_completed', 'perceived_effort_rpe',
            'exercises_count', 'duration_minutes',
            'total_exercises', 'total_sets', 'total_volume',
        )

    def get_duration_minutes(self, obj):
        if obj.start_time and obj.end_time:
            diff = obj.end_time - obj.start_time
            return round(diff.total_seconds() / 60)
        return None

    def get_total_exercises(self, obj):
        annotated = getattr(obj, 'annotated_exercises', None)
        if annotated is not None and annotated > 0:
            return int(annotated)
        planned = self._get_planned_exercises_count(obj)
        if planned > 0:
            return planned
        if annotated is not None:
            return int(annotated)
        return len(list(obj.logged_exercises.all()))

    def get_total_sets(self, obj):
        annotated = getattr(obj, 'annotated_sets', None)
        if annotated is not None:
            return int(annotated)
        return sum(len(list(le.logged_sets.all())) for le in obj.logged_exercises.all())

    def get_total_volume(self, obj):
        annotated = getattr(obj, 'annotated_volume', None)
        if annotated is not None:
            return round(float(annotated), 2)
        total = 0.0
        for le in obj.logged_exercises.all():
            for s in le.logged_sets.all():
                total += float(s.weight) * s.reps
        return round(total, 2)


class CompletedWorkoutSessionSerializer(WorkoutSessionListSerializer):
    routine = serializers.SerializerMethodField()
    exercises_count = serializers.SerializerMethodField()

    def get_routine(self, obj):
        return self.get_routine_detail(obj)

    def get_exercises_count(self, obj):
        return self.get_total_exercises(obj)


class WorkoutSessionDetailSerializer(_WorkoutSessionCommonMixin):
    logged_exercises = WorkoutLogExerciseSerializer(many=True, read_only=True)
    has_logged_sets = serializers.SerializerMethodField()
    total_exercises = serializers.SerializerMethodField()
    total_sets = serializers.SerializerMethodField()
    total_volume = serializers.SerializerMethodField()
    exercises = serializers.SerializerMethodField()

    class Meta:
        model = WorkoutSession
        fields = (
            'id', 'user', 'routine', 'routine_id', 'routine_title', 'routine_detail',
            'routine_day', 'title',
            'start_time', 'end_time', 'started_at', 'ended_at',
            'duration_seconds', 'status', 'date',
            'perceived_effort_rpe', 'notes', 'is_completed', 'logged_exercises',
            'has_logged_sets', 'total_exercises', 'total_sets', 'total_volume',
            'exercises',
        )
        read_only_fields = ('id', 'user')

    def _build_session_exercises_data(self, obj):
        cache = getattr(self, '_session_exercises_cache', None)
        if cache is None:
            cache = {}
            self._session_exercises_cache = cache
        cache_key = str(obj.pk)
        if cache_key in cache:
            return cache[cache_key]

        logged_list = sorted(
            obj.logged_exercises.all(),
            key=lambda le: (le.order, str(le.id)),
        )
        all_sets_count = sum(len(list(le.logged_sets.all())) for le in logged_list)
        has_sets = all_sets_count > 0

        exercises_payload = []
        total_volume = 0.0

        if has_sets:
            grouped = {}
            ordered_keys = []
            for le in logged_list:
                ex_sets = list(le.logged_sets.all())
                if not ex_sets:
                    continue
                ex_id = str(le.exercise_id)
                if ex_id not in grouped:
                    grouped[ex_id] = {
                        'first_log': le,
                        'exercise': le.exercise,
                        'sets': [],
                    }
                    ordered_keys.append(ex_id)
                grouped[ex_id]['sets'].extend(ex_sets)

            for idx, ex_id in enumerate(ordered_keys, start=1):
                bucket = grouped[ex_id]
                ex_sets = sorted(
                    bucket['sets'],
                    key=lambda s: (s.set_number, s.logged_at, str(s.id)),
                )
                serialized_sets = []
                for set_idx, s in enumerate(ex_sets, start=1):
                    w = float(s.weight)
                    total_volume += w * s.reps
                    serialized_sets.append({
                        'id': str(s.id),
                        'set_number': set_idx,
                        'weight': w,
                        'reps': s.reps,
                        'rpe': float(s.rpe) if s.rpe is not None else None,
                        'estimated_1rm': s.estimated_1rm,
                        'set_type': s.set_type,
                    })
                exercises_payload.append({
                    'id': str(bucket['first_log'].id),
                    'exercise_id': ex_id,
                    'exercise_name': bucket['exercise'].name,
                    'order': idx,
                    'unrecorded': False,
                    'status': 'registrado',
                    'sets': serialized_sets,
                })
        else:
            routine = self._resolve_routine(obj)
            if routine:
                idx = 1
                for day in sorted(routine.days.all(), key=lambda d: (d.order, str(d.id))):
                    for routine_ex in sorted(day.exercises.all(), key=lambda rx: (rx.order, str(rx.id))):
                        target_sets = list(routine_ex.target_sets.all())
                        sets_count = len(target_sets)
                        min_r = target_sets[0].min_reps if target_sets else None
                        max_r = target_sets[0].max_reps if target_sets else None
                        planned_reps = (
                            f"{min_r}-{max_r}"
                            if min_r is not None and max_r is not None and min_r != max_r
                            else (str(min_r) if min_r is not None else None)
                        )
                        exercises_payload.append({
                            'id': str(routine_ex.id),
                            'exercise_id': str(routine_ex.exercise_id),
                            'exercise_name': routine_ex.exercise.name,
                            'order': idx,
                            'unrecorded': True,
                            'status': 'sin registro',
                            'planned_sets': sets_count,
                            'planned_reps': planned_reps,
                            'sets': [],
                        })
                        idx += 1
            elif logged_list:
                for idx, le in enumerate(logged_list, start=1):
                    exercises_payload.append({
                        'id': str(le.id),
                        'exercise_id': str(le.exercise_id),
                        'exercise_name': le.exercise.name,
                        'order': idx,
                        'unrecorded': True,
                        'status': 'sin registro',
                        'sets': [],
                    })

        result = {
            'has_logged_sets': has_sets,
            'total_exercises': len(exercises_payload),
            'total_sets': all_sets_count,
            'total_volume': round(total_volume, 2),
            'exercises': exercises_payload,
        }
        cache[cache_key] = result
        return result

    def get_has_logged_sets(self, obj):
        return self._build_session_exercises_data(obj)['has_logged_sets']

    def get_total_exercises(self, obj):
        return self._build_session_exercises_data(obj)['total_exercises']

    def get_total_sets(self, obj):
        return self._build_session_exercises_data(obj)['total_sets']

    def get_total_volume(self, obj):
        return self._build_session_exercises_data(obj)['total_volume']

    def get_exercises(self, obj):
        return self._build_session_exercises_data(obj)['exercises']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)


class PersonalRecordSerializer(serializers.ModelSerializer):
    exercise_name = serializers.CharField(source='exercise.name', read_only=True)

    class Meta:
        model = PersonalRecord
        fields = ('id', 'exercise', 'exercise_name', 'record_type', 'value', 'achieved_at')

