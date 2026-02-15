"""Seed data generator for realistic test data."""

import asyncio
import json
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from core.types import InferredField, InferredFieldType, InferredModel

logger = logging.getLogger(__name__)


class SeedDataGenerator:
    """Generate realistic seed data for testing."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.generated_ids = {}  # Track generated IDs for foreign keys

    async def generate_seed_data(
        self,
        models: list[InferredModel],
        db_type: str = "postgresql",
        records_per_model: int = 10,
    ) -> dict[str, Path]:
        """Generate seed data for all models."""
        logger.info(f"Generating seed data for {len(models)} models")

        # Sort models by dependency (models with no foreign keys first)
        sorted_models = self._sort_by_dependency(models)

        files = {}

        for model in sorted_models:
            logger.info(f"Generating {records_per_model} records for {model.name}")

            records = []
            for i in range(records_per_model):
                record = await self._generate_record(model, i)
                records.append(record)

            # Save to file
            if db_type == "mongodb":
                file_path = await self._save_as_json(model.name, records)
            else:
                file_path = await self._save_as_sql(model.name, records, db_type)

            files[model.name] = file_path

        logger.info(f"Generated seed data files: {list(files.keys())}")
        return files

    def _sort_by_dependency(self, models: list[InferredModel]) -> list[InferredModel]:
        """Sort models so independent models come first."""
        # Simple heuristic: models with fewer fields first
        # In production, would analyze foreign key relationships
        return sorted(models, key=lambda m: len(m.fields))

    async def _generate_record(self, model: InferredModel, index: int) -> dict[str, Any]:
        """Generate a single record."""
        record = {}

        for field in model.fields:
            value = self._generate_field_value(field, model.name, index)
            record[field.name] = value

        # Store generated ID for foreign key references
        if model.primary_key in record:
            if model.name not in self.generated_ids:
                self.generated_ids[model.name] = []
            self.generated_ids[model.name].append(record[model.primary_key])

        # Add timestamps
        if model.timestamps:
            now = datetime.now()
            record["created_at"] = now.isoformat()
            record["updated_at"] = now.isoformat()

        return record

    def _generate_field_value(self, field: InferredField, model_name: str, index: int) -> Any:
        """Generate value for a field based on its type and name."""
        # Check if this is a primary key
        if field.name in ("id", "uuid"):
            if field.field_type == InferredFieldType.UUID:
                import uuid
                return str(uuid.uuid4())
            else:
                return index + 1

        # Check if this is a foreign key (ends with _id)
        if field.name.endswith("_id"):
            referenced_model = field.name[:-3].title()
            if referenced_model in self.generated_ids and self.generated_ids[referenced_model]:
                return random.choice(self.generated_ids[referenced_model])

        # Generate based on field name patterns
        field_lower = field.name.lower()

        # Email
        if "email" in field_lower:
            return f"user{index + 1}@example.com"

        # Name
        if "name" in field_lower or field.name == "title":
            names = ["Product", "Service", "Item", "Entity", "Resource"]
            return f"{random.choice(names)} {index + 1}"

        # Description
        if "description" in field_lower or "desc" in field_lower:
            return f"This is a description for {model_name} {index + 1}"

        # Price
        if "price" in field_lower or "amount" in field_lower:
            return round(random.uniform(10.0, 1000.0), 2)

        # Quantity
        if "quantity" in field_lower or "count" in field_lower or "stock" in field_lower:
            return random.randint(0, 100)

        # Phone
        if "phone" in field_lower or "mobile" in field_lower:
            return f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"

        # Address
        if "address" in field_lower or "street" in field_lower:
            return f"{random.randint(100, 9999)} Main St"

        # City
        if "city" in field_lower:
            cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]
            return random.choice(cities)

        # Status
        if "status" in field_lower or "state" in field_lower:
            statuses = ["active", "pending", "completed", "cancelled"]
            return random.choice(statuses)

        # Generate based on field type
        if field.field_type == InferredFieldType.STRING:
            return f"{field.name}_{index + 1}"
        elif field.field_type == InferredFieldType.TEXT:
            return f"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Record {index + 1}."
        elif field.field_type == InferredFieldType.INTEGER:
            return random.randint(1, 1000)
        elif field.field_type == InferredFieldType.FLOAT:
            return round(random.uniform(1.0, 1000.0), 2)
        elif field.field_type == InferredFieldType.DECIMAL:
            return round(random.uniform(1.0, 1000.0), 2)
        elif field.field_type == InferredFieldType.BOOLEAN:
            return random.choice([True, False])
        elif field.field_type == InferredFieldType.DATE:
            days_ago = random.randint(0, 365)
            date = datetime.now() - timedelta(days=days_ago)
            return date.strftime("%Y-%m-%d")
        elif field.field_type == InferredFieldType.DATETIME:
            days_ago = random.randint(0, 365)
            dt = datetime.now() - timedelta(days=days_ago)
            return dt.isoformat()
        elif field.field_type == InferredFieldType.JSON:
            return {"key": f"value_{index + 1}"}
        elif field.field_type == InferredFieldType.UUID:
            import uuid
            return str(uuid.uuid4())
        elif field.field_type == InferredFieldType.ENUM:
            return random.choice(["active", "pending", "completed"])
        elif field.field_type == InferredFieldType.RELATION:
            return index + 1  # Simple foreign key
        else:
            return f"{field.name}_{index + 1}"

    async def _save_as_sql(self, model_name: str, records: list[dict], db_type: str) -> Path:
        """Save records as SQL INSERT statements."""
        file_path = self.output_dir / f"{model_name.lower()}_seed.sql"

        lines = [f"-- Seed data for {model_name}", ""]

        for record in records:
            # Build INSERT statement
            columns = ", ".join(record.keys())
            values = []

            for value in record.values():
                if value is None:
                    values.append("NULL")
                elif isinstance(value, bool):
                    if db_type == "postgresql":
                        values.append(str(value).upper())
                    else:
                        values.append(str(1 if value else 0))
                elif isinstance(value, (int, float)):
                    values.append(str(value))
                elif isinstance(value, (dict, list)):
                    # JSON
                    json_str = json.dumps(value).replace("'", "''")
                    if db_type == "postgresql":
                        values.append(f"'{json_str}'::jsonb")
                    else:
                        values.append(f"'{json_str}'")
                else:
                    # String - escape single quotes
                    escaped = str(value).replace("'", "''")
                    values.append(f"'{escaped}'")

            values_str = ", ".join(values)
            sql = f"INSERT INTO {model_name.lower()} ({columns}) VALUES ({values_str});"
            lines.append(sql)

        lines.append("")

        file_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Saved SQL seed data: {file_path}")
        return file_path

    async def _save_as_json(self, model_name: str, records: list[dict]) -> Path:
        """Save records as JSON for MongoDB."""
        file_path = self.output_dir / f"{model_name.lower()}_seed.json"

        # Convert datetime objects to ISO strings
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        json_data = {
            "collection": model_name.lower(),
            "documents": records,
        }

        file_path.write_text(
            json.dumps(json_data, indent=2, default=serialize),
            encoding="utf-8",
        )

        logger.info(f"Saved JSON seed data: {file_path}")
        return file_path
