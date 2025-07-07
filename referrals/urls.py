from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('create/', views.create_code, name='create_code'),
    path('codes/', views.generated_codes, name='generated_codes'),
    path('analytics/<int:code_id>/', views.code_analytics, name='code_analytics'),
    path('delete/<int:code_id>/', views.delete_code, name='delete_code'),
    path('track/', views.track_click, name='track_click'),
    path('accounts/signup/', views.signup, name='signup'),
    path('api/track-signup/', views.track_signup_api, name='track_signup_api'),
]
