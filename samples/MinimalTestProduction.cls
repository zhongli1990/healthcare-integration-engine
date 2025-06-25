Class Test.MinimalProduction Extends Ens.Production [ Not ProcedureBlock ]
{
XData ProductionDefinition
{
<Production Name="Test.MinimalProduction" TestingEnabled="true" LogGeneralTraceEvents="true">
  <Description>Minimal test production with 3 components</Description>
  <ActorPoolSize>1</ActorPoolSize>
  
  <Item Name="Test.Service" Category="Test" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="true">
    <Setting Target="Host" Name="MessageSchemaCategory">2.4</Setting>
    <Setting Target="Host" Name="TargetConfigNames">Test.Router</Setting>
    <Setting Target="Adapter" Name="Port">1234</Setting>
  </Item>
  
  <Item Name="Test.Router" Category="Test" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true">
    <Setting Target="Host" Name="BusinessRuleName">Test.Router.Rules</Setting>
  </Item>
  
  <Item Name="Test.Operation" Category="Test" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true">
    <Setting Target="Adapter" Name="IPAddress">127.0.0.1</Setting>
    <Setting Target="Adapter" Name="Port">5678</Setting>
  </Item>
  
</Production>
}
}
