from datetime import timedelta
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User

from .models import KYCSubmission, UserProfile
from .serializers import (
    KYCSubmissionSerializer,
    SubmissionTransitionSerializer,
)
from .permissions import TokenAuthentication, IsOwnerOrReviewer, IsReviewer


class LoginAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if not user:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'token': user.profile.api_token,
                'role': user.profile.role,
            }
        )


class SubmissionListCreateAPIView(generics.ListCreateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = KYCSubmissionSerializer

    def get_queryset(self):
        if self.request.user.profile.role == UserProfile.ROLE_REVIEWER:
            return KYCSubmission.objects.all().order_by('status_changed_at')
        return KYCSubmission.objects.filter(user=self.request.user).order_by('status_changed_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SubmissionDetailAPIView(generics.RetrieveUpdateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsOwnerOrReviewer]
    serializer_class = KYCSubmissionSerializer
    queryset = KYCSubmission.objects.all()


class SubmissionTransitionAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsOwnerOrReviewer]

    def post(self, request, pk):
        try:
            submission = KYCSubmission.objects.get(pk=pk)
        except KYCSubmission.DoesNotExist:
            return Response({'error': 'Submission not found'}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, submission)

        serializer = SubmissionTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        status_value = serializer.validated_data['status']
        reason = serializer.validated_data.get('reason', '')

        if status_value == KYCSubmission.STATUS_SUBMITTED:
            if request.user.profile.role != UserProfile.ROLE_MERCHANT:
                return Response({'error': 'Only merchants can submit a draft.'}, status=status.HTTP_403_FORBIDDEN)
            if submission.user != request.user:
                return Response({'error': 'Cannot submit another merchant\'s draft.'}, status=status.HTTP_403_FORBIDDEN)
        else:
            if request.user.profile.role != UserProfile.ROLE_REVIEWER:
                return Response({'error': 'Only reviewers may update review state.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            submission.transition_to(status_value, actor=request.user, reason=reason)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'message': 'Submission status updated.',
                'id': submission.id,
                'status': submission.status,
            }
        )


class ReviewerQueueAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsReviewer]

    def get(self, request):
        queue_statuses = [
            KYCSubmission.STATUS_SUBMITTED,
            KYCSubmission.STATUS_UNDER_REVIEW,
            KYCSubmission.STATUS_MORE_INFO,
        ]
        queue = KYCSubmission.objects.filter(status__in=queue_statuses).order_by('status_changed_at')

        data = [
            {
                'id': item.id,
                'merchant': item.user.username,
                'status': item.status,
                'status_changed_at': item.status_changed_at,
                'at_risk': item.is_at_risk(),
            }
            for item in queue
        ]

        return Response({'queue': data})


class ReviewerDashboardAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsReviewer]

    def get(self, request):
        now = timezone.now()
        queue_items = KYCSubmission.objects.filter(
            status__in=[
                KYCSubmission.STATUS_SUBMITTED,
                KYCSubmission.STATUS_UNDER_REVIEW,
                KYCSubmission.STATUS_MORE_INFO,
            ]
        ).order_by('status_changed_at')

        queue_count = queue_items.count()
        total_wait_seconds = sum(
            (now - item.status_changed_at).total_seconds() for item in queue_items
        )
        avg_time_in_queue_hours = (total_wait_seconds / queue_count / 3600) if queue_count else 0

        decision_window = now - timedelta(days=7)
        decisions = KYCSubmission.objects.filter(
            status__in=[KYCSubmission.STATUS_APPROVED, KYCSubmission.STATUS_REJECTED],
            status_changed_at__gte=decision_window,
        )
        approved_count = decisions.filter(status=KYCSubmission.STATUS_APPROVED).count()
        approval_rate = (approved_count / decisions.count() * 100) if decisions.count() else 0

        return Response(
            {
                'metrics': {
                    'queue_count': queue_count,
                    'avg_time_in_queue_hours': round(avg_time_in_queue_hours, 2),
                    'approval_rate_last_7_days': round(approval_rate, 2),
                },
                'queue': [
                    {
                        'id': item.id,
                        'merchant': item.user.username,
                        'status': item.status,
                        'status_changed_at': item.status_changed_at,
                        'at_risk': item.is_at_risk(),
                    }
                    for item in queue_items
                ],
            }
        )
