"""Sandbox abstraction: run pytest against migrated code in isolation.

Phase 2: LocalSubprocessSandbox (dev / agent repair loop).
Phase 3: HardenedSubprocessSandbox (benchmark runner — process-group kill,
         RLIMIT_AS memory cap, trusted benchmark code only).
"""

from sandbox.base import SandboxRunner, TestResult
from sandbox.hardened import HardenedSubprocessSandbox
from sandbox.local import LocalSubprocessSandbox

__all__ = ["SandboxRunner", "TestResult", "LocalSubprocessSandbox", "HardenedSubprocessSandbox"]
