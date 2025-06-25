"""
Parser for IRIS production files (.cls).
"""
import re
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)


def parse_production_file(file_path: str) -> Dict:
    """
    Parse an IRIS production file and extract components and their configurations.
    
    Args:
        file_path: Path to the production .cls file
        
    Returns:
        Dict containing the parsed production data
    """
    logger.info(f"Starting to parse production file: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.debug(f"File content size: {len(content)} bytes")
        
        # Extract production class name
        class_match = re.search(r'Class\s+([^\s\(]+)', content)
        production_name = class_match.group(1) if class_match else "UnknownProduction"
        logger.info(f"Found production class: {production_name}")
        
        # Extract production description if available
        description_match = re.search(r'Description\s*=\s*"([^"]*)"', content)
        description = description_match.group(1) if description_match else ""
        
        # Find all XData blocks which contain component definitions
        xdata_blocks = re.findall(
            r'XData\s+([^\s{]+)\s*\{([^}]*)\}',
            content,
            re.DOTALL
        )
        
        logger.info(f"Found {len(xdata_blocks)} XData blocks in the file")
        
        components = []
        for i, (xdata_name, xdata_content) in enumerate(xdata_blocks, 1):
            logger.debug(f"XData block {i}: {xdata_name.strip()}")
            logger.debug(f"XData content sample: {xdata_content[:200]}...")
            
            if 'ProductionDefinition' in xdata_name:
                logger.info(f"Found ProductionDefinition in XData block: {xdata_name}")
                # This is where the production components are defined
                components = _parse_production_definition(xdata_content)
            else:
                logger.debug(f"Skipping XData block {xdata_name} (not a ProductionDefinition)")
        
        return {
            'name': production_name,
            'description': description,
            'components': components,
            'source_file': str(file_path)
        }
    except Exception as e:
        logger.error(f"Error parsing production file: {str(e)}", exc_info=True)
        return {
            'name': "Error",
            'description': f"Error parsing file: {str(e)}",
            'components': [],
            'source_file': str(file_path)
        }

def _parse_production_definition(xdata_content: str) -> List[Dict]:
    """Parse the ProductionDefinition XData block to extract components."""
    logger.info("Parsing ProductionDefinition XData block")
    components = []
    
    # Log a sample of the content being parsed
    logger.debug(f"XData content to parse: {xdata_content[:500]}...")
    
    # Find all Item elements which define components
    item_pattern = r'<Item[^>]*\s+name="([^"]+)"[^>]*>([\s\S]*?)</Item>'
    item_matches = list(re.finditer(item_pattern, xdata_content))
    
    logger.info(f"Found {len(item_matches)} Item elements in ProductionDefinition")
    
    for i, match in enumerate(item_matches, 1):
        try:
            item_name = match.group(1)
            item_content = match.group(2)
            
            logger.debug(f"Processing Item {i}: {item_name}")
            logger.debug(f"Item content: {item_content[:200]}...")
            
            # Extract component type (class name)
            class_match = re.search(r'ClassName\s*=\s*"([^"]+)"', item_content)
            if not class_match:
                logger.warning(f"No ClassName found in Item: {item_name}")
                continue
                
            component_type = class_match.group(1)
            logger.debug(f"Component type: {component_type}")
            
            # Extract all settings
            settings = {}
            setting_matches = re.finditer(
                r'<Setting\s+target="([^"]+)"\s+value="([^"]*)"\s*/>',
                item_content
            )
            
            for setting in setting_matches:
                settings[setting.group(1)] = setting.group(2)
            
            logger.debug(f"Found {len(settings)} settings for {item_name}")
            
            component = {
                'name': item_name,
                'type': component_type,
                'settings': settings
            }
            
            components.append(component)
            logger.info(f"Successfully parsed component: {item_name} ({component_type})")
            
        except Exception as e:
            logger.error(f"Error parsing Item {i}: {str(e)}", exc_info=True)
    
    logger.info(f"Finished parsing ProductionDefinition. Found {len(components)} components.")
    return components
