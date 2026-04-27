from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from myapp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/login/', views.LoginAPIView.as_view()),
    path('api/v1/submissions/', views.SubmissionListCreateAPIView.as_view()),
    path('api/v1/submissions/<int:pk>/', views.SubmissionDetailAPIView.as_view()),
    path('api/v1/submissions/<int:pk>/transition/', views.SubmissionTransitionAPIView.as_view()),
    path('api/v1/reviewer/queue/', views.ReviewerQueueAPIView.as_view()),
    path('api/v1/reviewer/dashboard/', views.ReviewerDashboardAPIView.as_view()),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
