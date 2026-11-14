from datetime import datetime, time
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.management import call_command
from django.db import connection
from django.db.models import (
    Avg,
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    Max,
    Q,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from apps.routines.models import Routine
from .models import WorkoutSession, WorkoutLogExercise, WorkoutSetLog, PersonalRecord
from .serializers import (
    WorkoutSessionListSerializer,
    CompletedWorkoutSessionSerializer,
    WorkoutSessionDetailSerializer,
    WorkoutLogExerciseSerializer,
    WorkoutSetLogSerializer,
    PersonalRecordSerializer,
)


class CompletedSessionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

_MIGRATIONS_CHECKED = False


def _ensure_tracking_migrations():
    global _MIGRATIONS_CHECKED
    if _MIGRATIONS_CHECKED:
        return
    try:
        with connection.cursor() as cursor:
            columns = [
                col.name
                for col in connection.introspection.get_table_description(
                    cursor, WorkoutSession._meta.db_table
                )
            ]
        if (
            'status' not in columns
            or 'routine_id' not in columns
            or 'duration_seconds' not in columns
        ):
            call_command('migrate', 'tracking', interactive=False, verbosity=0)
        _MIGRATIONS_CHECKED = True
    except Exception:
        try:
            call_command('migrate', 'tracking', interactive=False, verbosity=0)
            _MIGRATIONS_CHECKED = True
        except Exception:
            pass


def _parse_query_datetime(raw_value, end_of_day=False):
    if not raw_value:
        return None
    dt = parse_datetime(raw_value)
    if dt is not None:
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    d = parse_date(raw_value)
    if d is not None:
        combined = datetime.combine(d, time.max if end_of_day else time.min)
        return timezone.make_aware(combined, timezone.get_current_timezone())
    return None


class WorkoutSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        _ensure_tracking_migrations()
        super().initial(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkoutSessionListSerializer
        return WorkoutSessionDetailSerializer

    def get_queryset(self):
        return (
            WorkoutSession.objects.filter(user=self.request.user)
            .select_related('routine', 'routine_day__routine')
            .prefetch_related(
                'logged_exercises__logged_sets',
                'logged_exercises__exercise',
                'routine__days__exercises__exercise',
                'routine__days__exercises__target_sets',
                'routine_day__routine__days__exercises__exercise',
                'routine_day__routine__days__exercises__target_sets',
            )
        )

    def perform_create(self, serializer):
        title = serializer.validated_data.get('title', '')
        routine = serializer.validated_data.get('routine')
        if routine is None and title == 'Entrenamiento Móvil':
            serializer.save(user=self.request.user, status='cancelled')
        else:
            serializer.save(user=self.request.user)

    def _get_active_session(self, user):
        return (
            WorkoutSession.objects.filter(
                user=user,
                status='active',
                is_completed=False,
                end_time__isnull=True,
            )
            .exclude(routine__isnull=True, title='Entrenamiento Móvil')
            .select_related('routine', 'routine_day__routine')
            .order_by('-start_time')
            .first()
        )

    @action(detail=False, methods=['post'], url_path='start')
    def start_session(self, request):
        """Inicia una sesión para la rutina indicada o devuelve la sesión activa existente."""
        existing = self._get_active_session(request.user)
        if existing:
            return Response(WorkoutSessionDetailSerializer(existing).data)

        routine_id = request.data.get('routine_id') or request.data.get('routine')
        routine = None
        if routine_id:
            routine = (
                Routine.objects.filter(
                    Q(user=request.user) | Q(is_template=True),
                    pk=routine_id,
                )
                .prefetch_related('days')
                .first()
            )
            if routine is None:
                return Response(
                    {'detail': 'Rutina no encontrada.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

        session = WorkoutSession.objects.create(
            user=request.user,
            routine=routine,
            routine_day=routine.days.first() if routine else None,
            title=routine.title if routine else (request.data.get('title') or 'Entrenamiento'),
            start_time=timezone.now(),
            status='active',
            is_completed=False,
        )
        return Response(
            WorkoutSessionDetailSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )

    def finish_active(self, request):
        """Finaliza la sesión activa del usuario autenticado."""
        session = self._get_active_session(request.user)
        if not session:
            return Response(
                {'detail': 'No hay sesión activa.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        now = timezone.now()
        session.end_time = now
        session.is_completed = True
        session.status = 'completed'
        if session.start_time:
            session.duration_seconds = max(
                1, int((now - session.start_time).total_seconds())
            )
        session.perceived_effort_rpe = request.data.get(
            'perceived_effort_rpe', session.perceived_effort_rpe
        )
        session.notes = request.data.get('notes', session.notes)
        session.save()
        return Response(WorkoutSessionDetailSerializer(session).data)

    @action(detail=True, methods=['post'], url_path='finish')
    def finish_session(self, request, pk=None):
        """Finaliza la sesión actual de entrenamiento."""
        session = self.get_object()
        now = timezone.now()
        session.end_time = now
        session.is_completed = True
        session.status = 'completed'
        if session.start_time:
            session.duration_seconds = max(
                1, int((now - session.start_time).total_seconds())
            )
        session.perceived_effort_rpe = request.data.get('perceived_effort_rpe', session.perceived_effort_rpe)
        session.notes = request.data.get('notes', session.notes)
        session.save()
        return Response(WorkoutSessionDetailSerializer(session).data)

    @action(detail=False, methods=['post'], url_path='cancel')
    def cancel_session(self, request):
        """Descarta la sesión activa del usuario autenticado."""
        session = self._get_active_session(request.user)
        if session:
            session.status = 'cancelled'
            session.end_time = timezone.now()
            session.is_completed = False
            session.save()
            return Response({'status': 'cancelled', 'id': str(session.id)})
        return Response({'status': 'cancelled', 'id': None})

    @action(detail=False, methods=['get'], url_path='active')
    def active_session(self, request):
        """Retorna la sesión activa del usuario autenticado o null."""
        session = self._get_active_session(request.user)
        if not session:
            return Response(None)
        return Response(WorkoutSessionDetailSerializer(session).data)

    def _filter_completed_sessions_qs(self, request):
        qs = WorkoutSession.objects.filter(
            user=request.user,
            status='completed',
            is_completed=True,
        )

        desde_raw = (
            request.query_params.get('desde')
            or request.query_params.get('from')
            or request.query_params.get('start_date')
        )
        hasta_raw = (
            request.query_params.get('hasta')
            or request.query_params.get('to')
            or request.query_params.get('end_date')
        )
        routine_id = (
            request.query_params.get('routine_id')
            or request.query_params.get('routine')
        )

        desde_dt = _parse_query_datetime(desde_raw, end_of_day=False)
        hasta_dt = _parse_query_datetime(hasta_raw, end_of_day=True)

        if desde_dt is not None:
            qs = qs.filter(
                Q(end_time__gte=desde_dt)
                | Q(end_time__isnull=True, start_time__gte=desde_dt)
            )
        if hasta_dt is not None:
            qs = qs.filter(
                Q(end_time__lte=hasta_dt)
                | Q(end_time__isnull=True, start_time__lte=hasta_dt)
            )
        if routine_id:
            qs = qs.filter(
                Q(routine_id=routine_id) | Q(routine_day__routine_id=routine_id)
            )
        return qs

    @action(detail=False, methods=['get'], url_path='history')
    def history(self, request):
        """Retorna las sesiones completadas del usuario paginadas (20/pág.) con métricas agregadas."""
        qs = self._filter_completed_sessions_qs(request)

        totals = qs.aggregate(
            total_sessions=Count('id'),
            total_duration=Coalesce(Sum(Coalesce('duration_seconds', Value(0))), Value(0)),
            avg_duration=Coalesce(
                Avg(Coalesce('duration_seconds', Value(0))), Value(0.0)
            ),
        )

        annotated_qs = (
            qs.select_related('routine', 'routine_day__routine')
            .prefetch_related(
                'routine__days__exercises',
                'routine_day__routine__days__exercises',
            )
            .annotate(
                annotated_exercises=Count('logged_exercises__exercise', distinct=True),
                annotated_sets=Count('logged_exercises__logged_sets', distinct=True),
                annotated_volume=Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F('logged_exercises__logged_sets__weight')
                            * F('logged_exercises__logged_sets__reps'),
                            output_field=FloatField(),
                        )
                    ),
                    Value(0.0),
                ),
            )
            .order_by('-start_time', '-end_time')
        )

        paginator = CompletedSessionPagination()
        page = paginator.paginate_queryset(annotated_qs, request, view=self)
        serializer = CompletedWorkoutSessionSerializer(page, many=True)
        return Response({
            'count': paginator.page.paginator.count,
            'next': paginator.get_next_link(),
            'previous': paginator.get_previous_link(),
            'summary': {
                'total_sessions': int(totals['total_sessions'] or 0),
                'total_duration_seconds': int(totals['total_duration'] or 0),
                'average_duration_seconds': int(
                    round(float(totals['avg_duration'] or 0))
                ),
            },
            'results': serializer.data,
        })

    @action(detail=True, methods=['get'], url_path='detail')
    def session_detail(self, request, pk=None):
        """Retorna el detalle completo de una sesión del usuario autenticado."""
        session = self.get_object()
        return Response(WorkoutSessionDetailSerializer(session).data)

    @action(detail=False, methods=['get'], url_path='routine-summary')
    def routine_summary(self, request):
        """Retorna el resumen agrupado por rutina para las sesiones completadas del usuario."""
        qs = self._filter_completed_sessions_qs(request)
        rows = (
            qs.annotate(
                resolved_routine_id=Coalesce('routine_id', 'routine_day__routine_id'),
                resolved_routine_name=Coalesce(
                    'routine__title', 'routine_day__routine__title', 'title'
                ),
                effective_duration=Coalesce('duration_seconds', Value(0)),
                effective_date=Coalesce('end_time', 'start_time'),
            )
            .values('resolved_routine_id', 'resolved_routine_name')
            .annotate(
                sessions_count=Count('id'),
                total_duration_seconds=Coalesce(Sum('effective_duration'), Value(0)),
                last_session_at=Max('effective_date'),
            )
            .order_by('-last_session_at')
        )

        grouped = {}
        for row in rows:
            rid = str(row['resolved_routine_id']) if row['resolved_routine_id'] else None
            rname = row['resolved_routine_name'] or 'Rutina'
            key = rid or f'unlinked:{rname}'
            sess_count = int(row['sessions_count'] or 0)
            tot_dur = int(row['total_duration_seconds'] or 0)
            last_dt = row['last_session_at']
            if key not in grouped:
                grouped[key] = {
                    'routine_id': rid,
                    'routine_name': rname,
                    'routine': {'id': rid, 'name': rname},
                    'sessions_count': sess_count,
                    'total_duration_seconds': tot_dur,
                    'last_session_at': last_dt,
                }
            else:
                grouped[key]['sessions_count'] += sess_count
                grouped[key]['total_duration_seconds'] += tot_dur
                if last_dt and (
                    grouped[key]['last_session_at'] is None
                    or last_dt > grouped[key]['last_session_at']
                ):
                    grouped[key]['last_session_at'] = last_dt

        summary_list = []
        for entry in grouped.values():
            count = entry['sessions_count']
            total_sec = entry['total_duration_seconds']
            entry['average_duration_seconds'] = (
                int(round(total_sec / count)) if count > 0 else 0
            )
            summary_list.append(entry)

        summary_list.sort(
            key=lambda item: item['last_session_at'].timestamp()
            if item['last_session_at']
            else 0,
            reverse=True,
        )
        return Response(summary_list)


class WorkoutLogExerciseViewSet(viewsets.ModelViewSet):
    serializer_class = WorkoutLogExerciseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WorkoutLogExercise.objects.filter(session__user=self.request.user)


class WorkoutSetLogViewSet(viewsets.ModelViewSet):
    serializer_class = WorkoutSetLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WorkoutSetLog.objects.filter(log_exercise__session__user=self.request.user)

    def perform_create(self, serializer):
        set_log = serializer.save()
        # Verificar y actualizar récord personal (PR)
        exercise = set_log.log_exercise.exercise
        user = self.request.user

        # Máximo peso levantado
        current_max = PersonalRecord.objects.filter(
            user=user, exercise=exercise, record_type='max_weight'
        ).first()

        if not current_max or set_log.weight > current_max.value:
            PersonalRecord.objects.update_or_create(
                user=user,
                exercise=exercise,
                record_type='max_weight',
                defaults={'value': set_log.weight, 'achieved_at': timezone.now()}
            )


class ExerciseProgressionView(APIView):
    """Retorna el historial cronológico de pesos, 1RM estimado y peso corporal del usuario."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, exercise_id):
        from apps.users.models import BodyWeightLog

        set_objs = WorkoutSetLog.objects.filter(
            log_exercise__session__user=request.user,
            log_exercise__exercise_id=exercise_id,
            is_completed=True
        ).order_by('logged_at')

        weight_logs = list(
            BodyWeightLog.objects.filter(user=request.user).order_by('date', 'id').values('date', 'weight')
        )

        def get_body_weight_at(dt):
            target_date = timezone.localtime(dt).date()
            matched = None
            for wl in weight_logs:
                if wl['date'] <= target_date:
                    matched = float(wl['weight'])
                else:
                    break
            if matched is None and request.user.current_weight:
                return float(request.user.current_weight)
            return matched

        history = []
        for s in set_objs:
            bw = get_body_weight_at(s.logged_at)
            e1rm = s.estimated_1rm
            history.append({
                'id': str(s.id),
                'logged_at': s.logged_at,
                'weight': float(s.weight),
                'reps': s.reps,
                'rpe': float(s.rpe) if s.rpe is not None else None,
                'set_type': s.set_type,
                'estimated_1rm': e1rm,
                'body_weight': bw,
                'relative_strength': round(e1rm / bw, 2) if bw else None,
            })

        prs = PersonalRecord.objects.filter(
            user=request.user,
            exercise_id=exercise_id
        )

        return Response({
            'exercise_id': exercise_id,
            'history': history,
            'body_weight_history': weight_logs,
            'records': PersonalRecordSerializer(prs, many=True).data
        })


class Weight1RMProgressView(APIView):
    """Cruza el historial de peso corporal (BodyWeightLog) con el 1RM estimado por fecha."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.users.models import BodyWeightLog

        exercise_id = request.query_params.get('exercise_id')
        sets_qs = WorkoutSetLog.objects.filter(
            log_exercise__session__user=request.user,
            is_completed=True
        ).select_related('log_exercise__exercise').order_by('logged_at')

        if exercise_id:
            sets_qs = sets_qs.filter(log_exercise__exercise_id=exercise_id)

        weight_logs = list(
            BodyWeightLog.objects.filter(user=request.user).order_by('date', 'id').values('id', 'date', 'weight')
        )

        def get_body_weight_at(target_date):
            matched = None
            for wl in weight_logs:
                if wl['date'] <= target_date:
                    matched = float(wl['weight'])
                else:
                    break
            if matched is None and request.user.current_weight:
                return float(request.user.current_weight)
            return matched

        points = []
        for s in sets_qs:
            local_date = timezone.localtime(s.logged_at).date()
            bw = get_body_weight_at(local_date)
            e1rm = s.estimated_1rm
            points.append({
                'set_id': str(s.id),
                'date': local_date,
                'logged_at': s.logged_at,
                'exercise_id': str(s.log_exercise.exercise_id),
                'exercise_name': s.log_exercise.exercise.name,
                'weight': float(s.weight),
                'reps': s.reps,
                'estimated_1rm': e1rm,
                'body_weight': bw,
                'relative_strength': round(e1rm / bw, 2) if bw else None,
            })

        return Response({
            'exercise_id': exercise_id,
            'weight_logs': [
                {'id': wl['id'], 'date': wl['date'], 'weight': float(wl['weight'])}
                for wl in weight_logs
            ],
            'progress': points,
        })


