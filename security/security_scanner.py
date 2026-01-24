"""Security scanner for generated code."""

import logging
import re
from dataclasses import dataclass

from core.types import GeneratedFile, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class SecurityIssue:
    """Security issue found in code."""

    severity: str  # critical, high, medium, low
    category: str
    message: str
    file: str
    line: int | None = None
    suggestion: str | None = None


class SecurityScanner:
    """Scan generated code for security issues."""

    # Patterns to detect
    SECRET_PATTERNS = [
        (
            r'(?i)(password|secret|key|token)\s*=\s*["\'][^"\']+["\']',
            "hardcoded_secret",
        ),
        (r'(?i)api[_-]?key\s*[:=]\s*["\'][a-zA-Z0-9]{20,}["\']', "hardcoded_api_key"),
        (
            r"(?i)bearer\s+[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+",
            "hardcoded_jwt",
        ),
    ]

    SQL_INJECTION_PATTERNS = [
        (r"\$\{.*\}.*(?:SELECT|INSERT|UPDATE|DELETE|DROP)", "sql_injection_template"),
        (r"`.*\$\{.*\}.*`", "sql_injection_template_literal"),
        (r"query\s*\([^)]*\+\s*(?:req|user|input)", "sql_injection_concatenation"),
    ]

    AUTH_ISSUES = [
        (r"verify\s*[:=]\s*false", "jwt_verify_disabled"),
        (r"secure\s*:\s*false", "insecure_cookie"),
        (r"httpOnly\s*:\s*false", "httponly_disabled"),
    ]

    def scan_files(self, files: list[GeneratedFile]) -> list[SecurityIssue]:
        """Scan generated files for security issues."""
        issues = []

        for file in files:
            file_issues = self._scan_file(file)
            issues.extend(file_issues)

        return issues

    def _scan_file(self, file: GeneratedFile) -> list[SecurityIssue]:
        """Scan a single file."""
        issues = []
        content = file.content
        lines = content.split("\n")

        # Check for secrets
        for pattern, category in self.SECRET_PATTERNS:
            for match in re.finditer(pattern, content):
                line_num = content[: match.start()].count("\n") + 1
                issues.append(
                    SecurityIssue(
                        severity="critical",
                        category=category,
                        message=f"Potential hardcoded secret detected",
                        file=file.path,
                        line=line_num,
                        suggestion="Use environment variables instead",
                    )
                )

        # Check for SQL injection
        for pattern, category in self.SQL_INJECTION_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[: match.start()].count("\n") + 1
                issues.append(
                    SecurityIssue(
                        severity="high",
                        category=category,
                        message="Potential SQL injection vulnerability",
                        file=file.path,
                        line=line_num,
                        suggestion="Use parameterized queries",
                    )
                )

        # Check for auth issues
        for pattern, category in self.AUTH_ISSUES:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[: match.start()].count("\n") + 1
                issues.append(
                    SecurityIssue(
                        severity="medium",
                        category=category,
                        message="Insecure authentication configuration",
                        file=file.path,
                        line=line_num,
                    )
                )

        # Check for eval usage
        if "eval(" in content:
            line_num = content.find("eval(")
            issues.append(
                SecurityIssue(
                    severity="high",
                    category="eval_usage",
                    message="Use of eval() is dangerous",
                    file=file.path,
                    suggestion="Avoid eval() - use safer alternatives",
                )
            )

        return issues

    def validate(self, files: list[GeneratedFile]) -> ValidationResult:
        """Validate security and return result."""
        issues = self.scan_files(files)

        errors = [
            f"[{i.severity.upper()}] {i.file}:{i.line or '?'} - {i.message}"
            for i in issues
            if i.severity in ("critical", "high")
        ]

        warnings = [
            f"[{i.severity.upper()}] {i.file}:{i.line or '?'} - {i.message}"
            for i in issues
            if i.severity in ("medium", "low")
        ]

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )
