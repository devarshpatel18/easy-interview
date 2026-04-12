from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ---------- AUTH ----------
    path('', views.landing_page, name='landing'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # ---------- PASSWORD RESET (OTP FLOW) ----------
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('reset-password-otp/', views.reset_password_otp, name='reset_password_otp'),

    # ---------- MAIN FEATURES ----------
    path('home/', views.home, name='home'),
    path('resume/', views.resume_view, name='resume'),
    path('view-resume/', views.view_resume, name='view_resume'),
    path('download-resume/', views.download_user_resume, name='download_user_resume'),
    path('configure-interview/', views.configure_interview, name='configure_interview'),
    path('start-interview/', views.start_interview, name='start_interview'),
    path('interview/<int:interview_id>/', views.take_interview, name='interview'),
    path('submit-interview/<int:interview_id>/', views.submit_interview, name='submit_interview'),
    path('result/<int:interview_id>/', views.result, name='result'),
    path('retry-interview/', views.retry_interview, name='retry_interview'),
    path('retry-interview/<int:interview_id>/', views.retry_interview, name='retry_interview_from'),
    path('history/', views.history_view, name='history'),

    # ---------- PROFILE ----------
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('delete-account/', views.delete_account, name='delete_account'),

    # ---------- ADMIN ----------
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('view-user/<int:id>/', views.view_user, name='view_user'),
    path('block-user/<int:id>/', views.block_user, name='block_user'),
    path('delete-user/<int:id>/', views.delete_user, name='delete_user'),
    path('admin-reports/', views.admin_reports, name='admin_reports'),
    path('admin-settings/', views.admin_settings, name='admin_settings'),
    path('admin-logout/', views.admin_logout, name='admin_logout'),
    path('admin-resume/<int:interview_id>/', views.admin_view_resume, name='admin_view_resume'),
]
