from django.utils import timezone
from rest_framework import serializers
from .models import KYCSubmission, NotificationEvent

ALLOWED_DOCUMENT_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
}

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB


def validate_document_file(file):
    if file.size > MAX_UPLOAD_SIZE:
        raise serializers.ValidationError('Each document must be 5 MB or smaller.')

    content_type = getattr(file, 'content_type', None)
    if content_type and content_type not in ALLOWED_DOCUMENT_TYPES:
        raise serializers.ValidationError('Invalid document type. Allowed: PDF, JPG, PNG.')

    extension = file.name.split('.')[-1].lower()
    if extension not in {'pdf', 'jpg', 'jpeg', 'png'}:
        raise serializers.ValidationError('Invalid file extension. Allowed: PDF, JPG, PNG.')

    return file


class KYCSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCSubmission
        fields = [
            'id',
            'name',
            'email',
            'phone',
            'business_name',
            'business_type',
            'expected_monthly_volume_usd',
            'pan_document',
            'aadhaar_document',
            'bank_statement',
            'status',
            'review_reason',
            'created_at',
            'updated_at',
            'status_changed_at',
            'submitted_at',
        ]
        read_only_fields = [
            'status',
            'review_reason',
            'created_at',
            'updated_at',
            'status_changed_at',
            'submitted_at',
        ]

    def validate_pan_document(self, value):
        return validate_document_file(value)

    def validate_aadhaar_document(self, value):
        return validate_document_file(value)

    def validate_bank_statement(self, value):
        return validate_document_file(value)

    def validate(self, data):
        if self.instance and self.instance.status not in {
            KYCSubmission.STATUS_DRAFT,
            KYCSubmission.STATUS_MORE_INFO,
        }:
            raise serializers.ValidationError(
                'Only draft or more_info_requested submissions can be edited.'
            )
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        return KYCSubmission.objects.create(user=request.user, **validated_data)


class SubmissionTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=KYCSubmission.STATUS_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        status = attrs['status']
        reason = attrs.get('reason', '')
        if status in {
            KYCSubmission.STATUS_REJECTED,
            KYCSubmission.STATUS_MORE_INFO,
        } and not reason:
            raise serializers.ValidationError('A reason is required for rejected or more_info_requested.')
        return attrs


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationEvent
        fields = ['id', 'event_type', 'payload', 'timestamp']
