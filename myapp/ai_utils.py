"""
AI Utility Functions for Easy Interview
Uses Google Gemini API for question generation, answer evaluation, and report generation.
"""
import json
import re
import requests
import time
from django.conf import settings


GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


def call_gemini(prompt):
    """Call the Gemini API with a text prompt and return the response text."""
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == 'PASTE_YOUR_GEMINI_API_KEY_HERE':
        return None

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 4096,
        }
    }

    try:
        response = requests.post(
            f"{GEMINI_API_URL}?key={api_key}",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None


def extract_resume_text(file_path):
    """Extract text from a .docx or .pdf resume file."""
    text = ""
    file_path = str(file_path)

    if file_path.endswith('.docx'):
        try:
            import docx
            doc = docx.Document(file_path)
            text = '\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
        except Exception as e:
            print(f"Error reading DOCX: {e}")
            text = "Resume uploaded (could not extract text)"

    elif file_path.endswith('.pdf'):
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n'
        except Exception as e:
            print(f"Error reading PDF: {e}")
            text = "Resume uploaded (could not extract text)"
    else:
        text = "Resume uploaded (unsupported format)"

    return text.strip() if text.strip() else "No content extracted from resume"


def extract_skills_from_resume(resume_text):
    """Extract a list of technical and soft skills from resume text using Gemini."""
    if not resume_text or len(resume_text) < 10:
        return []

    prompt = f"""You are an expert HR and Technical Recruiter. Extract a comprehensive list of technical skills, programming languages, frameworks, and core professional competencies from the following resume text.

RESUME TEXT:
{resume_text[:4000]}

RULES:
- Extract specific skills (e.g., 'Python', 'React', 'Project Management', 'System Design').
- Do not extract entire sentences, just keywords or short phrases.
- Return ONLY a valid JSON array of strings.
- If no skills are found, return an empty array [].

Example Output: ["Python", "Django", "REST API", "AWS", "Team Leadership"]"""

    result = call_gemini(prompt)
    if result:
        try:
            cleaned = result.strip()
            cleaned = re.sub(r'^```json\s*', '', cleaned)
            cleaned = re.sub(r'^```\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            skills = json.loads(cleaned)
            if isinstance(skills, list):
                return skills
        except Exception as e:
            print(f"Skill extraction parse error: {e}")
    
    return []


def generate_questions(resume_text, interview_type, skills, difficulty_level='medium', count=10, seen_questions=None):
    """Generate X interview questions based on resume, type, skills, and difficulty using Gemini.
    Uses seen_questions to ensure uniqueness and avoid repeats."""
    if seen_questions is None:
        seen_questions = []

    skills_str = ', '.join(skills) if isinstance(skills, list) else skills
    if not skills_str or not skills_str.strip():
        skills_str = 'programming fundamentals' if interview_type == 'technical' else 'general'

    difficulty_instructions = {
        'easy': 'Generate EASY level questions focused on basic concepts, definitions, and fundamentals. Questions should be suitable for freshers or beginners.',
        'medium': 'Generate MEDIUM level questions that test understanding, application of concepts, and intermediate problem-solving. Mix of conceptual and practical questions.',
        'hard': 'Generate HARD level questions that test deep expertise, complex problem-solving, system design, and advanced concepts. Questions should challenge experienced professionals.',
    }

    diff_instruction = difficulty_instructions.get(difficulty_level, difficulty_instructions['medium'])

    if interview_type == 'technical':
        fallback_source = [
            {"question": f"Explain the core concepts of {skills_str}. What makes it unique?", "ideal_answer": "Explain key features and paradigms."},
            {"question": "Describe a challenging technical project you worked on. What was your approach?", "ideal_answer": "Structured problem-solving approach."},
            {"question": f"What are design patterns you commonly use in {skills_str}?", "ideal_answer": "Common patterns and when to use them."},
            {"question": "How do you handle debugging and troubleshooting in your code?", "ideal_answer": "Systematic debugging approach."},
            {"question": "Explain the concept of scalability. How would you design a scalable system?", "ideal_answer": "Horizontal/vertical scaling, caching, load balancing."},
            {"question": f"What are the best practices for writing clean, maintainable code in {skills_str}?", "ideal_answer": "Naming conventions, modularity, comments, testing."},
            {"question": "Explain how you would optimize a slow database query.", "ideal_answer": "Indexing, query optimization, caching, denormalization."},
            {"question": f"Describe the difference between various data structures and when to use them in {skills_str}.", "ideal_answer": "Arrays, linked lists, trees, hash maps with use cases."},
            {"question": "How do you ensure code quality and prevent bugs in your projects?", "ideal_answer": "Code reviews, unit testing, CI/CD, linting."},
            {"question": "Design a solution for a real-world problem using the skills on your resume.", "ideal_answer": "Structured approach with requirements, architecture, and tradeoffs."},
        ]
    else:
        fallback_source = [
            {"question": "Tell me about yourself and your professional journey.", "ideal_answer": "Concise professional summary."},
            {"question": "Describe a challenging situation at work and how you handled it.", "ideal_answer": "STAR method response."},
            {"question": "Where do you see yourself in 5 years?", "ideal_answer": "Growth-oriented career goals."},
            {"question": "Why should we hire you for this position?", "ideal_answer": "Unique value proposition."},
            {"question": "How do you handle pressure and tight deadlines?", "ideal_answer": "Time management and prioritization strategies."},
            {"question": "Tell me about a time you worked in a team and faced a conflict.", "ideal_answer": "Conflict resolution and collaboration."},
            {"question": "What is your greatest strength and how has it helped you professionally?", "ideal_answer": "Specific strength with real example."},
            {"question": "Describe a situation where you had to learn something new quickly.", "ideal_answer": "Adaptability and learning approach."},
            {"question": "How do you prioritize tasks when you have multiple deadlines?", "ideal_answer": "Organization and time management skills."},
            {"question": "What motivates you to do your best work?", "ideal_answer": "Intrinsic and extrinsic motivation factors."},
        ]

    if not skills:
        return fallback_source[:count]

    seen_context = ""
    if seen_questions:
        seen_context = "CRITICAL - PREVIOUSLY ASKED QUESTIONS (SHUN THESE TOPICS AND TEXTS):\n"
        # Increase context to 30 past questions
        for i, q in enumerate(seen_questions[-30:]):
            seen_context += f"- {q}\n"

    prompt = f"""You are an elite, unpredictable interviewer known for never asking the same thin twice.
    (Diversity Seed: {int(time.time())})

    {seen_context}

RESUME CONTENT:
{resume_text[:4000]}

INTERVIEW TYPE: {interview_type}
SELECTED SKILLS: {skills_str}
DIFFICULTY LEVEL: {difficulty_level.upper()}

RULES FOR TOTAL UNIQUENESS:
- Generate exactly {count} questions.
- {diff_instruction}
- AT LEAST 5 questions MUST be "Grounded" in specific details from the resume (projects, specific years, specific bullet points).
- FORBIDDEN: Do not ask any question listed in the "PREVIOUSLY ASKED QUESTIONS" section.
- TOPIC ROTATION: Look at the previous questions. If they were about syntax, ask about architecture. If they were about backend, ask about testing/deployment. DO NOT stick to one sub-topic.
- BE RANDOM: Change the framing of questions. Instead of "What is X?", ask "In a scenario where X fails, how would you...".
- INCREASE COMPLEXITY: For Technical, avoid definitions; ask for problem-solving or trade-off analysis.

Return ONLY a valid JSON array of exactly {count} objects:
[
    {{"question": "Fresh, unique, scenario-based question...", "ideal_answer": "Expert response guide..."}}
]"""

    result = call_gemini(prompt)

    if interview_type == 'technical':
        fallback_source = [
            {"question": f"Explain the core concepts of {skills_str}. What makes it unique?", "ideal_answer": "Explain key features and paradigms."},
            {"question": "Describe a challenging technical project you worked on. What was your approach?", "ideal_answer": "Structured problem-solving approach."},
            {"question": f"What are design patterns you commonly use in {skills_str}?", "ideal_answer": "Common patterns and when to use them."},
            {"question": "How do you handle debugging and troubleshooting in your code?", "ideal_answer": "Systematic debugging approach."},
            {"question": "Explain the concept of scalability. How would you design a scalable system?", "ideal_answer": "Horizontal/vertical scaling, caching, load balancing."},
            {"question": f"What are the best practices for writing clean, maintainable code in {skills_str}?", "ideal_answer": "Naming conventions, modularity, comments, testing."},
            {"question": "Explain how you would optimize a slow database query.", "ideal_answer": "Indexing, query optimization, caching, denormalization."},
            {"question": f"Describe the difference between various data structures and when to use them in {skills_str}.", "ideal_answer": "Arrays, linked lists, trees, hash maps with use cases."},
            {"question": "How do you ensure code quality and prevent bugs in your projects?", "ideal_answer": "Code reviews, unit testing, CI/CD, linting."},
            {"question": "Design a solution for a real-world problem using the skills on your resume.", "ideal_answer": "Structured approach with requirements, architecture, and tradeoffs."},
        ]
    else:
        fallback_source = [
            {"question": "Tell me about yourself and your professional journey.", "ideal_answer": "Concise professional summary."},
            {"question": "Describe a challenging situation at work and how you handled it.", "ideal_answer": "STAR method response."},
            {"question": "Where do you see yourself in 5 years?", "ideal_answer": "Growth-oriented career goals."},
            {"question": "Why should we hire you for this position?", "ideal_answer": "Unique value proposition."},
            {"question": "How do you handle pressure and tight deadlines?", "ideal_answer": "Time management and prioritization strategies."},
            {"question": "Tell me about a time you worked in a team and faced a conflict.", "ideal_answer": "Conflict resolution and collaboration."},
            {"question": "What is your greatest strength and how has it helped you professionally?", "ideal_answer": "Specific strength with real example."},
            {"question": "Describe a situation where you had to learn something new quickly.", "ideal_answer": "Adaptability and learning approach."},
            {"question": "How do you prioritize tasks when you have multiple deadlines?", "ideal_answer": "Organization and time management skills."},
            {"question": "What motivates you to do your best work?", "ideal_answer": "Intrinsic and extrinsic motivation factors."},
        ]

    if result:
        try:
            # Clean up the response - remove markdown code blocks if present
            cleaned = result.strip()
            cleaned = re.sub(r'^```json\s*', '', cleaned)
            cleaned = re.sub(r'^```\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            questions = json.loads(cleaned)
            if isinstance(questions, list) and len(questions) >= 1 and isinstance(questions[0], dict):
                # Filter for quality: remove any questions that are too short (junk data like 's')
                filtered_questions = [q for q in questions if isinstance(q, dict) and len(q.get('question', '')) >= 10]
                
                valid_questions = filtered_questions[:count]
                if len(valid_questions) < count:
                    # Fill missing questions from fallback
                    offset = len(valid_questions)
                    valid_questions.extend(fallback_source[:count - offset])
                return valid_questions
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            print(f"JSON parse error: {e}")
            # Try to extract JSON if it was buried in text
            match = re.search(r'\[\s*\{.*\}\s*\]', cleaned, re.DOTALL)
            if match:
                try:
                    questions = json.loads(match.group())
                    return questions[:count]
                except: pass
            print(f"Raw response: {result[:500]}")

    return fallback_source[:count]


def evaluate_answer(question_text, user_answer, ideal_answer, interview_type):
    """Evaluate a single answer and return score + feedback using Gemini."""

    # If the answer is empty, skipped, or just placeholder text, give 0 immediately
    clean_answer = user_answer.strip() if user_answer else ''
    if not clean_answer or clean_answer == '(No answer provided)' or len(clean_answer) < 3:
        return 0.0, "No answer was provided. Score: 0/10."

    prompt = f"""You are an expert interview evaluator. Score and provide feedback for this interview answer.

INTERVIEW TYPE: {interview_type}
QUESTION: {question_text}
IDEAL ANSWER OUTLINE: {ideal_answer}
CANDIDATE'S ANSWER: {user_answer}

SCORING CRITERIA (out of 10):
- Relevance to question: 3 points (if the answer is completely unrelated to the question, give 0 for this)
- Depth and completeness: 3 points
- Communication clarity: 2 points
- Technical accuracy (for technical) / Professionalism (for HR): 2 points

IMPORTANT RULES:
- If the answer is COMPLETELY IRRELEVANT to the question (talks about something totally different), give a score of 0 or 1.
- If the answer is very vague or generic with no substance, give a score of 1-2.
- If the answer is partially relevant but lacks depth, give 3-5.
- If the answer is good and relevant, give 6-8.
- If the answer is excellent and comprehensive, give 9-10.
- NEVER give more than 2 points to an answer that does not address the question at all.

Return ONLY a valid JSON object with this exact format (no markdown, no code blocks):
{{"score": 7, "feedback": "Brief constructive feedback here"}}"""

    result = call_gemini(prompt)

    if result:
        try:
            cleaned = result.strip()
            cleaned = re.sub(r'^```json\s*', '', cleaned)
            cleaned = re.sub(r'^```\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            
            # Robust parsing for evaluation
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError:
                match = re.search(r'\{.*\}', cleaned, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                else: raise

            score = min(10, max(0, float(data.get('score', 0))))
            feedback = data.get('feedback', 'Answer evaluated.')
            return score, feedback
        except (json.JSONDecodeError, ValueError, Exception) as e:
            print(f"Eval parse error: {e}")

    # Fallback scoring — much stricter
    word_count = len(clean_answer.split())
    if word_count > 50:
        return 5.0, "Answer has reasonable length but could not be AI-evaluated."
    elif word_count > 15:
        return 3.0, "Short answer with limited detail."
    elif word_count > 5:
        return 1.0, "Very brief answer. Needs much more detail."
    else:
        return 0.0, "Answer too short to evaluate meaningfully."


def generate_report(interview):
    """Generate overall interview report using Gemini."""
    from .models import Answer

    answers = Answer.objects.filter(interview=interview).select_related('question')

    qa_text = ""
    for ans in answers:
        qa_text += f"\nQ: {ans.question.question_text}\n"
        qa_text += f"A: {ans.user_answer}\n"
        qa_text += f"Score: {ans.marks_obtained}/10\n"
        qa_text += f"Feedback: {ans.feedback}\n"

    total = sum(a.marks_obtained for a in answers)
    max_total = sum(a.max_marks for a in answers)

    prompt = f"""You are an expert interview coach. Generate a comprehensive interview performance report.

INTERVIEW TYPE: {interview.interview_type}
SKILLS TESTED: {interview.skills}
TOTAL SCORE: {total}/{max_total}

QUESTIONS AND ANSWERS:
{qa_text}

Generate a detailed report with:
1. STRENGTHS: 3-5 bullet points of what the candidate did well
2. AREAS_OF_IMPROVEMENT: 3-5 bullet points of what needs improvement with specific suggestions
3. SUMMARY: A 3-4 sentence overall assessment and encouragement

Return ONLY a valid JSON object with this exact format (no markdown, no code blocks):
{{
    "strengths": "• Strength 1\\n• Strength 2\\n• Strength 3",
    "areas_of_improvement": "• Area 1\\n• Area 2\\n• Area 3",
    "summary": "Overall assessment summary here."
}}"""

    result = call_gemini(prompt)

    if result:
        try:
            cleaned = result.strip()
            cleaned = re.sub(r'^```json\s*', '', cleaned)
            cleaned = re.sub(r'^```\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            
            # Robust parsing for reports
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError:
                match = re.search(r'\{.*\}', cleaned, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                else: raise

            interview.strengths = data.get('strengths', 'Strengths analyzed based on performance.')
            interview.areas_of_improvement = data.get('areas_of_improvement', 'Improvement points identified.')
            interview.ai_summary = data.get('summary', 'Performance summary generated.')
        except (json.JSONDecodeError, ValueError, Exception) as e:
            print(f"Report parse error: {e}")
            interview.strengths = "• Provided clear responses to technical queries\n• Demonstrated basic domain knowledge"
            interview.areas_of_improvement = "• Elaborate more on past project details\n• Focus on technical depth and problem-solving"
            interview.ai_summary = "Report generation had a minor error, but your performance shows potential. Focus on providing more detailed scenarios in your next attempt."
    else:
        interview.strengths = "• Completed the interview\n• Showed willingness to engage"
        interview.areas_of_improvement = "• Try to provide more detailed answers\n• Practice articulating thoughts clearly"
        interview.ai_summary = "Interview completed. Keep practicing to improve your performance."

    interview.total_score = total
    interview.max_score = max_total
    interview.overall_feedback = f"Score: {total}/{max_total}"
    interview.save()

    return interview
