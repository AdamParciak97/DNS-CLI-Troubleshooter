from __future__ import annotations
from abc import ABC, abstractmethod
from cli_troubleshooter.models import CheckResult

class BaseCheck(ABC):
    name: str = ""
    description: str = ""
    timeout: int = 10

    @abstractmethod
    async def run(self, target: str, **kwargs) -> CheckResult:
        ...
