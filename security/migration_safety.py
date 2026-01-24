"""Migration safety checker."""

import logging
import re
from dataclasses import dataclass

from core.types import DatabaseSchema, Migration

logger = logging.getLogger(__name__)


@dataclass
class MigrationRisk:
    """Risk assessment for a migration."""

    level: str  # low, medium, high, critical
    description: str
    mitigation: str | None = None


class MigrationSafetyChecker:
    """Check migrations for safety issues."""

    DANGEROUS_OPERATIONS = [
        ("DROP TABLE", "critical", "Table deletion - data loss"),
        ("DROP COLUMN", "high", "Column deletion - data loss"),
        (
            "ALTER COLUMN.*NOT NULL",
            "medium",
            "Adding NOT NULL may fail on existing data",
        ),
        ("TRUNCATE", "critical", "Data deletion"),
        ("DELETE FROM.*WHERE", "high", "Bulk data deletion"),
    ]

    def check_migration(self, migration: Migration) -> list[MigrationRisk]:
        """Check a migration for risks."""
        risks = []
        up_sql = migration.up_sql.upper()

        for pattern, level, description in self.DANGEROUS_OPERATIONS:
            if re.search(pattern, up_sql, re.IGNORECASE):
                risks.append(
                    MigrationRisk(
                        level=level,
                        description=description,
                        mitigation=self._get_mitigation(pattern),
                    )
                )

        # Check for missing down migration
        if not migration.down_sql or migration.down_sql.strip() == "":
            risks.append(
                MigrationRisk(
                    level="medium",
                    description="Missing down migration - rollback not possible",
                    mitigation="Add corresponding DOWN migration",
                )
            )

        return risks

    def _get_mitigation(self, operation: str) -> str:
        """Get mitigation advice for an operation."""
        mitigations = {
            "DROP TABLE": "Backup table before dropping. Consider renaming instead.",
            "DROP COLUMN": "Backup column data. Consider deprecating instead of dropping.",
            "ALTER COLUMN.*NOT NULL": "Ensure all existing rows have values, or provide DEFAULT.",
            "TRUNCATE": "Backup data before truncating.",
            "DELETE FROM": "Verify WHERE clause. Consider soft delete.",
        }

        for key, mitigation in mitigations.items():
            if key in operation:
                return mitigation

        return "Review carefully before applying"

    def suggest_strategy(self, risks: list[MigrationRisk]) -> str:
        """Suggest deployment strategy based on risks."""
        if any(r.level == "critical" for r in risks):
            return "manual"  # Require manual approval
        elif any(r.level == "high" for r in risks):
            return "blue_green"  # Use blue-green deployment
        elif any(r.level == "medium" for r in risks):
            return "staged"  # Roll out in stages
        else:
            return "standard"  # Normal deployment

    def generate_rollback(self, migration: Migration) -> str | None:
        """Generate rollback SQL if possible."""
        # Simple heuristics - in practice would need more sophisticated analysis
        up_sql = migration.up_sql

        rollback_parts = []

        # CREATE TABLE -> DROP TABLE
        for match in re.finditer(r"CREATE TABLE\s+(\w+)", up_sql, re.IGNORECASE):
            table_name = match.group(1)
            rollback_parts.append(f"DROP TABLE IF EXISTS {table_name};")

        # ADD COLUMN -> DROP COLUMN
        for match in re.finditer(
            r"ALTER TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)", up_sql, re.IGNORECASE
        ):
            table_name = match.group(1)
            column_name = match.group(2)
            rollback_parts.append(
                f"ALTER TABLE {table_name} DROP COLUMN {column_name};"
            )

        if rollback_parts:
            return "\n".join(reversed(rollback_parts))

        return None
