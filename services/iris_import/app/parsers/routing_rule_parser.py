"""
Parser for IRIS routing rule files (.cls).
"""
import re
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)


def parse_routing_rule_file(file_path: str) -> Dict:
    """
    Parse an IRIS routing rule file and extract rules and their configurations.
    
    Args:
        file_path: Path to the routing rule .cls file
        
    Returns:
        Dict containing the parsed routing rules data
    """
    logger.info(f"Starting to parse routing rule file: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.debug(f"File content size: {len(content)} bytes")
        
        # Extract rule class name
        class_match = re.search(r'Class\s+([^\s\(]+)', content)
        rule_name = class_match.group(1) if class_match else "UnknownRule"
        logger.info(f"Found rule class: {rule_name}")
        
        # Extract rule description if available
        description_match = re.search(r'Description\s*=\s*"([^"]*)"', content)
        description = description_match.group(1) if description_match else ""
        
        # Find all XData blocks which contain rule definitions
        xdata_blocks = re.findall(
            r'XData\s+([^\s{]+)\s*\{([^}]*)\}',
            content,
            re.DOTALL
        )
        
        logger.info(f"Found {len(xdata_blocks)} XData blocks in the file")
        
        rules = []
        for i, (xdata_name, xdata_content) in enumerate(xdata_blocks, 1):
            logger.debug(f"XData block {i}: {xdata_name.strip()}")
            logger.debug(f"XData content sample: {xdata_content[:200]}...")
            
            if 'RuleDefinition' in xdata_name:
                logger.info(f"Found RuleDefinition in XData block: {xdata_name}")
                # This is where the routing rules are defined
                rules = _parse_rule_definition(xdata_content)
            else:
                logger.debug(f"Skipping XData block {xdata_name} (not a RuleDefinition)")
        
        return {
            'name': rule_name,
            'description': description,
            'rules': rules,
            'source_file': str(file_path)
        }
    except Exception as e:
        logger.error(f"Error parsing routing rule file: {str(e)}", exc_info=True)
        return {
            'name': "Error",
            'description': f"Error parsing file: {str(e)}",
            'rules': [],
            'source_file': str(file_path)
        }

def _parse_rule_definition(xdata_content: str) -> List[Dict]:
    """Parse the RuleDefinition XData block to extract routing rules."""
    logger.info("Parsing RuleDefinition XData block")
    rules = []
    
    # Log a sample of the content being parsed
    logger.debug(f"XData content to parse: {xdata_content[:500]}...")
    
    # Find all Rule elements
    rule_pattern = r'<Rule\s+name="([^"]+)"[^>]*>([\s\S]*?)</Rule>'
    rule_matches = list(re.finditer(rule_pattern, xdata_content))
    
    logger.info(f"Found {len(rule_matches)} Rule elements in RuleDefinition")
    
    for i, match in enumerate(rule_matches, 1):
        try:
            rule_name = match.group(1)
            rule_content = match.group(2)
            
            logger.debug(f"Processing Rule {i}: {rule_name}")
            logger.debug(f"Rule content: {rule_content[:200]}...")
            
            # Extract rule condition
            condition_match = re.search(r'<condition>([\s\S]*?)</condition>', rule_content)
            condition = condition_match.group(1).strip() if condition_match else ""
            
            if not condition:
                logger.warning(f"No condition found in Rule: {rule_name}")
            
            # Extract rule actions
            actions = []
            action_matches = re.finditer(
                r'<action>\s*<![\s\S]*?<target>([^<]+)</target>\s*<value>([^<]+)</value>\s*</action>',
                rule_content
            )
            
            for j, action in enumerate(action_matches, 1):
                action_data = {
                    'target': action.group(1).strip(),
                    'value': action.group(2).strip()
                }
                actions.append(action_data)
                logger.debug(f"  Action {j}: {action_data}")
            
            if not actions:
                logger.warning(f"No actions found in Rule: {rule_name}")
            
            rule = {
                'name': rule_name,
                'condition': condition,
                'actions': actions
            }
            
            rules.append(rule)
            logger.info(f"Successfully parsed rule: {rule_name} with {len(actions)} actions")
            
        except Exception as e:
            logger.error(f"Error parsing Rule {i}: {str(e)}", exc_info=True)
    
    logger.info(f"Finished parsing RuleDefinition. Found {len(rules)} rules.")
    return rules
