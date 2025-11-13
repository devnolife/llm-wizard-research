"""
GLM-4.6 Interface for Ollama Integration

This module provides a comprehensive interface for interacting with the GLM-4.6 model
through Ollama, including prompt management, streaming support, and error handling.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Generator, Union
from dataclasses import dataclass
import time

try:
    import ollama
except ImportError:
    raise ImportError("ollama package not installed. Run: pip install ollama")

from loguru import logger


@dataclass
class ModelConfig:
    """Configuration for GLM-4.6 model"""
    model_name: str = "glm-4.6:cloud"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 2048
    timeout: int = 120
    num_ctx: int = 4096  # Context window size


@dataclass
class ChatMessage:
    """Represents a chat message"""
    role: str  # 'system', 'user', or 'assistant'
    content: str


class PromptTemplate:
    """Manages prompt templates for different tasks"""
    
    RESEARCH_ANALYSIS = """You are an expert research analyst. Analyze the following research paper content and provide insights:

Paper Content:
{content}

Focus on:
1. Main contributions and findings
2. Methodologies used
3. Key citations and related work
4. Potential research gaps

Provide a comprehensive analysis:"""

    GAP_DETECTION = """You are a research gap detection specialist. Based on the following research context, identify potential research gaps:

Research Context:
{context}

Papers Reviewed:
{papers}

Identify:
1. Unexplored areas
2. Contradictions or inconsistencies
3. Methodological gaps
4. Application gaps

List the top research gaps:"""

    RECOMMENDATION = """You are a research recommendation assistant. Based on the user's query and available papers, provide relevant recommendations:

User Query: {query}

Available Papers:
{papers}

Provide:
1. Top {top_k} most relevant papers
2. Relevance explanation for each
3. Suggested reading order
4. Additional research directions

Recommendations:"""

    SUMMARIZATION = """Summarize the following research paper concisely:

Title: {title}
Content: {content}

Provide a summary covering:
1. Problem statement
2. Approach/methodology
3. Key results
4. Significance

Summary:"""

    @classmethod
    def format(cls, template_name: str, **kwargs) -> str:
        """Format a template with given parameters"""
        template = getattr(cls, template_name.upper(), None)
        if template is None:
            raise ValueError(f"Template '{template_name}' not found")
        return template.format(**kwargs)


class GLMInterface:
    """
    Interface for interacting with GLM-4.6 model through Ollama
    
    Features:
    - Connection management and health checks
    - Prompt template management
    - Streaming and non-streaming responses
    - Token counting and usage tracking
    - Error handling and retries
    """
    
    def __init__(self, config: Optional[ModelConfig] = None):
        """
        Initialize GLM interface
        
        Args:
            config: Model configuration (uses defaults if not provided)
        """
        self.config = config or ModelConfig()
        self.client = ollama.Client(host=self.config.base_url)
        self.conversation_history: List[ChatMessage] = []
        
        logger.info(f"Initialized GLM Interface with model: {self.config.model_name}")
        logger.info(f"Ollama base URL: {self.config.base_url}")
    
    def health_check(self) -> bool:
        """
        Check if Ollama server and model are available
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # List available models
            models = self.client.list()
            model_names = [m['name'] for m in models.get('models', [])]
            
            if self.config.model_name not in model_names:
                logger.warning(f"Model {self.config.model_name} not found. Available models: {model_names}")
                return False
            
            logger.info(f"Health check passed. Model {self.config.model_name} is available.")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Union[str, Generator[str, None, None]]:
        """
        Generate a response from GLM-4.6
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt to set context
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stream: Whether to stream the response
            
        Returns:
            Generated text or generator for streaming
        """
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add user prompt
        messages.append({"role": "user", "content": prompt})
        
        options = {
            "temperature": temperature or self.config.temperature,
            "num_predict": max_tokens or self.config.max_tokens,
            "top_p": self.config.top_p,
            "num_ctx": self.config.num_ctx,
        }
        
        try:
            if stream:
                return self._generate_stream(messages, options)
            else:
                return self._generate_complete(messages, options)
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
    
    def _generate_complete(self, messages: List[Dict], options: Dict) -> str:
        """Generate complete response (non-streaming)"""
        start_time = time.time()
        
        response = self.client.chat(
            model=self.config.model_name,
            messages=messages,
            options=options,
            stream=False
        )
        
        elapsed = time.time() - start_time
        content = response['message']['content']
        
        # Log usage stats
        if 'eval_count' in response:
            tokens = response['eval_count']
            logger.info(f"Generated {tokens} tokens in {elapsed:.2f}s ({tokens/elapsed:.1f} tokens/s)")
        
        return content
    
    def _generate_stream(self, messages: List[Dict], options: Dict) -> Generator[str, None, None]:
        """Generate streaming response"""
        try:
            stream = self.client.chat(
                model=self.config.model_name,
                messages=messages,
                options=options,
                stream=True
            )
            
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            raise
    
    def chat(
        self,
        message: str,
        role: str = "user",
        use_history: bool = True,
        max_history: int = 10
    ) -> str:
        """
        Chat with conversation history
        
        Args:
            message: User message
            role: Message role ('user' or 'system')
            use_history: Whether to include conversation history
            max_history: Maximum number of history messages to include
            
        Returns:
            Assistant's response
        """
        # Add user message to history
        self.conversation_history.append(ChatMessage(role=role, content=message))
        
        # Prepare messages for API
        messages = []
        if use_history:
            # Use last N messages
            history_to_use = self.conversation_history[-max_history:]
            messages = [
                {"role": msg.role, "content": msg.content}
                for msg in history_to_use
            ]
        else:
            messages = [{"role": role, "content": message}]
        
        # Generate response
        options = {
            "temperature": self.config.temperature,
            "num_predict": self.config.max_tokens,
            "top_p": self.config.top_p,
            "num_ctx": self.config.num_ctx,
        }
        
        response = self.client.chat(
            model=self.config.model_name,
            messages=messages,
            options=options,
            stream=False
        )
        
        assistant_response = response['message']['content']
        
        # Add assistant response to history
        self.conversation_history.append(
            ChatMessage(role="assistant", content=assistant_response)
        )
        
        return assistant_response
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    def analyze_research(self, content: str) -> str:
        """
        Analyze research paper content
        
        Args:
            content: Paper content to analyze
            
        Returns:
            Analysis results
        """
        prompt = PromptTemplate.format("research_analysis", content=content)
        return self.generate(prompt, temperature=0.3)  # Lower temp for factual analysis
    
    def detect_gaps(self, context: str, papers: List[str]) -> str:
        """
        Detect research gaps
        
        Args:
            context: Research context
            papers: List of paper summaries
            
        Returns:
            Identified research gaps
        """
        papers_text = "\n\n".join([f"- {paper}" for paper in papers])
        prompt = PromptTemplate.format(
            "gap_detection",
            context=context,
            papers=papers_text
        )
        return self.generate(prompt, temperature=0.4)
    
    def recommend_papers(self, query: str, papers: List[Dict[str, str]], top_k: int = 5) -> str:
        """
        Recommend relevant papers
        
        Args:
            query: User's research query
            papers: List of available papers with metadata
            top_k: Number of recommendations
            
        Returns:
            Paper recommendations
        """
        papers_text = "\n\n".join([
            f"Title: {p.get('title', 'Unknown')}\nAbstract: {p.get('abstract', 'N/A')}"
            for p in papers
        ])
        prompt = PromptTemplate.format(
            "recommendation",
            query=query,
            papers=papers_text,
            top_k=top_k
        )
        return self.generate(prompt, temperature=0.5)
    
    def summarize_paper(self, title: str, content: str) -> str:
        """
        Summarize a research paper
        
        Args:
            title: Paper title
            content: Paper content
            
        Returns:
            Paper summary
        """
        prompt = PromptTemplate.format(
            "summarization",
            title=title,
            content=content[:3000]  # Limit content length
        )
        return self.generate(prompt, temperature=0.3)
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embeddings for text using Ollama
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            response = self.client.embeddings(
                model=self.config.model_name,
                prompt=text
            )
            return response['embedding']
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    def __repr__(self) -> str:
        return f"GLMInterface(model={self.config.model_name}, base_url={self.config.base_url})"


# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logger.add("logs/glm_interface.log", rotation="10 MB")
    
    # Initialize interface
    glm = GLMInterface()
    
    # Health check
    if glm.health_check():
        print("✅ GLM-4.6 is ready!")
        
        # Test simple generation
        response = glm.generate(
            "Explain the transformer architecture in one paragraph.",
            temperature=0.7
        )
        print(f"\n🤖 Response:\n{response}")
        
        # Test chat
        chat_response = glm.chat("What are the key innovations in GPT-3?")
        print(f"\n💬 Chat:\n{chat_response}")
    else:
        print("❌ GLM-4.6 is not available. Please check Ollama installation.")
