"""Prompt engineering using local Gemma 4 via Ollama."""
import requests
import json
from dataclasses import dataclass
from typing import List, Optional, Tuple
import re


@dataclass
class PromptAnalysis:
    """Analysis of a prompt and improvement suggestions."""

    original_prompt: str
    improved_prompt: str
    issues_found: List[str]
    followup_questions: List[str]
    reasoning: str


class OllamaClient:
    """Lightweight client for Ollama API."""

    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 30):
        """Initialize Ollama client.

        Args:
            base_url: Ollama API base URL (default: localhost:11434).
            timeout: Request timeout in seconds.

        Raises:
            ConnectionError: If Ollama is not available.
        """
        self.base_url = base_url
        self.timeout = timeout
        self._verify_connection()

    def _verify_connection(self) -> None:
        """Verify Ollama is running and Gemma4 is available.

        Raises:
            ConnectionError: If Ollama not running or Gemma4 not available.
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags", timeout=self.timeout
            )
            response.raise_for_status()
            tags = response.json().get("models", [])
            available_models = [m.get("name", "") for m in tags]

            has_gemma = any("gemma" in model.lower() for model in available_models)
            if not has_gemma:
                raise ConnectionError(
                    "Gemma model not found in Ollama. "
                    "Pull a Gemma model first: ollama pull gemma4"
                )
        except requests.RequestException as e:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running: ollama serve"
            ) from e

    def generate(
        self, prompt: str, model: str = "gemma:latest", stream: bool = False
    ) -> str:
        """Generate response from Gemma.

        Args:
            prompt: Input prompt.
            model: Model to use (default: gemma:latest).
            stream: Whether to stream response (not used, kept for compat).

        Returns:
            Generated response text.

        Raises:
            RequestException: If API call fails.
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.7,
        }

        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "").strip()


class PromptEngineer:
    """Engineer and improve prompts using local Gemma."""

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        """Initialize prompt engineer.

        Args:
            ollama_url: Ollama API URL.

        Raises:
            ConnectionError: If Ollama not available.
        """
        self.client = OllamaClient(base_url=ollama_url)
        self.session_context = []

    def improve_prompt(self, prompt: str) -> PromptAnalysis:
        """Improve a prompt with suggestions.

        Args:
            prompt: Original prompt to improve.

        Returns:
            PromptAnalysis with improvements and questions.
        """
        # Clear session context for new analysis
        self.session_context = []

        # First turn: analyze and improve
        analysis_prompt = f"""Analyze this prompt and suggest improvements. Be concise.

Original prompt: "{prompt}"

Provide:
1. Issues (max 3 specific problems)
2. Improved prompt (concrete rewrite)
3. Reasoning (1-2 sentences why it's better)

Format your response as JSON: {{"issues": [...], "improved": "...", "reasoning": "..."}}"""

        response = self.client.generate(analysis_prompt)
        analysis = self._parse_analysis(response)

        # Store in session context for follow-ups
        self.session_context = [
            {"role": "user", "content": analysis_prompt},
            {"role": "assistant", "content": response},
        ]

        return PromptAnalysis(
            original_prompt=prompt,
            improved_prompt=analysis.get("improved", prompt),
            issues_found=analysis.get("issues", []),
            followup_questions=[],
            reasoning=analysis.get("reasoning", ""),
        )

    def ask_followup_questions(
        self, prompt: str, analysis: PromptAnalysis, max_questions: int = 3
    ) -> List[str]:
        """Ask clarifying questions to refine the prompt.

        Args:
            prompt: Original prompt.
            analysis: Previous analysis.
            max_questions: Max questions to ask (default: 3).

        Returns:
            List of clarifying questions.
        """
        if not self.session_context:
            # No prior context, do initial analysis first
            analysis = self.improve_prompt(prompt)

        # Second turn: ask clarifying questions
        questions_prompt = f"""Based on this prompt: "{prompt}"

Ask {max_questions} specific clarifying questions to help the user write a better prompt. Questions should focus on:
- What problem they're solving
- Expected output format
- Constraints or limitations
- Examples of desired output

Format as JSON: {{"questions": ["Q1", "Q2", "Q3"]}}"""

        # Build context from session
        context = self._build_context_for_request(questions_prompt)

        response = self.client.generate(context)
        questions_data = self._parse_json(response)
        questions = questions_data.get("questions", [])[:max_questions]

        # Update session context
        self.session_context.append(
            {"role": "user", "content": questions_prompt}
        )
        self.session_context.append({"role": "assistant", "content": response})

        return questions

    def analyze_vague_prompts(
        self, conversations: List, max_to_analyze: int = 5
    ) -> List[PromptAnalysis]:
        """Analyze and improve vague prompts from conversation history.

        Args:
            conversations: List of Conversation objects.
            max_to_analyze: Max prompts to analyze (memory-efficient).

        Returns:
            List of PromptAnalysis for vague prompts found.
        """
        from src.models import Role
        from src.patterns import PatternDetector

        detector = PatternDetector()
        analyses = []

        # Find vague prompts
        vague_prompts = []
        for conv in conversations:
            for msg in conv.messages:
                if msg.role == Role.USER and detector.is_short_prompt(msg.content):
                    vague_prompts.append(msg.content)
                    if len(vague_prompts) >= max_to_analyze:
                        break
            if len(vague_prompts) >= max_to_analyze:
                break

        # Clear session context between analyses
        for vague_prompt in vague_prompts:
            self.session_context = []  # Fresh context each time
            analysis = self.improve_prompt(vague_prompt)
            analyses.append(analysis)

        return analyses

    def _build_context_for_request(self, new_prompt: str) -> str:
        """Build context string from session history.

        Keeps context small to avoid memory bloat on MacBook.

        Args:
            new_prompt: New prompt to add.

        Returns:
            Context string for Ollama (last ~500 chars of history + new prompt).
        """
        # Keep only recent context (last ~2 turns max)
        recent = self.session_context[-4:] if self.session_context else []

        context_parts = []
        for msg in recent:
            role = msg.get("role", "").capitalize()
            content = msg.get("content", "")
            # Truncate long messages to keep context small
            if len(content) > 200:
                content = content[:200] + "..."
            context_parts.append(f"{role}: {content}")

        context_parts.append(f"User: {new_prompt}")
        return "\n".join(context_parts)

    @staticmethod
    def _parse_analysis(response: str) -> dict:
        """Parse JSON analysis from Gemma response.

        Args:
            response: Gemma's response text.

        Returns:
            Parsed analysis dict with issues, improved, reasoning keys.
        """
        return PromptEngineer._parse_json(response)

    @staticmethod
    def _parse_json(response: str) -> dict:
        """Extract and parse JSON from response text.

        Args:
            response: Response text that may contain JSON.

        Returns:
            Parsed JSON dict, or empty dict if parsing fails.
        """
        try:
            # Try direct parse
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON block
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return {}
