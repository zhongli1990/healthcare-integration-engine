from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class BaseModel:
    """Base model for all IRIS production components."""
    name: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "name": self.name,
            "type": self.type,
            **self.properties
        }

@dataclass
class Component(BaseModel):
    """Represents a component in an IRIS production."""
    class_name: str
    pool_size: int = 1
    enabled: bool = True
    comment: str = ""
    settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "class_name": self.class_name,
            "pool_size": self.pool_size,
            "enabled": self.enabled,
            "comment": self.comment,
            "settings": self.settings
        })
        return base

@dataclass
class RoutingRule(BaseModel):
    """Represents a routing rule in an IRIS production."""
    description: str = ""
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "description": self.description,
            "conditions": self.conditions,
            "actions": self.actions
        })
        return base

@dataclass
class Production(BaseModel):
    """Represents an IRIS production."""
    description: str = ""
    actor_pool_size: int = 2
    log_general_trace_events: bool = False
    components: List[Component] = field(default_factory=list)
    routing_rules: List[RoutingRule] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "description": self.description,
            "actor_pool_size": self.actor_pool_size,
            "log_general_trace_events": self.log_general_trace_events,
            "components": [comp.to_dict() for comp in self.components],
            "routing_rules": [rule.to_dict() for rule in self.routing_rules]
        })
        return base
