import logging
import requests
import json
from app.core.config import settings

logger = logging.getLogger(__name__)

class GroqService:
    """
    Dedicated service for LLM execution using Groq API.
    Handles repository mentor reviews, chat, and explanation modes.
    """
    
    @classmethod
    def generate(
        cls,
        prompt: str,
        system_instruction: str = None,
        history: list[dict] = None,
        temperature: float = 0.0
    ) -> str:
        """
        Executes completions via Groq API.
        """
        if not settings.GROQ_API_KEY:
            logger.error("GROQ_API_KEY is not configured in environment variables.")
            return "[Configuration Error] Groq API Key is missing. Please configure GROQ_API_KEY."

        endpoint = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        # Build messages block
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
            
        if history:
            for msg in history:
                messages.append({"role": msg.get("role"), "content": msg.get("content")})
                
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": settings.GROQ_MODEL,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }

        try:
            res = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=settings.GROQ_TIMEOUT
            )
            
            if res.status_code == 200:
                data = res.json()
                choices = data.get("choices")
                if choices and len(choices) > 0:
                    answer = choices[0].get("message", {}).get("content", "").strip()
                    return answer
                else:
                    logger.warning("Groq API returned an empty choices list.")
                    return "Error: Groq returned no completions choices."
            else:
                err_text = res.text
                logger.error(f"Groq API call failed with code {res.status_code}: {err_text}")
                return f"[API Error] Groq API returned status code {res.status_code}: {err_text}"
        except requests.Timeout:
            logger.error(f"Groq API call timed out after {settings.GROQ_TIMEOUT} seconds.")
            return f"[Timeout Error] Connection to Groq timed out after {settings.GROQ_TIMEOUT} seconds."
        except Exception as e:
            logger.error(f"Failed to query Groq service: {str(e)}")
            return f"[Connection Error] Failed to reach Groq. Error: {str(e)}"

    @classmethod
    def generate_stream(
        cls,
        prompt: str,
        system_instruction: str = None,
        history: list[dict] = None,
        temperature: float = 0.0
    ):
        """
        Queries Groq API with stream=True, yielding tokens as they arrive.
        """
        if not settings.GROQ_API_KEY:
            logger.error("GROQ_API_KEY is not configured in environment variables.")
            yield "[Configuration Error] Groq API Key is missing."
            return

        endpoint = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        # Build messages block
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
            
        if history:
            for msg in history:
                messages.append({"role": msg.get("role"), "content": msg.get("content")})
                
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": settings.GROQ_MODEL,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }

        try:
            res = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=settings.GROQ_TIMEOUT,
                stream=True
            )
            
            if res.status_code == 200:
                for line in res.iter_lines():
                    if not line:
                        continue
                    decoded_line = line.decode("utf-8").strip()
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data_str)
                            choices = chunk_data.get("choices")
                            if choices and len(choices) > 0:
                                delta = choices[0].get("delta", {})
                                token = delta.get("content", "")
                                if token:
                                    yield token
                        except Exception:
                            pass
            else:
                err_text = res.text
                logger.error(f"Groq API stream failed with code {res.status_code}: {err_text}")
                yield f"[API Error] Status {res.status_code}"
        except Exception as e:
            logger.error(f"Failed to query Groq service stream: {str(e)}")
            yield f"[Connection Error] {str(e)}"
