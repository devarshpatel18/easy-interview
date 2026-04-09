import json
import time
import os
import re
import uuid
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Avg, Count, Q, F
from django.urls import path, reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder

from .models import Interview, Question, Answer, SystemSettings, ExpertQuestion, LiveRoom
from .ai_utils import extract_resume_text, generate_questions, evaluate_answer, generate_report

User = get_user_model()


def validate_password_strength(password):
    """Check password has at least 1 uppercase, 1 digit, and 1 special character."""
    errors = []
    if not re.search(r'[A-Z]', password):
        errors.append('at least one uppercase letter')
    if not re.search(r'[0-9]', password):
        errors.append('at least one digit')
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?~`]', password):
        errors.append('at least one special character (!@#$%^&* etc.)')
    return errors


# ============================================
# AUTH VIEWS
# ============================================

def landing_page(request):
    return render(request, "myapp/landing.html")

def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password")
        confirm = request.POST.get("confirm")

        if not username or not email or not password:
            messages.error(request, "All fields are required")
            return redirect("register")

        if password != confirm:
            messages.error(request, "Passwords do not match")
            return redirect("register")

        pwd_errors = validate_password_strength(password)
        if pwd_errors:
            messages.error(request, "Password must contain: " + ", ".join(pwd_errors))
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "This username is already taken")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered")
            return redirect("register")

        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "Registration successful! Please login.")
        return redirect("login")

    return render(request, "myapp/register.html")


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_expert:
            return redirect("expert_dashboard")
        if request.user.is_staff:
            return redirect("admin_dashboard")
        return redirect("home")
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Email not found. Please create an account.")
            return redirect("login")

        user_auth = authenticate(request, username=user.username, password=password)
        if user_auth is not None:
            login(request, user_auth)
            messages.success(request, "Login successful!")
            
            # Smart Redirection based on priority
            if user_auth.is_expert:
                return redirect("expert_dashboard")
            if user_auth.is_staff:
                return redirect("admin_dashboard")
            return redirect("home")
        else:
            messages.error(request, "Incorrect password. Please try again.")
            return redirect("login")

    return render(request, "myapp/login.html")


def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully")
    return redirect("login")


import random
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

# ============================================
# PASSWORD RESET (OTP FLOW)
# ============================================

import threading

def _send_otp_email(subject, message, from_email, recipient_list):
    """Send OTP email in a background thread for instant user response."""
    try:
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
    except Exception:
        pass  # Email failure is logged; user can resend from the verify page

def forgot_password(request):
    if request.user.is_authenticated:
        return redirect("home")
        
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        
        # 1. Validate email format
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Please enter a valid email address.")
            return redirect("forgot_password")
            
        # 2. Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No account found with this email address.")
            return redirect("forgot_password")
            
        # 3. Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        
        # 4. Store in session with expiry timestamp (3 minutes)
        request.session['reset_otp'] = otp
        request.session['reset_email'] = email
        request.session['otp_verified'] = False
        request.session['otp_created_at'] = time.time()
        
        # 5. Send OTP email in background thread (non-blocking)
        subject = "Your Password Reset Code - Easy Interview"
        message = f"Hello {user.username},\n\nYour password reset code is: {otp}\n\nThis code will expire in 3 minutes.\n\nEnter this code on the website to reset your password.\n\nThanks,\nThe Easy Interview Team"
        
        email_thread = threading.Thread(
            target=_send_otp_email,
            args=(subject, message, settings.DEFAULT_FROM_EMAIL, [email]),
            daemon=True,
        )
        email_thread.start()
        
        # Redirect immediately — don't wait for email to finish sending
        messages.success(request, f"Verification code sent to {email}")
        return redirect("verify_otp")
            
    return render(request, "myapp/forgot_password_otp.html")

def verify_otp(request):
    if request.user.is_authenticated:
        return redirect("home")
        
    email = request.session.get('reset_email')
    if not email:
        return redirect("forgot_password")

    # Calculate remaining seconds for countdown timer (3-minute = 180s window)
    otp_created_at = request.session.get('otp_created_at', 0)
    elapsed = time.time() - otp_created_at
    remaining_seconds = max(0, int(180 - elapsed))

    if request.method == "POST":
        user_otp = request.POST.get("otp", "").strip()
        stored_otp = request.session.get('reset_otp')

        # Check expiry first
        if remaining_seconds <= 0:
            # Clear expired OTP
            for key in ['reset_otp', 'reset_email', 'otp_verified', 'otp_created_at']:
                request.session.pop(key, None)
            messages.error(request, "Verification code has expired. Please request a new one.")
            return redirect("forgot_password")
        
        if user_otp == stored_otp:
            request.session['otp_verified'] = True
            messages.success(request, "Code verified! Please set your new password.")
            return redirect("reset_password_otp")
        else:
            messages.error(request, "Invalid verification code. Please try again.")
            return redirect("verify_otp")
            
    return render(request, "myapp/verify_otp.html", {
        'email': email,
        'remaining_seconds': remaining_seconds,
    })

def reset_password_otp(request):
    if request.user.is_authenticated:
        return redirect("home")
        
    if not request.session.get('otp_verified'):
        messages.error(request, "Please verify your email first.")
        return redirect("forgot_password")
        
    email = request.session.get('reset_email')
    
    if request.method == "POST":
        password = request.POST.get("password")
        confirm = request.POST.get("confirm")
        
        if password != confirm:
            messages.error(request, "Passwords do not match")
            return redirect("reset_password_otp")
            
        pwd_errors = validate_password_strength(password)
        if pwd_errors:
            messages.error(request, "Password must contain: " + ", ".join(pwd_errors))
            return redirect("reset_password_otp")
            
        user = User.objects.get(email=email)
        user.set_password(password)
        user.save()
        
        # Clear session
        del request.session['reset_otp']
        del request.session['reset_email']
        del request.session['otp_verified']
        
        messages.success(request, "Password reset successfully! You can now log in.")
        return redirect("login")
        
    return render(request, "myapp/reset_password_otp.html", {'email': email})


# ============================================
# MAIN APP VIEWS
# ============================================

@login_required
def home(request):
    interviews = Interview.objects.filter(user=request.user)
    total_interviews = interviews.count()
    completed_interviews = interviews.filter(is_completed=True).count()

    completed_set = interviews.filter(is_completed=True)
    avg_score = 0
    if completed_set.exists():
        scores = []
        for iv in completed_set:
            if iv.max_score > 0:
                scores.append((iv.total_score / iv.max_score) * 100)
        if scores:
            avg_score = round(sum(scores) / len(scores), 1)

    latest_interview = completed_set.order_by('-completed_at').first()
    has_resume = interviews.filter(resume__isnull=False).exclude(resume='').exists()

    context = {
        'total_interviews': total_interviews,
        'completed_interviews': completed_interviews,
        'avg_score': avg_score,
        'latest_interview': latest_interview,
        'has_resume': has_resume,
    }
    return render(request, "myapp/home.html", context)


@login_required
def resume_view(request):
    """Upload resume (Step 1)."""
    if request.method == "POST":
        resume_file = request.FILES.get("resume")
        if not resume_file:
            # Check if we already have a resume in session or database
            if request.session.get('temp_resume_filename') or Interview.objects.filter(user=request.user, resume__isnull=False).exclude(resume='').exists():
                return redirect("configure_interview")
            
            messages.error(request, "Please upload your resume")
            return redirect("resume")

        # Validation: PDF and 3MB
        if not resume_file.name.lower().endswith('.pdf'):
            messages.error(request, "Resume must be in PDF format.")
            return redirect("resume")
        
        if resume_file.size > 3 * 1024 * 1024:
            messages.error(request, "Resume must be under 3 MB in size.")
            return redirect("resume")

        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'resumes'))
        filename = fs.save(resume_file.name, resume_file)
        request.session['temp_resume_filename'] = filename

        return redirect("configure_interview")

    latest_with_resume = Interview.objects.filter(
        user=request.user, resume__isnull=False
    ).exclude(resume='').order_by('-created_at').first()

    return render(request, "myapp/resume.html", {
        'latest_resume': latest_with_resume,
        'temp_resume_filename': request.session.get('temp_resume_filename'),
    })


@login_required
def configure_interview(request):
    """Configure interview settings (Step 2)."""
    filename = request.session.get('temp_resume_filename')
    latest_with_resume = Interview.objects.filter(
        user=request.user, resume__isnull=False
    ).exclude(resume='').order_by('-created_at').first()
    
    if not filename and not latest_with_resume:
        messages.error(request, "Please upload a resume first.")
        return redirect("resume")

    if request.method == "POST":
        interview_type = request.POST.get("interview_type")
        skills = request.POST.getlist("skills")
        difficulty_level = request.POST.get("difficulty_level", "medium")

        if not interview_type:
            messages.error(request, "Please select an interview type.")
            return redirect("configure_interview")

        if interview_type == 'technical' and not skills:
            messages.error(request, "Please select at least one skill for a Technical Interview.")
            return redirect("configure_interview")

        # For HR interviews, we can default to 'general' or allow empty skills list
        if not skills:
            skills = ['general']

        interview = Interview.objects.create(
            user=request.user,
            interview_type=interview_type,
            skills=','.join(skills),
            difficulty_level=difficulty_level,
        )
        
        if filename:
            interview.resume.name = f"resumes/{filename}"
            if 'temp_resume_filename' in request.session:
                del request.session['temp_resume_filename']
        elif latest_with_resume:
            interview.resume = latest_with_resume.resume
            
        interview.save()

        messages.success(request, "Configuration saved successfully! Click 'Start Interview' to begin.")
        return redirect("home")

    return render(request, "myapp/configure_interview.html", {
        'skill_choices': Interview.SKILL_CHOICES,
        'has_new_upload': bool(filename),
        'latest_resume': latest_with_resume,
    })

@login_required
def view_resume(request):
    """View the latest uploaded resume."""
    latest_with_resume = Interview.objects.filter(
        user=request.user, resume__isnull=False
    ).exclude(resume='').order_by('-created_at').first()
    
    if not latest_with_resume:
        messages.error(request, "No resume found. Please upload one first.")
        return redirect("resume")
        
    return render(request, "myapp/view_resume.html", {
        'resume_url': f"{latest_with_resume.resume.url}?v={int(timezone.now().timestamp())}"
    })

@login_required
def start_interview(request):
    """Start a new interview using the latest uploaded resume."""
    # Look for the absolute latest in-progress interview
    latest_iv = Interview.objects.filter(
        user=request.user, is_completed=False
    ).order_by('-created_at').first()

    if latest_iv and latest_iv.questions.count() > 0:
        # Only resume if the absolute latest session already has questions
        return redirect("interview", interview_id=latest_iv.id)

    latest_with_resume = Interview.objects.filter(
        user=request.user, resume__isnull=False
    ).exclude(resume='').order_by('-created_at').first()

    if not latest_iv and not latest_with_resume:
        messages.warning(request, "Please upload your resume first before starting an interview.")
        return redirect("resume")

    # If we have a latest_iv but it has no questions, use it. Otherwise create new.
    if latest_iv and latest_iv.questions.count() == 0:
        interview = latest_iv
    else:
        interview = Interview.objects.create(
            user=request.user,
            resume=latest_with_resume.resume,
            interview_type=latest_with_resume.interview_type,
            skills=latest_with_resume.skills,
            difficulty_level=latest_with_resume.difficulty_level,
        )

    # Extract resume text
    resume_path = os.path.join(settings.MEDIA_ROOT, str(interview.resume))
    resume_text = extract_resume_text(resume_path)

    # 1. Fetch matching expert questions (Up to 5)
    import random as _random
    expert_qs = list(ExpertQuestion.objects.filter(
        skill__in=skills_list,
        difficulty=interview.difficulty_level,
    ))
    _random.shuffle(expert_qs)
    picked_expert_qs = expert_qs[:5]

    # 2. Add picked expert questions as Question objects
    for idx, eq in enumerate(picked_expert_qs):
        Question.objects.create(
            interview=interview,
            question_text=eq.question_text,
            ideal_answer=eq.ideal_answer or '',
            order=idx + 1,
        )

    # 3. Generate remaining questions using AI (up to total 10)
    needed_ai_count = 10 - len(picked_expert_qs)
    if needed_ai_count > 0:
        questions_data = generate_questions(
            resume_text, 
            interview.interview_type, 
            skills_list, 
            interview.difficulty_level,
            count=needed_ai_count
        )
        
        current_order = len(picked_expert_qs)
        for idx, q_data in enumerate(questions_data):
            current_order += 1
            Question.objects.create(
                interview=interview,
                question_text=q_data.get('question', f'Question {current_order}'),
                ideal_answer=q_data.get('ideal_answer', ''),
                order=current_order,
            )

    return redirect("interview", interview_id=interview.id)


@login_required
def take_interview(request, interview_id):
    """Interview page – shows one question at a time."""
    interview = get_object_or_404(Interview, id=interview_id, user=request.user)

    if interview.is_completed:
        return redirect("result", interview_id=interview.id)

    questions = Question.objects.filter(interview=interview).order_by('order')

    if not questions.exists():
        messages.error(request, "No questions were generated. Please try starting a new interview.")
        return redirect("home")

    # Serialize questions as proper JSON for JavaScript
    questions_list = []
    for q in questions:
        questions_list.append({
            'id': q.id,
            'question_text': q.question_text,
            'order': q.order,
        })

    questions_json = json.dumps(questions_list, cls=DjangoJSONEncoder)

    # Fetch system settings and override timer based on difficulty
    system_settings = SystemSettings.objects.first()
    difficulty_timers = {
        'easy': 30,
        'medium': 20,
        'hard': 10
    }
    
    timer_minutes = difficulty_timers.get(interview.difficulty_level, 25)
    if system_settings and interview.difficulty_level in difficulty_timers:
        system_settings.interview_timer = timer_minutes

    # === TIMER PERSISTENCE: compute remaining seconds ===
    total_seconds = timer_minutes * 60
    now = timezone.now()

    if not interview.started_at:
        # First visit — record start time
        interview.started_at = now
        interview.save(update_fields=['started_at'])
        remaining_seconds = total_seconds
    else:
        elapsed = (now - interview.started_at).total_seconds()
        remaining_seconds = max(0, int(total_seconds - elapsed))

    # If time expired while away, auto-submit
    if remaining_seconds <= 0:
        if not interview.is_completed:
            interview.is_completed = True
            interview.completed_at = now
            interview.save()
            # Create empty answers for unanswered questions
            for question in questions:
                if not Answer.objects.filter(interview=interview, question=question).exists():
                    Answer.objects.create(
                        interview=interview, question=question,
                        user_answer='(No answer provided - time expired)',
                        marks_obtained=0, max_marks=10,
                        feedback='Time expired before this question was answered.'
                    )
            generate_report(interview)
            messages.warning(request, '⏰ Your interview time expired. Here are your results.')
        return redirect("result", interview_id=interview.id)
    # === END TIMER PERSISTENCE ===

    return render(request, "myapp/interview.html", {
        "interview": interview,
        "questions_json": questions_json,
        "total_questions": questions.count(),
        "system_settings": system_settings,
        "remaining_seconds": remaining_seconds,
    })


@login_required
def submit_interview(request, interview_id):
    """Submit all answers and generate AI report."""
    if request.method != "POST":
        return redirect("interview", interview_id=interview_id)

    interview = get_object_or_404(Interview, id=interview_id, user=request.user)

    if interview.is_completed:
        return redirect("result", interview_id=interview.id)

    questions = Question.objects.filter(interview=interview).order_by('order')

    # Process each answer
    for question in questions:
        user_answer = request.POST.get(f"answer_{question.id}", "").strip()
        if not user_answer:
            user_answer = "(No answer provided)"

        # AI evaluation for each answer
        score, feedback = evaluate_answer(
            question.question_text,
            user_answer,
            question.ideal_answer or "",
            interview.interview_type,
        )

        Answer.objects.create(
            interview=interview,
            question=question,
            user_answer=user_answer,
            marks_obtained=score,
            max_marks=10,
            feedback=feedback,
        )

    # Mark as completed
    interview.is_completed = True
    interview.completed_at = timezone.now()
    interview.save()

    # Generate comprehensive AI report (strengths, improvements, summary)
    generate_report(interview)

    messages.success(request, "Interview completed! Here's your AI-generated report.")
    return redirect("result", interview_id=interview.id)


@login_required
def result(request, interview_id):
    """Show AI-generated interview report."""
    # Staff/admin can view any report, regular users only their own
    if request.user.is_staff:
        interview = get_object_or_404(Interview, id=interview_id)
    else:
        interview = get_object_or_404(Interview, id=interview_id, user=request.user)
    answers = Answer.objects.filter(interview=interview).select_related('question').order_by('question__order')

    return render(request, "myapp/result.html", {
        "interview": interview,
        "answers": answers,
    })


@login_required
def retry_interview(request, interview_id=None):
    """Retry interview – uses same resume, generates new questions."""
    if interview_id:
        old_interview = get_object_or_404(Interview, id=interview_id, user=request.user)
        source = old_interview
    else:
        source = Interview.objects.filter(
            user=request.user, resume__isnull=False
        ).exclude(resume='').order_by('-created_at').first()

    if not source:
        messages.warning(request, "Please upload your resume first.")
        return redirect("resume")

    # Create new interview using same resume
    interview = Interview.objects.create(
        user=request.user,
        resume=source.resume,
        interview_type=source.interview_type,
        skills=source.skills,
    )

    # Extract resume and generate fresh questions
    resume_path = os.path.join(settings.MEDIA_ROOT, str(interview.resume))
    resume_text = extract_resume_text(resume_path)
    questions_data = generate_questions(resume_text, interview.interview_type, interview.skills_list)

    for idx, q_data in enumerate(questions_data):
        Question.objects.create(
            interview=interview,
            question_text=q_data.get('question', f'Question {idx + 1}'),
            ideal_answer=q_data.get('ideal_answer', ''),
            order=idx + 1,
        )

    return redirect("interview", interview_id=interview.id)


@login_required
def history_view(request):
    """Interview history."""
    interviews = Interview.objects.filter(user=request.user).order_by("-created_at")

    # Stats for the history page
    completed = interviews.filter(is_completed=True)
    total_all = interviews.count()
    completed_count = completed.count()

    avg_score = 0
    best_score = 0
    if completed.exists():
        scores = []
        for iv in completed:
            if iv.max_score > 0:
                pct = (iv.total_score / iv.max_score) * 100
                scores.append(pct)
        if scores:
            avg_score = round(sum(scores) / len(scores), 1)
            best_score = round(max(scores), 0)

    return render(request, "myapp/history.html", {
        "interviews": interviews,
        "total_all": total_all,
        "completed_count": completed_count,
        "avg_score": avg_score,
        "best_score": best_score,
        "technical_count": interviews.filter(interview_type='technical').count(),
        "hr_count": interviews.filter(interview_type='hr').count(),
    })


@login_required
def profile_view(request):
    all_interviews = Interview.objects.filter(user=request.user)
    completed = all_interviews.filter(is_completed=True)
    total_interviews = completed.count()

    avg_score = 0
    if completed.exists():
        scores = []
        for iv in completed:
            if iv.max_score > 0:
                scores.append((iv.total_score / iv.max_score) * 100)
        if scores:
            avg_score = round(sum(scores) / len(scores), 1)

    # Recent interviews for history
    recent_interviews = completed.order_by('-completed_at')[:5]

    # Best score
    best_interview = None
    best_pct = 0
    for iv in completed:
        pct = iv.score_percentage
        if pct > best_pct:
            best_pct = pct
            best_interview = iv

    # Count by type
    technical_count = completed.filter(interview_type='technical').count()
    hr_count = completed.filter(interview_type='hr').count()

    return render(request, "myapp/profile.html", {
        "user": request.user,
        "total_interviews": total_interviews,
        "average_score": avg_score,
        "recent_interviews": recent_interviews,
        "best_interview": best_interview,
        "best_score": best_pct,
        "technical_count": technical_count,
        "hr_count": hr_count,
        "total_all": all_interviews.count(),
    })


@login_required
def settings_view(request):
    return render(request, "myapp/settings.html")


@login_required
def change_password(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect")
            return redirect("settings")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("settings")

        pwd_errors = validate_password_strength(new_password)
        if pwd_errors:
            messages.error(request, "Password must contain: " + ", ".join(pwd_errors))
            return redirect("settings")

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)
        messages.success(request, "Password changed successfully")
        return redirect("settings")

    return redirect("settings")


@login_required
def delete_account(request):
    if request.method == "POST":
        request.user.delete()
        return redirect("login")
    return redirect("settings")


@login_required
def update_profile(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()

        if username:
            request.user.username = username
        if email:
            request.user.email = email

        # Handle profile photo upload
        profile_photo = request.FILES.get("profile_photo")
        if profile_photo:
            request.user.profile_photo = profile_photo

        # Handle password change
        current_password = request.POST.get("current_password", "").strip()
        new_password = request.POST.get("new_password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        if current_password and new_password:
            if not request.user.check_password(current_password):
                messages.error(request, "Current password is incorrect")
                return redirect("profile")

            if new_password != confirm_password:
                messages.error(request, "New passwords do not match")
                return redirect("profile")

            pwd_errors = validate_password_strength(new_password)
            if pwd_errors:
                messages.error(request, "Password must contain: " + ", ".join(pwd_errors))
                return redirect("profile")

            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Profile and password updated successfully")
            return redirect("profile")

        request.user.save()
        messages.success(request, "Profile updated successfully")
        return redirect("profile")

    return render(request, "myapp/update_profile.html")


# ============================================
# ADMIN VIEWS
# ============================================

def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect("home")

    from datetime import timedelta

    today = timezone.now().date()
    seven_days_ago = timezone.now() - timedelta(days=7)

    total_users = User.objects.filter(is_staff=False).count()
    active_users = User.objects.filter(is_active=True, is_staff=False).count()
    blocked_users = User.objects.filter(is_active=False, is_staff=False).count()
    today_signups = User.objects.filter(date_joined__date=today).count()

    total_interviews = Interview.objects.count()
    completed_interviews = Interview.objects.filter(is_completed=True).count()
    in_progress_interviews = Interview.objects.filter(is_completed=False).count()
    interviews_today = Interview.objects.filter(created_at__date=today).count()
    interviews_this_week = Interview.objects.filter(created_at__gte=seven_days_ago).count()

    completed_qs = Interview.objects.filter(is_completed=True)
    avg_score_raw = completed_qs.aggregate(Avg('total_score'))['total_score__avg'] or 0
    avg_max_raw = completed_qs.aggregate(Avg('max_score'))['max_score__avg'] or 1
    avg_percentage = round((avg_score_raw / avg_max_raw) * 100, 1) if avg_max_raw > 0 else 0

    completion_rate = round((completed_interviews / total_interviews) * 100, 1) if total_interviews > 0 else 0

    technical_count = Interview.objects.filter(interview_type='technical').count()
    hr_count = Interview.objects.filter(interview_type='hr').count()

    # Chart 1: Daily Trends (Last 7 days)
    trends_labels = []
    trends_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        trends_labels.append(day.strftime("%b %d"))
        trends_data.append(Interview.objects.filter(created_at__date=day).count())

    # Chart 2: Score Distribution (Completed interviews)
    score_ranges = {
        'Low (0-40%)': completed_qs.filter(total_score__lt=F('max_score') * 0.4).count(),
        'Mid (40-70%)': completed_qs.filter(total_score__gte=F('max_score') * 0.4, total_score__lt=F('max_score') * 0.7).count(),
        'High (70-100%)': completed_qs.filter(total_score__gte=F('max_score') * 0.7).count()
    }
    score_labels = list(score_ranges.keys())
    score_data = list(score_ranges.values())

    # Recent activity
    recent_interviews = Interview.objects.select_related('user').order_by('-created_at')[:8]

    # Top performers
    top_performers = []
    for iv in completed_qs.select_related('user').order_by('-total_score')[:5]:
        pct = round((iv.total_score / iv.max_score) * 100, 1) if iv.max_score > 0 else 0
        top_performers.append({'user': iv.user, 'score': pct, 'type': iv.get_interview_type_display(), 'date': iv.created_at})

    # Recent users
    recent_users = User.objects.filter(is_staff=False).order_by('-date_joined')[:5]

    context = {
        "total_users": total_users,
        "active_users": active_users,
        "blocked_users": blocked_users,
        "today_signups": today_signups,
        "total_interviews": total_interviews,
        "completed_interviews": completed_interviews,
        "in_progress_interviews": in_progress_interviews,
        "interviews_today": interviews_today,
        "interviews_this_week": interviews_this_week,
        "avg_percentage": avg_percentage,
        "completion_rate": completion_rate,
        "technical_count": technical_count,
        "hr_count": hr_count,
        "trends_labels": trends_labels,
        "trends_data": trends_data,
        "score_labels": score_labels,
        "score_data": score_data,
        "recent_interviews": recent_interviews,
        "top_performers": top_performers,
        "recent_users": recent_users,
    }
    return render(request, "admin/admin_dashboard.html", context)


def manage_users(request):
    if not request.user.is_staff:
        return redirect("home")
    from django.core.paginator import Paginator
    search = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "all")

    users = User.objects.filter(is_staff=False).order_by("-date_joined")

    if search:
        users = users.filter(username__icontains=search) | users.filter(email__icontains=search)

    if status_filter == "active":
        users = users.filter(is_active=True)
    elif status_filter == "blocked":
        users = users.filter(is_active=False)

    paginator = Paginator(users, 10)
    page = request.GET.get("page")
    users = paginator.get_page(page)

    return render(request, "admin/manage_users.html", {
        "users": users,
        "search": search,
        "status_filter": status_filter,
    })


def view_user(request, id):
    if not request.user.is_staff:
        return redirect("home")
    user = get_object_or_404(User, id=id)
    interviews = Interview.objects.filter(user=user).order_by('-created_at')
    completed = interviews.filter(is_completed=True)

    total_interviews = interviews.count()
    completed_count = completed.count()
    technical_count = interviews.filter(interview_type='technical').count()
    hr_count = interviews.filter(interview_type='hr').count()

    avg_score = 0
    if completed_count > 0:
        scores = []
        for iv in completed:
            if iv.max_score > 0:
                scores.append(round((iv.total_score / iv.max_score) * 100, 1))
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    return render(request, "admin/view_user.html", {
        "user_obj": user,
        "interviews": interviews,
        "total_interviews": total_interviews,
        "completed_count": completed_count,
        "technical_count": technical_count,
        "hr_count": hr_count,
        "avg_score": avg_score,
    })


def block_user(request, id):
    if not request.user.is_staff:
        return redirect("home")
    user = get_object_or_404(User, id=id)
    user.is_active = not user.is_active
    user.save()
    return redirect("manage_users")


def delete_user(request, id):
    if not request.user.is_staff:
        return redirect("home")
    user = get_object_or_404(User, id=id)
    user.delete()
    return redirect("manage_users")


def admin_reports(request):
    if not request.user.is_staff:
        return redirect("home")
    from django.core.paginator import Paginator

    type_filter = request.GET.get("type", "all")
    status_filter = request.GET.get("status", "all")

    reports = Interview.objects.select_related("user").all().order_by("-created_at")

    if type_filter == "technical":
        reports = reports.filter(interview_type="technical")
    elif type_filter == "hr":
        reports = reports.filter(interview_type="hr")

    if status_filter == "completed":
        reports = reports.filter(is_completed=True)
    elif status_filter == "in_progress":
        reports = reports.filter(is_completed=False)

    paginator = Paginator(reports, 15)
    page = request.GET.get("page")
    reports = paginator.get_page(page)

    return render(request, "admin/reports.html", {
        "reports": reports,
        "type_filter": type_filter,
        "status_filter": status_filter,
    })


def admin_settings(request):
    if not request.user.is_staff:
        return redirect("home")
    settings_obj, created = SystemSettings.objects.get_or_create(id=1)
    if request.method == "POST":
        settings_obj.allow_registration = 'allow_registration' in request.POST
        settings_obj.interview_timer = request.POST.get("interview_timer", 30)
        settings_obj.maintenance_mode = 'maintenance_mode' in request.POST
        settings_obj.save()
        messages.success(request, "Settings saved successfully!")
    return render(request, "admin/admin_settings.html", {"settings": settings_obj})


def admin_logout(request):
    logout(request)
    return redirect("login")


def admin_view_resume(request, interview_id):
    """Allow admin to view/download a user's resume."""
    if not request.user.is_staff:
        return redirect("home")
    interview = get_object_or_404(Interview, id=interview_id)
    if not interview.resume:
        messages.error(request, "No resume file found for this interview.")
        return redirect("admin_reports")

    file_path = os.path.join(settings.MEDIA_ROOT, str(interview.resume))
    if os.path.exists(file_path):
        from django.http import FileResponse
        return FileResponse(open(file_path, 'rb'), as_attachment=False)
    else:
        messages.error(request, "Resume file not found on disk.")
        return redirect("admin_reports")


# === EXPERT FEATURE ===
# ============================================
# EXPERT QUESTION BANK VIEWS
# ============================================

@login_required
def expert_questions(request):
    """Expert question bank — list, add, edit, delete."""
    if not request.user.is_expert and not request.user.is_staff:
        messages.error(request, "You don't have expert access.")
        return redirect("home")

    # Handle add / edit / delete via POST
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            question_text = request.POST.get("question_text", "").strip()
            ideal_answer = request.POST.get("ideal_answer", "").strip()
            skill = request.POST.get("skill", "general")
            difficulty = request.POST.get("difficulty", "medium")

            if not question_text:
                messages.error(request, "Question text is required.")
            else:
                ExpertQuestion.objects.create(
                    question_text=question_text,
                    ideal_answer=ideal_answer,
                    skill=skill,
                    difficulty=difficulty,
                    created_by=request.user,
                )
                messages.success(request, "Question added successfully!")
            return redirect("expert_questions")

        elif action == "edit":
            eq_id = request.POST.get("eq_id")
            eq = get_object_or_404(ExpertQuestion, id=eq_id)
            # Only creator or admin can edit
            if eq.created_by != request.user and not request.user.is_staff:
                messages.error(request, "You can only edit your own questions.")
                return redirect("expert_questions")

            eq.question_text = request.POST.get("question_text", eq.question_text).strip()
            eq.ideal_answer = request.POST.get("ideal_answer", "").strip()
            eq.skill = request.POST.get("skill", eq.skill)
            eq.difficulty = request.POST.get("difficulty", eq.difficulty)
            eq.save()
            messages.success(request, "Question updated!")
            return redirect("expert_questions")

        elif action == "delete":
            eq_id = request.POST.get("eq_id")
            eq = get_object_or_404(ExpertQuestion, id=eq_id)
            if eq.created_by != request.user and not request.user.is_staff:
                messages.error(request, "You can only delete your own questions.")
                return redirect("expert_questions")
            eq.delete()
            messages.success(request, "Question deleted!")
            return redirect("expert_questions")

    # List questions — experts see their own, admins see all
    if request.user.is_staff:
        questions = ExpertQuestion.objects.all()
    else:
        questions = ExpertQuestion.objects.filter(created_by=request.user)

    return render(request, "myapp/expert_questions.html", {
        "questions": questions,
        "skill_choices": Interview.SKILL_CHOICES,
        "difficulty_choices": Interview.DIFFICULTY_CHOICES,
    })


def toggle_expert(request, id):
    """Admin toggles expert status on a user."""
    if not request.user.is_staff:
        return redirect("home")
    user = get_object_or_404(User, id=id)
    user.is_expert = not user.is_expert
    user.save()
    status = "Expert" if user.is_expert else "Regular User"
    messages.success(request, f"{user.username} is now: {status}")
    return redirect("view_user", id=user.id)

# === END EXPERT FEATURE ===


# === LIVE INTERVIEW FEATURE ===
# ============================================
# LIVE VIDEO INTERVIEW ROOMS (JITSI MEET)
# ============================================

@login_required
def live_rooms(request):
    """List live rooms and create new ones."""
    if request.method == "POST":
        # Only experts and staff can create rooms
        if not request.user.is_expert and not request.user.is_staff:
            messages.error(request, "Only experts can create live rooms.")
            return redirect("live_rooms")

        title = request.POST.get("title", "Live Interview").strip()
        participant_id = request.POST.get("participant_id", "").strip()
        room_name = f"easy-interview-{uuid.uuid4().hex[:12]}"

        room = LiveRoom.objects.create(
            room_name=room_name,
            title=title or "Live Interview",
            created_by=request.user,
        )

        if participant_id:
            try:
                participant = User.objects.get(id=participant_id)
                room.participant = participant
                room.save()
            except User.DoesNotExist:
                pass

        messages.success(request, f"Room '{room.title}' created! Share the link with your candidate.")
        return redirect("join_live_room", room_id=room.id)

    # Show relevant rooms
    if request.user.is_staff or request.user.is_expert:
        # Experts see rooms they created + active rooms they're invited to
        my_rooms = LiveRoom.objects.filter(created_by=request.user)
        invited_rooms = LiveRoom.objects.filter(participant=request.user, is_active=True)
        rooms = (my_rooms | invited_rooms).distinct()
    else:
        # Regular users see rooms they're invited to
        rooms = LiveRoom.objects.filter(participant=request.user, is_active=True)

    # Get all non-staff users for the participant dropdown
    users = User.objects.filter(is_staff=False, is_active=True).exclude(id=request.user.id).order_by('username') if (request.user.is_expert or request.user.is_staff) else []

    return render(request, "myapp/live_rooms.html", {
        "rooms": rooms,
        "users": users,
        "is_expert": request.user.is_expert or request.user.is_staff,
    })


@login_required
def join_live_room(request, room_id):
    """Join a live room — embedded Jitsi Meet."""
    room = get_object_or_404(LiveRoom, id=room_id)

    # Only creator, participant, or admin can join
    if room.created_by != request.user and room.participant != request.user and not request.user.is_staff:
        messages.error(request, "You don't have access to this room.")
        return redirect("live_rooms")

    return render(request, "myapp/live_room.html", {
        "room": room,
    })


@login_required
def end_live_room(request, room_id):
    """End/deactivate a live room."""
    room = get_object_or_404(LiveRoom, id=room_id)
    if room.created_by != request.user and not request.user.is_staff:
        messages.error(request, "Only the room creator can end this room.")
        return redirect("expert_dashboard" if request.user.is_expert else "live_rooms")

    room.is_active = False
    room.save()
    messages.success(request, "Live room ended.")
    
    if request.user.is_expert or request.user.is_staff:
        return redirect("expert_dashboard")
    return redirect("live_rooms")

# === END LIVE INTERVIEW FEATURE ===


# === EXPERT DASHBOARD FEATURE ===
# ============================================
# EXPERT AUTH & DASHBOARD VIEWS
# ============================================

def expert_login_view(request):
    """Login page for experts."""
    if request.user.is_authenticated:
        if request.user.is_staff and not request.user.is_expert:
            return redirect("admin_dashboard")
        if request.user.is_expert or request.user.is_staff:
            return redirect("expert_dashboard")
        return redirect("home")

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Email not found. Please create an expert account.")
            return redirect("expert_login")

        user_auth = authenticate(request, username=user.username, password=password)
        if user_auth is not None:
            if not user_auth.is_expert and not user_auth.is_staff:
                messages.error(request, "This account is not registered as an expert. Please use regular login.")
                return redirect("expert_login")
            login(request, user_auth)
            messages.success(request, "Expert login successful!")
            return redirect("expert_dashboard")
        else:
            messages.error(request, "Incorrect password. Please try again.")
            return redirect("expert_login")

    return render(request, "myapp/expert_login.html")


def expert_register_view(request):
    """Registration page for experts — sets is_expert=True."""
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password")
        confirm = request.POST.get("confirm")

        if not username or not email or not password:
            messages.error(request, "All fields are required")
            return redirect("expert_register")

        if password != confirm:
            messages.error(request, "Passwords do not match")
            return redirect("expert_register")

        pwd_errors = validate_password_strength(password)
        if pwd_errors:
            messages.error(request, "Password must contain: " + ", ".join(pwd_errors))
            return redirect("expert_register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "This username is already taken")
            return redirect("expert_register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered")
            return redirect("expert_register")

        user = User.objects.create_user(username=username, email=email, password=password)
        user.is_expert = True
        user.save()
        messages.success(request, "Expert registration successful! Please login.")
        return redirect("expert_login")

    return render(request, "myapp/expert_register.html")


@login_required
def expert_dashboard(request):
    """Expert dashboard home — stats and quick actions."""
    if not request.user.is_expert and not request.user.is_staff:
        messages.error(request, "You don't have expert access.")
        return redirect("home")

    total_questions = ExpertQuestion.objects.filter(created_by=request.user).count()
    total_rooms = LiveRoom.objects.filter(created_by=request.user).count()
    active_rooms = LiveRoom.objects.filter(created_by=request.user, is_active=True).count()

    return render(request, "expert/expert_dashboard.html", {
        "total_questions": total_questions,
        "total_rooms": total_rooms,
        "active_rooms": active_rooms,
    })


@login_required
def expert_questions_dashboard(request):
    """Expert question bank — rendered inside expert dashboard layout."""
    if not request.user.is_expert and not request.user.is_staff:
        messages.error(request, "You don't have expert access.")
        return redirect("home")

    # Handle add / edit / delete via POST
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            question_text = request.POST.get("question_text", "").strip()
            ideal_answer = request.POST.get("ideal_answer", "").strip()
            skill = request.POST.get("skill", "general")
            difficulty = request.POST.get("difficulty", "medium")

            if not question_text:
                messages.error(request, "Question text is required.")
            else:
                ExpertQuestion.objects.create(
                    question_text=question_text,
                    ideal_answer=ideal_answer,
                    skill=skill,
                    difficulty=difficulty,
                    created_by=request.user,
                )
                messages.success(request, "Question added successfully!")
            return redirect("expert_questions_dashboard")

        elif action == "edit":
            eq_id = request.POST.get("eq_id")
            eq = get_object_or_404(ExpertQuestion, id=eq_id)
            if eq.created_by != request.user and not request.user.is_staff:
                messages.error(request, "You can only edit your own questions.")
                return redirect("expert_questions_dashboard")

            eq.question_text = request.POST.get("question_text", eq.question_text).strip()
            eq.ideal_answer = request.POST.get("ideal_answer", "").strip()
            eq.skill = request.POST.get("skill", eq.skill)
            eq.difficulty = request.POST.get("difficulty", eq.difficulty)
            eq.save()
            messages.success(request, "Question updated!")
            return redirect("expert_questions_dashboard")

        elif action == "delete":
            eq_id = request.POST.get("eq_id")
            eq = get_object_or_404(ExpertQuestion, id=eq_id)
            if eq.created_by != request.user and not request.user.is_staff:
                messages.error(request, "You can only delete your own questions.")
                return redirect("expert_questions_dashboard")
            eq.delete()
            messages.success(request, "Question deleted!")
            return redirect("expert_questions_dashboard")

    questions = ExpertQuestion.objects.filter(created_by=request.user)

    return render(request, "expert/expert_questions.html", {
        "questions": questions,
        "skill_choices": Interview.SKILL_CHOICES,
        "difficulty_choices": Interview.DIFFICULTY_CHOICES,
    })


@login_required
def expert_live_rooms_dashboard(request):
    """Live rooms — rendered inside expert dashboard layout."""
    if not request.user.is_expert and not request.user.is_staff:
        messages.error(request, "You don't have expert access.")
        return redirect("home")

    if request.method == "POST":
        title = request.POST.get("title", "Live Interview").strip()
        participant_id = request.POST.get("participant_id", "").strip()
        room_name = f"easy-interview-{uuid.uuid4().hex[:12]}"

        room = LiveRoom.objects.create(
            room_name=room_name,
            title=title or "Live Interview",
            created_by=request.user,
        )

        if participant_id:
            try:
                participant = User.objects.get(id=participant_id)
                room.participant = participant
                room.save()
            except User.DoesNotExist:
                pass

        messages.success(request, f"Room '{room.title}' created! Share the link with your candidate.")
        return redirect("expert_join_live_room", room_id=room.id)

    my_rooms = LiveRoom.objects.filter(created_by=request.user)
    invited_rooms = LiveRoom.objects.filter(participant=request.user, is_active=True)
    rooms = (my_rooms | invited_rooms).distinct()

    users = User.objects.filter(is_staff=False, is_active=True).exclude(id=request.user.id).order_by('username')

    return render(request, "expert/expert_live_rooms.html", {
        "rooms": rooms,
        "users": users,
    })


@login_required
def expert_join_live_room(request, room_id):
    """Join a live room — rendered inside expert dashboard layout."""
    room = get_object_or_404(LiveRoom, id=room_id)

    if room.created_by != request.user and room.participant != request.user and not request.user.is_staff:
        messages.error(request, "You don't have access to this room.")
        return redirect("expert_live_rooms_dashboard")

    return render(request, "expert/expert_live_room.html", {
        "room": room,
    })


def expert_logout(request):
    """Logout from expert panel."""
    logout(request)
    messages.success(request, "Logged out successfully")
    return redirect("expert_login")

# === EXPERT DASHBOARD: SEND INVITE ===
@login_required
def send_room_invite(request, room_id):
    """Send an email invitation to the candidate for a live room."""
    if not request.user.is_expert and not request.user.is_staff:
        messages.error(request, "Only experts can send invites.")
        return redirect("expert_dashboard")

    room = get_object_or_404(LiveRoom, id=room_id)
    if not room.participant:
        messages.error(request, "No candidate assigned to this room. Please edit the room to add a candidate.")
        return redirect("expert_join_live_room", room_id=room.id)

    if not room.participant.email:
        messages.error(request, "Candidate has no email address associated with their account.")
        return redirect("expert_join_live_room", room_id=room.id)

    # Build join URL
    join_url = request.build_absolute_uri(reverse('join_live_room', args=[room.id]))

    # Send email in background
    subject = f"Interview Invitation: {room.title} - Easy Interview"
    message = f"Hello {room.participant.username},\n\n" \
              f"You have been invited to a live interview session with {request.user.username}.\n\n" \
              f"Room: {room.title}\n" \
              f"Link: {join_url}\n\n" \
              f"Please click the link above or copy-paste it into your browser to join the session.\n\n" \
              f"Thanks,\nThe Easy Interview Team"

    email_thread = threading.Thread(
        target=_send_otp_email,
        args=(subject, message, settings.DEFAULT_FROM_EMAIL, [room.participant.email]),
        daemon=True,
    )
    email_thread.start()

    messages.success(request, f"Invitation link successfully sent to {room.participant.email}")
    return redirect("expert_join_live_room", room_id=room.id)

# === END EXPERT DASHBOARD FEATURE ===


