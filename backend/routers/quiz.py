from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.core.agents.quiz_agent import QuizAgent, QuizSubmission

router = APIRouter()
agent = QuizAgent()

class QuizGenerateRequest(BaseModel):
    topic: str
    content: Optional[str] = None  # Can be summary text or code
    num_questions: int = 5
    difficulty: str = "intermediate"

class QuizGradeRequest(BaseModel):
    quiz: Dict[str, Any]  # The original quiz object
    submissions: List[QuizSubmission]

@router.post("/generate")
async def generate_quiz(req: QuizGenerateRequest):
    """Generate a quiz based on topic and optional content."""
    try:
        # If no content provided, use topic as content prompt
        content = req.content or f"General knowledge about {req.topic}"
        
        quiz = await agent.generate_quiz(
            content=content,
            num_questions=req.num_questions,
            difficulty=req.difficulty,
            topic=req.topic
        )
        return quiz
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/grade")
async def grade_quiz(req: QuizGradeRequest):
    """Grade a user's quiz submission."""
    try:
        # Reconstruct Quiz object from dict
        from backend.core.agents.quiz_agent import Quiz
        quiz_obj = Quiz(**req.quiz)
        
        result = await agent.grade_submission(req.submissions, quiz_obj)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
