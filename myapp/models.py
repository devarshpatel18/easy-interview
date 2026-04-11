from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone


# -------------------------
# CUSTOM USER
# -------------------------
class User(AbstractUser):
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    # === EXPERT FEATURE ===
    is_expert = models.BooleanField(default=False)

    def __str__(self):
        return self.username


# -------------------------
# INTERVIEW
# -------------------------
class Interview(models.Model):

    INTERVIEW_TYPE_CHOICES = [
        ('hr', 'HR Interview'),
        ('technical', 'Technical Interview'),
    ]

    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]

    SKILL_CHOICES = [
        ('python', 'Python'),
        ('java', 'Java'),
        ('javascript', 'JavaScript'),
        ('cpp', 'C++'),
        ('csharp', 'C#'),
        ('sql', 'SQL'),
        ('react', 'React'),
        ('django', 'Django'),
        ('nodejs', 'Node.js'),
        ('html_css', 'HTML/CSS'),
        ('machine_learning', 'Machine Learning'),
        ('data_science', 'Data Science'),
        ('general', 'General'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    interview_type = models.CharField(max_length=20, choices=INTERVIEW_TYPE_CHOICES)
    skills = models.CharField(max_length=255, default='general', help_text="Comma-separated skills")
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='medium')

    resume = models.FileField(upload_to='resumes/', null=True, blank=True)

    total_score = models.FloatField(default=0)
    max_score = models.FloatField(default=50)
    overall_feedback = models.TextField(blank=True, null=True)
    strengths = models.TextField(blank=True, null=True)
    areas_of_improvement = models.TextField(blank=True, null=True)
    ai_summary = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)  # === TIMER PERSISTENCE ===
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.interview_type} - {self.created_at}"

    @property
    def score_percentage(self):
        if self.max_score > 0:
            return round((self.total_score / self.max_score) * 100, 1)
        return 0

    @property
    def skills_list(self):
        return [s.strip() for s in self.skills.split(',') if s.strip()]

    @property
    def skills_display(self):
        skill_map = dict(self.SKILL_CHOICES)
        return ', '.join(skill_map.get(s, s) for s in self.skills_list)


# -------------------------
# QUESTION (AI Generated, linked to Interview)
# -------------------------
class Question(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    question_text = models.TextField()
    ideal_answer = models.TextField(blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.question_text[:80]


# -------------------------
# ANSWER
# -------------------------
class Answer(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    user_answer = models.TextField()

    marks_obtained = models.FloatField(default=0)
    max_marks = models.FloatField(default=10)
    feedback = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.interview.user.username} - Q{self.question.order} - {self.marks_obtained}/{self.max_marks}"


# -------------------------
# ADMIN SETTINGS
# -------------------------
class SystemSettings(models.Model):
    allow_registration = models.BooleanField(default=True)
    interview_timer = models.IntegerField(default=30)
    maintenance_mode = models.BooleanField(default=False)
    interview_duration = models.IntegerField(default=30)
    site_base_url = models.URLField(default='http://127.0.0.1:8000', help_text="The public URL of your site (e.g. https://easy-interview.onrender.com)")

    def __str__(self):
        return "System Settings"


# === EXPERT FEATURE ===
# -------------------------
# EXPERT QUESTION BANK
# -------------------------
class ExpertQuestion(models.Model):
    SKILL_CHOICES = Interview.SKILL_CHOICES
    DIFFICULTY_CHOICES = Interview.DIFFICULTY_CHOICES

    question_text = models.TextField()
    ideal_answer = models.TextField(blank=True, null=True)
    skill = models.CharField(max_length=50, choices=Interview.SKILL_CHOICES, default='general')
    difficulty = models.CharField(max_length=20, choices=Interview.DIFFICULTY_CHOICES, default='medium')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='expert_questions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_skill_display()}] {self.question_text[:60]}"


# === LIVE INTERVIEW FEATURE ===
# -------------------------
# LIVE INTERVIEW ROOMS (Jitsi Meet)
# -------------------------
class LiveRoom(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('completed', 'Completed'),
    ]

    room_name = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=200, default='Live Interview')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_rooms')
    participant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='invited_rooms')
    
    scheduled_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.room_name}"
