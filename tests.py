from django.contrib.auth.models import User
from django.test import TestCase
from .models import KYCSubmission, UserProfile


class KYCStateMachineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='merchant_test', password='password123')
        UserProfile.objects.update_or_create(user=self.user, defaults={'role': UserProfile.ROLE_MERCHANT})
        self.submission = KYCSubmission.objects.create(user=self.user)

    def test_illegal_transition_raises_value_error(self):
        with self.assertRaises(ValueError) as context:
            self.submission.transition_to(KYCSubmission.STATUS_APPROVED, actor=self.user)

        self.assertIn('Illegal transition', str(context.exception))

    def test_draft_to_submitted_transition_creates_notification(self):
        self.submission.transition_to(KYCSubmission.STATUS_SUBMITTED, actor=self.user)
        self.assertEqual(self.submission.status, KYCSubmission.STATUS_SUBMITTED)
        self.assertIsNotNone(self.submission.submitted_at)
        self.assertEqual(self.user.notifications.count(), 1)

