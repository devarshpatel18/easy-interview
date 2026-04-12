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
        expected = room.participant.username if room.participant else "the assigned expert"
        messages.error(request, f"Access denied. This room is reserved for {expected}. You are currently logged in as {request.user.username}.")
        return redirect("home")

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

        user = User.objects.filter(email=email).first()
        if not user:
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
    
    # Assigned Interviews for Expert
    assigned_interviews = LiveRoom.objects.filter(
        created_by=request.user, 
        is_active=True
    ).order_by('scheduled_at')

    return render(request, "expert/expert_dashboard.html", {
        "total_questions": total_questions,
        "assigned_interviews": assigned_interviews,
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
        scheduled_at = request.POST.get("scheduled_at")
        room_name = f"easy-interview-{uuid.uuid4().hex[:12]}"

        room = LiveRoom.objects.create(
            room_name=room_name,
            title=title or "Live Interview",
            created_by=request.user,
            scheduled_at=scheduled_at if scheduled_at else None,
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


@login_required
def start_live_interview(request, room_id):
    """Transition a scheduled interview to Live status."""
    room = get_object_or_404(LiveRoom, id=room_id, created_by=request.user)
    room.status = 'live'
    room.save()
    messages.success(request, f"Interview '{room.title}' is now LIVE.")
    return redirect("expert_join_live_room", room_id=room.id)

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
    
    # MOBILE FIX: If using 127.0.0.1 or localhost, replace with actual local IP
    # so the link works when clicked on a mobile phone (same Wi-Fi)
    import socket
    try:
        current_host = request.get_host().split(':')[0]
        if current_host in ['127.0.0.1', 'localhost']:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80)) # Doesn't actually send data
            local_ip = s.getsockname()[0]
            s.close()
            join_url = join_url.replace(current_host, local_ip)
    except Exception:
        pass

    # Format date for email
    scheduled_time = room.scheduled_at.strftime("%B %d, %Y at %I:%M %p") if room.scheduled_at else "TBD"

    # Send email in background
    subject = f"Interview Invitation: {room.title} - Easy Interview"
    message = f"Hello {room.participant.username},\n\n" \
              f"You have been invited to a live interview session.\n\n" \
              f"Interviewer: {request.user.username}\n" \
              f"Interview Title: {room.title}\n" \
              f"Scheduled Date & Time: {scheduled_time}\n" \
              f"Unique Join Link: {join_url}\n\n" \
              f"Please click the link above at the scheduled time to join the session.\n\n" \
              f"Best regards,\nThe Easy Interview Team"

    email_thread = threading.Thread(
        target=_send_otp_email,
        args=(subject, message, settings.DEFAULT_FROM_EMAIL, [room.participant.email]),
        daemon=True,
    )
    email_thread.start()

    messages.success(request, f"Invitation link successfully sent to {room.participant.email}")
    return redirect("expert_join_live_room", room_id=room.id)

# === END EXPERT DASHBOARD FEATURE ===


