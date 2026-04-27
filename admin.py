from django.contrib import admin
from .models import KYCSubmission, NotificationEvent, UserProfile

admin.site.register(KYCSubmission)
admin.site.register(NotificationEvent)
admin.site.register(UserProfile)

