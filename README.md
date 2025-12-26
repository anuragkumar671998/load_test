Quick Start


git clone https://github.com/anuragkumar671998/load_test.git && cd load_test && sudo chmod +x load_test.py && sudo ./load_test.py && tail -f /tmp/load_test.log


bashDownloadCopy code# 

Save and make executable

chmod +x load_test.py


# Start in background
sudo python3 load_test.py


What's New in v2.2
FeatureDescriptiondpkg --configure -aRuns every 10 packages to fix interrupted installsapt-get install -fRuns after dpkg to fix broken dependenciesInitial fixRuns both commands at startup before any installsFinal fixRuns both commands at the end before exit
Workflow Diagram
┌─────────────────────────────────────────────────────────────────┐
│                        WORKFLOW v2.2                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  START                                                          │
│    ↓                                                            │
│  dpkg --configure -a  (initial fix)                             │
│  apt-get install -f   (fix broken deps)                         │
│    ↓                                                            │
│  apt-get update                                                 │
│    ↓                                                            │
│  Start CPU stress workers                                       │
│    ↓                                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  FOR EACH PACKAGE (1 to 500+):                           │   │
│  │    │                                                     │   │
│  │    ├──→ Install package                                  │   │
│  │    ├──→ Wait 1 second                                    │   │
│  │    ├──→ Uninstall package                                │   │
│  │    ├──→ Quick cleanup                                    │   │
│  │    │                                                     │   │
│  │    └──→ IF package # is multiple of 10:                  │   │
│  │            ├──→ dpkg --configure -a                      │   │
│  │            ├──→ apt-get install -f                       │   │
│  │            └──→ Medium cleanup                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│    ↓                                                            │
│  dpkg --configure -a  (final fix)                               │
│  apt-get install -f   (fix broken deps)                         │
│    ↓                                                            │
│  Print final report                                             │
│    ↓                                                            │
│  STOP                                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Package Count
MetricValueTotal Packages~500 (after removing duplicates)dpkg --configure -a runs~50 times (every 10 packages)apt-get install -f runs~50 times (after each dpkg configure)
Sample Log Output
[10/500] 2.0% | CPU:65% | Mem:280MB | Disk:6GB | OK:8 FAIL:2 | curl
✓ Installed: curl (3.2s)
✓ Removed: curl (1.5s)

============================================================
  MAINTENANCE: After 10 packages
============================================================
Running: dpkg --configure -a
✓ dpkg --configure -a completed successfully
Running: apt-get install -f
✓ apt-get install -f completed successfully
Medium cleanup...
After cleanup: 6GB available
============================================================

[11/500] 2.2% | CPU:72% | Mem:275MB | Disk:6GB | OK:9 FAIL:2 | wget
✓ Installed: wget (2.8s)
✓ Removed: wget (1.2s)

Run Commands
bashDownloadCopy code# Save and run in background
sudo python3 load_test.py

# Watch logs
tail -f /tmp/load_test.log

# Check status
python3 load_test.py --status

# Stop
python3 load_test.py --stop
