Class Test.Production Extends Ens.Production
{

XData ProductionDefinition
{
<Production Name="Test.Production" TestingEnabled="true" LogGeneralTraceEvents="true">
  <Description></Description>
  <ActorPoolSize>2</ActorPoolSize>
  <Item Name="HL7.Service.FileService" Category="" ClassName="EnsLib.HL7.Service.FileService" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="TargetConfigNames">HL7.Router.RoutingEngine</Setting>
    <Setting Target="Host" Name="MessageSchemaCategory">2.5.1</Setting>
    <Setting Target="Host" Name="LocalFacilityApplication">HOSPITAL</Setting>
    <Setting Target="Host" Name="FileAccessTimeout">10</Setting>
    <Setting Target="Host" Name="FilePath">/irisdev/app/input</Setting>
    <Setting Target="Host" Name="FileSpec">*.hl7</Setting>
    <Setting Target="Host" Name="ArchivePath">/irisdev/app/archive</Setting>
  </Item>
  <Item Name="HL7.Operation.FileOperation" Category="" ClassName="EnsLib.HL7.Operation.FileOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="Filename">HL7_Out_%Q%!+(_a).hl7</Setting>
    <Setting Target="Host" Name="FilePath">/irisdev/app/output</Setting>
    <Setting Target="Host" Name="AutoBatchParentSegs">1</Setting>
  </Item>
  <Item Name="HL7.Router.RoutingEngine" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">Test.RoutingRule</Setting>
  </Item>
</Production>
}

}
