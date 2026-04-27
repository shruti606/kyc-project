import uuid
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import JSONField
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class UserProfile(models.Model):
    ROLE_MERCHANT = 'merchant'
    ROLE_REVIEWER = 'reviewer'
    ROLE_CHOICES = [
        (ROLE_MERCHANT, 'Merchant'),
        (ROLE_REVIEWER, 'Reviewer'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MERCHANT)
    api_token = models.CharField(max_length=40, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.api_token:
            self.api_token = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.username} ({self.role})'


class KYCSubmission(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_SUBMITTED = 'submitted'
    STATUS_UNDER_REVIEW = 'under_review'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_MORE_INFO = 'more_info_requested'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_UNDER_REVIEW, 'Under review'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_MORE_INFO, 'More information requested'),
    ]

    TRANSITIONS = {
        STATUS_DRAFT: [STATUS_SUBMITTED],
        STATUS_SUBMITTED: [STATUS_UNDER_REVIEW],
        STATUS_UNDER_REVIEW: [STATUS_APPROVED, STATUS_REJECTED, STATUS_MORE_INFO],
        STATUS_MORE_INFO: [STATUS_SUBMITTED],
    }

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submissions')
    name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    business_name = models.CharField(max_length=100, blank=True)
    business_type = models.CharField(max_length=50, blank=True)
    expected_monthly_volume_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    pan_document = models.FileField(upload_to='documents/pan/', null=True, blank=True)
    aadhaar_document = models.FileField(upload_to='documents/aadhaar/', null=True, blank=True)
    bank_statement = models.FileField(upload_to='documents/bank_statements/', null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    review_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status_changed_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    def can_transition(self, new_status):
        if self.status == new_status:
            return False
        return new_status in self.TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status, actor=None, reason=None):
        if not self.can_transition(new_status):
            raise ValueError(f'Illegal transition from {self.status} to {new_status}')

        self.status = new_status
        self.status_changed_at = timezone.now()

        if new_status == self.STATUS_SUBMITTED:
            self.submitted_at = timezone.now()

        if reason is not None:
            self.review_reason = reason

        self.save(update_fields=['status', 'status_changed_at', 'review_reason', 'submitted_at', 'updated_at'])
        NotificationEvent.objects.create(
            merchant=self.user,
            event_type=f'submission_{new_status}',
            payload={
                'submission_id': self.pk,
                'new_status': new_status,
                'actor': actor.username if actor else None,
                'reason': reason,
            },
        )

    def is_at_risk(self):
        return (
            self.status in {
                self.STATUS_SUBMITTED,
                self.STATUS_UNDER_REVIEW,
                self.STATUS_MORE_INFO,
            }
            and (timezone.now() - self.status_changed_at).total_seconds() > 24 * 3600
        )

    def __str__(self):
        return f'Submission {self.pk} by {self.user.username} ({self.status})'


class NotificationEvent(models.Model):
    merchant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    event_type = models.CharField(max_length=80)
    payload = JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.event_type} for {self.merchant.username} at {self.timestamp.isoformat()}'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
