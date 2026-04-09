from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Interview, Question, Answer, SystemSettings


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    pass


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ("user", "interview_type", "skills", "total_score", "is_completed", "created_at")
    list_filter = ("interview_type", "is_completed")
    search_fields = ("user__username",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("question_text", "interview", "order")
    list_filter = ("interview",)


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("interview", "question", "marks_obtained", "max_marks")


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ("allow_registration", "maintenance_mode", "interview_timer")