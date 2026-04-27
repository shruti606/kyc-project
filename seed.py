import os
import django
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User
from myapp.models import UserProfile, KYCSubmission


def create_user(username, password, role):
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_password(password)
        user.save()

    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': role})
    print(f'{role.title()} created: {username}, token={profile.api_token}')
    return user


def main():
    merchant_draft = create_user('merchant_draft', 'password123', UserProfile.ROLE_MERCHANT)
    merchant_review = create_user('merchant_review', 'password123', UserProfile.ROLE_MERCHANT)
    reviewer = create_user('reviewer', 'password123', UserProfile.ROLE_REVIEWER)

    KYCSubmission.objects.create(
        user=merchant_draft,
        name='Draft Merchant',
        email='draft@example.com',
        phone='9999999999',
        business_name='Draft Agency',
        business_type='Marketing',
        expected_monthly_volume_usd=1200,
    )

    KYCSubmission.objects.create(
        user=merchant_review,
        name='Review Merchant',
        email='review@example.com',
        phone='8888888888',
        business_name='Review Agency',
        business_type='Software',
        expected_monthly_volume_usd=7800,
        status=KYCSubmission.STATUS_UNDER_REVIEW,
        submitted_at=timezone.now() - timedelta(hours=26),
        status_changed_at=timezone.now() - timedelta(hours=26),
    )

    print('Seed completed. Use the printed tokens with Authorization: Token <token>.')


if __name__ == '__main__':
    main()
