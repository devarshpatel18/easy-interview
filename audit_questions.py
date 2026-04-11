import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Question, ExpertQuestion

def check_questions():
    print("--- Checking Expert Questions ---")
    expert_qs = ExpertQuestion.objects.all()
    count = 0
    for q in expert_qs:
        text = q.question_text.strip()
        if len(text) < 10:
            print(f"ID: {q.id} | Short/Garbage Question: '{text}'")
            count += 1
    if count == 0:
        print("No obviously bad Expert Questions found.")
    else:
        print(f"Total suspicious Expert Questions: {count}")

    print("\n--- Checking Interview Questions ---")
    interview_qs = Question.objects.all()
    count = 0
    for q in interview_qs:
        text = q.question_text.strip()
        if len(text) < 10:
            print(f"ID: {q.id} (Interview ID: {q.interview_id if q.interview else 'N/A'}) | Short/Garbage Question: '{text}'")
            count += 1
    if count == 0:
        print("No obviously bad Interview Questions found.")
    else:
        print(f"Total suspicious Interview Questions: {count}")

if __name__ == "__main__":
    try:
        check_questions()
    except Exception as e:
        print(f"Error checking database: {e}")
