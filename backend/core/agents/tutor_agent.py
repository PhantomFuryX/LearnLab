"""
Tutor Agent - handles interactive teaching, code walkthroughs, and personalized explanations
"""
from typing import List, Dict, Any, Optional
from backend.services.llm_service import LLMService
from backend.utils.env_setup import get_logger
from backend.core.tools.retrieval import RetrievalTool
from backend.services.memory_service import MemoryService
import json

logger = get_logger()

class TutorAgent:
    """
    Tutor Agent provides interactive, step-by-step guidance.
    It uses RAG for context but frames answers pedagogically.
    """
    
    def __init__(self):
        self.logger = logger
        self.llm = LLMService()
        self.retrieval = RetrievalTool()
        self.memory = MemoryService()
        
    async def chat(
        self, 
        message: str, 
        history: List[Dict[str, str]], 
        context_docs: List[str] = None,
        mode: str = "general",  # general, walkthrough, code_review
        user_id: str = "guest"
    ) -> Dict[str, Any]:
        """
        Main chat interface for the tutor.
        """
        
        # 1. Retrieve RAG Context
        if not context_docs:
            retrieval_res = self.retrieval.run("default", message, k=3)
            context_docs = [d.get("text", "") for d in retrieval_res.get("docs", [])]
            
        context_str = "\n\n".join([f"[{i+1}] {doc}" for i, doc in enumerate(context_docs)])
        
        # 2. Retrieve User Memory
        memory_str = self.memory.get_context(user_id, current_topic=self._extract_topic(message))
        
        # 3. Build System Prompt
        system_prompt = self._build_system_prompt(mode)
        
        # 4. Construct Prompt
        full_prompt = f"""
System: {system_prompt}

{memory_str}

Context from Knowledge Base:
{context_str}

Conversation History:
"""
        for msg in history[-5:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            full_prompt += f"{role.title()}: {content}\n"
        
        full_prompt += f"User: {message}\nTutor:"
        
        try:
            # 5. Generate Response
            response = await self.llm.generate(full_prompt, max_tokens=800)
            text = self._extract_text(response)
            
            # 6. Auto-Update Memory (Async/Side-effect)
            if "struggle" in message.lower() or "don't understand" in message.lower():
                self.memory.log_struggle(user_id, self._extract_topic(message), f"Struggled with: {message[:50]}...")
            
            # 7. Generate Exercises (if needed)
            exercises = []
            if mode == "walkthrough" or "exercise" in message.lower():
                exercises = await self._generate_exercises(text)

            return {
                "response": text,
                "mode": mode,
                "suggested_exercises": exercises
            }
        except Exception as e:
            self.logger.error(f"Tutor chat failed: {e}")
            return {"response": "I'm having trouble thinking right now. Can you ask that differently?", "error": str(e)}

    def _build_system_prompt(self, mode: str) -> str:
        base = """You are an expert AI Tutor. Your goal is not just to answer, but to TEACH.
- Explain concepts simply first, then add depth.
- Use analogies.
- If the user is wrong, gently correct them and explain why.
- Cite the provided context using [1], [2] etc.
- Use the 'User Memory' to personalize examples if available.
"""
        
        if mode == "walkthrough":
            base += """
MODE: STEP-BY-STEP WALKTHROUGH
- Break the answer down into numbered steps.
- Explain the 'WHY' behind every step.
- DO NOT dump a wall of text. Keep steps concise.
- After the explanation, ask a checking question to ensure understanding.
"""
        elif mode == "code_review":
            base += """
MODE: CODE REVIEW
- Look for bugs, security issues, and style improvements.
- Explain the fix, don't just paste code.
- Show 'Before' and 'After' examples.
"""
        return base

    async def _generate_exercises(self, context_text: str) -> List[str]:
        """Generate a quick exercise based on the explanation."""
        prompt = f"""Based on this explanation, generate 2 short, practical exercises for the student to try immediately.
        
        Explanation:
        {context_text[:1000]}
        
        Return ONLY a JSON list of strings. Example: ["Try changing X to Y", "Write a function that..."]
        """
        try:
            res = await self.llm.generate(prompt, max_tokens=200)
            txt = self._extract_text(res)
            if "[" in txt and "]" in txt:
                import json
                # extracted json might be wrapped in markdown
                if "```" in txt:
                    txt = txt.split("```")[1].replace("json", "").strip()
                return json.loads(txt)
            return []
        except:
            return ["Explain this concept back to me in your own words", "Try changing one parameter and see what happens"]

    def _extract_topic(self, text: str) -> str:
        # Very naive topic extraction
        words = text.split()
        return words[0] if words else "general"

    def _extract_text(self, llm_response: Any) -> str:
        if isinstance(llm_response, dict):
            if "choices" in llm_response:
                return llm_response["choices"][0].get("message", {}).get("content", "") or \
                       llm_response["choices"][0].get("text", "")
            if "content" in llm_response:
                return llm_response["content"][0].get("text", "")
        return str(llm_response)
