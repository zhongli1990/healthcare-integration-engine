import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple
from dataclasses import asdict
from ..models.base import Production, Component, RoutingRule

class ProductionParser:
    """Parser for InterSystems IRIS Production XML definitions."""
    
    def __init__(self):
        self.ns = {'ns': 'http://www.intersystems.com/Production'}
    
    def parse_production(self, content: str) -> Production:
        """Parse a production definition from XML content."""
        # Clean and extract the XData section
        xdata_content = self._extract_xdata(content)
        if not xdata_content:
            raise ValueError("No XData section found in production file")
        
        # Parse the XML
        root = ET.fromstring(xdata_content)
        
        # Create production
        production = Production(
            name=root.get('Name', ''),
            type='Production',
            description=root.findtext('ns:Description', '', self.ns).strip(),
            actor_pool_size=int(root.get('ActorPoolSize', '2')),
            log_general_trace_events=root.get('LogGeneralTraceEvents', 'false').lower() == 'true'
        )
        
        # Parse components
        for item in root.findall('ns:Item', self.ns):
            component = self._parse_component(item)
            if component:
                production.components.append(component)
        
        return production
    
    def _extract_xdata(self, content: str) -> str:
        """Extract and clean the XData section from the class file."""
        # Look for XData ProductionDefinition section
        pattern = r'XData\s+ProductionDefinition\s*\{([\s\S]*?)\}'
        match = re.search(pattern, content)
        if not match:
            return ""
        
        xdata = match.group(1).strip()
        # Remove CDATA if present
        if xdata.startswith('{') and xdata.endswith('}'):
            xdata = xdata[1:-1].strip()
        
        # Remove any leading/trailing whitespace and newlines
        return xdata.strip()
    
    def _parse_component(self, item: ET.Element) -> Optional[Component]:
        """Parse a component from an Item element."""
        name = item.get('Name')
        class_name = item.get('ClassName')
        
        if not name or not class_name:
            return None
        
        component = Component(
            name=name,
            type=self._get_component_type(class_name),
            class_name=class_name,
            pool_size=int(item.get('PoolSize', '1')),
            enabled=item.get('Enabled', 'true').lower() == 'true',
            comment=item.get('Comment', '').strip()
        )
        
        # Parse settings
        for setting in item.findall('ns:Setting', self.ns):
            target = setting.get('Target', '')
            name = setting.get('Name', '')
            value = setting.get('Value', '')
            
            if target and name:
                component.settings[f"{target}.{name}"] = value
        
        return component
    
    def _get_component_type(self, class_name: str) -> str:
        """Determine component type based on class name."""
        class_name = class_name.lower()
        if 'service' in class_name:
            return 'Service'
        elif 'process' in class_name or 'businessprocess' in class_name:
            return 'Process'
        elif 'operation' in class_name:
            return 'Operation'
        elif 'router' in class_name or 'routingengine' in class_name:
            return 'Router'
        return 'Component'
