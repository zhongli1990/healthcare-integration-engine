Class BHRUH.Production.ADTProdudction Extends Ens.Production [ Not ProcedureBlock ]
{

XData ProductionDefinition
{
<Production Name="BHRUH.Production.ADTProdudction" TestingEnabled="true" LogGeneralTraceEvents="true">
  <Description></Description>
  <ActorPoolSize>1</ActorPoolSize>
  <Item Name="to.Aqure.ADT" Category="Aqure" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.117.106</Setting>
    <Setting Target="Adapter" Name="Port">2005</Setting>
  </Item>
  <Item Name="to.Cyberlab.ADT" Category="Cyberlab" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.99.52</Setting>
    <Setting Target="Adapter" Name="Port">45501</Setting>
    <Setting Target="Adapter" Name="LocalInterface">10.124.117.64 (IPv4 Ethernet0)</Setting>
    <Setting Target="Host" Name="ReplyCodeActions">:?R=F,:?E=S,:~=S,:?A=C,:*=S,:I?=W,:T?=C</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
    <Setting Target="Host" Name="FailureTimeout">15</Setting>
  </Item>
  <Item Name="to.ICNet.ADT" Category="ICNet" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="Info from Baxter: 27.12.24 Test Server - 24580 (used below) [feeds the dev sandbox] Live server: 10.124.117.13 (used below) PAS Live port is 24570  Lab Live port is 34570 LS (Live Staging) and Live use the same live port.   VMSVRICNETUAT01 [10.124.117.166]." LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.117.13</Setting>
    <Setting Target="Adapter" Name="Port">24580</Setting>
    <Setting Target="Host" Name="ReplyCodeActions">:?R=F,:?E=S,:~=S,:?A=C,:*=S,:I?=W,:T?=C</Setting>
    <Setting Target="Adapter" Name="ConnectTimeout">30</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
  </Item>
  <Item Name="to.iFit.ADT" Category="iFit" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.117.29</Setting>
    <Setting Target="Adapter" Name="Port">6661</Setting>
  </Item>
  <Item Name="to.InfoflexCIMS.ADT" Category="C1" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="TEST 10.124.101.33:9001 LIVE 10.124.101.32:9000 VMSVRIFLEX01" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.101.33</Setting>
    <Setting Target="Adapter" Name="Port">9001</Setting>
    <Setting Target="Host" Name="ReplyCodeActions">:?R=F,:?E=F,:~=S,:?A=C,:*=S,:I?=W</Setting>
  </Item>
  <Item Name="to.WinPath.ADT" Category="WinPath" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.99.50</Setting>
    <Setting Target="Adapter" Name="Port">17001</Setting>
    <Setting Target="Adapter" Name="LocalInterface">10.124.117.64 (IPv4 Ethernet0)</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
    <Setting Target="Host" Name="ReplyCodeActions">:?R=S,:?E=S,:~=S,:?A=C,:*=S,:I?=W,:T?=C</Setting>
  </Item>
  <Item Name="to.Viewpoint.ADT" Category="C1" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.101.22</Setting>
    <Setting Target="Adapter" Name="Port">8300</Setting>
  </Item>
  <Item Name="to.CaptureStroke.ADT" Category="C1" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="false" Foreground="false" Comment="Re-enable later. is hosted off-site on one of CaptureStroke&apos;s Redcentric servers 10.41.130.61:7110" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.41.130.61</Setting>
    <Setting Target="Adapter" Name="Port">7110</Setting>
    <Setting Target="Adapter" Name="LocalInterface">10.124.117.64 (IPv4 Ethernet0)</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
  </Item>
  <Item Name="Placeholder Careflow medicines ADT" Category="" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="false" Foreground="false" Comment="no test system" LogTraceEvents="false" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.117.25</Setting>
    <Setting Target="Adapter" Name="Port">56773</Setting>
    <Setting Target="Adapter" Name="LocalInterface">10.124.117.64 (IPv4 Ethernet0)</Setting>
  </Item>
  <Item Name="to.Omnicell.ADT" Category="Omnicell" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="&lt;!&gt; SAME IP AS LIVE Different port for test.  Back-end points to test DB: CPC99  VMSVRK2SQL01 = 10.124.117.33" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">VMSVROMNI01</Setting>
    <Setting Target="Adapter" Name="Port">51000</Setting>
    <Setting Target="Adapter" Name="LocalInterface"></Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
  </Item>
  <Item Name="to.Sectra.ADT" Category="Sectra" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="MS:Natted to 10.124.119.250 after being sent to 10.7.232.72" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.7.232.72</Setting>
    <Setting Target="Adapter" Name="Port">7911</Setting>
    <Setting Target="Adapter" Name="LocalInterface">10.124.117.64 (IPv4 Ethernet0)</Setting>
    <Setting Target="Adapter" Name="ReconnectRetry">10</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
  </Item>
  <Item Name="to.SCR.ADT" Category="C1" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="10.124.117.49 6671 (port 6670 is LIVE) 
Renabled EPR to SCR 24.1 Test by Clint 20 June.
Disabled in ADT_MOCK by CC 5 June 2025 for live testing from CareFlow via TEST namespace for the SCR 24.1 upgrade, part of BAU activity not EPR." LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.117.49</Setting>
    <Setting Target="Adapter" Name="Port">6671</Setting>
    <Setting Target="Host" Name="ReplyCodeActions">:?R=F,:?E=S,:~=S,:?A=C,:*=S,:I?=W,:T?=C</Setting>
  </Item>
  <Item Name="to.SCRRMS.ADT" Category="C1" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="Renabled EPR to SCR RMS 24.1 Test by Clint 20 June.
SCR RMS does not report on Brain, it reports on: • Breast • Collorectal • Haematology • Prostate 

Disabled CC 5 June 2025 for live testing vis TEST (SCR 24.1 upgrade)" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.117.16</Setting>
    <Setting Target="Adapter" Name="Port">6691</Setting>
    <Setting Target="Host" Name="ReplyCodeActions">:?R=F,:?E=F,:~=S,:?A=C,:*=S,:I?=W</Setting>
  </Item>
  <Item Name="to.Varian.ADT" Category="Varian" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="Live: 172.20.118.154 test: 172.20.118.170  The internal IP of the TBox test server is 172.20.4.150 " LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">172.20.118.170</Setting>
    <Setting Target="Adapter" Name="Port">11002</Setting>
    <Setting Target="Adapter" Name="LocalInterface">10.124.117.64 (IPv4 Ethernet0)</Setting>
  </Item>
  <Item Name="to.SolusEndoscopy.ADT" Category="Solus" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.117.69</Setting>
    <Setting Target="Adapter" Name="Port">9000</Setting>
  </Item>
  <Item Name="to.SolusCardiology.ADT" Category="Solus" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="aka Solus Clinical  HN: VMSVRSOLCUAT01" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.101.67</Setting>
    <Setting Target="Adapter" Name="Port">9000</Setting>
  </Item>
  <Item Name="TCP_Discard" Category="" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="false" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">127.0.0.1</Setting>
  </Item>
  <Item Name="Main ADT Router" Category="Oracle Health, C1" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.ADTGeneral</Setting>
    <Setting Target="Host" Name="Validation"></Setting>
  </Item>
  <Item Name="to.OH.QRY" Category="Oracle Health,Medicus,mediSIGHT" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="BHR_ADT_QUERY (Millennium Ref)
todo: hostname  Incoming queries interface for Millenium" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">104.170.248.172</Setting>
    <Setting Target="Adapter" Name="Port">6002</Setting>
    <Setting Target="Host" Name="AlertOnError">1</Setting>
    <Setting Target="Adapter" Name="LocalInterface">10.124.117.64 (IPv4 Ethernet0)</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
    <Setting Target="Adapter" Name="ConnectTimeout">55</Setting>
    <Setting Target="Adapter" Name="ReadTimeout">50</Setting>
    <Setting Target="Adapter" Name="ResponseTimeout">55</Setting>
  </Item>
  <Item Name="from.TEST.QRY" Category="" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="false" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
    <Setting Target="Host" Name="MessageSchemaCategory">2.3.CER</Setting>
    <Setting Target="Host" Name="TargetConfigNames">Main QRY Router</Setting>
    <Setting Target="Adapter" Name="Port">55556</Setting>
    <Setting Target="Host" Name="AckMode">App</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
  </Item>
  <Item Name="Local_Service_TEST_TCP" Category="Medicus,Oracle Health,mediSIGHT" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="false" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">127.0.0.1</Setting>
    <Setting Target="Adapter" Name="Port"></Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
  </Item>
  <Item Name="from.Medicus.QRY" Category="Medicus" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="2" Enabled="true" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
    <Setting Target="Host" Name="MessageSchemaCategory">2.4</Setting>
    <Setting Target="Host" Name="TargetConfigNames">Main QRY Router custom</Setting>
    <Setting Target="Adapter" Name="Port">7567</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
    <Setting Target="Adapter" Name="JobPerConnection">1</Setting>
    <Setting Target="Host" Name="AckMode">App</Setting>
    <Setting Target="Adapter" Name="ReadTimeout">10</Setting>
    <Setting Target="Adapter" Name="StayConnected">10</Setting>
  </Item>
  <Item Name="Main MFN Router" Category="Oracle Health" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.MFNGeneral</Setting>
    <Setting Target="Host" Name="Validation"></Setting>
  </Item>
  <Item Name="from.mediSight.QRY" Category="mediSIGHT" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="true" Foreground="false" Comment="test system: VMSVRMDSGTUAT01, under the IP - 10.124.117.74" LogTraceEvents="true" Schedule="">
    <Setting Target="Host" Name="MessageSchemaCategory">MEDISOFT2.3.1</Setting>
    <Setting Target="Host" Name="TargetConfigNames">Main QRY Router custom</Setting>
    <Setting Target="Adapter" Name="Port">4444</Setting>
    <Setting Target="Adapter" Name="StayConnected">10</Setting>
    <Setting Target="Host" Name="AckMode">App</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
    <Setting Target="Adapter" Name="ReadTimeout">10</Setting>
    <Setting Target="Adapter" Name="JobPerConnection">1</Setting>
  </Item>
  <Item Name="SCR Router" Category="C1" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="Replaces Cancer Registry" LogTraceEvents="true" Schedule="">
    <Setting Target="Host" Name="Validation">dm-z</Setting>
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.SCRRoutingRules</Setting>
  </Item>
  <Item Name="to.SCR.DroppedFiles" Category="" ClassName="EnsLib.HL7.Operation.FileOperation" PoolSize="1" Enabled="false" Foreground="false" Comment="Disabled until required." LogTraceEvents="false" Schedule="">
    <Setting Target="Adapter" Name="FilePath">E:\Test\CancerReg</Setting>
    <Setting Target="Host" Name="Filename">%f_%Q</Setting>
  </Item>
  <Item Name="to.E3.ADT" Category="" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="Call outstanding to Test he patient. " LogTraceEvents="false" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.117.38</Setting>
    <Setting Target="Adapter" Name="Port">9205</Setting>
    <Setting Target="Host" Name="FailureTimeout">60</Setting>
    <Setting Target="Host" Name="RetryInterval">20</Setting>
    <Setting Target="Host" Name="ReplyCodeActions">:?R=F,:?E=S,:~=S,:?A=C,:*=S,:I?=W,:T?=C</Setting>
  </Item>
  <Item Name="to.K2.ADT" Category="" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="10.169.184.172  " LogTraceEvents="false" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.117.33</Setting>
    <Setting Target="Adapter" Name="Port">30105</Setting>
    <Setting Target="Host" Name="ReplyCodeActions">:?R=F,:?E=S,:~=S,:?A=C,:*=S,:I?=W,:T?=C</Setting>
  </Item>
  <Item Name="to.PKB" Category="C1" ClassName="PKBBHR.Operation.DefaultAcceptMessagePort" PoolSize="1" Enabled="false" Foreground="false" Comment="CC 28/04 Disabled whilst new endpoint is implemented. " LogTraceEvents="false" Schedule="">
    <Setting Target="Adapter" Name="ConnectTimeout">15</Setting>
    <Setting Target="Adapter" Name="Credentials">org_bhrut</Setting>
    <Setting Target="Adapter" Name="ResponseTimeout">45</Setting>
    <Setting Target="Adapter" Name="SOAPCredentials">org_bhrut</Setting>
    <Setting Target="Adapter" Name="SSLConfig">PKB_Client</Setting>
  </Item>
  <Item Name="to.HaemonteticsTEG.ADT" Category="Haemonetics TEG" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.101.167</Setting>
    <Setting Target="Adapter" Name="Port">50005</Setting>
  </Item>
  <Item Name="to.CareflowMedicinesManager.ADT" Category="" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="test needs updating- jira" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.117.25</Setting>
    <Setting Target="Adapter" Name="Port">5600</Setting>
    <Setting Target="Adapter" Name="LocalInterface">10.124.117.64 (IPv4 Ethernet0)</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
    <Setting Target="Adapter" Name="StayConnected">-1</Setting>
    <Setting Target="Host" Name="ReplyCodeActions">:?R=F,:?E=S,:~=S,:?A=C,:*=S,:I?=W,:T?=C</Setting>
  </Item>
  <Item Name="Haemonetics TEG ADT" Category="Haemonetics TEG, M1" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.HaemoneticsTEGADT</Setting>
    <Setting Target="Host" Name="Validation"></Setting>
  </Item>
  <Item Name="Aqure ADT" Category="Aqure,RAK, RRS" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.AqureADT</Setting>
    <Setting Target="Host" Name="Validation"></Setting>
  </Item>
  <Item Name="FutureAppointments.SIU" Category="" ClassName="EnsLib.HL7.Operation.FileOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="FilePath">D:\FileOutput\FutureAppointmentsSIU_9December2024\</Setting>
    <Setting Target="Host" Name="Filename">FutureAppointment_%f_%Q%!+(_a).txt</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
  </Item>
  <Item Name="Main QRY Router custom" Category="Oracle Health,mediSIGHT,Medicus,CardioBridge" ClassName="BHRUH.Process.OracleHealthQRYRouter" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
  </Item>
  <Item Name="PKB Exclude" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="Validation"></Setting>
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.PKBRoutingRulesExclude</Setting>
  </Item>
  <Item Name="PKB Router" Category="C1" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="Send to PKB RouterOP if not an E (Emergency) Patient" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="Validation"></Setting>
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.PKBRoutingRules0</Setting>
  </Item>
  <Item Name="PKB A38" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="false" Foreground="false" Comment=" " LogTraceEvents="true" Schedule="">
    <Setting Target="Host" Name="Validation"></Setting>
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.PKBRoutingRules0A38</Setting>
  </Item>
  <Item Name="PKB NSTS" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="Validation"></Setting>
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.PKBRoutingRulesNSTS</Setting>
  </Item>
  <Item Name="PKB Other" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="Validation"></Setting>
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.PKBRoutingRulesOther</Setting>
  </Item>
  <Item Name="PKB PDIY" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="PDIY (Patient Death Indicator = Y)" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="Validation"></Setting>
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.PKBRoutingRulesPDIY</Setting>
  </Item>
  <Item Name="PKB RouterOP" Category="C1" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="false" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="Validation">dm-z</Setting>
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.PKBRoutingRules1</Setting>
  </Item>
  <Item Name="PKB U16" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="Validation"></Setting>
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.PKBRoutingRulesU16</Setting>
  </Item>
  <Item Name="Capture Stroke Router" Category="C1" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="false" Foreground="false" Comment="*** Descoped *** From Andy Hagan 20/12/2024: Laura Jones will not renew CaptureStroke in May 2025 and is intending to use Millennium for the same functionality." LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.CaptureADTRoutingRules</Setting>
    <Setting Target="Host" Name="Validation">dm-z</Setting>
  </Item>
  <Item Name="Roche Cobas Router" Category="C1" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="Roche Cobas Infinity POC" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.RocheCobasRoutingRules</Setting>
    <Setting Target="Host" Name="Validation">dm-z</Setting>
  </Item>
  <Item Name="to.RocheCobas.ADT" Category="C1" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="Server Name VMSVRROCHECBTST IP Address 10.124.117.162 " LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">VMSVRROCHECBTST</Setting>
    <Setting Target="Adapter" Name="Port">14001</Setting>
    <Setting Target="Adapter" Name="LocalInterface">10.124.117.64 (IPv4 Ethernet0)</Setting>
  </Item>
  <Item Name="InfoflexCIMS Router" Category="C1" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.InfoflexCIMSRoutingRules</Setting>
    <Setting Target="Host" Name="Validation">dm-z</Setting>
  </Item>
  <Item Name="Viewpoint Router" Category="C1" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="May change due to different workflow with Sectra" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.ViewpointRoutingRules</Setting>
    <Setting Target="Host" Name="Validation">dm-z</Setting>
  </Item>
  <Item Name="WinPath ADT" Category="WinPath, RUK" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.WinPathADT</Setting>
  </Item>
  <Item Name="Sectra ADT" Category="Sectra" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.SectraADT</Setting>
  </Item>
  <Item Name="EuroKing E3 ADT" Category="E3, RAC" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.EuroKingE3Router</Setting>
  </Item>
  <Item Name="From.E3.BabyReg" Category="E3" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="true" Foreground="false" Comment="Trturn port 9224/5" LogTraceEvents="true" Schedule="">
    <Setting Target="Host" Name="MessageSchemaCategory">2.4.E3</Setting>
    <Setting Target="Host" Name="TargetConfigNames">E3 Baby Reg Process</Setting>
    <Setting Target="Adapter" Name="Port">2010</Setting>
    <Setting Target="Host" Name="AckMode">App</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
  </Item>
  <Item Name="K2 Router" Category="RRS" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.K2RoutingRules</Setting>
    <Setting Target="Host" Name="ActOnTransformError">1</Setting>
    <Setting Target="Host" Name="ActOnValidationError">1</Setting>
  </Item>
  <Item Name="K2 Age" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="false" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.K2OtherRoutingRules</Setting>
  </Item>
  <Item Name="K2 Other" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="false" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.K2OtherRoutingRules</Setting>
  </Item>
  <Item Name="iFit Router" Category="iFit, RAK" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.iFitRoutingRules</Setting>
  </Item>
  <Item Name="ICNet Router" Category="ICNet, RAK" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.ICNetRoutingRules</Setting>
  </Item>
  <Item Name="Omnicell Router" Category="Omnicell, RAK" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="PV1-3.1 Has a Millennium Alias to CareFlow Short Code lookup." LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.OmnicellRouter</Setting>
  </Item>
  <Item Name="Varian Router" Category="Varian, RAK" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.VarianRoutingRules</Setting>
  </Item>
  <Item Name="CyberLab Router" Category="RRS" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.CyberLabRoutingRules</Setting>
    <Setting Target="Host" Name="ActOnTransformError">1</Setting>
    <Setting Target="Host" Name="ActOnValidationError">1</Setting>
  </Item>
  <Item Name="Solus Endoscopy ADT" Category="Solus, RAC" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.SolusEndoscopyADT</Setting>
  </Item>
  <Item Name="Solus Cardiology ADT" Category="Solus, RAC" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.SolusCardiologyADT</Setting>
  </Item>
  <Item Name="to.LabComms.ORU" Category="" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="false" Foreground="false" Comment="&lt;!&gt; Do not send/resend random test messages. This is a live interface. ----------------------------------- For email to GPS. Will be used by Sectra, but is currently owner by Labs ------------------------------- " LogTraceEvents="false" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.124.101.107</Setting>
    <Setting Target="Adapter" Name="Port">5002</Setting>
    <Setting Target="Adapter" Name="StayConnected">0</Setting>
  </Item>
  <Item Name="CMM Router" Category="RRS" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.CMMRoutingRules</Setting>
  </Item>
  <Item Name="WinPath Results PKB" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="false" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
    <Setting Target="Host" Name="Validation"></Setting>
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.WinpathResultsPKBRoutingRules</Setting>
  </Item>
  <Item Name="from.Winpath.Results.PKB" Category="" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="true" Foreground="false" Comment="Note the Main Winpath ORU (for PKB) feed is:
from.Winpath.ORU [OCS_MOCK]
From: 10.124.99.50 to port 9201

(port 7500 was mentioned, but why is unknown)
" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="TargetConfigNames">WinPath Results PKB</Setting>
    <Setting Target="Adapter" Name="Port">9201</Setting>
    <Setting Target="Host" Name="MessageSchemaCategory">ICE_OrderComms_Inbound_2.4</Setting>
    <Setting Target="Host" Name="UseAckCommitCodes">0</Setting>
    <Setting Target="Adapter" Name="JobPerConnection">1</Setting>
    <Setting Target="Adapter" Name="QSize">100</Setting>
  </Item>
  <Item Name="to.EmailAlert" Category="" ClassName="EnsLib.EMail.AlertOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="IncludeDetails">1</Setting>
    <Setting Target="Adapter" Name="From">alert-test-tie.bhrut@nhs.net</Setting>
    <Setting Target="Adapter" Name="Recipient">pia.boltiador1@nhs.net;clint.childs@nhs.net</Setting>
    <Setting Target="Adapter" Name="SMTPPort">587</Setting>
    <Setting Target="Adapter" Name="SMTPServer">send.nhs.net</Setting>
    <Setting Target="Adapter" Name="SSLConfig">AlertNHSMail*</Setting>
    <Setting Target="Adapter" Name="Credentials">AlertEmail</Setting>
    <Setting Target="Adapter" Name="Cc">Zhong.li2@nhs.net</Setting>
  </Item>
  <Item Name="Euroking QRY RSP Router" Category="E3" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.EurokingToCerner</Setting>
  </Item>
  <Item Name="to.PKB2" Category="C1" ClassName="PKBBHR.Operation.DefaultAcceptMessagePort" PoolSize="1" Enabled="false" Foreground="false" Comment="# Do Not USe# " LogTraceEvents="false" Schedule="">
    <Setting Target="Adapter" Name="ConnectTimeout">15</Setting>
    <Setting Target="Adapter" Name="Credentials">org_bhrut</Setting>
    <Setting Target="Adapter" Name="ResponseTimeout">45</Setting>
    <Setting Target="Adapter" Name="SOAPCredentials">org_bhrut</Setting>
    <Setting Target="Adapter" Name="SSLConfig">PKB_Client</Setting>
  </Item>
  <Item Name="from.CardioBridge.QRY" Category="CardioBridge" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="true" Foreground="false" Comment="from MAIN&apos;s CardioBridge app in the same TIE" LogTraceEvents="true" Schedule="">
    <Setting Target="Host" Name="MessageSchemaCategory">2.4</Setting>
    <Setting Target="Host" Name="TargetConfigNames">Main QRY Router custom</Setting>
    <Setting Target="Adapter" Name="Port">4445</Setting>
    <Setting Target="Adapter" Name="StayConnected">10</Setting>
    <Setting Target="Host" Name="AckMode">App</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
    <Setting Target="Adapter" Name="ReadTimeout">10</Setting>
    <Setting Target="Adapter" Name="JobPerConnection">1</Setting>
  </Item>
  <Item Name="Pre ADT Router" Category="ADT,Pre,Router" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="false" Foreground="false" Comment="not required?" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.PreADT</Setting>
    <Setting Target="Host" Name="RuleLogging">a</Setting>
  </Item>
  <Item Name="to File" Category="" ClassName="EnsLib.HL7.Operation.FileOperation" PoolSize="1" Enabled="false" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="Filename">%f_%Q%!+(_a)</Setting>
    <Setting Target="Adapter" Name="FilePath">D:\FileOutput\PAS_ADT2\</Setting>
  </Item>
  <Item Name="from.BHR.ADT1" Category="Oracle Health" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="true" Foreground="false" Comment="Millennium (Oracle Health) call this BHR_ADT_SIU_TCPIP_OUT (no number at the end) TIE reference from.BHR.ADT1" LogTraceEvents="true" Schedule="">
    <Setting Target="Host" Name="MessageSchemaCategory">2.3.CER</Setting>
    <Setting Target="Adapter" Name="Port">35001</Setting>
    <Setting Target="Host" Name="TargetConfigNames">Main ADT Router</Setting>
    <Setting Target="Host" Name="AlertOnError">1</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
  </Item>
  <Item Name="from.BHR.ADT2" Category="Oracle Health" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="true" Foreground="false" Comment="Millennium (Oracle Health) call this BHR_ADT_SIU_TCPIP_OUT_2 TIE reference from.BHR.ADT2" LogTraceEvents="true" Schedule="">
    <Setting Target="Host" Name="MessageSchemaCategory">2.3.CER</Setting>
    <Setting Target="Adapter" Name="Port">35002</Setting>
    <Setting Target="Host" Name="TargetConfigNames">Main ADT Router</Setting>
    <Setting Target="Host" Name="AlertOnError">1</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
  </Item>
  <Item Name="from.BHR.MFN" Category="Oracle Health" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="true" Foreground="false" Comment="Millennium (Oracle Health) call this BHR_MFN_TCPIP_OUT TIE reference from.BHR.MFN" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="MessageSchemaCategory">2.3.CER</Setting>
    <Setting Target="Adapter" Name="Port">35004</Setting>
    <Setting Target="Host" Name="TargetConfigNames">Main MFN Router</Setting>
  </Item>
  <Item Name="to.BHR.ADT" Category="Oracle Health" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="BHR_ADT_TCPIP_IN (Millennium Ref)" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">104.170.248.172</Setting>
    <Setting Target="Adapter" Name="Port">6001</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
  </Item>
  <Item Name="to.BHR.QRY" Category="Oracle Health,Medicus,mediSIGHT" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="false" Foreground="false" Comment="todo: hostname  Incoming queries interface for Millenium" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">104.170.248.172</Setting>
    <Setting Target="Adapter" Name="Port">6002</Setting>
    <Setting Target="Host" Name="AlertOnError">1</Setting>
    <Setting Target="Adapter" Name="LocalInterface">10.124.117.64 (IPv4 Ethernet0)</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
    <Setting Target="Adapter" Name="ConnectTimeout">10</Setting>
  </Item>
  <Item Name="to.BHR.SIU" Category="" ClassName="EnsLib.HL7.Operation.FileOperation" PoolSize="1" Enabled="false" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="FilePath">D:\FileOutput\FutureAppointmentsSIU_9December2024\</Setting>
    <Setting Target="Host" Name="Filename">FutureAppointment_%f_%Q%!+(_a).txt</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
  </Item>
  <Item Name="E3 Baby Reg Process" Category="E3,Reg,Process,Baby" ClassName="BHRUH.Process.E3BabyReg" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="true" Schedule="">
  </Item>
  <Item Name="from.BHR.PKB" Category="Oracle Health" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="true" Foreground="false" Comment="Millennium (Oracle Health) call this ADT_SIU_TL3_FOR_PKB TIE reference from.BHR.PKB Contains the SIU appointments messages generated due to the Datawarehouse data load into Millennium. Used by Trial Load 3 (TL3) " LogTraceEvents="true" Schedule="">
    <Setting Target="Host" Name="MessageSchemaCategory">2.3.CER</Setting>
    <Setting Target="Adapter" Name="Port">35023</Setting>
    <Setting Target="Host" Name="TargetConfigNames">PKB SIU (Data Load)</Setting>
    <Setting Target="Host" Name="AlertOnError">1</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
  </Item>
  <Item Name="PKB SIU (Data Load)" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="Validation"></Setting>
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.PKBRoutingRulesSIUDataLoad</Setting>
  </Item>
  <Item Name="RAM Alert Monitor" Category="RAM" ClassName="ReStart.RAM.Client.Services.AlertMonitor" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Adapter" Name="CallInterval">600</Setting>
    <Setting Target="Adapter" Name="IgnoreList">TCP_DISCARD,WINPATH RESULTS PKB,TO.PKB,K2 OTHER,K2 AGE,</Setting>
  </Item>
  <Item Name="RAM Router" Category="RAM" ClassName="EnsLib.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">ReStart.RAM.Client.Rules.RouterRules</Setting>
  </Item>
  <Item Name="Ens.Alert" Category="" ClassName="EnsLib.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">ReStart.RAM.Client.Rules.EnsAlert</Setting>
  </Item>
  <Item Name="PKBAppt" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="Create Basic Appointment List" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="Validation">dm-z</Setting>
    <Setting Target="Host" Name="BusinessRuleName">BHRUH.Router.PKBAppt</Setting>
  </Item>
  <Item Name="PKBApptFile" Category="" ClassName="EnsLib.RecordMap.Operation.BatchFileOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="START:*-*-*T09:00:00" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="DefaultBatchClass">User.PKBAppt.Batch</Setting>
    <Setting Target="Host" Name="DelayDefaultBatchOutput">1</Setting>
    <Setting Target="Host" Name="Filename">PKBAppts_%Y%m%d_%H%M%S_%N.txt</Setting>
    <Setting Target="Host" Name="IntermediateFilePath">C:\BHRUT\InterfaceFiles\PKBAppts\Working\</Setting>
    <Setting Target="Host" Name="RecordMap">PKBAppt</Setting>
    <Setting Target="Host" Name="RolloverLimit">50</Setting>
    <Setting Target="Host" Name="UseDefaultBatch">1</Setting>
    <Setting Target="Adapter" Name="FilePath">C:\BHRUT\InterfaceFiles\PKBAppts\</Setting>
  </Item>
</Production>
}

}
