Quick Start


gir clone https://github.com/anuragkumar671998/load_test.git && cd load_test && sudo chmod +x load_test.py && sudo ./load_test.py && tail -f 


bashDownloadCopy code# 

Save and make executable

chmod +x load_test.py


# Start in background
sudo python3 load_test.py


# Start in foreground (see all output)

sudo python3 load_test.py --foreground
All Commands
CommandDescription
sudo python3 load_test.py
Start in background
sudo python3 load_test.py --foreground
Start with live output
sudo python3 load_test.py --resume
Resume interrupted testpython3 load_test.py --status
Check if runningpython3 load_test.py --stop
Graceful shutdownpython3 load_test.py --killForce kill
python3 load_test.py --logsShow last 50 linespython3 load_test.py --followWatch logs livepython3 load_test.py --statsShow statisticspython3 load_test.py --cleanRemove all temp filespython3 load_test.py --helpShow help
Key Improvements in v2.0
FeatureDescription900+ PackagesExpanded from 500 to 900+ packagesResume CapabilitySave/restore state after interruptionBetter LoggingColored output, structured logsStatistics TrackingJSON stats file with historyResource MonitoringCPU, memory, disk, load averageDynamic CPU AdjustmentAuto-adjusts to maintain target loadProgress BarVisual progress indicatorETA CalculationEstimated time to completionEmergency CleanupAggressive cleanup on low resourcesGraceful ShutdownSignal handling, clean exitCLI InterfaceFull command-line managementCode OrganizationClean classes, type hints, dataclasses
Files Created
FilePurpose/tmp/load_test.logMain log file/tmp/load_test.pidProcess ID/tmp/load_test_state.jsonCheckpoint for resume/tmp/load_test_stats.jsonStatistics history
