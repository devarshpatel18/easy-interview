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
    path('serve-resume/<int:interview_id>/', views.serve_resume, name='serve_resume'),
    path('emergency-admin/', views.emergency_admin, name='emergency_admin'),

    # === EXPERT DASHBOARD FEATURE ===
    path('expert/questions/', views.expert_questions, name='expert_questions'),
    path('toggle-expert/<int:id>/', views.toggle_expert, name='toggle_expert'),

    # === EXPERT NEW DASHBOARD PATHS ===
    path('expert/login/', views.expert_login_view, name='expert_login'),
    path('expert/register/', views.expert_register_view, name='expert_register'),
    path('expert/dashboard/', views.expert_dashboard, name='expert_dashboard'),
    path('expert/dashboard/questions/', views.expert_questions_dashboard, name='expert_questions_dashboard'),
    path('expert/dashboard/live-rooms/', views.expert_live_rooms_dashboard, name='expert_live_rooms_dashboard'),
    path('expert/dashboard/live-room/<int:room_id>/', views.expert_join_live_room, name='expert_join_live_room'),
    path('expert/dashboard/live-room/start/<int:room_id>/', views.start_live_interview, name='start_live_interview'),
    path('expert/dashboard/live-room/send-invite/<int:room_id>/', views.send_room_invite, name='send_room_invite'),
    path('debug-email/', views.debug_email_sync, name='debug_email_sync'),
    path('expert/logout/', views.expert_logout, name='expert_logout'),

    # === LIVE INTERVIEW FEATURE ===
    path('live-rooms/', views.live_rooms, name='live_rooms'),
    path('live-room/<int:room_id>/', views.join_live_room, name='join_live_room'),
    path('end-live-room/<int:room_id>/', views.end_live_room, name='end_live_room'),
]
