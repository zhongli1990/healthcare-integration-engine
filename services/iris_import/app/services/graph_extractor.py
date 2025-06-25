"""
Graph extractor for IRIS production files.

This module provides functionality to extract a graph structure from IRIS production
and routing rule files, suitable for import into Neo4j.
"""
import os
import re
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG to see all log messages

class GraphExtractor:
    """
    Extracts a graph structure from IRIS production and routing rule files.
    
    The extractor identifies different types of components (Services, Operations, Routers)
    and their relationships based on the production configuration and routing rules.
    """
    
    def __init__(self):
        """Initialize the graph extractor with empty node and relationship stores."""
        self.nodes = {}  # name -> node dict
        self.relationships = []  # List of relationship dicts
        self._node_counter = 0
        
        # Regular expressions for parsing
        self._patterns = {
            'class': re.compile(r'Class\s+([^\s\(]+)'),
            'description': re.compile(r'Description\s*=\s*"([^"]*)"'),
            'xdata': re.compile(r'XData\s+(\w+)\s*\{[\s\n]*(<[^>]+>[\s\S]*?<\/[^>]+>)[\s\n]*\}', re.DOTALL),
            'item': re.compile(r'<Item[^>]*\s+name="([^"]+)"[^>]*>([\s\S]*?)</Item>'),
            'setting': re.compile(r'<Setting\s+Target="([^"]+)"\s+Name="([^"]+)"\s*[^>]*?>(.*?)</Setting>', re.DOTALL),
            'rule': re.compile(r'<Rule\s+name="([^"]+)"[^>]*>([\s\S]*?)</Rule>'),
            'constraint': re.compile(r'<constraint\s+name="([^"]+)"\s+value="([^"]+)"\s*/>'),
            'send': re.compile(r'<send\s+[^>]*?target="([^"]+)"'),
        }
    
    def extract_from_files(self, production_file: str, routing_rule_file: str) -> Dict[str, Any]:
        """
        Extract graph from production and routing rule files.
        
        Args:
            production_file: Path to the production .cls file
            routing_rule_file: Path to the routing rule .cls file
            
        Returns:
            Dictionary containing 'nodes' and 'relationships' keys with the extracted graph
        """
        logger.info(f"Extracting graph from {production_file} and {routing_rule_file}")
        
        try:
            # Parse production file to get components
            production_data = self._parse_production_file(production_file)
            
            # Parse routing rules to get relationships
            routing_data = self._parse_routing_rules(routing_rule_file)
            
            # Create nodes from components
            for component in production_data.get('components', []):
                self._add_component_node(component)
                
            # Add relationships from routing rules
            for rule in routing_data.get('rules', []):
                self._process_rule(rule)
            
            # Add relationships from target configurations
            self._extract_implicit_relationships(production_data.get('components', []))
            
            return {
                'nodes': list(self.nodes.values()),
                'relationships': self.relationships,
                'metadata': {
                    'production_name': production_data.get('name', 'Unknown'),
                    'component_count': len(production_data.get('components', [])),
                    'rule_count': len(routing_data.get('rules', [])),
                    'node_count': len(self.nodes),
                    'relationship_count': len(self.relationships)
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting graph: {str(e)}", exc_info=True)
            raise
    
    def _add_component_node(self, component: Dict) -> str:
        """
        Add a component as a node in the graph.
        
        Args:
            component: Component data from production file
            
        Returns:
            Node ID of the created node
        """
        node_name = component['name']
        
        # Skip if node already exists
        if node_name in self.nodes:
            return self.nodes[node_name]['id']
        
        # Generate a unique ID
        node_id = f"node_{self._node_counter}"
        self._node_counter += 1
        
        # Determine node type and label
        component_type = component.get('type', '')
        label = self._get_node_label(component_type)
        
        # Create node with properties
        node = {
            'id': node_id,
            'name': node_name,
            'type': component_type,
            'label': label,
            'properties': {
                'className': component_type,
                'settings': component.get('settings', {})
            }
        }
        
        self.nodes[node_name] = node
        logger.debug(f"Added node: {node_name} ({label})")
        return node_id
    
    def _get_node_label(self, component_type: str) -> str:
        """
        Get the appropriate Neo4j label based on component type.
        
        Args:
            component_type: The class name of the component
            
        Returns:
            Label string (Service, Operation, Router, or Component)
        """
        if not component_type:
            return 'Component'
            
        component_type = component_type.lower()
        if 'service' in component_type:
            return 'Service'
        elif 'operation' in component_type:
            return 'Operation'
        elif 'router' in component_type or 'routingengine' in component_type:
            return 'Router'
        return 'Component'
    
    def _find_matching_node(self, name: str) -> str:
        """
        Find a node that matches the given name, with flexible matching.
        
        Args:
            name: The name to match against node names
            
        Returns:
            The matching node name or None if no match found
        """
        if not name:
            return None
            
        # Try exact match first
        if name in self.nodes:
            return name
            
        # Try case-insensitive match
        name_lower = name.lower()
        for node_name in self.nodes:
            if node_name.lower() == name_lower:
                return node_name
                
        # Try partial match (if name is part of node name or vice versa)
        for node_name in self.nodes:
            if name in node_name or node_name in name:
                return node_name
                
        # Try matching after removing common prefixes/suffixes
        clean_name = name.replace('EnsLib.HL7.Service.', '').replace('EnsLib.HL7.Operation.', '')
        for node_name in self.nodes:
            clean_node = node_name.replace('EnsLib.HL7.Service.', '').replace('EnsLib.HL7.Operation.', '')
            if clean_name == clean_node or clean_name in clean_node or clean_node in clean_name:
                return node_name
                
        return None
    
    def _process_rule(self, rule: Dict):
        """
        Process a routing rule to extract relationships.
        
        Args:
            rule: Parsed rule data from routing rule file
        """
        source = rule.get('source')
        target = rule.get('target')
        rule_name = rule.get('name', 'unnamed')
        constraints = rule.get('constraints', {})
        
        if not source or not target:
            logger.warning(f"Skipping rule '{rule_name}' - missing source or target")
            return
            
        logger.debug(f"Processing rule '{rule_name}': {source} -> {target}")
        
        # Try to find matching source and target nodes with flexible matching
        source_node = self._find_matching_node(source)
        target_node = self._find_matching_node(target)
        
        if not source_node:
            logger.warning(f"Source node '{source}' not found in nodes for rule '{rule_name}'. Available nodes: {list(self.nodes.keys())[:10]}...")
            return
            
        if not target_node:
            logger.warning(f"Target node '{target}' not found in nodes for rule '{rule_name}'. Available nodes: {list(self.nodes.keys())[:10]}...")
            return
            
        # Check if relationship already exists
        existing_rel = next((r for r in self.relationships 
                           if r['source'] == source_node and r['target'] == target_node), None)
        
        if existing_rel:
            # Update existing relationship with additional rule info
            if 'rules' not in existing_rel['properties']:
                existing_rel['properties']['rules'] = []
            existing_rel['properties']['rules'].append({
                'name': rule_name,
                'constraints': constraints
            })
            logger.debug(f"Updated existing relationship: {source_node} -> {target_node} with rule '{rule_name}'")
        else:
            # Create new relationship data
            rel_data = {
                'source': source_node,
                'target': target_node,
                'type': 'ROUTES_TO',
                'properties': {
                    'rule_name': rule_name,
                    'rules': [{
                        'name': rule_name,
                        'constraints': constraints
                    }],
                    'constraints': constraints
                }
            }
            
            # Add docCategory and docName if available in constraints
            if 'docCategory' in constraints:
                rel_data['properties']['doc_category'] = constraints['docCategory']
            if 'docName' in constraints:
                rel_data['properties']['message_types'] = constraints['docName']
            
            # Add the relationship
            self.relationships.append(rel_data)
            logger.info(f"Added relationship: {source_node} -> {target_node} (ROUTES_TO) for rule '{rule_name}'")
    
    def _extract_implicit_relationships(self, components: List[Dict]):
        """
        Extract implicit relationships from component settings.
        
        Args:
            components: List of component dictionaries
        """
        for component in components:
            settings = component.get('settings', {})
            
            # Check for target configurations
            if 'TargetConfigNames' in settings:
                targets = settings['TargetConfigNames']
                if isinstance(targets, str):
                    targets = [t.strip() for t in targets.split(',')]
                
                for target in targets:
                    if target and target in self.nodes:
                        self.relationships.append({
                            'source': component['name'],
                            'target': target,
                            'type': 'SENDS_TO',
                            'properties': {
                                'source': 'TargetConfigNames',
                                'implicit': True
                            }
                        })
    
    def _parse_production_file(self, file_path: str) -> Dict:
        """
        Parse production file to extract components.
        
        Args:
            file_path: Path to the production .cls file
            
        Returns:
            Dictionary containing parsed production data
        """
        logger.info(f"Parsing production file: {file_path}")
        
        try:
            # Check if file exists and is readable
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                raise FileNotFoundError(f"File not found: {file_path}")
                
            logger.debug(f"Reading file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content:
                logger.error(f"File is empty: {file_path}")
                raise ValueError(f"File is empty: {file_path}")
                
            logger.debug(f"File content length: {len(content)} characters")
            
            # Extract production class name
            class_match = self._patterns['class'].search(content)
            if class_match:
                production_name = class_match.group(1)
                logger.debug(f"Found production class: {production_name}")
            else:
                production_name = "UnknownProduction"
                logger.warning("No production class name found in file")
            
            # Extract production description if available
            description_match = self._patterns['description'].search(content)
            description = description_match.group(1) if description_match else ""
            logger.debug(f"Production description: {description[:50]}..." if description else "No description found")
            
            # Find all XData blocks which contain component definitions
            xdata_matches = self._patterns['xdata'].findall(content)
            logger.debug(f"Found {len(xdata_matches)} XData blocks in file")
            
            components = []
            for i, (xdata_name, xdata_content) in enumerate(xdata_matches, 1):
                logger.debug(f"Processing XData block {i}: {xdata_name}")
                logger.debug(f"XData content: {xdata_content[:200]}...")
                
                if 'ProductionDefinition' in xdata_name or 'Production' in xdata_name:
                    logger.debug(f"Found ProductionDefinition XData block: {xdata_name}")
                    # Parse production definition to get components
                    parsed_components = self._parse_production_definition(xdata_content)
                    logger.debug(f"Extracted {len(parsed_components)} components from ProductionDefinition")
                    components.extend(parsed_components)
                else:
                    logger.debug(f"Skipping non-ProductionDefinition XData block: {xdata_name}")
            
            result = {
                'name': production_name,
                'description': description,
                'components': components,
                'source_file': str(file_path)
            }
            
            logger.info(f"Parsed {len(components)} components from {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing production file {file_path}: {str(e)}", exc_info=True)
            return {
                'name': 'Error',
                'description': f'Error parsing file: {str(e)}',
                'components': [],
                'source_file': str(file_path)
            }
    
    def _parse_production_definition(self, xdata_content: str) -> List[Dict]:
        """
        Parse the ProductionDefinition XData block to extract components.
        
        Args:
            xdata_content: Content of the XData block
            
        Returns:
            List of component dictionaries
        """
        components = []
        logger.debug(f"Parsing ProductionDefinition content, length: {len(xdata_content)} chars")
        
        # First try to find Item elements with flexible attribute ordering
        item_pattern = re.compile(
            r'<Item\s+'
            r'(?P<all_attrs>.*?)'  # All attributes
            r'\s*>(?P<content>.*?)</Item>',  # Content between tags
            re.DOTALL | re.IGNORECASE
        )
        
        # Pattern to extract individual attributes
        attr_pattern = re.compile(
            r'(\w+)\s*=\s*"([^"]*)"',  # key="value"
            re.IGNORECASE
        )
        
        setting_pattern = re.compile(r'<Setting\s+Target=["\']([^"\']*)["\']\s+Name=["\']([^"\']*?)["\'][^>]*>([^<]*)</Setting>', 
                                   re.DOTALL | re.IGNORECASE)
        
        items = list(item_pattern.finditer(xdata_content))
        logger.info(f"Found {len(items)} Item elements in ProductionDefinition")
        
        if not items:
            logger.warning("No <Item> elements found in XData content")
            logger.debug(f"XData content that failed to match: {xdata_content[:500]}...")
            return components
            
        for i, match in enumerate(items, 1):
            try:
                all_attrs = match.group('all_attrs')
                item_content = match.group('content')
                
                # Parse all attributes
                attrs = {}
                for attr_match in attr_pattern.finditer(all_attrs):
                    key = attr_match.group(1).lower()  # Convert to lowercase for case-insensitive comparison
                    value = attr_match.group(2)
                    attrs[key] = value
                
                # Check for required attributes
                if 'name' not in attrs:
                    logger.warning(f"Item at position {i} is missing required 'Name' attribute")
                    continue
                    
                if 'classname' not in attrs:
                    logger.warning(f"Item at position {i} is missing required 'ClassName' attribute")
                    continue
                
                item_name = attrs['name']
                logger.debug(f"Processing item {i}: {item_name}")
                
                # Parse settings from the item content
                settings = {}
                setting_matches = list(setting_pattern.finditer(item_content))
                logger.debug(f"Found {len(setting_matches)} settings for {item_name}")
                
                for j, setting in enumerate(setting_matches, 1):
                    try:
                        if not setting.groups() or len(setting.groups()) < 3:
                            logger.warning(f"Invalid setting match at position {j} in item {item_name}")
                            continue
                            
                        target = setting.group(1)
                        name = setting.group(2)
                        value = setting.group(3).strip()
                        settings[f"{target}.{name}"] = value
                        logger.debug(f"  Setting: {target}.{name} = {value[:50]}")
                    except Exception as e:
                        logger.error(f"Error parsing setting {j} in item {item_name}: {str(e)}", exc_info=True)
                
                # Create component dictionary
                component = {
                    'name': item_name,
                    'type': attrs['classname'],
                    'settings': settings
                }
                
                # Add other attributes as settings
                for key, value in attrs.items():
                    if key not in ['name', 'classname']:
                        component['settings'][key] = value
                
                components.append(component)
                logger.info(f"Parsed component: {item_name} ({attrs['classname']}) with {len(settings)} settings")
                
            except Exception as e:
                logger.error(f"Error parsing component {i}: {str(e)}", exc_info=True)
        
        logger.info(f"Extracted {len(components)} components from ProductionDefinition")
        return components
    
    def _parse_routing_rules(self, file_path: str) -> Dict:
        """
        Parse routing rules file to extract rules and their configurations.
        
        Args:
            file_path: Path to the routing rule .cls file
            
        Returns:
            Dictionary containing parsed routing rules
        """
        logger.info(f"Parsing routing rules file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract rule class name
            class_match = self._patterns['class'].search(content)
            rule_name = class_match.group(1) if class_match else "UnknownRule"
            
            # Extract rule description if available
            description_match = self._patterns['description'].search(content)
            description = description_match.group(1) if description_match else ""
            
            # Find all XData blocks which contain rule definitions
            xdata_blocks = self._patterns['xdata'].findall(content)
            
            rules = []
            for xdata_name, xdata_content in xdata_blocks:
                if 'RuleDefinition' in xdata_name:
                    # Parse rule definition to get rules
                    rules.extend(self._parse_rule_definition(xdata_content))
            
            return {
                'name': rule_name,
                'description': description,
                'rules': rules,
                'source_file': str(file_path)
            }
            
        except Exception as e:
            logger.error(f"Error parsing routing rules file {file_path}: {str(e)}", exc_info=True)
            return {
                'name': 'Error',
                'description': f'Error parsing file: {str(e)}',
                'rules': [],
                'source_file': str(file_path)
            }
    
    def _parse_rule_definition(self, xdata_content: str) -> List[Dict]:
        """
        Parse the RuleDefinition XData block to extract routing rules.
        
        Args:
            xdata_content: Content of the XData block
            
        Returns:
            List of rule dictionaries
        """
        rules = []
        
        # Find all Rule elements - updated to handle the XML structure more flexibly
        rule_pattern = re.compile(
            r'<rule\s+name=["\']([^"\']+)["\'][^>]*>\s*'
            r'(<constraint[^>]*>.*?</constraint>\s*)*'
            r'<when[^>]*>\s*'
            r'(<send[^>]*>.*?</send>\s*)*'
            r'</when>\s*</rule>',
            re.DOTALL | re.IGNORECASE
        )
        
        # Pattern to extract constraints
        constraint_pattern = re.compile(
            r'<constraint\s+name=["\']([^"\']+)["\']\s+value=["\']([^"\']*)["\']',
            re.IGNORECASE
        )
        
        # Pattern to extract send targets
        send_pattern = re.compile(
            r'<send[^>]*?target=["\']([^"\']+)["\']',
            re.IGNORECASE
        )
        
        rule_matches = rule_pattern.finditer(xdata_content)
        
        for match in rule_matches:
            try:
                rule_name = match.group(1)
                rule_content = match.group(0)  # Full rule content
                
                # Extract constraints
                constraints = {}
                for constr_match in constraint_pattern.finditer(rule_content):
                    constraints[constr_match.group(1)] = constr_match.group(2)
                
                # Extract source from constraints
                source = constraints.get('source')
                
                # Extract targets from send actions
                send_matches = send_pattern.finditer(rule_content)
                targets = [m.group(1).strip() for m in send_matches]
                
                # Create a rule for each target
                for target in targets:
                    if source and target:
                        rule_data = {
                            'name': rule_name,
                            'source': source,
                            'target': target,
                            'constraints': constraints
                        }
                        rules.append(rule_data)
                        logger.debug(f"Parsed rule: {rule_name} ({source} -> {target})")
                
            except Exception as e:
                logger.error(f"Error parsing rule {rule_name if 'rule_name' in locals() else 'unknown'}: {str(e)}", 
                           exc_info=True)
        
        logger.info(f"Extracted {len(rules)} routing rules from RuleDefinition")
        return rules
