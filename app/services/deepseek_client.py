"""
DeepSeek API Client

DeepSeek uses OpenAI-compatible API, so we use the openai library.

COST OPTIMIZATION:
- Use deepseek-chat model (cheapest)
- Keep prompts short and structured
- Cache results in MongoDB
- Never re-parse the same document

IMPORTANT FOR VIVA:
- AI is used ONLY for: resume parsing, JD parsing, skill extraction
- AI output is STRUCTURED and STORED in database
- The DBMS (PostgreSQL) is the source of truth
"""
from openai import OpenAI
from app.core.config import get_settings
import json

settings = get_settings()


class DeepSeekClient:
    """
    Wrapper for DeepSeek API with cost-optimized methods.
    """
    
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url
        )
        # Use the cheapest model
        self.model = "deepseek-chat"
    
    def _call_api(self, system_prompt: str, user_content: str, max_tokens: int = 1000) -> str:
        """
        Internal method to call DeepSeek API.
        Returns raw text response.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=max_tokens,
            temperature=0.1  # Low temp for consistent structured output
        )
        return response.choices[0].message.content
    
    def _extract_json(self, text: str) -> dict:
        """
        Extract JSON from API response.
        Handles cases where model wraps JSON in markdown code blocks.
        """
        # Remove markdown code blocks if present
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        return json.loads(text.strip())
    
    def parse_resume(self, resume_text: str) -> dict:
        """
        Parse resume text and extract structured data.
        """
        system_prompt = """You are a resume parser. Extract information and return ONLY valid JSON.
Output format:
{
  "name": "string",
  "email": "string or null",
  "phone": "string or null",
  "skills": ["skill1", "skill2"],
  "experience_years": number,
  "education": [{"degree": "string", "field": "string", "institution": "string"}],
  "experience": [{"company": "string", "role": "string", "duration": "string"}]
}
Return ONLY the JSON, no explanation."""

        response = self._call_api(system_prompt, resume_text, max_tokens=800)
        return self._extract_json(response)
    
    def parse_job_description(self, jd_text: str) -> dict:
        """
        Parse job description and extract structured data.
        """
        system_prompt = """You are a job description parser. Extract information and return ONLY valid JSON.
Output format:
{
  "title": "string",
  "required_skills": ["skill1", "skill2"],
  "preferred_skills": ["skill1", "skill2"],
  "min_experience": number,
  "max_experience": number or null,
  "education_required": "string or null"
}
Return ONLY the JSON, no explanation."""

        response = self._call_api(system_prompt, jd_text, max_tokens=500)
        return self._extract_json(response)
    
    def normalize_skills(self, skills: list[str]) -> list[str]:
        """
        Normalize skill names to standard form.
        """
        if not skills:
            return []
        
        system_prompt = """Normalize these skill names to their standard forms.
Return ONLY a JSON array of normalized skills.
Examples: "JS" -> "JavaScript", "ML" -> "Machine Learning", "py" -> "Python"
Return format: ["Skill1", "Skill2"]"""

        skills_text = ", ".join(skills)
        response = self._call_api(system_prompt, skills_text, max_tokens=300)
        return self._extract_json(response)
    
    def test_connection(self) -> bool:
        """Test if DeepSeek API is reachable"""
        try:
            response = self._call_api(
                "You are a test assistant.",
                "Reply with exactly: OK",
                max_tokens=10
            )
            return "OK" in response.upper()
        except Exception as e:
            print(f"DeepSeek connection failed: {e}")
            return False


# Singleton instance
_deepseek_client: DeepSeekClient = None


def get_deepseek_client() -> DeepSeekClient:
    """Get or create DeepSeek client (singleton pattern)"""
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = DeepSeekClient()
    return _deepseek_client