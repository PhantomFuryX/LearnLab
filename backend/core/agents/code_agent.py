"""
Code Agent - generates runnable code examples from research summaries
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.services.llm_service import LLMService
from backend.utils.env_setup import get_logger
from pydantic import BaseModel

logger = get_logger()

class CodeExample(BaseModel):
    """Structured code example output"""
    title: str
    description: str
    language: str
    stack: str  # e.g., "langchain", "pytorch", "tensorflow"
    code: str
    explanation: str
    dependencies: List[str]
    usage_instructions: str
    test_code: Optional[str] = None

class CodeAgent:
    """
    Code Agent generates runnable code examples from research summaries.
    
    Inputs: Research summary
    Outputs: Runnable code with explanations, dependencies, and tests
    """
    
    def __init__(self):
        self.logger = logger
        self.llm = LLMService()
    
    async def generate_code(
        self,
        summary: Dict[str, Any],
        stack: str = "langchain",
        language: str = "python",
        include_tests: bool = True
    ) -> CodeExample:
        """
        Generate code example from a summary.
        
        Args:
            summary: Summary object from SummarizerAgent
            stack: Target stack (langchain, pytorch, tensorflow, vanilla)
            language: Programming language (python, javascript)
            include_tests: Whether to include test code
            
        Returns:
            CodeExample object with runnable code
        """
        prompt = self._build_code_prompt(summary, stack, language, include_tests)
        
        try:
            response = await self.llm.generate(
                prompt=prompt,
                temperature=0.4,  # Slightly higher for creative but correct code
                max_tokens=2000
            )
            
            # Parse response into structured format
            code_text = self._extract_text(response)
            code_example = self._parse_code_response(code_text, stack, language)
            
            self.logger.info(f"Generated code example for: '{summary.get('headline', '')[:50]}...'")
            return code_example
            
        except Exception as e:
            self.logger.error(f"Code generation failed: {e}")
            # Return basic example on failure
            return CodeExample(
                title=summary.get("headline", "Example"),
                description="Code generation failed",
                language=language,
                stack=stack,
                code="# Code generation failed\npass",
                explanation="An error occurred during code generation",
                dependencies=[],
                usage_instructions="N/A"
            )
    
    async def generate_multiple(
        self,
        summaries: List[Dict[str, Any]],
        stack: str = "langchain",
        language: str = "python",
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate code examples for multiple summaries.
        
        Args:
            summaries: List of summary objects
            stack: Target stack
            language: Programming language
            limit: Max number of code examples to generate
            
        Returns:
            List of code examples with metadata
        """
        examples = []
        
        for idx, summary_obj in enumerate(summaries[:limit]):
            summary = summary_obj.get("summary", {})
            original = summary_obj.get("original", {})
            
            try:
                code_example = await self.generate_code(
                    summary=summary,
                    stack=stack,
                    language=language,
                    include_tests=True
                )
                
                examples.append({
                    "summary_ref": summary,
                    "original_ref": original,
                    "code": code_example.model_dump(),
                    "index": idx
                })
            except Exception as e:
                self.logger.error(f"Failed to generate code for summary {idx}: {e}")
                continue
        
        return examples
    
    def _build_code_prompt(
        self, 
        summary: Dict[str, Any], 
        stack: str, 
        language: str,
        include_tests: bool
    ) -> str:
        """Build the code generation prompt."""
        
        headline = summary.get("headline", "")
        tldr = summary.get("tldr", "")
        key_points = summary.get("key_points", [])
        methods = summary.get("methods", [])
        
        points_str = "\n".join(f"- {p}" for p in key_points[:3])
        methods_str = "\n".join(f"- {m}" for m in methods[:3])
        
        stack_guidance = {
            "langchain": "Use LangChain framework with proper chains, agents, and tools",
            "pytorch": "Use PyTorch with proper tensor operations and model definitions",
            "tensorflow": "Use TensorFlow/Keras with proper layers and model compilation",
            "vanilla": "Use vanilla Python with standard libraries only"
        }
        
        return f"""You are an expert {language} developer. Generate a complete, runnable code example based on this research summary.

Research Summary:
Title: {headline}
TL;DR: {tldr}

Key Points:
{points_str}

Methods/Techniques:
{methods_str}

Stack: {stack}
Language: {language}

Requirements:
- {stack_guidance.get(stack, "Use best practices for the chosen stack")}
- Include clear comments explaining each section
- Make it production-ready and follow best practices
- Include proper error handling
- {"Include test cases" if include_tests else "No tests needed"}

Provide the code in this exact format:

TITLE: [A descriptive title for the code example]

DESCRIPTION: [2-3 sentences describing what this code does]

DEPENDENCIES:
- [package1==version]
- [package2==version]
- [package3==version]

CODE:
```{language}
[Your complete, runnable code here with comments]
```

EXPLANATION:
[Detailed explanation of how the code works, step by step]

USAGE:
[Clear instructions on how to run this code]

{"TEST_CODE:" if include_tests else ""}
{"```" + language if include_tests else ""}
{f"[Test code here]" if include_tests else ""}
{"```" if include_tests else ""}

Focus on creating a practical, educational example that demonstrates the key concepts from the research."""

    def _extract_text(self, llm_response: Any) -> str:
        """Extract text from LLM response."""
        if isinstance(llm_response, dict):
            if "choices" in llm_response:
                return llm_response["choices"][0].get("message", {}).get("content", "") or \
                       llm_response["choices"][0].get("text", "")
            if "content" in llm_response:
                return llm_response["content"][0].get("text", "")
        return str(llm_response)
    
    def _parse_code_response(self, text: str, stack: str, language: str) -> CodeExample:
        """Parse LLM response into CodeExample object."""
        lines = text.split('\n')
        
        title = ""
        description = ""
        dependencies = []
        code = ""
        explanation = ""
        usage = ""
        test_code = None
        
        current_section = None
        code_block = False
        test_block = False
        
        for line in lines:
            stripped = line.strip()
            
            # Detect sections
            if stripped.upper().startswith('TITLE:'):
                title = stripped.split(':', 1)[1].strip()
            elif stripped.upper().startswith('DESCRIPTION:'):
                description = stripped.split(':', 1)[1].strip()
                current_section = 'description'
            elif stripped.upper().startswith('DEPENDENCIES:'):
                current_section = 'dependencies'
            elif stripped.upper().startswith('CODE:'):
                current_section = 'code'
            elif stripped.upper().startswith('EXPLANATION:'):
                current_section = 'explanation'
            elif stripped.upper().startswith('USAGE:'):
                current_section = 'usage'
            elif stripped.upper().startswith('TEST_CODE:'):
                current_section = 'test_code'
            elif stripped.startswith('```'):
                # Code block delimiter
                if current_section == 'code' and not code_block:
                    code_block = True
                elif current_section == 'code' and code_block:
                    code_block = False
                    current_section = None
                elif current_section == 'test_code' and not test_block:
                    test_block = True
                elif current_section == 'test_code' and test_block:
                    test_block = False
                    current_section = None
            elif current_section == 'description' and stripped and not stripped.startswith('DEPENDENCIES'):
                description += " " + stripped
            elif current_section == 'dependencies' and stripped.startswith('-'):
                dependencies.append(stripped.lstrip('- ').strip())
            elif current_section == 'code' and code_block:
                code += line + '\n'
            elif current_section == 'explanation' and stripped and not stripped.startswith('USAGE'):
                explanation += stripped + " "
            elif current_section == 'usage' and stripped and not stripped.startswith('TEST_CODE'):
                usage += stripped + " "
            elif current_section == 'test_code' and test_block:
                if test_code is None:
                    test_code = ""
                test_code += line + '\n'
        
        # Fallback: extract code from markdown code blocks if parsing failed
        if not code:
            import re
            code_blocks = re.findall(f'```(?:{language})?\n(.*?)```', text, re.DOTALL)
            if code_blocks:
                code = code_blocks[0]
                if len(code_blocks) > 1:
                    test_code = code_blocks[1]
        
        return CodeExample(
            title=title or "Code Example",
            description=description.strip() or "No description",
            language=language,
            stack=stack,
            code=code.strip() or "# No code generated",
            explanation=explanation.strip() or "No explanation",
            dependencies=dependencies or [],
            usage_instructions=usage.strip() or "Run the code directly",
            test_code=test_code.strip() if test_code else None
        )
