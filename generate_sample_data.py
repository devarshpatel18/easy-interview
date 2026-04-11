import os
import django
import random
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Interview, User
from django.db import transaction

def generate_sample_data():
    print("--- Starting Sample Data Generation ---")
    
    # Ensure we have some test users
    users = []
    for i in range(1, 6):
        username = f"test_candidate_{i}"
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': f"{username}@example.com", 'is_staff': False}
        )
        if created:
            user.set_password("TestPass123!")
            user.save()
            print(f"Created user: {username}")
        users.append(user)

    interview_types = ['technical', 'hr']
    difficulties = ['easy', 'medium', 'hard']
    
    # 0-40%: 5 interviews
    # 40-70%: 7 interviews
    # 70-100%: 3 interviews
    score_targets = [
        (0.2, 5), # Low
        (0.55, 7), # Mid
        (0.85, 3) # High
    ]

    total_created = 0
    with transaction.atomic():
        for target_pct, count in score_targets:
            for _ in range(count):
                user = random.choice(users)
                max_score = 100
                # Generate a score around the target percentage (+/- 10%)
                variance = random.uniform(-0.1, 0.1)
                actual_pct = max(0, min(1.0, target_pct + variance))
                total_score = int(max_score * actual_pct)
                
                Interview.objects.create(
                    user=user,
                    interview_type=random.choice(interview_types),
                    difficulty_level=random.choice(difficulties),
                    is_completed=True,
                    total_score=total_score,
                    max_score=max_score,
                    completed_at=timezone.now() - timezone.timedelta(days=random.randint(0, 7)),
                    created_at=timezone.now() - timezone.timedelta(days=random.randint(0, 7)),
                    skills="Python, Django, Testing" if random.random() > 0.5 else "Communication, Teamwork",
                    strengths="• Good communication\n• Clear code",
                    areas_of_improvement="• Improve depth\n• Better timing",
                    ai_summary="Successfully completed sample interview."
                )
                total_created += 1

    print(f"--- Finished! Created {total_created} sample completed interviews ---")
    print("You can now refresh the Admin Dashboard to see the populated graph.")

if __name__ == "__main__":
    generate_sample_data()
