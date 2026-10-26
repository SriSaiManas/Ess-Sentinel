"""Grouped real routes with consistent material icons."""
from ui.pages import command,engineering,intelligence,governance,system
ROUTES={
 'COMMAND':{'Overview':(command.overview,'space_dashboard','Engineering Intelligence Overview','Quality surveillance · Predictive analytics · Decision support'),
 'Live Operations':(command.operations,'monitoring','Local Operations','Stored processing activity and measurement context'),
 'Batch Explorer':(command.batches,'inventory_2','Batch Explorer','Select, inspect and compare retained batches')},
 'ENGINEERING':{'Data Ingestion':(engineering.ingestion,'upload_file','Data Ingestion','Preview, map, validate and explicitly commit measurement records'),
 'Data Quality':(engineering.quality,'rule','Data Quality','Trace every finding back to a field and source record'),
 'Screening':(engineering.screening,'fact_check','Screening Workbench','Run a reproducible assessment and prioritize engineering review'),
 'Anomaly Analysis':(engineering.anomaly,'scatter_plot','Anomaly Analysis','Separate observed deviations from predictive evidence'),
 'Component Explorer':(engineering.component,'memory','Component Explorer','Inspect the trajectory, evidence, policy and review history')},
 'INTELLIGENCE':{'Predictive Analytics':(intelligence.predictions,'query_stats','Predictive Analytics','Early observations → 168-hour estimates'),
 'Model Laboratory':(intelligence.laboratory,'science','Model Laboratory','Controlled experiments, held-out evaluation and explicit activation'),
 'Scenario Simulator':(intelligence.simulator,'tune','Scenario Simulator','Compare reproducible synthetic populations'),
 'Model Evaluation':(intelligence.evaluation,'analytics','Model Evaluation','Validation, test and descriptive screening evidence')},
 'GOVERNANCE':{'Policy Center':(governance.policy,'policy','Policy Center','Preview decision changes before saving a policy version'),
 'Audit Trail':(governance.audit,'history','Audit Trail','Actual operations, immutable through the interface'),
 'Reports & Exports':(governance.reporting,'description','Reports & Exports','Traceable evidence packages from the current workspace')},
 'SYSTEM':{'Settings':(system.settings,'settings','Workspace Settings','Local preferences, backup and safe demonstration reset'),
 'System Diagnostics':(system.diagnostics,'health_and_safety','System Diagnostics','Inspect environment readiness and recorded errors')}}
