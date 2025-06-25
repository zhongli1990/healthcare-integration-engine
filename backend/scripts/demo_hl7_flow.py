"""
Demo script for end-to-end HL7 message processing flow.

This script demonstrates:
1. Sending an HL7 message to the API
2. Processing the message through the pipeline
3. Viewing the processed message and routing results
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.messaging.hl7 import HL7Message
from app.core.messaging.hl7_processor import hl7_message_processor
from app.core.messaging.message_store import message_store
from app.core.messaging.neo4j_client import Neo4jClient

# Sample HL7 messages
SAMPLE_ADT_A01 = """MSH|^~\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEIVING_FACILITY|20230624120000||ADT^A01|MSG00001|P|2.5|EVN|A01|20230624120000|PID|1||12345||DOE^JOHN^A||19700101|M||2106-3|123 MAIN ST^^ANYTOWN^CA^12345||555-555-1234|555-555-5678|ENG|S|CDM|123-45-6789||PV1|1|O|OP7^^^^^||||37^DISNEY^WALT^A^^^MD|37^DISNEY^WALT^A^^^MD|09|||||||||123456^DISNEY^WALT^A^^^MD|7654321||450|A0"""

SAMPLE_ORU_R01 = """MSH|^~\&|LIS|LAB|EHR|HOSPITAL|20230624120000||ORU^R01|MSG00002|P|2.5|PID|1||12345||DOE^JOHN^A||19700101|M||2106-3|123 MAIN ST^^ANYTOWN^CA^12345||555-555-1234|555-555-5678|ENG|S|CDM|123-45-6789||OBR|1|12345678^LIS|987654321^LIS|LAB123^COMPREHENSIVE METABOLIC PANEL|||20230624110000|||||||||123456^DISNEY^WALT^A^^^MD|||||||||||20230624120000||LAB|F||1^^^R||^^^^^ROBX|1|NM|GLU^GLUCOSE|1|90|mg/dL|70-100|N|F|||20230624113000"""

async def init_neo4j() -> None:
    """Initialize Neo4j with sample routing rules."""
    neo4j = Neo4jClient()
    
    # Clear existing data
    await neo4j.execute_write("""
    MATCH (n) DETACH DELETE n
    """)
    
    # Create sample routing rules
    await neo4j.execute_write("""
    // Create sample systems
    CREATE (ehr:System {id: 'ehr_system', name: 'EHR System', type: 'EHR'})
    CREATE (lis:System {id: 'lis_system', name: 'Lab System', type: 'LIS'})
    CREATE (analytics:System {id: 'analytics_warehouse', name: 'Analytics Warehouse', type: 'ANALYTICS'})
    
    // Create message types
    CREATE (adt:MessageType {id: 'ADT_A01', name: 'ADT^A01', description: 'Admit/Visit Notification'})
    CREATE (oru:MessageType {id: 'ORU_R01', name: 'ORU^R01', description: 'Observation Result'})
    
    // Create routing rules
    // Rule 1: Route all ADT messages to EHR and Analytics
    CREATE (rule1:RoutingRule {
        id: 'rule_adt_route',
        name: 'Route ADT Messages',
        condition: 'message_type == "ADT_A01"',
        priority: 1
    })
    
    // Rule 2: Route all ORU messages to EHR
    CREATE (rule2:RoutingRule {
        id: 'rule_oru_route',
        name: 'Route ORU Messages',
        condition: 'message_type == "ORU_R01"',
        priority: 1
    })
    
    // Create relationships
    MATCH (ehr:System {id: 'ehr_system'}), (adt:MessageType {id: 'ADT_A01'})
    CREATE (ehr)-[:RECEIVES {protocol: 'HL7v2', endpoint: 'tcp://ehr:2575'}]->(adt)
    
    MATCH (ehr:System {id: 'ehr_system'}), (oru:MessageType {id: 'ORU_R01'})
    CREATE (ehr)-[:RECEIVES {protocol: 'HL7v2', endpoint: 'tcp://ehr:2575'}]->(oru)
    
    MATCH (analytics:System {id: 'analytics_warehouse'}), (adt:MessageType {id: 'ADT_A01'})
    CREATE (analytics)-[:RECEIVES {protocol: 'REST', endpoint: 'https://analytics/api/hl7'}]->(adt)
    
    // Apply routing rules
    MATCH (adt:MessageType {id: 'ADT_A01'}), (rule:RoutingRule {id: 'rule_adt_route'})
    CREATE (adt)-[:HAS_ROUTE]->(rule)
    
    MATCH (oru:MessageType {id: 'ORU_R01'}), (rule:RoutingRule {id: 'rule_oru_route'})
    CREATE (oru)-[:HAS_ROUTE]->(rule)
    """)
    
    print("✅ Neo4j initialized with sample routing rules")

async def process_sample_message(hl7_message: str, message_type: str, source_system: str) -> Dict[str, Any]:
    """Process a sample HL7 message through the pipeline."""
    print(f"\n📤 Processing {message_type} message from {source_system}")
    print("-" * 80)
    
    # Create and process the message
    message = HL7Message(
        message_id=f"DEMO_{message_type}_{int(asyncio.get_event_loop().time())}",
        raw_message=hl7_message,
        source_system=source_system,
        metadata={
            "demo": True,
            "source": "demo_script"
        }
    )
    
    try:
        # Process the message
        result = await hl7_message_processor.process_message(message)
        print(f"✅ Message processed successfully")
        print(f"Message ID: {result['message_id']}")
        print(f"Status: {result['status']}")
        print(f"Destinations: {', '.join(result.get('destinations', []))}")
        
        # Get the stored message
        stored_msg = await message_store.get_message(result['message_id'])
        if stored_msg:
            print("\n📄 Stored message details:")
            print(f"Status: {stored_msg.get('status')}")
            print(f"Source: {stored_msg.get('source_system')}")
            print(f"Type: {stored_msg.get('message_type')}")
            print(f"Created: {stored_msg.get('created_at')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error processing message: {str(e)}")
        raise

async def main():
    """Run the demo."""
    print("🚀 Starting HL7 Message Processing Demo")
    print("=" * 80)
    
    try:
        # Initialize Neo4j with sample data
        print("\n🔧 Initializing Neo4j with sample routing rules...")
        await init_neo4j()
        
        # Process an ADT message
        print("\n📨 Sending ADT^A01 message...")
        adt_result = await process_sample_message(
            SAMPLE_ADT_A01,
            "ADT_A01",
            "registration_system"
        )
        
        # Process an ORU message
        print("\n📨 Sending ORU^R01 message...")
        oru_result = await process_sample_message(
            SAMPLE_ORU_R01,
            "ORU_R01",
            "lab_system"
        )
        
        print("\n✅ Demo completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 All done!")

if __name__ == "__main__":
    asyncio.run(main())
