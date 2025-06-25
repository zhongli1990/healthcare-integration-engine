Class Test.RoutingRule Extends Ens.Rule.Definition
{

Parameter RuleAssistClass = "EnsLib.HL7.MsgRouter.RuleAssist";

XData RuleDefinition [ XMLNamespace = "http://www.intersystems.com/rule" ]
{
<ruleDefinition alias="" context="EnsLib.HL7.MsgRouter.RoutingEngine" production="">
<ruleSet name="" effectiveBegin="" effectiveEnd="">
<rule name="Route ADT Messages" disabled="false">
<constraint name="source" value="HL7.Service.FileService"></constraint>
<constraint name="docCategory" value="2.5.1"></constraint>
<constraint name="docName" value="ADT_A01,ADT_A04,ADT_A08"></constraint>
<when condition="1" comment="">
<send transform="" target="HL7.Operation.FileOperation"></send>
<return></return>
</when>
</rule>
<rule name="Route ORU Messages" disabled="false">
<constraint name="source" value="HL7.Service.FileService"></constraint>
<constraint name="docCategory" value="2.5.1"></constraint>
<constraint name="docName" value="ORU_R01"></constraint>
<when condition="1" comment="">
<send transform="" target="HL7.Operation.FileOperation"></send>
<return></return>
</when>
</rule>
<rule name="Default Route" disabled="false">
<constraint name="source" value="HL7.Service.FileService"></constraint>
<when condition="1">
<send transform="" target="HL7.Operation.FileOperation"></send>
<return></return>
</when>
</rule>
</ruleSet>
</ruleDefinition>
}

}
