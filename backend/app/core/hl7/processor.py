from typing import Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class HL7Processor:
    """Process HL7 messages from files"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with processing configuration"""
        self.config = config
        self.processed_count = 0
        self.error_count = 0
    
    async def process_file(self, file_path: Path) -> Dict[str, Any]:
        """Process a single HL7 file"""
        try:
            # Read and validate HL7 message
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Basic HL7 validation
            if not content.startswith('MSH|'):
                raise ValueError("Invalid HL7 message: Missing MSH segment")
                
            # Extract basic message info
            segments = content.split('\r')
            msh_segment = segments[0].split('|')
            
            message_info = {
                'message_type': msh_segment[8] if len(msh_segment) > 8 else 'UNKNOWN',
                'message_control_id': msh_segment[9] if len(msh_segment) > 9 else 'UNKNOWN',
                'processing_id': msh_segment[10] if len(msh_segment) > 10 else 'UNKNOWN',
                'timestamp': msh_segment[6] if len(msh_segment) > 6 else 'UNKNOWN',
                'content': content
            }
            
            self.processed_count += 1
            return message_info
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error processing file {file_path}: {str(e)}")
            raise
    
    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics"""
        return {
            'processed': self.processed_count,
            'errors': self.error_count
        }
