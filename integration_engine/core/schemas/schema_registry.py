import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

import jsonschema
from pydantic import BaseModel, Field, validator

from core.utils.singleton import SingletonMeta

T = TypeVar('T', bound='Schema')


class SchemaValidationError(Exception):
    """Raised when schema validation fails."""
    pass


class Schema(BaseModel):
    """Base class for all schemas."""
    id: str = Field(..., description="Unique identifier for the schema")
    name: str = Field(..., description="Human-readable name of the schema")
    description: Optional[str] = Field(None, description="Description of the schema")
    version: str = Field("1.0.0", description="Schema version")
    schema_def: Dict[str, Any] = Field(..., description="JSON Schema definition")
    schema_type: str = Field(..., description="Type of schema (e.g., 'hl7v2', 'fhir')")
    
    class Config:
        extra = "forbid"
        json_encoders = {
            # Add custom JSON encoders if needed
        }
    
    @validator('schema_def')
    def validate_schema_def(cls, v):
        """Validate that schema_def is a valid JSON Schema."""
        try:
            jsonschema.Draft7Validator.check_schema(v)
            return v
        except jsonschema.exceptions.SchemaError as e:
            raise ValueError(f"Invalid JSON Schema: {e}")
    
    def validate(self, data: Any) -> bool:
        """Validate data against this schema."""
        try:
            jsonschema.validate(instance=data, schema=self.schema_def)
            return True
        except jsonschema.ValidationError as e:
            raise SchemaValidationError(f"Validation failed: {e}")
        except jsonschema.SchemaError as e:
            raise SchemaValidationError(f"Schema error: {e}")


class SchemaRegistry(metaclass=SingletonMeta):
    """Manages schemas for validation and transformation."""
    
    def __init__(self, schema_dirs: Optional[List[Union[str, Path]]] = None):
        self.schemas: Dict[str, Schema] = {}
        self.schema_dirs = schema_dirs or []
        self._load_schemas()
    
    def _load_schemas(self) -> None:
        """Load schemas from configured directories."""
        for schema_dir in self.schema_dirs:
            schema_dir = Path(schema_dir)
            if not schema_dir.exists() or not schema_dir.is_dir():
                continue
                
            for schema_file in schema_dir.glob("**/*.json"):
                try:
                    with open(schema_file, 'r', encoding='utf-8') as f:
                        schema_data = json.load(f)
                        schema = Schema(**schema_data)
                        self.register(schema)
                except Exception as e:
                    print(f"Error loading schema from {schema_file}: {e}")
    
    def register(self, schema: Schema) -> None:
        """Register a new schema."""
        if not isinstance(schema, Schema):
            raise ValueError("Schema must be an instance of Schema class")
        
        schema_id = schema.id
        if schema_id in self.schemas:
            raise ValueError(f"Schema with ID '{schema_id}' already exists")
        
        self.schemas[schema_id] = schema
    
    def get(self, schema_id: str) -> Optional[Schema]:
        """Get a schema by ID."""
        return self.schemas.get(schema_id)
    
    def get_by_type(self, schema_type: str) -> List[Schema]:
        """Get all schemas of a specific type."""
        return [s for s in self.schemas.values() if s.schema_type == schema_type]
    
    def validate(self, schema_id: str, data: Any) -> bool:
        """Validate data against a schema."""
        schema = self.get(schema_id)
        if not schema:
            raise ValueError(f"Schema '{schema_id}' not found")
        return schema.validate(data)
    
    def list(self) -> List[Dict[str, Any]]:
        """List all registered schemas."""
        return [
            {
                "id": schema.id,
                "name": schema.name,
                "description": schema.description,
                "version": schema.version,
                "type": schema.schema_type
            }
            for schema in self.schemas.values()
        ]
    
    def clear(self) -> None:
        """Clear all registered schemas."""
        self.schemas.clear()


# Example usage:
if __name__ == "__main__":
    # Initialize registry with schema directories
    registry = SchemaRegistry([
        "/path/to/schemas/hl7v2",
        "/path/to/schemas/fhir"
    ])
    
    # Register a schema programmatically
    hl7_schema = Schema(
        id="hl7v2.ADT_A01",
        name="HL7 v2 ADT^A01",
        description="HL7 v2 ADT A01 message schema",
        version="2.5.1",
        schema_type="hl7v2",
        schema_def={
            "type": "object",
            "properties": {
                "MSH": {"type": "object"},
                "EVN": {"type": "object"},
                "PID": {"type": "object"}
            },
            "required": ["MSH", "EVN", "PID"]
        }
    )
    
    registry.register(hl7_schema)
    
    # Validate data
    sample_message = {
        "MSH": {"MSH.1": "|", "MSH.2": "^~\\&"},
        "EVN": {"EVN.1": "A01"},
        "PID": {"PID.1": "1", "PID.5": {"PID.5.1": "Doe", "PID.5.2": "John"}}
    }
    
    try:
        registry.validate("hl7v2.ADT_A01", sample_message)
        print("Message is valid!")
    except SchemaValidationError as e:
        print(f"Validation failed: {e}")
