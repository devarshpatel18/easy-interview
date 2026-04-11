import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.ai_utils import extract_skills_from_resume, generate_questions

def test_skill_extraction():
    print("\n--- Testing Skill Extraction ---")
    resume_text = """
    John Doe
    Software Engineer with 5 years of experience in Python, Django, and React.
    Developed scalable microservices using AWS and Kubernetes.
    Proficient in SQL and JavaScript.
    """
    skills = extract_skills_from_resume(resume_text)
    print(f"Extracted Skills: {skills}")
    
def test_unique_questions():
    print("\n--- Testing Unique Questions ---")
    resume_text = "Software Engineer with experience in Python and Django."
    seen = ["What is Django?", "How do you handle migrations in Django?"]
    
    print(f"Seen questions: {seen}")
    questions = generate_questions(
        resume_text=resume_text,
        interview_type='technical',
        skills=['django'],
        difficulty_level='medium',
        count=3,
        seen_questions=seen
    )
    
    for i, q in enumerate(questions):
        print(f"Q{i+1}: {q['question']}")
        if q['question'] in seen:
            print("FAILED: Repeated a seen question!")
        else:
            print("PASSED: Unique question.")

if __name__ == "__main__":
    try:
        test_skill_extraction()
        test_unique_questions()
    except Exception as e:
        print(f"Error during verification: {e}")
