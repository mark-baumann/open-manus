"""
Docker Sandbox Module

Provides secure containerized execution environment with resource limits
and isolation for running untrusted code.
"""

from app.sandbox.core.exceptions import (
    SandboxError,
    SandboxResourceError,
    SandboxTimeoutError,
)

try:
    from app.sandbox.client import (
        BaseSandboxClient,
        LocalSandboxClient,
        create_sandbox_client,
    )
except ImportError:
    BaseSandboxClient = None  # type: ignore
    LocalSandboxClient = None  # type: ignore
    create_sandbox_client = None  # type: ignore

try:
    from app.sandbox.core.manager import SandboxManager
except ImportError:
    SandboxManager = None  # type: ignore

try:
    from app.sandbox.core.sandbox import DockerSandbox
except ImportError:
    DockerSandbox = None  # type: ignore


__all__ = [
    "DockerSandbox",
    "SandboxManager",
    "BaseSandboxClient",
    "LocalSandboxClient",
    "create_sandbox_client",
    "SandboxError",
    "SandboxTimeoutError",
    "SandboxResourceError",
]
