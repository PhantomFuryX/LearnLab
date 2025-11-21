"""
Planner Agent: Generates structured learning paths & schedules
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
import json
import logging

logger = logging.getLogger(__name__)


class PlannerAgent:
    """
    Generates personalized learning plans with week-by-week breakdowns,
    milestones, quizzes, and resource assignments.
    """

    def __init__(self, llm=None):
        self.llm = llm or ChatOpenAI(model="gpt-4-turbo", temperature=0.7)
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return """You are an expert learning architect and curriculum designer.

Your task is to create highly personalized, structured learning plans.

When given a user's goal, available time, and skill level, you:
1. Break the goal into logical, progressive modules
2. Assign each module to a specific week
3. Estimate realistic hours per module (respect user's available time)
4. Add milestones (projects, quizzes) every 2 weeks
5. Structure difficulty to increase gradually
6. Recommend specific resource types (papers, tutorials, code projects)
7. Suggest quiz topics and learning outcomes for each module

IMPORTANT OUTPUT FORMAT:
Always return ONLY valid JSON (no markdown, no extra text) in this exact structure:

{
  "plan_title": "string",
  "plan_overview": "string (2-3 sentences)",
  "total_hours_estimated": number,
  "difficulty_progression": "string (describe how difficulty increases)",
  "modules": [
    {
      "week": number,
      "module_id": "mod_XXX",
      "title": "string",
      "description": "string",
      "learning_outcomes": ["outcome1", "outcome2"],
      "estimated_hours": number,
      "difficulty": "beginner|intermediate|advanced",
      "resource_types": ["paper", "tutorial", "code_project", "video"],
      "key_topics": ["topic1", "topic2"],
      "prerequisites": ["module_id or 'none'"]
    }
  ],
  "milestones": [
    {
      "week": number,
      "type": "quiz|project|assessment",
      "title": "string",
      "description": "string",
      "deliverables": ["item1"]
    }
  ],
  "quiz_schedule": [
    {
      "week": number,
      "module_ids": ["mod_001"],
      "num_questions": 10,
      "difficulty": "beginner|intermediate|advanced",
      "topics": ["topic1", "topic2"]
    }
  ],
  "success_criteria": ["criterion1"],
  "notes": "string"
}
"""

    def generate_plan(
        self,
        goal: str,
        skill_level: str,
        hours_per_week: int,
        duration_weeks: int,
        topics: List[str],
        past_summaries: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a learning plan.

        Args:
            goal: User's learning goal (e.g., "Master agentic AI in 4 weeks")
            skill_level: "beginner", "intermediate", or "advanced"
            hours_per_week: Available hours per week
            duration_weeks: Total duration in weeks
            topics: List of topics to cover
            past_summaries: List of summaries user has already read

        Returns:
            Dict with plan structure (modules, milestones, quizzes)
        """

        # Build context from past summaries
        past_context = ""
        if past_summaries:
            past_context = "\n\nUser has already learned:\n"
            for summary in past_summaries:
                past_context += f"- {summary.get('title', 'Untitled')}: {summary.get('headline', '')}\n"

        user_message = f"""
Create a {duration_weeks}-week learning plan with these parameters:

GOAL: {goal}
SKILL LEVEL: {skill_level}
AVAILABLE TIME: {hours_per_week} hours/week
TOTAL DURATION: {duration_weeks} weeks
TOPICS: {', '.join(topics)}
TOTAL AVAILABLE HOURS: {hours_per_week * duration_weeks}

Constraints:
- Each week has {hours_per_week} hours available
- Increase difficulty gradually (start at {skill_level}, progress slightly harder)
- Include practical code projects, not just theory
- Schedule 1 quiz every 2 weeks
- Add 1 capstone project in final week
- Mix resource types (papers, tutorials, code projects)
{past_context}

Generate a comprehensive, structured learning plan in JSON format.
"""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message),
        ]

        try:
            response = self.llm.invoke(messages)
            plan_json = response.content.strip()

            # Try to extract JSON if wrapped in markdown
            if "```json" in plan_json:
                plan_json = plan_json.split("```json")[1].split("```")[0].strip()
            elif "```" in plan_json:
                plan_json = plan_json.split("```")[1].split("```")[0].strip()

            plan = json.loads(plan_json)

            # Add metadata
            plan["user_goal"] = goal
            plan["skill_level"] = skill_level
            plan["hours_per_week"] = hours_per_week
            plan["duration_weeks"] = duration_weeks
            plan["created_at"] = datetime.utcnow().isoformat()
            plan["status"] = "active"

            logger.info(f"✓ Generated learning plan: {plan.get('plan_title')}")
            return plan

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse planner agent response: {e}")
            logger.debug(f"Response content: {response.content[:500]}")
            return self._fallback_plan(goal, skill_level, hours_per_week, duration_weeks, topics)

    def _fallback_plan(
        self,
        goal: str,
        skill_level: str,
        hours_per_week: int,
        duration_weeks: int,
        topics: List[str],
    ) -> Dict[str, Any]:
        """Fallback plan if LLM parsing fails"""
        logger.warning("Using fallback plan structure")

        return {
            "plan_title": f"Learning Path: {goal}",
            "plan_overview": f"A structured {duration_weeks}-week plan to achieve: {goal}",
            "total_hours_estimated": hours_per_week * duration_weeks,
            "difficulty_progression": f"Starting at {skill_level}, gradually advancing",
            "modules": self._generate_fallback_modules(topics, duration_weeks, hours_per_week),
            "milestones": self._generate_fallback_milestones(duration_weeks),
            "quiz_schedule": self._generate_fallback_quizzes(duration_weeks),
            "success_criteria": ["Complete all modules", "Score 80%+ on quizzes"],
            "notes": "Fallback plan structure",
            "user_goal": goal,
            "skill_level": skill_level,
            "hours_per_week": hours_per_week,
            "duration_weeks": duration_weeks,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
        }

    def _generate_fallback_modules(self, topics: List[str], weeks: int, hours_per_week: int) -> List[Dict]:
        """Generate fallback modules"""
        modules = []
        module_per_week = max(1, len(topics) // weeks) or 1

        for week in range(1, weeks + 1):
            topic_idx = (week - 1) % len(topics)
            topic = topics[topic_idx]

            modules.append(
                {
                    "week": week,
                    "module_id": f"mod_{week:03d}",
                    "title": f"Week {week}: {topic.title()}",
                    "description": f"Learn and practice {topic}",
                    "learning_outcomes": [f"Understand {topic}", f"Apply {topic} concepts"],
                    "estimated_hours": hours_per_week,
                    "difficulty": "intermediate",
                    "resource_types": ["paper", "tutorial", "code_project"],
                    "key_topics": [topic],
                    "prerequisites": ["none"],
                }
            )

        return modules

    def _generate_fallback_milestones(self, weeks: int) -> List[Dict]:
        """Generate fallback milestones"""
        milestones = []

        if weeks >= 2:
            milestones.append(
                {
                    "week": weeks // 2,
                    "type": "project",
                    "title": "Mid-point Project",
                    "description": "Apply knowledge learned so far",
                    "deliverables": ["working code", "documentation"],
                }
            )

        milestones.append(
            {
                "week": weeks,
                "type": "project",
                "title": "Capstone Project",
                "description": "Comprehensive final project integrating all concepts",
                "deliverables": ["code", "demo", "writeup"],
            }
        )

        return milestones

    def _generate_fallback_quizzes(self, weeks: int) -> List[Dict]:
        """Generate fallback quiz schedule"""
        quizzes = []

        for week in range(2, weeks + 1, 2):
            quizzes.append(
                {
                    "week": week,
                    "module_ids": [f"mod_{week-1:03d}", f"mod_{week:03d}"],
                    "num_questions": 10,
                    "difficulty": "intermediate",
                    "topics": ["core concepts"],
                }
            )

        return quizzes

    def refine_plan(self, plan: Dict[str, Any], feedback: str) -> Dict[str, Any]:
        """
        Refine an existing plan based on user feedback.

        Args:
            plan: The original plan
            feedback: User feedback (e.g., "Too hard, slow down", "Add more projects")

        Returns:
            Updated plan
        """
        user_message = f"""
The user gave feedback on their learning plan:

FEEDBACK: {feedback}

Original plan:
{json.dumps(plan, indent=2)}

Adjust the plan to address the feedback while keeping the same goal and duration.
Return updated plan in JSON format.
"""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message),
        ]

        response = self.llm.invoke(messages)
        refined_plan = json.loads(response.content.strip())

        logger.info(f"✓ Refined learning plan based on feedback")
        return refined_plan
