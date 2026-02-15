# Validators
"""
Schema Validators
"""

from typing import List, Dict, Any, Tuple
from database_generation.db_types import ForgeSchema, EntityDef, FieldDef


class SchemaValidator:
    """Validate schema structure and integrity"""
    
    def validate(self, schema: ForgeSchema) -> Tuple[bool, List[str], List[str]]:
        """
        Validate schema
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Run all validations
        errors.extend(self._validate_entity_names(schema))
        errors.extend(self._validate_field_names(schema))
        errors.extend(self._validate_references(schema))
        errors.extend(self._validate_primary_keys(schema))
        
        warnings.extend(self._check_naming_conventions(schema))
        warnings.extend(self._check_missing_indexes(schema))
        
        is_valid = len(errors) == 0
        return is_valid, errors, warnings
    
    def _validate_entity_names(self, schema: ForgeSchema) -> List[str]:
        """Validate entity names"""
        errors = []
        seen = set()
        
        for entity in schema.entities:
            name = entity.name.lower()
            
            if name in seen:
                errors.append(f"Duplicate entity name: {entity.name}")
            seen.add(name)
            
            if not name.replace('_', '').isalnum():
                errors.append(f"Invalid entity name: {entity.name}")
        
        return errors
    
    def _validate_field_names(self, schema: ForgeSchema) -> List[str]:
        """Validate field names"""
        errors = []
        reserved = {'select', 'from', 'where', 'table', 'index', 'order', 'group'}
        
        for entity in schema.entities:
            seen = set()
            
            for field in entity.fields:
                name = field.name.lower()
                
                if name in seen:
                    errors.append(f"Duplicate field in {entity.name}: {field.name}")
                seen.add(name)
                
                if name in reserved:
                    errors.append(f"Reserved word in {entity.name}: {field.name}")
        
        return errors
    
    def _validate_references(self, schema: ForgeSchema) -> List[str]:
        """Validate foreign key references"""
        errors = []
        entity_names = {e.name.lower() for e in schema.entities}
        
        for entity in schema.entities:
            for field in entity.fields:
                if field.reference:
                    ref_name = field.reference.entity.lower()
                    if ref_name not in entity_names:
                        errors.append(
                            f"Invalid reference in {entity.name}.{field.name}: "
                            f"Entity '{field.reference.entity}' not found"
                        )
        
        return errors
    
    def _validate_primary_keys(self, schema: ForgeSchema) -> List[str]:
        """Validate primary keys"""
        errors = []
        
        for entity in schema.entities:
            pk_count = sum(1 for f in entity.fields if f.primary_key)
            
            if pk_count == 0:
                errors.append(f"No primary key in entity: {entity.name}")
            elif pk_count > 1:
                errors.append(f"Multiple primary keys in entity: {entity.name}")
        
        return errors
    
    def _check_naming_conventions(self, schema: ForgeSchema) -> List[str]:
        """Check naming conventions (warnings)"""
        warnings = []
        
        for entity in schema.entities:
            # Check plural names
            if not entity.name.endswith('s') and entity.name not in ['data', 'staff', 'media']:
                warnings.append(f"Entity '{entity.name}' should be plural")
        
        return warnings
    
    def _check_missing_indexes(self, schema: ForgeSchema) -> List[str]:
        """Check for missing indexes (warnings)"""
        warnings = []
        
        for entity in schema.entities:
            indexed_fields = set()
            for idx in entity.indexes:
                indexed_fields.update(idx.fields)
            
            for field in entity.fields:
                # Foreign keys should be indexed
                if field.reference and field.name not in indexed_fields:
                    warnings.append(
                        f"Foreign key without index: {entity.name}.{field.name}"
                    )
        
        return warnings


# Singleton
schema_validator = SchemaValidator()