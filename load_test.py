#!/usr/bin/env python3
"""
Ubuntu 24.04 LTS Load Generator v2.4 - FULLY FIXED
500+ packages | 40%+ CPU Load | Background Execution
Waits for each operation to complete before next
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
    INSTALL_TIMEOUT = 600      # 10 minutes max per install
    UNINSTALL_TIMEOUT = 300    # 5 minutes max per uninstall
    APT_UPDATE_TIMEOUT = 300
    
    # Lock handling
    MAX_LOCK_WAIT = 120        # Wait up to 2 minutes for lock
    LOCK_CHECK_INTERVAL = 3   # Check every 3 seconds
    
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
    "net-tools", "iproute2", "iputils-ping", "traceroute", "mtr-tiny",
    "tcpdump", "nmap", "netcat-openbsd", "socat", "telnet", "ftp",
    "lftp", "wget", "curl", "aria2", "axel", "httpie", "links",
    "lynx", "w3m", "elinks", "whois", "dnsutils", "bind9-host",
    "ldnsutils", "avahi-utils", "smbclient", "nfs-common", "rsync",
    "rclone", "iperf3", "ethtool", "bridge-utils", "vlan",
    "wireless-tools", "iw", "rfkill", "bluez", "netperf",
    "hping3", "arping", "fping", "arp-scan", "snmp", "tshark",
    
    # Compression
    "gzip", "bzip2", "xz-utils", "lzma", "lzip", "lzop", "zstd", "lz4",
    "pigz", "pbzip2", "zip", "unzip", "p7zip", "p7zip-full",
    "arj", "lhasa", "sharutils", "uudeview", "cabextract",
    "cpio", "pax", "genisoimage", "xorriso", "mtools",
    "squashfs-tools", "dosfstools", "ntfs-3g", "hfsprogs",
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
    "rustc", "cargo", "default-jdk", "default-jre", "ant", "maven",
    
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
    "acpid", "acpi", "lm-sensors", "hddtemp", "pciutils", "usbutils",
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
#                              APT LOCK HANDLER - COMPLETELY REWRITTEN
# ============================================================================

class AptLock:
    """
    Handles apt/dpkg locks properly by:
    1. Checking if lock is held
    2. Waiting for it to be released
    3. Force killing if stuck too long
    """
    
    LOCK_FILES = [
        "/var/lib/dpkg/lock-frontend",
        "/var/lib/dpkg/lock",
        "/var/lib/apt/lists/lock",
        "/var/cache/apt/archives/lock",
    ]
    
    APT_PROCESSES = ["apt", "apt-get", "dpkg", "aptitude", "synaptic"]
    
    @classmethod
    def get_apt_pids(cls) -> List[int]:
        """Get PIDs of all running apt/dpkg processes"""
        pids = []
        try:
            result = subprocess.run(
                "ps aux | grep -E 'apt|dpkg' | grep -v grep | awk '{print $2}'",
                shell=True, capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        pids.append(int(line.strip()))
                    except:
                        pass
        except:
            pass
        
        # Also check with fuser
        for lock_file in cls.LOCK_FILES:
            try:
                result = subprocess.run(
                    f"fuser {lock_file} 2>/dev/null",
                    shell=True, capture_output=True, text=True, timeout=10
                )
                for pid_str in result.stdout.strip().split():
                    try:
                        pid = int(pid_str.strip())
                        if pid not in pids:
                            pids.append(pid)
                    except:
                        pass
            except:
                pass
        
        # Filter out our own process
        our_pid = os.getpid()
        pids = [p for p in pids if p != our_pid]
        
        return pids
    
    @classmethod
    def is_locked(cls) -> bool:
        """Check if any apt/dpkg lock is held"""
        pids = cls.get_apt_pids()
        return len(pids) > 0
    
    @classmethod
    def wait_for_unlock(cls, timeout: int = None) -> bool:
        """Wait for all apt locks to be released"""
        if timeout is None:
            timeout = Config.MAX_LOCK_WAIT
        
        start = time.time()
        
        while time.time() - start < timeout:
            if not cls.is_locked():
                return True
            
            pids = cls.get_apt_pids()
            if pids:
                logger.debug(f"Waiting for apt/dpkg (PIDs: {pids})...")
            
            time.sleep(Config.LOCK_CHECK_INTERVAL)
        
        return False
    
    @classmethod
    def kill_apt_processes(cls) -> bool:
        """Kill all stuck apt/dpkg processes"""
        pids = cls.get_apt_pids()
        
        if not pids:
            return True
        
        logger.warning(f"Killing stuck apt/dpkg processes: {pids}")
        
        # First try SIGTERM
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except:
                pass
        
        time.sleep(3)
        
        # Then SIGKILL for any remaining
        pids = cls.get_apt_pids()
        for pid in pids:
            try:
                logger.warning(f"Force killing PID {pid}")
                os.kill(pid, signal.SIGKILL)
            except:
                pass
        
        time.sleep(2)
        return not cls.is_locked()
    
    @classmethod
    def remove_locks(cls):
        """Remove stale lock files"""
        for lock_file in cls.LOCK_FILES:
            try:
                if os.path.exists(lock_file):
                    os.remove(lock_file)
                    logger.info(f"Removed stale lock: {lock_file}")
            except:
                subprocess.run(f"sudo rm -f {lock_file}", shell=True, 
                             capture_output=True, timeout=10)
    
    @classmethod
    def ensure_unlocked(cls) -> bool:
        """Make sure apt/dpkg is not locked, killing processes if needed"""
        # First check if locked
        if not cls.is_locked():
            return True
        
        logger.info("apt/dpkg is locked, waiting...")
        
        # Wait for normal unlock
        if cls.wait_for_unlock(timeout=60):
            return True
        
        # Still locked - kill processes
        logger.warning("Lock held too long, killing stuck processes...")
        cls.kill_apt_processes()
        cls.remove_locks()
        
        # Final check
        time.sleep(2)
        if cls.is_locked():
            logger.error("Could not release apt lock!")
            cls.kill_apt_processes()
            cls.remove_locks()
            time.sleep(3)
        
        return not cls.is_locked()
    
    @classmethod
    def fix_dpkg(cls):
        """Fix dpkg state after interruption"""
        logger.info("Fixing dpkg state...")
        cls.ensure_unlocked()
        
        subprocess.run(
            "sudo dpkg --configure -a",
            shell=True, capture_output=True, timeout=300,
            env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'}
        )
        
        cls.ensure_unlocked()
        
        subprocess.run(
            "sudo apt-get install -f -y",
            shell=True, capture_output=True, timeout=300,
            env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'}
        )


# ============================================================================
#                              APT COMMAND RUNNER - SYNCHRONOUS
# ============================================================================

class Apt:
    """
    Run apt commands SYNCHRONOUSLY - waits for completion before returning
    """
    
    @staticmethod
    def _run_apt_command(cmd: str, timeout: int) -> Tuple[bool, str, str]:
        """
        Run an apt command and WAIT for it to complete
        Returns (success, stdout, stderr)
        """
        # First ensure no other apt is running
        if not AptLock.ensure_unlocked():
            return False, "", "Could not get apt lock"
        
        try:
            # Run command and WAIT for completion
            result = subprocess.run(
                f"sudo {cmd}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'}
            )
            
            # Wait a moment and verify apt is done
            time.sleep(1)
            
            # Double-check no apt process is running
            wait_count = 0
            while AptLock.is_locked() and wait_count < 30:
                time.sleep(1)
                wait_count += 1
            
            return result.returncode == 0, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out: {cmd[:50]}...")
            AptLock.kill_apt_processes()
            return False, "", "Timeout"
        except Exception as e:
            logger.error(f"Command error: {e}")
            return False, "", str(e)
    
    @staticmethod
    def update() -> bool:
        """Update apt package cache"""
        logger.info("Updating apt cache...")
        AptLock.ensure_unlocked()
        ok, _, err = Apt._run_apt_command("apt-get update -y", Config.APT_UPDATE_TIMEOUT)
        if not ok:
            logger.warning(f"apt update issues: {err[:100]}")
        return True
    
    @staticmethod
    def install(pkg: str) -> Tuple[bool, float, str]:
        """Install a package - waits for completion"""
        start = time.time()
        
        ok, _, err = Apt._run_apt_command(
            f"apt-get install -y --no-install-recommends {pkg}",
            Config.INSTALL_TIMEOUT
        )
        
        elapsed = time.time() - start
        return ok, elapsed, err[:200] if not ok else ""
    
    @staticmethod
    def remove(pkg: str) -> Tuple[bool, float, str]:
        """Remove a package - waits for completion"""
        start = time.time()
        
        ok, _, err = Apt._run_apt_command(
            f"apt-get remove -y --purge {pkg}",
            Config.UNINSTALL_TIMEOUT
        )
        
        elapsed = time.time() - start
        return ok, elapsed, err[:200] if not ok else ""
    
    @staticmethod
    def dpkg_configure() -> bool:
        """Run dpkg --configure -a"""
        logger.info("Running: dpkg --configure -a")
        AptLock.ensure_unlocked()
        ok, _, err = Apt._run_apt_command("dpkg --configure -a", 300)
        if ok:
            logger.info("✓ dpkg --configure -a completed")
        else:
            logger.warning(f"dpkg --configure -a issues: {err[:100]}")
        return ok
    
    @staticmethod
    def fix_broken() -> bool:
        """Run apt-get install -f"""
        logger.info("Running: apt-get install -f")
        AptLock.ensure_unlocked()
        ok, _, err = Apt._run_apt_command("apt-get install -f -y", 300)
        if ok:
            logger.info("✓ apt-get install -f completed")
        else:
            logger.warning(f"apt-get install -f issues: {err[:100]}")
        return ok


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
            tmp.unlink()

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
        # Wait for any apt to finish first
        AptLock.wait_for_unlock(timeout=30)
        
        subprocess.run("sudo apt-get clean -y", shell=True, 
                      capture_output=True, timeout=60,
                      env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'})
        subprocess.run("sudo rm -rf /var/cache/apt/archives/*.deb", 
                      shell=True, capture_output=True, timeout=30)
        subprocess.run("sudo sh -c 'echo 1 > /proc/sys/vm/drop_caches'",
                      shell=True, capture_output=True, timeout=10)

    @staticmethod
    def medium():
        logger.info("Medium cleanup...")
        AptLock.ensure_unlocked()
        
        Cleaner.quick()
        
        subprocess.run("sudo apt-get autoclean -y", shell=True,
                      capture_output=True, timeout=120,
                      env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'})
        
        AptLock.wait_for_unlock(timeout=60)
        
        subprocess.run("sudo apt-get autoremove -y", shell=True,
                      capture_output=True, timeout=180,
                      env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'})
        
        AptLock.wait_for_unlock(timeout=60)
        
        subprocess.run("sudo journalctl --vacuum-time=1h",
                      shell=True, capture_output=True, timeout=60)
        subprocess.run("sudo rm -rf /var/log/*.gz /var/log/*.1",
                      shell=True, capture_output=True, timeout=30)
        subprocess.run("sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'",
                      shell=True, capture_output=True, timeout=10)
        
        _, avail = SystemMonitor.get_disk()
        logger.info(f"After cleanup: {avail}GB available")

    @staticmethod
    def emergency():
        logger.warning("EMERGENCY CLEANUP!")
        AptLock.kill_apt_processes()
        AptLock.remove_locks()
        
        subprocess.run("sudo apt-get clean -y", shell=True,
                      capture_output=True, timeout=60,
                      env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'})
        subprocess.run("sudo apt-get autoremove -y --purge", shell=True,
                      capture_output=True, timeout=180,
                      env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'})
        subprocess.run("sudo journalctl --vacuum-size=10M",
                      shell=True, capture_output=True, timeout=60)
        subprocess.run("sudo rm -rf /var/log/* /tmp/* /var/tmp/*",
                      shell=True, capture_output=True, timeout=30)
        subprocess.run("sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'",
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
║  LOAD TEST v2.4 - STARTED IN BACKGROUND                            ║
╠════════════════════════════════════════════════════════════════════╣
║  PID: {pid:<58}║
║  Log: {str(Config.LOG_FILE):<58}║
╠════════════════════════════════════════════════════════════════════╣
║  FIXED IN v2.4:                                                    ║
║  • Waits for each install/uninstall to FULLY complete              ║
║  • Properly handles apt/dpkg locks                                 ║
║  • Kills stuck processes automatically                             ║
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
        logger.debug(f"Installing {pkg}...")
        ok, elapsed, err = Apt.install(pkg)
        result.install_time = elapsed

        if not ok:
            result.status = Status.INSTALL_FAILED
            result.error = err
            logger.warning(f"✗ INSTALL FAIL: {pkg} - {err[:60]}")
            return result

        logger.info(f"✓ Installed: {pkg} ({elapsed:.1f}s)")
        
        # Wait to ensure install is complete
        time.sleep(2)
        AptLock.wait_for_unlock(timeout=30)

        # ========== UNINSTALL ==========
        logger.debug(f"Removing {pkg}...")
        ok, elapsed, err = Apt.remove(pkg)
        result.uninstall_time = elapsed

        if not ok:
            result.status = Status.UNINSTALL_FAILED
            result.error = err
            logger.warning(f"✗ UNINSTALL FAIL: {pkg}")
            return result

        logger.info(f"✓ Removed: {pkg} ({elapsed:.1f}s)")
        
        # Wait to ensure uninstall is complete
        time.sleep(2)
        AptLock.wait_for_unlock(timeout=30)
        
        result.status = Status.COMPLETED
        return result

    def print_status(self, i: int, total: int, pkg: str):
        elapsed = time.time() - self.start_time
        cpu = SystemMonitor.get_cpu_usage()
        mem_used, _, _ = SystemMonitor.get_memory()
        _, disk_avail = SystemMonitor.get_disk()
        
        ok = sum(1 for r in self.results if r.status == Status.COMPLETED)
        fail = sum(1 for r in self.results if r.status in [Status.INSTALL_FAILED, Status.UNINSTALL_FAILED])
        
        pct = (i / total) * 100
        eta = (elapsed / i) * (total - i) if i > 0 else 0
        
        logger.info(f"[{i}/{total}] {pct:.1f}% | CPU:{cpu:.0f}% | "
                   f"Mem:{mem_used}MB | Disk:{disk_avail}GB | "
                   f"OK:{ok} FAIL:{fail} | ETA:{eta/60:.0f}m | {pkg}")

    def run(self):
        self.setup_signals()
        
        logger.info("=" * 70)
        logger.info("  UBUNTU 24.04 LOAD GENERATOR v2.4 - FULLY FIXED")
        logger.info("=" * 70)
        logger.info(f"  Packages: {len(PACKAGES)}")
        logger.info(f"  PID: {os.getpid()}")
        logger.info(f"  dpkg --configure -a: Every {Config.DPKG_FIX_EVERY_N} packages")
        
        mem_used, _, mem_total = SystemMonitor.get_memory()
        _, disk_avail = SystemMonitor.get_disk()
        logger.info(f"  Memory: {mem_used}MB/{mem_total}MB | Disk: {disk_avail}GB")
        logger.info("=" * 70)

        # Initial cleanup - kill any stuck apt processes
        logger.info("Killing any stuck apt/dpkg processes...")
        AptLock.kill_apt_processes()
        AptLock.remove_locks()
        AptLock.fix_dpkg()
        
        Cleaner.medium()
        Apt.update()
        self.stress.start()

        self.start_time = time.time()
        total = len(PACKAGES)

        try:
            for i, pkg in enumerate(PACKAGES, 1):
                if not self.running:
                    logger.info("Stopping...")
                    break

                self.print_status(i, total, pkg)
                
                # Process package (install + uninstall)
                result = self.process_package(pkg)
                self.results.append(result)

                # Quick cleanup
                Cleaner.quick()

                # Every N packages: maintenance
                if i % Config.DPKG_FIX_EVERY_N == 0:
                    logger.info("")
                    logger.info("=" * 60)
                    logger.info(f"  MAINTENANCE: After {i} packages")
                    logger.info("=" * 60)
                    
                    # Kill any stuck processes
                    AptLock.ensure_unlocked()
                    
                    # Run dpkg --configure -a
                    Apt.dpkg_configure()
                    
                    # Fix broken
                    Apt.fix_broken()
                    
                    # Cleanup
                    Cleaner.medium()
                    
                    logger.info("=" * 60)
                    logger.info("")

        except Exception as e:
            logger.error(f"Error: {e}")

        finally:
            logger.info("Final cleanup...")
            AptLock.kill_apt_processes()
            AptLock.fix_dpkg()
            
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
║  UBUNTU 24.04 LOAD GENERATOR v2.4                                  ║
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
║    --fix-locks   Kill stuck apt/dpkg and fix locks                 ║
║    --help        Show help                                         ║
╚════════════════════════════════════════════════════════════════════╝
""")
        sys.exit(0)

    if '--fix-locks' in args:
        print("Fixing apt/dpkg locks...")
        AptLock.kill_apt_processes()
        AptLock.remove_locks()
        time.sleep(2)
        AptLock.fix_dpkg()
        print("Done!")
        sys.exit(0)

    if '--status' in args:
        if Process.is_running():
            print(f"✓ Running (PID: {Process.get_pid()})")
            os.system(f"tail -5 {Config.LOG_FILE}")
        else:
            print("✗ Not running")
        
        # Check for stuck processes
        pids = AptLock.get_apt_pids()
        if pids:
            print(f"\n⚠ apt/dpkg processes running: {pids}")
            print("  Run with --fix-locks to clear")
        
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
