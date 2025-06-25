"""
Tests for the GraphExtractor class.
"""
import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.graph_extractor import GraphExtractor

class TestGraphExtractor(unittest.TestCase):
    """Test cases for GraphExtractor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_data_dir = Path(__file__).parent.parent / 'test_data'
        self.sample_production = self.test_data_dir / 'TestProduction.cls'
        self.sample_routing = self.test_data_dir / 'TestRoutingRule.cls'
        
        # Ensure test data directory exists
        self.test_data_dir.mkdir(exist_ok=True)
        
        # Create sample test files if they don't exist
        if not self.sample_production.exists():
            self.sample_production.write_text("""
            Class Test.Production Extends Ens.Production
            {
            XData ProductionDefinition
            {
            <Production Name="Test.Production" LogGeneralTraceEvents="true">
              <ActorPoolSize>2</ActorPoolSize>
              <Item Name="TestService" Category="" ClassName="Test.Service" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
                <Setting Target="Host" Name="TargetConfigNames">TestRouter</Setting>
              </Item>
              <Item Name="TestRouter" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
                <Setting Target="Host" Name="BusinessRuleName">Test.RouterRoutingRule</Setting>
              </Item>
              <Item Name="TestOperation" Category="" ClassName="Test.Operation" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
                <Setting Target="Host" Name="TargetConfigNames"></Setting>
              </Item>
            </Production>
            }
            }
            """)
            
        if not self.sample_routing.exists():
            self.sample_routing.write_text("""
            Class Test.RouterRoutingRule Extends Ens.Rule.Definition
            {
              XData RuleDefinition [ XMLNamespace = "http://www.intersystems.com/rule" ]
              {
                <RuleDefinition>
                  <Rule Name="RouteToTest" InPort="" OutPort="">
                    <constraint name="source" value="TestService" />
                    <when condition="1">
                      <send target="TestOperation" />
                    </when>
                  </Rule>
                </RuleDefinition>
              }
            }
            """)
    
    def test_extract_from_files(self):
        """Test extracting graph data from production and routing rule files."""
        extractor = GraphExtractor()
        graph_data = extractor.extract_from_files(
            str(self.sample_production),
            str(self.sample_routing)
        )
        
        # Verify basic structure
        self.assertIn('nodes', graph_data)
        self.assertIn('relationships', graph_data)
        self.assertIn('metadata', graph_data)
        
        # Verify nodes were extracted
        self.assertGreater(len(graph_data['nodes']), 0, "No nodes were extracted")
        
        # Verify relationships were extracted
        self.assertGreater(len(graph_data['relationships']), 0, "No relationships were extracted")
        
        # Verify node types
        node_types = {node['type'] for node in graph_data['nodes']}
        self.assertIn('Test.Service', node_types, "Service node not found")
        self.assertIn('EnsLib.HL7.MsgRouter.RoutingEngine', node_types, "Router node not found")
        self.assertIn('Test.Operation', node_types, "Operation node not found")
        
        # Verify relationships
        rel_sources = {rel['source'] for rel in graph_data['relationships']}
        rel_targets = {rel['target'] for rel in graph_data['relationships']}
        node_names = {node['name'] for node in graph_data['nodes']}
        
        self.assertIn('TestService', node_names, "TestService node not found")
        self.assertIn('TestOperation', node_names, "TestOperation node not found")
        
        # Check if there's a relationship from TestService to TestOperation
        has_relationship = any(
            rel['source'] == 'TestService' and rel['target'] == 'TestOperation'
            for rel in graph_data['relationships']
        )
        self.assertTrue(has_relationship, "Expected relationship from TestService to TestOperation not found")

if __name__ == '__main__':
    unittest.main()
