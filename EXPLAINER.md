# EXPLAINER

## The State Machine
The state machine lives in `myapp/models.py` inside `KYCSubmission.TRANSITIONS` and the `transition_to` method.

Example:
```python
TRANSITIONS = {
    STATUS_DRAFT: [STATUS_SUBMITTED],
    STATUS_SUBMITTED: [STATUS_UNDER_REVIEW],
    STATUS_UNDER_REVIEW: [STATUS_APPROVED, STATUS_REJECTED, STATUS_MORE_INFO],
    STATUS_MORE_INFO: [STATUS_SUBMITTED],
}
```
Illegal transitions are prevented by `KYCSubmission.can_transition` and `transition_to` raising `ValueError`.

## The Upload
File validation is in `myapp/serializers.py`:
```python
def validate_document_file(file):
    if file.size > MAX_UPLOAD_SIZE:
        raise serializers.ValidationError('Each document must be 5 MB or smaller.')
    if content_type and content_type not in ALLOWED_DOCUMENT_TYPES:
        raise serializers.ValidationError('Invalid document type. Allowed: PDF, JPG, PNG.')
```
If someone sends a 50 MB file, the serializer rejects it with `400` and an error message.

## The Queue
The reviewer queue is powered by:
```python
queue = KYCSubmission.objects.filter(
    status__in=[
        KYCSubmission.STATUS_SUBMITTED,
        KYCSubmission.STATUS_UNDER_REVIEW,
        KYCSubmission.STATUS_MORE_INFO,
    ]
).order_by('status_changed_at')
```
This query selects open review items oldest first and keeps the SLA flag dynamic by computing `status_changed_at` age at request time.

## The Auth
Merchant isolation is enforced in `myapp/permissions.py`:
```python
class IsOwnerOrReviewer(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.profile.role == UserProfile.ROLE_REVIEWER:
            return True
        return obj.user == request.user
```
A merchant cannot access another merchant's submission because object-level permission only allows `obj.user == request.user`.

## The AI Audit
An AI suggestion initially proposed using the request user directly for state transitions without role checks. That code would have allowed any authenticated user to approve or reject a submission.

What I replaced it with:
- explicit reviewer-only permission classes for review actions
- merchant-only submit behavior for `draft -> submitted`
- centralized state machine in `KYCSubmission.transition_to`
