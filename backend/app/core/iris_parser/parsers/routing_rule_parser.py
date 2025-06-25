import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from ..models.base import RoutingRule

class RoutingRuleParser:
    """Parser for InterSystems IRIS Routing Rules."""
    
    def __init__(self):
        self.ns = {'rule': 'http://www.intersystems.com/rule'}
    
    def parse_routing_rule(self, content: str) -> Optional[RoutingRule]:
        """Parse a routing rule from class content."""
        xdata_content = self._extract_xdata(content)
        if not xdata_content:
            return None
            
        root = ET.fromstring(xdata_content)
        rule_set = root.find('rule:ruleSet', self.ns)
        if rule_set is None:
            return None
            
        rule = rule_set.find('rule:rule', self.ns)
        if rule is None:
            return None
            
        # Create routing rule
        routing_rule = RoutingRule(
            name=rule.get('name', 'UnnamedRule'),
            type='RoutingRule',
            description=rule_set.get('description', '').strip()
        )
        
        # Parse constraints
        for constraint in rule.findall('rule:constraint', self.ns):
            name = constraint.get('name', '')
            value = constraint.get('value', '')
            if name and value:
                routing_rule.conditions.append({
                    'type': 'constraint',
                    'name': name,
                    'value': value
                })
        
        # Parse when conditions and actions
        for when in rule.findall('rule:when', self.ns):
            condition = when.get('condition', 'true')
            if condition != '1':  # Skip if condition is not just '1'
                routing_rule.conditions.append({
                    'type': 'condition',
                    'expression': condition
                })
            
            # Parse actions (send, return, etc.)
            for action in when.findall('*'):
                action_data = {
                    'type': action.tag.split('}')[-1],  # Remove namespace
                    **action.attrib
                }
                routing_rule.actions.append(action_data)
        
        return routing_rule
    
    def _extract_xdata(self, content: str) -> str:
        """Extract and clean the XData section from the class file."""
        pattern = r'XData\s+RuleDefinition[\s\S]*?\{([\s\S]*?)\}'
        match = re.search(pattern, content)
        if not match:
            return ""
        
        xdata = match.group(1).strip()
        # Remove CDATA if present
        if xdata.startswith('{') and xdata.endswith('}'):
            xdata = xdata[1:-1].strip()
        
        # Remove any leading/trailing whitespace and newlines
        return xdata.strip()
