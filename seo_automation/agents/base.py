"""
Base Agent Class for GoRentals SEO Automation
All agents inherit from this base class for consistent behavior.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import yaml


@dataclass
class AgentResult:
    """Standardized result from agent execution"""
    agent_name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    files_created: List[str] = field(default_factory=list)


class BaseAgent(ABC):
    """Base class for all SEO agents"""

    def __init__(self, name: str, config: Dict[str, Any], project_root: Path):
        self.name = name
        self.config = config
        self.project_root = project_root
        self.logger = self._setup_logger()
        self.enabled = config.get('enabled', True)

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(f"seo_agent.{self.name}")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute the agent's main logic"""
        pass

    async def run(self, context: Dict[str, Any]) -> AgentResult:
        """Run the agent with timing and error handling"""
        if not self.enabled:
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={'status': 'disabled'}
            )

        start_time = datetime.now()
        self.logger.info(f"Starting {self.name} agent")

        try:
            result = await self.execute(context)
            result.execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Completed {self.name} in {result.execution_time:.2f}s")
            return result
        except Exception as e:
            self.logger.error(f"Error in {self.name}: {e}")
            return AgentResult(
                agent_name=self.name,
                success=False,
                errors=[str(e)],
                execution_time=(datetime.now() - start_time).total_seconds()
            )

    def save_output(self, content: str, filepath: str) -> str:
        """Save output to file and return path"""
        full_path = self.project_root / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding='utf-8')
        return str(full_path)

    def save_json(self, data: Dict[str, Any], filepath: str) -> str:
        """Save JSON output to file"""
        import json
        full_path = self.project_root / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        return str(full_path)


def load_config(config_path: str = "config/settings.yaml") -> Dict[str, Any]:
    """Load YAML configuration"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)