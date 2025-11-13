"""
Configuration Loader Utility

Handles loading and validation of configuration from YAML files and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv
from loguru import logger


@dataclass
class LLMConfig:
    """LLM configuration"""
    base_url: str = "http://localhost:11434"
    model_name: str = "glm-4.6:cloud"
    temperature: float = 0.7
    max_tokens: int = 2048
    context_window: int = 4096


@dataclass
class VectorDBConfig:
    """Vector database configuration"""
    persist_directory: str = "./chroma_db"
    collection_name: str = "research_papers"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    distance_metric: str = "cosine"


@dataclass
class Neo4jConfig:
    """Neo4j configuration"""
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = ""
    database: str = "neo4j"


@dataclass
class RetrievalConfig:
    """Retrieval configuration"""
    top_k: int = 5
    chunk_size: int = 512
    chunk_overlap: int = 50
    min_relevance_score: float = 0.7


@dataclass
class APIConfig:
    """API configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    reload: bool = False


@dataclass
class DataConfig:
    """Data paths configuration"""
    raw_path: str = "./data/raw"
    processed_path: str = "./data/processed"


@dataclass
class AppConfig:
    """Main application configuration"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    vector_db: VectorDBConfig = field(default_factory=VectorDBConfig)
    neo4j: Neo4jConfig = field(default_factory=Neo4jConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    api: APIConfig = field(default_factory=APIConfig)
    data: DataConfig = field(default_factory=DataConfig)
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"


class ConfigLoader:
    """
    Loads configuration from YAML files and environment variables
    
    Priority order:
    1. Environment variables (highest)
    2. YAML configuration file
    3. Default values (lowest)
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader
        
        Args:
            config_path: Path to YAML config file (optional)
        """
        self.config_path = config_path or self._find_config_file()
        load_dotenv()  # Load .env file
        self.config = self._load_config()
    
    def _find_config_file(self) -> Optional[str]:
        """Find config file in standard locations"""
        possible_paths = [
            "./configs/config.yaml",
            "./config.yaml",
            "../configs/config.yaml",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found config file: {path}")
                return path
        
        logger.warning("No config file found, using defaults")
        return None
    
    def _load_yaml(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path or not os.path.exists(self.config_path):
            return {}
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            return {}
    
    def _load_config(self) -> AppConfig:
        """Load complete configuration with priority handling"""
        yaml_config = self._load_yaml()
        
        # LLM Configuration
        llm_config = LLMConfig(
            base_url=os.getenv("OLLAMA_BASE_URL") or yaml_config.get("llm", {}).get("base_url", "http://localhost:11434"),
            model_name=os.getenv("OLLAMA_MODEL") or yaml_config.get("llm", {}).get("model_name", "glm-4.6:cloud"),
            temperature=float(os.getenv("LLM_TEMPERATURE", yaml_config.get("llm", {}).get("temperature", 0.7))),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", yaml_config.get("llm", {}).get("max_tokens", 2048))),
            context_window=int(os.getenv("LLM_CONTEXT_WINDOW", yaml_config.get("llm", {}).get("context_window", 4096))),
        )
        
        # Vector DB Configuration
        vector_db_config = VectorDBConfig(
            persist_directory=os.getenv("CHROMA_PERSIST_DIRECTORY") or yaml_config.get("vector_db", {}).get("persist_directory", "./chroma_db"),
            collection_name=os.getenv("CHROMA_COLLECTION_NAME") or yaml_config.get("vector_db", {}).get("collection_name", "research_papers"),
            embedding_model=os.getenv("EMBEDDING_MODEL") or yaml_config.get("vector_db", {}).get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"),
            distance_metric=yaml_config.get("vector_db", {}).get("distance_metric", "cosine"),
        )
        
        # Neo4j Configuration
        neo4j_config = Neo4jConfig(
            uri=os.getenv("NEO4J_URI") or yaml_config.get("neo4j", {}).get("uri", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER") or yaml_config.get("neo4j", {}).get("user", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD") or yaml_config.get("neo4j", {}).get("password", ""),
            database=yaml_config.get("neo4j", {}).get("database", "neo4j"),
        )
        
        # Retrieval Configuration
        retrieval_config = RetrievalConfig(
            top_k=int(os.getenv("RETRIEVAL_TOP_K", yaml_config.get("retrieval", {}).get("top_k", 5))),
            chunk_size=int(os.getenv("CHUNK_SIZE", yaml_config.get("retrieval", {}).get("chunk_size", 512))),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", yaml_config.get("retrieval", {}).get("chunk_overlap", 50))),
            min_relevance_score=float(os.getenv("MIN_RELEVANCE_SCORE", yaml_config.get("retrieval", {}).get("min_relevance_score", 0.7))),
        )
        
        # API Configuration
        api_config = APIConfig(
            host=os.getenv("API_HOST") or yaml_config.get("api", {}).get("host", "0.0.0.0"),
            port=int(os.getenv("API_PORT", yaml_config.get("api", {}).get("port", 8000))),
            workers=int(os.getenv("API_WORKERS", yaml_config.get("api", {}).get("workers", 4))),
            reload=yaml_config.get("api", {}).get("reload", False),
        )
        
        # Data Configuration
        data_config = DataConfig(
            raw_path=os.getenv("DATA_RAW_PATH") or yaml_config.get("data", {}).get("raw_path", "./data/raw"),
            processed_path=os.getenv("DATA_PROCESSED_PATH") or yaml_config.get("data", {}).get("processed_path", "./data/processed"),
        )
        
        # Main Configuration
        app_config = AppConfig(
            llm=llm_config,
            vector_db=vector_db_config,
            neo4j=neo4j_config,
            retrieval=retrieval_config,
            api=api_config,
            data=data_config,
            log_level=os.getenv("LOG_LEVEL") or yaml_config.get("log_level", "INFO"),
            log_file=os.getenv("LOG_FILE") or yaml_config.get("log_file", "./logs/app.log"),
        )
        
        logger.info("Configuration loaded successfully")
        return app_config
    
    def get_config(self) -> AppConfig:
        """Get the loaded configuration"""
        return self.config
    
    def reload(self):
        """Reload configuration"""
        logger.info("Reloading configuration...")
        self.config = self._load_config()
    
    def save_config(self, output_path: str):
        """
        Save current configuration to YAML file
        
        Args:
            output_path: Path to save configuration
        """
        config_dict = {
            "llm": {
                "base_url": self.config.llm.base_url,
                "model_name": self.config.llm.model_name,
                "temperature": self.config.llm.temperature,
                "max_tokens": self.config.llm.max_tokens,
                "context_window": self.config.llm.context_window,
            },
            "vector_db": {
                "persist_directory": self.config.vector_db.persist_directory,
                "collection_name": self.config.vector_db.collection_name,
                "embedding_model": self.config.vector_db.embedding_model,
                "distance_metric": self.config.vector_db.distance_metric,
            },
            "neo4j": {
                "uri": self.config.neo4j.uri,
                "user": self.config.neo4j.user,
                "password": "***",  # Don't save password
                "database": self.config.neo4j.database,
            },
            "retrieval": {
                "top_k": self.config.retrieval.top_k,
                "chunk_size": self.config.retrieval.chunk_size,
                "chunk_overlap": self.config.retrieval.chunk_overlap,
                "min_relevance_score": self.config.retrieval.min_relevance_score,
            },
            "api": {
                "host": self.config.api.host,
                "port": self.config.api.port,
                "workers": self.config.api.workers,
                "reload": self.config.api.reload,
            },
            "data": {
                "raw_path": self.config.data.raw_path,
                "processed_path": self.config.data.processed_path,
            },
            "log_level": self.config.log_level,
            "log_file": self.config.log_file,
        }
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Configuration saved to {output_path}")


# Global configuration instance
_config_loader: Optional[ConfigLoader] = None


def get_config() -> AppConfig:
    """Get global configuration instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader.get_config()


def reload_config():
    """Reload global configuration"""
    global _config_loader
    if _config_loader is not None:
        _config_loader.reload()


# Example usage
if __name__ == "__main__":
    loader = ConfigLoader()
    config = loader.get_config()
    
    print(f"LLM Model: {config.llm.model_name}")
    print(f"Vector DB: {config.vector_db.collection_name}")
    print(f"API Port: {config.api.port}")
    
    # Save config
    loader.save_config("./configs/config.yaml")
