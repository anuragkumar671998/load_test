#!/usr/bin/env python3
"""
Ubuntu 24.04 LTS Load Generator v2.5 - STABLE VERSION
500+ packages | 40%+ CPU Load | Background Execution
Waits 30 seconds between each install/uninstall cycle
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
from datetime import datetime
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
    
    # Timeouts
    INSTALL_TIMEOUT = 600
    UNINSTALL_TIMEOUT = 300
    APT_UPDATE_TIMEOUT = 300
    
    # Wait time between packages
    WAIT_AFTER_PACKAGE = 30  # 30 seconds between each package cycle
    
    # Maintenance
    DPKG_FIX_EVERY_N = 10
    DEEP_CLEANUP_EVERY_N = 30


class Status(Enum):
    PENDING = "pending"
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
#                              PACKAGE LIST (500+)
# ============================================================================

PACKAGES = [
    # Core utilities
    "htop", "tree", "ncdu", "iotop", "iftop", "nethogs", "nload",
    "bmon", "vnstat", "dstat", "sysstat", "atop", "glances", "nmon",
    
    # Editors
    "nano", "vim", "vim-tiny", "emacs-nox", "joe", "jed", "ne", "mg",
    "ed", "nvi", "elvis-tiny", "zile", "neovim", "hexedit",
    
    # Shells
    "zsh", "fish", "tcsh", "ksh", "mksh", "dash", "busybox",
    
    # Terminal multiplexers
    "screen", "tmux", "byobu",
    
    # File managers
    "mc", "ranger", "vifm", "nnn",
    
    # Network tools
    "net-tools", "iputils-ping", "traceroute", "mtr-tiny",
    "tcpdump", "nmap", "netcat-openbsd", "socat", "telnet", "ftp",
    "lftp", "wget", "curl", "aria2", "axel", "httpie", "links",
    "lynx", "w3m", "elinks", "whois", "dnsutils", "bind9-host",
    "ldnsutils", "avahi-utils", "smbclient", "nfs-common", "rsync",
    "rclone", "iperf3", "ethtool", "bridge-utils", "vlan",
    "wireless-tools", "iw", "rfkill", "bluez", "netperf",
    "hping3", "arping", "fping", "arp-scan", "snmp", "tshark",
    
    # Compression
    "gzip", "bzip2", "xz-utils", "lzip", "lzop", "zstd", "lz4",
    "pigz", "pbzip2", "zip", "unzip", "p7zip", "p7zip-full",
    "arj", "lhasa", "sharutils", "uudeview", "cabextract",
    "cpio", "pax", "genisoimage", "xorriso", "mtools",
    "squashfs-tools", "dosfstools", "ntfs-3g",
    "xfsprogs", "btrfs-progs", "f2fs-tools", "exfatprogs",
    
    # Development
    "build-essential", "gcc", "g++", "gfortran", "make", "cmake",
    "ninja-build", "meson", "autoconf", "automake", "libtool",
    "pkg-config", "bison", "flex", "gawk", "m4", "patch",
    "diffutils", "quilt", "git", "git-lfs", "subversion", "mercurial",
    "cvs", "rcs", "indent", "astyle", "universal-ctags", "cscope",
    "global", "gdb", "valgrind", "binutils", "elfutils", "patchelf",
    "strace", "ltrace",
    
    # Python
    "python3-pip", "python3-venv", "python3-dev",
    "python3-setuptools", "python3-wheel", "python3-numpy",
    "python3-requests", "python3-flask", "python3-pytest",
    
    # Other languages
    "ruby", "ruby-dev", "perl", "perl-doc", "lua5.4", "tcl", "tk",
    "php-cli", "php-common", "nodejs", "npm", "golang-go",
    "default-jdk", "default-jre", "ant", "maven",
    
    # Text processing
    "sed", "grep", "findutils", "coreutils", "moreutils", "parallel",
    "wdiff", "colordiff", "xxd", "jq", "pandoc", "asciidoc", "groff",
    
    # Security
    "openssl", "gnutls-bin", "gnupg", "gnupg2", "pass", "pwgen", "apg",
    "checksec", "debsums", "aide", "rkhunter", "chkrootkit", "lynis",
    "fail2ban", "ufw", "iptables", "nftables", "ipset",
    "apparmor", "apparmor-utils", "firejail", "clamav",
    
    # System utilities
    "cron", "anacron", "at", "logrotate", "rsyslog",
    "acl", "attr", "quota", "hdparm", "sdparm", "smartmontools",
    "nvme-cli", "lvm2", "mdadm", "cryptsetup", "dmsetup",
    "parted", "gdisk", "fdisk", "e2fsprogs",
    "fuse3", "sshfs", "bindfs",
    "initramfs-tools", "grub-common", "efibootmgr",
    "acpid", "acpi", "lm-sensors", "pciutils", "usbutils",
    "dmidecode", "lshw", "hwinfo", "inxi", "powertop", "cpufrequtils",
    
    # Misc utilities
    "bc", "dc", "units", "dateutils", "remind", "calcurse",
    "fortune-mod", "cowsay", "figlet", "toilet", "boxes",
    "lolcat", "cmatrix", "sl", "neofetch", "screenfetch",
    "pv", "progress", "most", "less", "highlight", "source-highlight",
    
    # Database clients
    "sqlite3", "mariadb-client", "postgresql-client", "redis-tools",
    
    # Web servers
    "lighttpd", "apache2-utils",
    
    # Mail
    "mutt", "alpine", "mailutils", "procmail", "fetchmail",
    
    # IRC/Chat
    "irssi", "weechat",
    
    # Media
    "ffmpeg", "sox", "lame", "vorbis-tools", "opus-tools", "flac",
    "mediainfo", "exiftool", "imagemagick", "graphicsmagick",
    "optipng", "jpegoptim",
    
    # Science
    "octave", "gnuplot-nox",
    
    # More network
    "openssh-client", "openssh-server", "openvpn", "wireguard-tools",
    "stunnel4", "proxychains4",
    
    # More dev tools
    "clang", "llvm", "ccache", "distcc", "colormake",
    "checkinstall", "fakeroot", "debhelper", "dpkg-dev",
    "dh-make", "lintian",
    
    # Backup
    "rsnapshot", "rdiff-backup", "duplicity", "borgbackup", "restic",
    
    # Log tools
    "logwatch", "logcheck", "logtail",
    
    # Benchmarking
    "stress-ng", "sysbench", "fio", "bonnie++",
    
    # Process management
    "supervisor", "monit", "runit",
    
    # Additional packages
    "ack", "alien", "apt-file", "apt-listchanges",
    "aptitude", "asciidoctor", "aspell",
    "autossh", "bash-completion", "bind9-utils",
    "binwalk", "blktrace", "bsdmainutils",
    "ca-certificates", "caca-utils",
    "ccze", "cdparanoia", "cgdb", "chafa",
    "chrony", "chrpath", "cifs-utils", "clang-format",
    "cloc", "convmv", "cpulimit", "daemon",
    "dcfldd", "ddrescue", "debconf-utils",
    "debianutils", "deborphan", "debootstrap", "devscripts",
    "dfc", "dialog", "diffstat",
    "dirmngr", "dlocate", "dnsmasq", "dos2unix",
    "doxygen", "dput",
    "eject", "enscript", "etckeeper",
    "expect", "fdupes", "file", "finger",
    "fontconfig", "fonts-dejavu", "foremost",
    "gddrescue", "gettext", "ghostscript", "gifsicle",
    "git-flow", "gitk", "gnuplot",
    "gpm", "graphviz",
    "hardinfo", "hashdeep", "haveged",
    "hexer", "hostname", "httping", "hunspell",
    "i2c-tools", "icu-devtools",
    "info", "inotify-tools",
    "ioping", "ipcalc", "iperf",
    "jfsutils", "jp2a", "kmod", "kpartx",
    "language-pack-en", "lcov",
    "ldap-utils", "libarchive-tools",
    "libtool-bin", "lnav", "locales",
    "lrzsz", "lsb-release", "lsof", "lsscsi",
    "manpages", "manpages-dev", "markdown", "mawk",
    "mlocate", "mosh",
    "mtr", "multitail", "ncftp",
    "netpbm", "nicstat",
    "openntpd", "par2", "pastebinit",
    "pigz", "pixz", "pkgconf", "poppler-utils",
    "psmisc", "qemu-utils", "qrencode",
    "rdate", "readline-common",
    "rename", "renameutils", "rng-tools",
    "rpm", "rpm2cpio", "rrdtool",
    "ruby-full", "s-nail", "safe-rm",
    "samba-common", "schedtool",
    "secure-delete", "sensible-utils", "shellcheck",
    "smem", "sockstat", "speedtest-cli",
    "sshpass", "sslscan", "stow", "stress",
    "sysfsutils", "syslinux",
    "tcl-dev", "tcpflow", "tcpreplay",
    "testdisk", "texinfo", "tftp", "time",
    "tk-dev", "tmate", "trash-cli", "tig",
    "udisks2", "unhide", "unison",
    "unrar-free", "uuid-runtime",
    "vbindiff", "vim-common",
    "wamerican", "wbritish", "whiptail",
    "wondershaper", "xauth", "xclip",
    "xdg-utils", "xmlstarlet", "xsel", "xsltproc",
    "yasm", "zerofree", "zsh-common",
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
#                              SIMPLE APT HANDLER - NO COMPLEX LOCK DETECTION
# ============================================================================

class SimpleApt:
    """
    Simple apt handler that just waits and retries
    No complex lock detection - just simple subprocess calls with waits
    """
    
    @staticmethod
    def run_command(cmd: str, timeout: int = 300) -> Tuple[bool, str, str]:
        """Run a command and wait for it to complete"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'}
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
    
    @staticmethod
    def wait_for_apt(max_wait: int = 60) -> bool:
        """Wait until no apt/dpkg processes are running"""
        logger.debug("Waiting for apt/dpkg to be free...")
        
        start = time.time()
        while time.time() - start < max_wait:
            # Check if any apt/dpkg process is running
            result = subprocess.run(
                "pgrep -x 'apt|apt-get|dpkg|aptitude' || true",
                shell=True, capture_output=True, text=True, timeout=10
            )
            
            if not result.stdout.strip():
                # No apt processes running
                return True
            
            time.sleep(2)
        
        return False
    
    @staticmethod
    def fix_dpkg_if_needed():
        """Run dpkg configure and apt fix if there are issues"""
        logger.info("Running dpkg --configure -a (if needed)...")
        
        # Wait for any running apt
        SimpleApt.wait_for_apt(30)
        
        # Run dpkg configure
        SimpleApt.run_command("sudo dpkg --configure -a", 120)
        
        # Wait
        time.sleep(5)
        SimpleApt.wait_for_apt(30)
        
        # Run apt fix
        SimpleApt.run_command("sudo apt-get install -f -y", 120)
        
        # Wait
        time.sleep(5)
        SimpleApt.wait_for_apt(30)
    
    @staticmethod
    def update() -> bool:
        """Update apt cache"""
        logger.info("Updating apt cache...")
        
        SimpleApt.wait_for_apt(60)
        
        ok, _, err = SimpleApt.run_command("sudo apt-get update -y", Config.APT_UPDATE_TIMEOUT)
        
        if not ok:
            logger.warning(f"apt update issues: {err[:100]}")
            # Try to fix and retry
            SimpleApt.fix_dpkg_if_needed()
            ok, _, _ = SimpleApt.run_command("sudo apt-get update -y", Config.APT_UPDATE_TIMEOUT)
        
        time.sleep(5)
        return ok
    
    @staticmethod
    def install(pkg: str) -> Tuple[bool, float, str]:
        """Install a package"""
        start = time.time()
        
        # Wait for apt to be free
        SimpleApt.wait_for_apt(60)
        
        # Try install
        cmd = f"sudo apt-get install -y --no-install-recommends {pkg}"
        ok, _, err = SimpleApt.run_command(cmd, Config.INSTALL_TIMEOUT)
        
        elapsed = time.time() - start
        
        if not ok and "lock" in err.lower():
            # Lock issue - wait and retry once
            logger.info(f"Lock issue, waiting 30s and retrying {pkg}...")
            time.sleep(30)
            SimpleApt.wait_for_apt(60)
            ok, _, err = SimpleApt.run_command(cmd, Config.INSTALL_TIMEOUT)
            elapsed = time.time() - start
        
        return ok, elapsed, err[:200] if not ok else ""
    
    @staticmethod
    def remove(pkg: str) -> Tuple[bool, float, str]:
        """Remove a package"""
        start = time.time()
        
        # Wait for apt to be free
        SimpleApt.wait_for_apt(60)
        
        # Try remove
        cmd = f"sudo apt-get remove -y --purge {pkg}"
        ok, _, err = SimpleApt.run_command(cmd, Config.UNINSTALL_TIMEOUT)
        
        elapsed = time.time() - start
        
        if not ok and "lock" in err.lower():
            # Lock issue - wait and retry once
            logger.info(f"Lock issue, waiting 30s and retrying remove {pkg}...")
            time.sleep(30)
            SimpleApt.wait_for_apt(60)
            ok, _, err = SimpleApt.run_command(cmd, Config.UNINSTALL_TIMEOUT)
            elapsed = time.time() - start
        
        return ok, elapsed, err[:200] if not ok else ""


# ============================================================================
#                              CPU STRESS
# ============================================================================

class CPUStress:
    def __init__(self):
        self.workers = []
        self.stop_flag = threading.Event()

    def _worker(self, wid: int):
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
                if tmp.exists():
                    tmp.unlink()
                time.sleep(0.5)
            except:
                time.sleep(1)
        if tmp.exists():
            try:
                tmp.unlink()
            except:
                pass

    def start(self):
        self.stop_flag.clear()
        n = max(1, int(multiprocessing.cpu_count() * 0.6))
        logger.info(f"Starting {n} CPU workers + 1 I/O worker")
        
        for i in range(n):
            t = threading.Thread(target=self._worker, args=(i,), daemon=True)
            t.start()
            self.workers.append(t)
        
        t = threading.Thread(target=self._io_worker, daemon=True)
        t.start()
        self.workers.append(t)
        
        time.sleep(2)
        logger.info(f"CPU load: {SystemMonitor.get_cpu_usage()}%")

    def stop(self):
        logger.info("Stopping stress workers...")
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
        """Quick cleanup - no apt commands"""
        subprocess.run("sudo rm -rf /var/cache/apt/archives/*.deb 2>/dev/null", 
                      shell=True, capture_output=True, timeout=30)
        subprocess.run("sudo rm -rf /tmp/*.tmp 2>/dev/null",
                      shell=True, capture_output=True, timeout=30)
        subprocess.run("sudo sh -c 'echo 1 > /proc/sys/vm/drop_caches' 2>/dev/null",
                      shell=True, capture_output=True, timeout=10)

    @staticmethod
    def medium():
        """Medium cleanup"""
        logger.info("Medium cleanup...")
        
        # Wait for apt first
        SimpleApt.wait_for_apt(30)
        
        # Clean
        subprocess.run("sudo apt-get clean -y 2>/dev/null", shell=True,
                      capture_output=True, timeout=60,
                      env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'})
        
        time.sleep(5)
        SimpleApt.wait_for_apt(30)
        
        subprocess.run("sudo apt-get autoclean -y 2>/dev/null", shell=True,
                      capture_output=True, timeout=60,
                      env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'})
        
        time.sleep(5)
        SimpleApt.wait_for_apt(30)
        
        subprocess.run("sudo apt-get autoremove -y 2>/dev/null", shell=True,
                      capture_output=True, timeout=120,
                      env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'})
        
        time.sleep(5)
        
        # Non-apt cleanup
        subprocess.run("sudo journalctl --vacuum-time=1h 2>/dev/null",
                      shell=True, capture_output=True, timeout=60)
        subprocess.run("sudo rm -rf /var/log/*.gz /var/log/*.1 2>/dev/null",
                      shell=True, capture_output=True, timeout=30)
        subprocess.run("sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null",
                      shell=True, capture_output=True, timeout=10)
        
        _, avail = SystemMonitor.get_disk()
        logger.info(f"After cleanup: {avail}GB available")

    @staticmethod
    def emergency():
        """Emergency cleanup"""
        logger.warning("EMERGENCY CLEANUP!")
        
        # Wait for apt
        SimpleApt.wait_for_apt(60)
        
        subprocess.run("sudo apt-get clean -y 2>/dev/null", shell=True,
                      capture_output=True, timeout=60,
                      env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'})
        
        time.sleep(10)
        SimpleApt.wait_for_apt(60)
        
        subprocess.run("sudo apt-get autoremove -y --purge 2>/dev/null", shell=True,
                      capture_output=True, timeout=180,
                      env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'})
        
        time.sleep(10)
        
        subprocess.run("sudo journalctl --vacuum-size=10M 2>/dev/null",
                      shell=True, capture_output=True, timeout=60)
        subprocess.run("sudo rm -rf /var/log/* /tmp/* /var/tmp/* 2>/dev/null",
                      shell=True, capture_output=True, timeout=30)
        subprocess.run("sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null",
                      shell=True, capture_output=True, timeout=10)
        
        _, avail = SystemMonitor.get_disk()
        logger.warning(f"After emergency cleanup: {avail}GB available")


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
╔════════════════════════════════════════════════════════════════════╗
║  LOAD TEST v2.5 - STABLE VERSION                                   ║
╠════════════════════════════════════════════════════════════════════╣
║  PID: {pid:<58}║
║  Log: {str(Config.LOG_FILE):<58}║
╠════════════════════════════════════════════════════════════════════╣
║  FEATURES:                                                         ║
║  • Waits 30 seconds between each package                           ║
║  • Simple apt handling (no complex lock detection)                 ║
║  • Automatic retry on lock issues                                  ║
║  • dpkg --configure -a every 10 packages                           ║
╠════════════════════════════════════════════════════════════════════╣
║  Monitor : tail -f /tmp/load_test.log                              ║
║  Status  : python3 {sys.argv[0]} --status                          ║
║  Stop    : python3 {sys.argv[0]} --stop                            ║
╚════════════════════════════════════════════════════════════════════╝
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
        """Process a single package: install, wait, uninstall, wait"""
        result = PackageResult(name=pkg, status=Status.PENDING)

        # Check disk
        _, avail = SystemMonitor.get_disk()
        if avail < Config.EMERGENCY_DISK_GB:
            Cleaner.emergency()
            _, avail = SystemMonitor.get_disk()
            if avail < Config.EMERGENCY_DISK_GB:
                result.status = Status.SKIPPED
                result.error = "Low disk"
                return result

        # ========== INSTALL ==========
        logger.info(f"Installing {pkg}...")
        ok, elapsed, err = SimpleApt.install(pkg)
        result.install_time = elapsed

        if not ok:
            result.status = Status.INSTALL_FAILED
            result.error = err
            logger.warning(f"✗ INSTALL FAIL: {pkg} - {err[:60]}")
            # Still wait before next package
            logger.info(f"Waiting {Config.WAIT_AFTER_PACKAGE}s before next package...")
            time.sleep(Config.WAIT_AFTER_PACKAGE)
            return result

        logger.info(f"✓ Installed: {pkg} ({elapsed:.1f}s)")
        
        # Wait after install
        logger.info("Waiting 10s after install...")
        time.sleep(10)
        SimpleApt.wait_for_apt(30)

        # ========== UNINSTALL ==========
        logger.info(f"Removing {pkg}...")
        ok, elapsed, err = SimpleApt.remove(pkg)
        result.uninstall_time = elapsed

        if not ok:
            result.status = Status.UNINSTALL_FAILED
            result.error = err
            logger.warning(f"✗ UNINSTALL FAIL: {pkg}")
            # Still wait before next package
            logger.info(f"Waiting {Config.WAIT_AFTER_PACKAGE}s before next package...")
            time.sleep(Config.WAIT_AFTER_PACKAGE)
            return result

        logger.info(f"✓ Removed: {pkg} ({elapsed:.1f}s)")
        result.status = Status.COMPLETED
        
        # ========== WAIT 30 SECONDS ==========
        logger.info(f"Waiting {Config.WAIT_AFTER_PACKAGE}s before next package...")
        time.sleep(Config.WAIT_AFTER_PACKAGE)
        
        return result

    def print_status(self, i: int, total: int, pkg: str):
        elapsed = time.time() - self.start_time
        cpu = SystemMonitor.get_cpu_usage()
        mem_used, _, _ = SystemMonitor.get_memory()
        _, disk_avail = SystemMonitor.get_disk()
        
        ok = sum(1 for r in self.results if r.status == Status.COMPLETED)
        fail = sum(1 for r in self.results if r.status in [Status.INSTALL_FAILED, Status.UNINSTALL_FAILED])
        
        pct = (i / total) * 100
        # ETA calculation includes 30s wait per package
        avg_time = elapsed / i if i > 0 else 60
        eta = avg_time * (total - i)
        
        logger.info(f"")
        logger.info(f"[{i}/{total}] {pct:.1f}% | CPU:{cpu:.0f}% | "
                   f"Mem:{mem_used}MB | Disk:{disk_avail}GB | "
                   f"OK:{ok} FAIL:{fail} | ETA:{eta/60:.0f}m")
        logger.info(f"Processing: {pkg}")
        logger.info(f"-" * 50)

    def run(self):
        self.setup_signals()
        
        logger.info("=" * 70)
        logger.info("  UBUNTU 24.04 LOAD GENERATOR v2.5 - STABLE")
        logger.info("=" * 70)
        logger.info(f"  Packages: {len(PACKAGES)}")
        logger.info(f"  PID: {os.getpid()}")
        logger.info(f"  Wait between packages: {Config.WAIT_AFTER_PACKAGE} seconds")
        logger.info(f"  dpkg --configure -a: Every {Config.DPKG_FIX_EVERY_N} packages")
        
        mem_used, _, mem_total = SystemMonitor.get_memory()
        _, disk_avail = SystemMonitor.get_disk()
        logger.info(f"  Memory: {mem_used}MB/{mem_total}MB | Disk: {disk_avail}GB")
        logger.info("=" * 70)

        # Initial setup
        logger.info("Initial setup - fixing dpkg state...")
        SimpleApt.fix_dpkg_if_needed()
        
        logger.info("Initial cleanup...")
        Cleaner.medium()
        
        logger.info("Updating apt cache...")
        SimpleApt.update()
        
        logger.info("Starting CPU stress workers...")
        self.stress.start()

        self.start_time = time.time()
        total = len(PACKAGES)

        try:
            for i, pkg in enumerate(PACKAGES, 1):
                if not self.running:
                    logger.info("Stopping...")
                    break

                self.print_status(i, total, pkg)
                
                # Process package (install + uninstall + 30s wait)
                result = self.process_package(pkg)
                self.results.append(result)

                # Quick cleanup (no apt commands)
                Cleaner.quick()

                # Every N packages: maintenance
                if i % Config.DPKG_FIX_EVERY_N == 0:
                    logger.info("")
                    logger.info("=" * 60)
                    logger.info(f"  MAINTENANCE: After {i} packages")
                    logger.info("=" * 60)
                    
                    # Fix dpkg
                    SimpleApt.fix_dpkg_if_needed()
                    
                    # Cleanup
                    Cleaner.medium()
                    
                    logger.info("=" * 60)
                    logger.info("")

        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            logger.error(traceback.format_exc())

        finally:
            logger.info("Final cleanup...")
            SimpleApt.fix_dpkg_if_needed()
            
            self.stress.stop()
            Cleaner.medium()
            self.print_report()
            Process.remove_pid()

    def print_report(self):
        elapsed = time.time() - self.start_time
        ok = [r for r in self.results if r.status == Status.COMPLETED]
        fail_i = [r for r in self.results if r.status == Status.INSTALL_FAILED]
        fail_u = [r for r in self.results if r.status == Status.UNINSTALL_FAILED]
        skip = [r for r in self.results if r.status == Status.SKIPPED]

        logger.info("")
        logger.info("=" * 70)
        logger.info("  FINAL REPORT")
        logger.info("=" * 70)
        logger.info(f"  Total: {len(self.results)}")
        logger.info(f"  Completed: {len(ok)}")
        logger.info(f"  Install Failed: {len(fail_i)}")
        logger.info(f"  Uninstall Failed: {len(fail_u)}")
        logger.info(f"  Skipped: {len(skip)}")
        if self.results:
            logger.info(f"  Success Rate: {len(ok)/len(self.results)*100:.1f}%")
        logger.info(f"  Runtime: {elapsed/60:.1f} minutes ({elapsed/3600:.1f} hours)")
        logger.info("=" * 70)

        if fail_i:
            logger.info(f"Install failures: {', '.join(r.name for r in fail_i[:20])}")
            if len(fail_i) > 20:
                logger.info(f"  ... and {len(fail_i) - 20} more")


# ============================================================================
#                              CLI
# ============================================================================

def main():
    args = sys.argv[1:]

    if '--help' in args or '-h' in args:
        print("""
╔════════════════════════════════════════════════════════════════════╗
║  UBUNTU 24.04 LOAD GENERATOR v2.5 - STABLE                         ║
╠════════════════════════════════════════════════════════════════════╣
║  Usage: sudo python3 load_test.py [OPTIONS]                        ║
║                                                                    ║
║  Options:                                                          ║
║    (none)        Run in background                                 ║
║    --foreground  Run in foreground                                 ║
║    --status      Check if running                                  ║
║    --stop        Stop gracefully                                   ║
║    --logs        Show recent logs                                  ║
║    --follow      Watch logs live                                   ║
║    --fix         Fix dpkg/apt state                                ║
║    --help        Show help                                         ║
║                                                                    ║
║  Features:                                                         ║
║    • 500+ packages install/uninstall                               ║
║    • 30 second wait between each package                           ║
║    • Simple apt handling (waits instead of killing)                ║
║    • Automatic retry on lock issues                                ║
║    • dpkg --configure -a every 10 packages                         ║
╚════════════════════════════════════════════════════════════════════╝
""")
        sys.exit(0)

    if '--fix' in args:
        print("Fixing dpkg/apt state...")
        SimpleApt.fix_dpkg_if_needed()
        print("Done!")
        sys.exit(0)

    if '--status' in args:
        if Process.is_running():
            print(f"✓ Running (PID: {Process.get_pid()})")
            os.system(f"tail -5 {Config.LOG_FILE}")
        else:
            print("✗ Not running")
        sys.exit(0)

    if '--stop' in args:
        pid = Process.get_pid()
        if pid and Process.is_running():
            os.kill(pid, signal.SIGTERM)
            print(f"Sent stop signal to PID {pid}")
        else:
            print("Not running")
        sys.exit(0)

    if '--logs' in args:
        os.system(f"tail -50 {Config.LOG_FILE}")
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

    # Daemonize unless foreground
    if '--foreground' not in args:
        Process.daemonize()

    # Run the test
    LoadTester().run()


if __name__ == "__main__":
    main()
