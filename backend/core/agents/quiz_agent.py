"""
Quiz Agent - generates quizzes and grades answers based on learning content
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from backend.services.llm_service import LLMService
from backend.utils.env_setup import get_logger
import json

logger = get_logger()

class Question(BaseModel):
    id: str
    type: str = "multiple_choice"  # multiple_choice, short_answer, code
    question: str
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: str
    difficulty: str = "intermediate"

class Quiz(BaseModel):
    title: str
    description: str
    questions: List[Question]
    module_id: Optional[str] = None

class QuizSubmission(BaseModel):
    question_id: str
    user_answer: str

class GradeResult(BaseModel):
    question_id: str
    correct: bool
    feedback: str
    correct_answer: str

class QuizAgent:
    """
    Quiz Agent generates assessments and grades user submissions.
    """
    
    def __init__(self):
        self.logger = logger
        self.llm = LLMService()
    
    async def generate_quiz(
        self, 
        content: str, 
        num_questions: int = 5, 
        difficulty: str = "intermediate",
        topic: str = "General"
    ) -> Quiz:
        """
        Generate a quiz based on provided content (summary, code, or text).
        """
        prompt = f"""You are an expert technical tutor. Create a quiz to test the user's understanding of the following content.

TOPIC: {topic}
DIFFICULTY: {difficulty}
NUM_QUESTIONS: {num_questions}

CONTENT:
{content[:8000]}  # Limit content length

REQUIREMENTS:
- Generate {num_questions} questions.
- Mix of Multiple Choice (mostly) and Short Answer.
- Questions should test understanding, not just memorization.
- Include a clear explanation for the correct answer.
- Return STRICT JSON format.

OUTPUT FORMAT:
{{
  "title": "Quiz Title",
  "description": "Short description",
  "questions": [
    {{
      "id": "q1",
      "type": "multiple_choice",
      "question": "Question text...",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option B",
      "explanation": "Why B is correct...",
      "difficulty": "{difficulty}"
    }}
  ]
}}
"""
        try:
            response = await self.llm.generate(prompt, temperature=0.5, max_tokens=2000)
            text = self._extract_text(response)
            
            # JSON parsing cleanup
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
                
            data = json.loads(text)
            return Quiz(**data)
            
        except Exception as e:
            self.logger.error(f"Quiz generation failed: {e}")
            # Fallback quiz
            return Quiz(
                title=f"Quiz: {topic}",
                description="Quiz generation failed. Please try again.",
                questions=[]
            )

    async def grade_submission(self, submission: List[QuizSubmission], original_quiz: Quiz) -> Dict[str, Any]:
        """
        Grade a list of user answers against the original quiz.
        """
        results = []
        score = 0
        total = len(original_quiz.questions)
        
        # Create lookup for questions
        q_map = {q.id: q for q in original_quiz.questions}
        
        for sub in submission:
            q = q_map.get(sub.question_id)
            if not q:
                continue
                
            is_correct = False
            feedback = q.explanation
            
            if q.type == "multiple_choice":
                # specific logic for MCQs (exact match)
                # Normalize: trim, lowercase for loose comparison if needed, but usually exact for MCQ
                if sub.user_answer.strip().lower() == q.correct_answer.strip().lower():
                    is_correct = True
                # Also check if user sent index (0, 1, 2) vs text
                elif sub.user_answer in q.options and sub.user_answer == q.correct_answer:
                     is_correct = True
            else:
                # For short answer, use LLM to grade fuzzy match
                is_correct, feedback = await self._grade_fuzzy(q.question, q.correct_answer, sub.user_answer)
            
            if is_correct:
                score += 1
                
            results.append(GradeResult(
                question_id=sub.question_id,
                correct=is_correct,
                feedback=feedback,
                correct_answer=q.correct_answer
            ))
            
        return {
            "score": score,
            "total": total,
            "percentage": int((score/total)*100) if total > 0 else 0,
            "results": [r.model_dump() for r in results]
        }

    async def _grade_fuzzy(self, question: str, correct: str, user: str) -> tuple[bool, str]:
        """Use LLM to grade open-ended short answers."""
        prompt = f"""Grade this short answer.
Question: {question}
Correct Answer Key: {correct}
User Answer: {user}

Is the user's answer correct? (True/False)
Provide short feedback.

FORMAT:
CORRECT: True
FEEDBACK: Your feedback here
"""
        try:
            res = await self.llm.generate(prompt, max_tokens=100)
            text = self._extract_text(res)
            
            is_correct = "CORRECT: True" in text or "CORRECT: true" in text
            feedback_line = [l for l in text.split('\n') if l.startswith("FEEDBACK:")]
            feedback = feedback_line[0].replace("FEEDBACK:", "").strip() if feedback_line else "Graded by AI"
            
            return is_correct, feedback
        except Exception:
            return False, "Could not grade automatically"

    def _extract_text(self, llm_response: Any) -> str:
        if isinstance(llm_response, dict):
            if "choices" in llm_response:
                return llm_response["choices"][0].get("message", {}).get("content", "") or \
                       llm_response["choices"][0].get("text", "")
            if "content" in llm_response:
                return llm_response["content"][0].get("text", "")
        return str(llm_response)
