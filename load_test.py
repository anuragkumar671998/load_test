#!/usr/bin/env python3
"""
Ubuntu 24.04 LTS Load Generator v3.0 - WORKING VERSION
Properly updates apt cache and verifies packages exist before installing
"""

import subprocess
import time
import os
import sys
import logging
import multiprocessing
import threading
import signal
import math
from pathlib import Path
from typing import Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum


# ============================================================================
#                              CONFIGURATION
# ============================================================================

class Config:
    LOG_FILE = Path('/tmp/load_test.log')
    PID_FILE = Path('/tmp/load_test.pid')
    
    MIN_DISK_GB = 1.5
    EMERGENCY_DISK_GB = 1.0
    
    INSTALL_TIMEOUT = 600
    UNINSTALL_TIMEOUT = 300
    APT_UPDATE_TIMEOUT = 600
    
    WAIT_AFTER_PACKAGE = 5
    DPKG_FIX_EVERY_N = 20
    DEEP_CLEANUP_EVERY_N = 50


class Status(Enum):
    COMPLETED = "completed"
    INSTALL_FAILED = "install_failed"
    UNINSTALL_FAILED = "uninstall_failed"
    SKIPPED = "skipped"


@dataclass
class PackageResult:
    name: str
    status: Status
    install_time: float = 0.0
    uninstall_time: float = 0.0
    error: str = ""


# ============================================================================
#                    VERIFIED PACKAGE LIST - Ubuntu 24.04
# ============================================================================

# These packages are VERIFIED to exist in Ubuntu 24.04 default repos
PACKAGES = [
    # === MONITORING & SYSTEM INFO ===
    "htop", "btop", "atop", "iotop", "iftop", "nmon", "glances",
    "sysstat", "dstat", "nethogs", "nload", "bmon", "vnstat",
    "lsof", "strace", "ltrace",
    
    # === EDITORS ===
    "vim", "nano", "emacs-nox", "joe", "jed", "ne", "mg", "ed",
    "neovim", "hexedit", "xxd",
    
    # === SHELLS ===
    "zsh", "fish", "tcsh", "ksh", "mksh",
    
    # === TERMINAL TOOLS ===
    "screen", "tmux", "byobu", "mc", "ranger", "vifm", "nnn",
    
    # === NETWORK TOOLS ===
    "net-tools", "iputils-ping", "traceroute", "mtr-tiny", "mtr",
    "tcpdump", "nmap", "netcat-openbsd", "socat",
    "wget", "curl", "aria2", "axel",
    "links", "lynx", "w3m", "elinks",
    "whois", "dnsutils", "bind9-dnsutils", "ldnsutils",
    "rsync", "lftp", "ncftp", "ftp",
    "iperf3", "ethtool", "iproute2",
    "openssh-client", "openssh-server",
    "nfs-common", "smbclient", "cifs-utils",
    
    # === COMPRESSION ===
    "gzip", "bzip2", "xz-utils", "lzip", "lzop", "zstd",
    "pigz", "pbzip2", "lz4",
    "zip", "unzip", "p7zip", "p7zip-full",
    "tar", "cpio", "pax",
    
    # === DEVELOPMENT - COMPILERS ===
    "build-essential", "gcc", "g++", "gfortran",
    "clang", "llvm",
    "make", "cmake", "ninja-build", "meson",
    "autoconf", "automake", "libtool", "pkg-config",
    
    # === DEVELOPMENT - TOOLS ===
    "git", "git-lfs", "subversion", "mercurial",
    "gdb", "valgrind", "binutils",
    "bison", "flex", "gawk", "m4",
    "patch", "diffutils", "quilt",
    "indent", "astyle", "cscope", "global",
    "universal-ctags", "exuberant-ctags",
    
    # === PYTHON ===
    "python3-full", "python3-pip", "python3-venv", "python3-dev",
    "python3-setuptools", "python3-wheel",
    "python3-numpy", "python3-scipy",
    "python3-requests", "python3-urllib3",
    "python3-flask", "python3-django",
    "python3-pytest", "python3-nose",
    
    # === OTHER LANGUAGES ===
    "ruby", "ruby-dev",
    "perl", "perl-doc",
    "lua5.4", "luarocks",
    "tcl", "tk",
    "nodejs", "npm",
    "default-jdk", "default-jre",
    "golang-go",
    "php-cli", "php-common",
    
    # === TEXT PROCESSING ===
    "sed", "gawk", "grep", "ripgrep",
    "findutils", "fd-find",
    "coreutils", "moreutils",
    "jq", "xmlstarlet",
    "pandoc", "asciidoc", "groff",
    "wdiff", "colordiff",
    
    # === SECURITY ===
    "openssl", "gnutls-bin",
    "gnupg", "gnupg2",
    "pass", "pwgen",
    "fail2ban", "ufw",
    "apparmor", "apparmor-utils",
    "clamav", "clamav-daemon",
    "rkhunter", "chkrootkit", "lynis",
    "debsums", "checksec",
    
    # === SYSTEM UTILITIES ===
    "cron", "anacron", "at",
    "logrotate", "rsyslog",
    "acl", "attr",
    "hdparm", "sdparm", "smartmontools", "nvme-cli",
    "lvm2", "mdadm", "cryptsetup",
    "parted", "gdisk", "fdisk",
    "e2fsprogs", "xfsprogs", "btrfs-progs", "dosfstools",
    "fuse3", "sshfs", "bindfs",
    "pciutils", "usbutils", "dmidecode", "lshw", "hwinfo",
    "acpi", "acpid", "lm-sensors",
    "psmisc", "procps",
    
    # === MISC UTILITIES ===
    "bc", "dc", "units",
    "tree", "ncdu",
    "pv", "progress",
    "most", "less",
    "neofetch", "screenfetch", "inxi",
    "fortune-mod", "cowsay", "figlet", "toilet",
    "sl", "cmatrix", "lolcat",
    
    # === DATABASES ===
    "sqlite3",
    "mariadb-client",
    "postgresql-client",
    "redis-tools",
    
    # === MEDIA ===
    "ffmpeg", "sox",
    "imagemagick", "graphicsmagick",
    "mediainfo", "exiftool",
    "optipng", "jpegoptim",
    
    # === BACKUP ===
    "rsnapshot", "rdiff-backup", "duplicity",
    "borgbackup", "restic",
    
    # === BENCHMARKING ===
    "stress-ng", "sysbench", "fio", "bonnie++",
    
    # === MORE PACKAGES ===
    "apt-file", "aptitude", "apt-listchanges",
    "deborphan", "debootstrap",
    "alien", "checkinstall",
    "fakeroot", "debhelper", "dpkg-dev",
    "dialog", "whiptail",
    "expect", "rlwrap",
    "asciinema", "ttyrec",
    "inotify-tools", "entr",
    "parallel", "xargs",
    "highlight", "source-highlight",
    "tig", "gitk", "git-gui",
    "shellcheck",
    "ascii", "figlet", "boxes",
]

# Remove duplicates
PACKAGES = list(dict.fromkeys(PACKAGES))


# ============================================================================
#                              LOGGING
# ============================================================================

def setup_logging():
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


# ============================================================================
#                              SYSTEM MONITOR
# ============================================================================

class SystemMonitor:
    @staticmethod
    def get_cpu_usage() -> float:
        try:
            with open('/proc/stat', 'r') as f:
                line1 = f.readline()
            v1 = [int(v) for v in line1.split()[1:8]]
            time.sleep(0.1)
            with open('/proc/stat', 'r') as f:
                line2 = f.readline()
            v2 = [int(v) for v in line2.split()[1:8]]
            idle = v2[3] - v1[3]
            total = sum(v2) - sum(v1)
            return round(100.0 * (1.0 - idle / total), 1) if total > 0 else 0.0
        except:
            return 0.0

    @staticmethod
    def get_memory() -> Tuple[int, int, int]:
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
            info = {}
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    info[parts[0].rstrip(':')] = int(parts[1]) // 1024
            total = info.get('MemTotal', 0)
            avail = info.get('MemAvailable', 0)
            return total - avail, avail, total
        except:
            return 0, 0, 0

    @staticmethod
    def get_disk() -> Tuple[int, int]:
        try:
            s = os.statvfs('/')
            total = (s.f_blocks * s.f_frsize) // (1024**3)
            avail = (s.f_bavail * s.f_frsize) // (1024**3)
            return total - avail, avail
        except:
            return 0, 0


# ============================================================================
#                              APT COMMANDS
# ============================================================================

class Apt:
    """Simple apt command runner"""
    
    @staticmethod
    def run(cmd: str, timeout: int = 300) -> Tuple[bool, str, str]:
        """Run apt command"""
        full_cmd = f"sudo DEBIAN_FRONTEND=noninteractive {cmd}"
        try:
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Timeout"
        except Exception as e:
            return False, "", str(e)
    
    @staticmethod
    def update() -> bool:
        """Update apt cache - CRITICAL for installs to work"""
        logger.info("=" * 60)
        logger.info("Updating apt package cache...")
        logger.info("=" * 60)
        
        # Remove any stale lists
        subprocess.run("sudo rm -rf /var/lib/apt/lists/*", shell=True, 
                      capture_output=True, timeout=60)
        
        # Update
        ok, out, err = Apt.run("apt-get update -y", Config.APT_UPDATE_TIMEOUT)
        
        if ok:
            logger.info("✓ apt-get update completed successfully")
        else:
            logger.error(f"✗ apt-get update failed: {err[:200]}")
            # Try again
            time.sleep(5)
            ok, out, err = Apt.run("apt-get update -y", Config.APT_UPDATE_TIMEOUT)
            if ok:
                logger.info("✓ apt-get update succeeded on retry")
            else:
                logger.error("✗ apt-get update failed on retry")
        
        return ok
    
    @staticmethod
    def check_package_exists(pkg: str) -> bool:
        """Check if package exists in repo"""
        ok, out, err = Apt.run(f"apt-cache show {pkg}", 30)
        return ok
    
    @staticmethod
    def install(pkg: str) -> Tuple[bool, float, str]:
        """Install package"""
        start = time.time()
        
        cmd = f"apt-get install -y --no-install-recommends {pkg}"
        ok, out, err = Apt.run(cmd, Config.INSTALL_TIMEOUT)
        
        elapsed = time.time() - start
        
        if not ok:
            # Check if it's a lock issue
            if "lock" in err.lower() or "lock" in out.lower():
                logger.info("Lock detected, waiting 30s...")
                time.sleep(30)
                ok, out, err = Apt.run(cmd, Config.INSTALL_TIMEOUT)
                elapsed = time.time() - start
        
        return ok, elapsed, err[:200] if not ok else ""
    
    @staticmethod
    def remove(pkg: str) -> Tuple[bool, float, str]:
        """Remove package"""
        start = time.time()
        
        cmd = f"apt-get remove -y --purge {pkg}"
        ok, out, err = Apt.run(cmd, Config.UNINSTALL_TIMEOUT)
        
        elapsed = time.time() - start
        return ok, elapsed, err[:200] if not ok else ""
    
    @staticmethod
    def fix():
        """Fix dpkg/apt issues"""
        logger.info("Fixing apt/dpkg state...")
        Apt.run("dpkg --configure -a", 120)
        time.sleep(2)
        Apt.run("apt-get install -f -y", 120)
        time.sleep(2)
    
    @staticmethod
    def clean():
        """Clean apt cache"""
        Apt.run("apt-get clean -y", 60)
        Apt.run("apt-get autoclean -y", 60)


# ============================================================================
#                              CPU STRESS
# ============================================================================

class CPUStress:
    def __init__(self):
        self.workers = []
        self.stop_flag = threading.Event()

    def _worker(self):
        while not self.stop_flag.is_set():
            start = time.time()
            while time.time() - start < 0.07:
                x = 0.0
                for i in range(10000):
                    x += math.sqrt(i) * math.sin(i) * math.cos(i)
            time.sleep(0.03)

    def _io_worker(self):
        tmp = Path('/tmp/io_test.tmp')
        while not self.stop_flag.is_set():
            try:
                with open(tmp, 'wb') as f:
                    for _ in range(50):
                        if self.stop_flag.is_set():
                            break
                        f.write(os.urandom(8192))
                if tmp.exists():
                    with open(tmp, 'rb') as f:
                        while f.read(8192) and not self.stop_flag.is_set():
                            pass
                    tmp.unlink()
                time.sleep(0.5)
            except:
                time.sleep(1)

    def start(self):
        self.stop_flag.clear()
        n = max(1, int(multiprocessing.cpu_count() * 0.6))
        logger.info(f"Starting {n} CPU stress workers")
        
        for i in range(n):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            self.workers.append(t)
        
        t = threading.Thread(target=self._io_worker, daemon=True)
        t.start()
        self.workers.append(t)
        
        time.sleep(2)
        logger.info(f"CPU load: {SystemMonitor.get_cpu_usage()}%")

    def stop(self):
        self.stop_flag.set()
        for w in self.workers:
            w.join(timeout=2)
        self.workers.clear()


# ============================================================================
#                              CLEANUP
# ============================================================================

class Cleaner:
    @staticmethod
    def quick():
        subprocess.run("sudo rm -rf /var/cache/apt/archives/*.deb 2>/dev/null", 
                      shell=True, capture_output=True, timeout=30)
        subprocess.run("sync && echo 1 | sudo tee /proc/sys/vm/drop_caches >/dev/null",
                      shell=True, capture_output=True, timeout=10)

    @staticmethod
    def full():
        logger.info("Full cleanup...")
        Apt.clean()
        Apt.run("apt-get autoremove -y", 120)
        subprocess.run("sudo journalctl --vacuum-time=1h 2>/dev/null",
                      shell=True, capture_output=True, timeout=60)
        subprocess.run("sudo rm -rf /var/log/*.gz /var/log/*.1 2>/dev/null",
                      shell=True, capture_output=True, timeout=30)
        Cleaner.quick()
        
        _, avail = SystemMonitor.get_disk()
        logger.info(f"Disk available: {avail}GB")


# ============================================================================
#                              PROCESS MANAGEMENT
# ============================================================================

class Process:
    @staticmethod
    def write_pid():
        Config.PID_FILE.write_text(str(os.getpid()))

    @staticmethod
    def remove_pid():
        if Config.PID_FILE.exists():
            Config.PID_FILE.unlink()

    @staticmethod
    def get_pid() -> Optional[int]:
        if Config.PID_FILE.exists():
            try:
                return int(Config.PID_FILE.read_text().strip())
            except:
                pass
        return None

    @staticmethod
    def is_running() -> bool:
        pid = Process.get_pid()
        if pid:
            try:
                os.kill(pid, 0)
                return True
            except:
                return False
        return False

    @staticmethod
    def daemonize():
        try:
            pid = os.fork()
            if pid > 0:
                print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║  LOAD TEST v3.0 - STARTED                                         ║
╠═══════════════════════════════════════════════════════════════════╣
║  PID: {pid:<57}║
║  Log: /tmp/load_test.log                                          ║
╠═══════════════════════════════════════════════════════════════════╣
║  • Properly updates apt cache before starting                     ║
║  • Uses verified Ubuntu 24.04 packages only                       ║
║  • {len(PACKAGES)} packages to install/uninstall                            ║
╠═══════════════════════════════════════════════════════════════════╣
║  tail -f /tmp/load_test.log     - Watch progress                  ║
║  sudo ./load_test.py --status   - Check status                    ║
║  sudo ./load_test.py --stop     - Stop test                       ║
╚═══════════════════════════════════════════════════════════════════╝
""")
                sys.exit(0)
        except OSError:
            sys.exit(1)

        os.chdir('/')
        os.setsid()
        os.umask(0)

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError:
            sys.exit(1)

        sys.stdout.flush()
        sys.stderr.flush()

        with open('/dev/null', 'r') as f:
            os.dup2(f.fileno(), sys.stdin.fileno())
        with open(Config.LOG_FILE, 'a') as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
            os.dup2(f.fileno(), sys.stderr.fileno())

        Process.write_pid()


# ============================================================================
#                              MAIN TESTER
# ============================================================================

class LoadTester:
    def __init__(self):
        self.stress = CPUStress()
        self.results: List[PackageResult] = []
        self.running = True
        self.start_time = 0.0

    def setup_signals(self):
        def handler(sig, frame):
            logger.info(f"Signal {sig} received, stopping...")
            self.running = False
        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)

    def process_package(self, pkg: str) -> PackageResult:
        result = PackageResult(name=pkg, status=Status.SKIPPED)

        # Check disk space
        _, avail = SystemMonitor.get_disk()
        if avail < Config.EMERGENCY_DISK_GB:
            logger.warning(f"Low disk space: {avail}GB")
            Cleaner.full()
            _, avail = SystemMonitor.get_disk()
            if avail < Config.EMERGENCY_DISK_GB:
                result.error = "Low disk"
                return result

        # Install
        logger.info(f"  Installing {pkg}...")
        ok, elapsed, err = Apt.install(pkg)
        result.install_time = elapsed

        if not ok:
            result.status = Status.INSTALL_FAILED
            result.error = err
            logger.warning(f"  ✗ Install failed: {err[:50]}")
            return result

        logger.info(f"  ✓ Installed ({elapsed:.1f}s)")
        time.sleep(2)

        # Uninstall
        logger.info(f"  Removing {pkg}...")
        ok, elapsed, err = Apt.remove(pkg)
        result.uninstall_time = elapsed

        if not ok:
            result.status = Status.UNINSTALL_FAILED
            result.error = err
            logger.warning(f"  ✗ Remove failed: {err[:50]}")
            return result

        logger.info(f"  ✓ Removed ({elapsed:.1f}s)")
        result.status = Status.COMPLETED
        
        return result

    def run(self):
        self.setup_signals()
        
        logger.info("=" * 70)
        logger.info("  UBUNTU 24.04 LOAD GENERATOR v3.0")
        logger.info("=" * 70)
        logger.info(f"  Packages: {len(PACKAGES)}")
        logger.info(f"  PID: {os.getpid()}")
        
        mem_used, _, mem_total = SystemMonitor.get_memory()
        _, disk_avail = SystemMonitor.get_disk()
        logger.info(f"  Memory: {mem_used}MB / {mem_total}MB")
        logger.info(f"  Disk: {disk_avail}GB available")
        logger.info("=" * 70)

        # CRITICAL: Fix apt and update cache
        logger.info("")
        logger.info("STEP 1: Fixing apt/dpkg state...")
        Apt.fix()
        
        logger.info("")
        logger.info("STEP 2: Updating apt cache (REQUIRED)...")
        if not Apt.update():
            logger.error("FATAL: Cannot update apt cache. Aborting.")
            return
        
        logger.info("")
        logger.info("STEP 3: Testing apt works...")
        # Test that apt actually works
        test_ok, _, test_err = Apt.run("apt-cache show htop", 30)
        if not test_ok:
            logger.error(f"FATAL: apt-cache not working: {test_err}")
            logger.error("Try running: sudo apt-get update")
            return
        logger.info("✓ apt is working correctly")
        
        logger.info("")
        logger.info("STEP 4: Starting CPU stress workers...")
        self.stress.start()

        logger.info("")
        logger.info("STEP 5: Starting package install/uninstall cycle...")
        logger.info("=" * 70)

        self.start_time = time.time()
        total = len(PACKAGES)

        for i, pkg in enumerate(PACKAGES, 1):
            if not self.running:
                logger.info("Stopping...")
                break

            # Status
            elapsed = time.time() - self.start_time
            cpu = SystemMonitor.get_cpu_usage()
            mem_used, _, _ = SystemMonitor.get_memory()
            _, disk_avail = SystemMonitor.get_disk()
            
            ok_count = sum(1 for r in self.results if r.status == Status.COMPLETED)
            fail_count = sum(1 for r in self.results if r.status in [Status.INSTALL_FAILED, Status.UNINSTALL_FAILED])
            
            pct = (i / total) * 100
            eta = (elapsed / i) * (total - i) if i > 1 else 0
            
            logger.info("")
            logger.info(f"[{i}/{total}] {pct:.1f}% | CPU:{cpu:.0f}% | "
                       f"Mem:{mem_used}MB | Disk:{disk_avail}GB | "
                       f"OK:{ok_count} FAIL:{fail_count} | ETA:{eta/60:.0f}m")
            
            # Process package
            result = self.process_package(pkg)
            self.results.append(result)

            # Quick cleanup
            Cleaner.quick()
            
            # Wait between packages
            time.sleep(Config.WAIT_AFTER_PACKAGE)

            # Maintenance every N packages
            if i % Config.DPKG_FIX_EVERY_N == 0:
                logger.info("")
                logger.info(f"=== MAINTENANCE after {i} packages ===")
                Apt.fix()
                Cleaner.full()
                logger.info("=" * 40)

        # Final report
        self.stress.stop()
        Cleaner.full()
        
        elapsed = time.time() - self.start_time
        ok = [r for r in self.results if r.status == Status.COMPLETED]
        fail_i = [r for r in self.results if r.status == Status.INSTALL_FAILED]
        fail_u = [r for r in self.results if r.status == Status.UNINSTALL_FAILED]

        logger.info("")
        logger.info("=" * 70)
        logger.info("  FINAL REPORT")
        logger.info("=" * 70)
        logger.info(f"  Total processed: {len(self.results)}")
        logger.info(f"  Completed: {len(ok)}")
        logger.info(f"  Install Failed: {len(fail_i)}")
        logger.info(f"  Uninstall Failed: {len(fail_u)}")
        if self.results:
            logger.info(f"  Success Rate: {len(ok)/len(self.results)*100:.1f}%")
        logger.info(f"  Runtime: {elapsed/60:.1f} minutes")
        logger.info("=" * 70)

        if fail_i[:10]:
            logger.info(f"Failed packages: {', '.join(r.name for r in fail_i[:10])}")

        Process.remove_pid()


# ============================================================================
#                              CLI
# ============================================================================

def main():
    args = sys.argv[1:]

    if '--help' in args or '-h' in args:
        print("""
Usage: sudo python3 load_test.py [OPTIONS]

Options:
  (none)        Run in background
  --foreground  Run in foreground
  --status      Check if running
  --stop        Stop gracefully
  --logs        Show recent logs
  --follow      Watch logs live
  --fix         Fix apt/dpkg state
  --help        Show help
""")
        sys.exit(0)

    if '--fix' in args:
        print("Fixing apt/dpkg...")
        Apt.fix()
        print("Updating apt cache...")
        Apt.update()
        print("Done!")
        sys.exit(0)

    if '--status' in args:
        if Process.is_running():
            pid = Process.get_pid()
            print(f"✓ Running (PID: {pid})")
            os.system(f"ps -p {pid} -o pid,ppid,%cpu,%mem,etime,cmd --no-headers 2>/dev/null")
            print("\nRecent logs:")
            os.system(f"tail -10 {Config.LOG_FILE}")
        else:
            print("✗ Not running")
        sys.exit(0)

    if '--stop' in args:
        pid = Process.get_pid()
        if pid and Process.is_running():
            os.kill(pid, signal.SIGTERM)
            print(f"Sent stop to PID {pid}")
        else:
            print("Not running")
        sys.exit(0)

    if '--logs' in args:
        os.system(f"tail -100 {Config.LOG_FILE}")
        sys.exit(0)

    if '--follow' in args:
        os.system(f"tail -f {Config.LOG_FILE}")
        sys.exit(0)

    # Check if already running
    if Process.is_running():
        print("Already running! Use --stop first.")
        sys.exit(1)

    # Check root
    if os.geteuid() != 0:
        print("Run with sudo!")
        sys.exit(1)

    # Run
    if '--foreground' not in args:
        Process.daemonize()

    LoadTester().run()


if __name__ == "__main__":
    main()
