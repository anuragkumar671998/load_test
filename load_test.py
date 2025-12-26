#!/usr/bin/env python3
"""
Ubuntu 24.04 LTS Load Generator v2.2
500+ packages | 40%+ CPU Load | Background Execution
With dpkg --configure -a every 10 packages
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
    
    TARGET_CPU_PERCENT = 45
    
    INSTALL_TIMEOUT = 300
    UNINSTALL_TIMEOUT = 180
    DPKG_CONFIGURE_TIMEOUT = 300
    APT_UPDATE_TIMEOUT = 300
    
    # Run dpkg --configure -a every N packages
    DPKG_FIX_EVERY_N = 10
    CLEANUP_EVERY_N = 10
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
    "cpio", "pax", "tar", "genisoimage", "xorriso", "mtools",
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
    "python3", "python3-pip", "python3-venv", "python3-dev",
    "python3-setuptools", "python3-wheel", "python3-numpy",
    "python3-requests", "python3-flask", "python3-pytest",
    
    # Other languages
    "ruby", "ruby-dev", "perl", "perl-doc", "lua5.4", "tcl", "tk",
    "php-cli", "php-common", "nodejs", "npm", "golang-go",
    "rustc", "cargo", "default-jdk", "default-jre", "ant", "maven",
    
    # Text processing
    "sed", "grep", "findutils", "coreutils", "moreutils", "parallel",
    "wdiff", "colordiff", "xxd", "jq",
    "pandoc", "asciidoc", "groff",
    
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
    "dmidecode", "lshw", "hwinfo", "inxi",
    "powertop", "cpufrequtils",
    
    # Misc utilities
    "bc", "dc", "units", "dateutils", "remind", "calcurse",
    "fortune-mod", "cowsay", "figlet", "toilet", "boxes",
    "lolcat", "cmatrix", "sl", "neofetch", "screenfetch",
    "pv", "progress", "most", "less",
    "highlight", "source-highlight", "bat",
    
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
    "stunnel4", "proxychains4", "tor", "privoxy",
    
    # More dev tools
    "clang", "llvm", "ccache", "distcc", "colormake",
    "checkinstall", "fakeroot", "debhelper", "dpkg-dev",
    "dh-make", "lintian", "piuparts",
    
    # Backup
    "rsnapshot", "rdiff-backup", "duplicity", "borgbackup", "restic",
    
    # Log tools
    "logwatch", "logcheck", "logtail", "swatch",
    
    # Benchmarking
    "stress-ng", "sysbench", "fio", "iozone3", "bonnie++",
    
    # Process management
    "supervisor", "monit", "runit",
    
    # Additional packages
    "acct", "ack", "agedu", "alien", "apt-file", "apt-listchanges",
    "apt-show-versions", "aptitude", "asciidoctor", "aspell",
    "autossh", "awscli", "bandwidthd",
    "base-files", "bash-completion", "bind9-utils", "binfmt-support",
    "binwalk", "blktrace", "bsdmainutils", "bsdutils",
    "ca-certificates", "caca-utils", "cadaver",
    "catdoc", "ccze", "cdparanoia", "cdrdao", "cflow", "cgdb", "chafa",
    "chrony", "chrpath", "cifs-utils", "clamav-daemon", "clang-format",
    "cloc", "cmake-curses-gui", "convmv",
    "cpulimit", "cups-client", "daemon", "dar",
    "dbus", "dcfldd", "ddrescue", "debconf-utils",
    "debianutils", "deborphan", "debootstrap", "devscripts",
    "dfc", "dialog", "dictionaries-common", "diffstat",
    "dirmngr", "dislocker", "dlocate", "dnsmasq",
    "docbook-xml", "docbook-xsl", "dos2unix",
    "doxygen", "dput", "duplicity", "dvd+rw-tools",
    "eject", "enscript", "etckeeper",
    "evtest", "exfat-fuse", "expect", "fatattr",
    "fdupes", "file", "finger",
    "fontconfig", "fonts-dejavu", "fonts-liberation", "foremost",
    "fwupd", "gddrescue",
    "gedit", "gettext", "ghostscript", "gifsicle",
    "git-flow", "gitk", "gnome-keyring", "gnuplot",
    "gparted", "gpm", "graphviz", "gron",
    "grub-efi-amd64-bin", "gsfonts", "gstreamer1.0-tools",
    "gtk-doc-tools", "gufw", "hardinfo", "hashdeep", "haveged",
    "hexer", "host", "hostname", "httping", "hunspell",
    "i2c-tools", "icu-devtools", "id3v2",
    "inetutils-ping", "info", "inkscape", "inotify-tools",
    "ioping", "ipcalc", "iperf", "iptraf-ng",
    "ipython3", "jfsutils", "john", "jp2a", "kmod", "kpartx",
    "language-pack-en", "laptop-detect", "latencytop", "lcov",
    "ldap-utils", "ldb-tools", "libarchive-tools",
    "libtool-bin", "lnav", "lndir", "locales",
    "login", "lrzsz", "lsb-release", "lsof", "lsscsi",
    "manpages", "manpages-dev", "markdown", "mawk",
    "mime-support", "mlocate", "moreutils", "mosh", "mpack",
    "mtr", "multitail", "nano", "ncftp", "netcat",
    "netpbm", "nfs-kernel-server", "nicstat", "nmap",
    "ntpdate", "open-iscsi", "openntpd",
    "p7zip-rar", "par2", "pastebinit", "patch",
    "pciutils", "perf-tools-unstable", "pigz", "pixz",
    "pkgconf", "pmount", "poppler-utils", "powermgmt-base",
    "procinfo", "procmail", "psmisc", "pv", "pwauth",
    "qemu-utils", "qrencode", "quota",
    "ranger", "rcs", "rdate", "rdiff", "readline-common",
    "realpath", "rename", "renameutils", "rfkill", "rng-tools",
    "rpm", "rpm2cpio", "rrdtool", "rsnapshot", "rtorrent",
    "ruby-full", "s-nail", "s3cmd", "safe-rm", "saidar",
    "samba-common", "sane-utils", "scapy", "schedtool",
    "screen", "scsitools", "sdparm", "secure-delete",
    "sensible-utils", "sharutils", "shellcheck", "siege",
    "slurm", "smartmontools", "smem", "snmp", "snmpd",
    "socat", "sockstat", "spectre-meltdown-checker", "speedtest-cli",
    "splitvt", "sqlite3", "squashfs-tools", "sshpass", "sslscan",
    "stow", "strace", "stress", "subnetcalc", "sudo",
    "sysfsutils", "syslinux", "syslinux-common", "sysstat",
    "systemd-coredump", "tcl-dev", "tcpdump", "tcpflow",
    "tcpreplay", "tcptrack", "telnet", "testdisk",
    "texinfo", "tftp", "time", "tinc", "tk-dev",
    "tmate", "tmpreaper", "toilet", "traceroute",
    "trash-cli", "trickle", "tshark", "tig",
    "udisks2", "ufw", "unar", "unhide", "unison",
    "units", "unrar-free", "unrtf", "unzip", "usbmuxd",
    "usbutils", "uuid", "uuid-runtime", "vbetool",
    "vbindiff", "vim-common", "vim-runtime", "vlan",
    "vnstat", "w3m", "wamerican", "wbritish", "wdiff",
    "wget", "whiptail", "whois", "wireshark-common",
    "wkhtmltopdf", "wondershaper", "wput", "x11-apps",
    "x11-utils", "x11-xserver-utils", "xauth", "xclip",
    "xdg-utils", "xdotool", "xmlstarlet", "xorriso",
    "xsel", "xsltproc", "xz-utils", "yasm", "yq",
    "zerofree", "zip", "zlib1g", "zsh-common",
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
#                              COMMAND RUNNER
# ============================================================================

class Cmd:
    @staticmethod
    def run(cmd: str, timeout: int = 300) -> Tuple[bool, str, str]:
        try:
            r = subprocess.run(
                f"sudo {cmd}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'}
            )
            return r.returncode == 0, r.stdout, r.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Timeout"
        except Exception as e:
            return False, "", str(e)

    @staticmethod
    def silent(cmd: str, timeout: int = 60) -> bool:
        try:
            r = subprocess.run(
                f"sudo {cmd}",
                shell=True,
                capture_output=True,
                timeout=timeout,
                env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'}
            )
            return r.returncode == 0
        except:
            return False


# ============================================================================
#                              CPU STRESS
# ============================================================================

class CPUStress:
    def __init__(self):
        self.workers = []
        self.stop_flag = threading.Event()

    def _worker(self, wid: int):
        logger.debug(f"CPU worker {wid} started")
        while not self.stop_flag.is_set():
            start = time.time()
            while time.time() - start < 0.07:
                x = 0.0
                for i in range(10000):
                    x += math.sqrt(i) * math.sin(i) * math.cos(i)
            time.sleep(0.03)
        logger.debug(f"CPU worker {wid} stopped")

    def _io_worker(self):
        logger.debug("I/O worker started")
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
        logger.debug("Quick cleanup...")
        Cmd.silent("apt-get clean -y", 30)
        Cmd.silent("rm -rf /var/cache/apt/archives/*.deb", 10)
        Cmd.silent("rm -rf /tmp/*.tmp", 10)
        Cmd.silent("sh -c 'echo 1 > /proc/sys/vm/drop_caches'", 5)

    @staticmethod
    def medium():
        logger.info("Medium cleanup...")
        Cleaner.quick()
        Cmd.silent("apt-get autoclean -y", 60)
        Cmd.silent("apt-get autoremove -y", 120)
        Cmd.silent("journalctl --vacuum-time=1h", 30)
        Cmd.silent("rm -rf /var/log/*.gz", 10)
        Cmd.silent("rm -rf /var/log/*.1", 10)
        Cmd.silent("sh -c 'echo 3 > /proc/sys/vm/drop_caches'", 5)
        
        _, avail = SystemMonitor.get_disk()
        logger.info(f"After cleanup: {avail}GB available")

    @staticmethod
    def emergency():
        logger.warning("EMERGENCY CLEANUP!")
        Cmd.silent("apt-get clean -y", 60)
        Cmd.silent("apt-get autoremove -y --purge", 180)
        Cmd.silent("journalctl --vacuum-size=10M", 30)
        Cmd.silent("rm -rf /var/log/*", 10)
        Cmd.silent("rm -rf /tmp/*", 10)
        Cmd.silent("rm -rf /var/tmp/*", 10)
        Cmd.silent("sh -c 'echo 3 > /proc/sys/vm/drop_caches'", 5)
        
        _, avail = SystemMonitor.get_disk()
        logger.warning(f"After emergency: {avail}GB available")


# ============================================================================
#                              PACKAGE MANAGER
# ============================================================================

class Apt:
    @staticmethod
    def update() -> bool:
        logger.info("Updating apt cache...")
        ok, _, err = Cmd.run("apt-get update -y", Config.APT_UPDATE_TIMEOUT)
        if not ok:
            logger.warning(f"apt update issues: {err[:100]}")
        return True

    @staticmethod
    def install(pkg: str) -> Tuple[bool, float, str]:
        start = time.time()
        ok, _, err = Cmd.run(
            f"apt-get install -y --no-install-recommends {pkg}",
            Config.INSTALL_TIMEOUT
        )
        return ok, time.time() - start, err[:200] if not ok else ""

    @staticmethod
    def remove(pkg: str) -> Tuple[bool, float, str]:
        start = time.time()
        ok, _, err = Cmd.run(
            f"apt-get remove -y --purge {pkg}",
            Config.UNINSTALL_TIMEOUT
        )
        return ok, time.time() - start, err[:200] if not ok else ""

    @staticmethod
    def dpkg_configure() -> bool:
        """Run dpkg --configure -a to fix any broken packages"""
        logger.info("Running: dpkg --configure -a")
        ok, _, err = Cmd.run("dpkg --configure -a", Config.DPKG_CONFIGURE_TIMEOUT)
        if ok:
            logger.info("✓ dpkg --configure -a completed successfully")
        else:
            logger.warning(f"dpkg --configure -a had issues: {err[:100]}")
        return ok

    @staticmethod
    def fix_broken() -> bool:
        """Run apt-get install -f to fix broken dependencies"""
        logger.info("Running: apt-get install -f")
        ok, _, err = Cmd.run("apt-get install -f -y", 180)
        if ok:
            logger.info("✓ apt-get install -f completed successfully")
        else:
            logger.warning(f"apt-get install -f had issues: {err[:100]}")
        return ok


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
║  LOAD TEST STARTED IN BACKGROUND                                   ║
╠════════════════════════════════════════════════════════════════════╣
║  PID: {pid:<58}║
║  Log: {str(Config.LOG_FILE):<58}║
╠════════════════════════════════════════════════════════════════════╣
║  Features:                                                         ║
║  • 500+ packages install/uninstall                                 ║
║  • dpkg --configure -a every 10 packages                           ║
║  • CPU stress workers                                              ║
║  • Automatic cleanup                                               ║
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

        # Install
        ok, elapsed, err = Apt.install(pkg)
        result.install_time = elapsed

        if not ok:
            result.status = Status.INSTALL_FAILED
            result.error = err
            logger.warning(f"✗ INSTALL FAIL: {pkg} - {err[:80]}")
            return result

        logger.info(f"✓ Installed: {pkg} ({elapsed:.1f}s)")
        time.sleep(1)

        # Uninstall
        ok, elapsed, err = Apt.remove(pkg)
        result.uninstall_time = elapsed

        if not ok:
            result.status = Status.UNINSTALL_FAILED
            result.error = err
            logger.warning(f"✗ UNINSTALL FAIL: {pkg}")
            return result

        logger.info(f"✓ Removed: {pkg} ({elapsed:.1f}s)")
        result.status = Status.COMPLETED
        return result

    def print_status(self, i: int, total: int, pkg: str):
        elapsed = time.time() - self.start_time
        cpu = SystemMonitor.get_cpu_usage()
        mem_used, mem_avail, mem_total = SystemMonitor.get_memory()
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
        logger.info("  UBUNTU 24.04 LOAD GENERATOR v2.2")
        logger.info("=" * 70)
        logger.info(f"  Packages: {len(PACKAGES)}")
        logger.info(f"  PID: {os.getpid()}")
        logger.info(f"  dpkg --configure -a: Every {Config.DPKG_FIX_EVERY_N} packages")
        
        mem_used, _, mem_total = SystemMonitor.get_memory()
        _, disk_avail = SystemMonitor.get_disk()
        logger.info(f"  Memory: {mem_used}MB/{mem_total}MB | Disk: {disk_avail}GB")
        logger.info("=" * 70)

        # Initial setup
        logger.info("Initial dpkg configure...")
        Apt.dpkg_configure()
        Apt.fix_broken()
        
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
                result = self.process_package(pkg)
                self.results.append(result)

                # Quick cleanup after each package
                Cleaner.quick()

                # Every N packages: run dpkg --configure -a
                if i % Config.DPKG_FIX_EVERY_N == 0:
                    logger.info(f"")
                    logger.info(f"{'='*60}")
                    logger.info(f"  MAINTENANCE: After {i} packages")
                    logger.info(f"{'='*60}")
                    
                    # Run dpkg --configure -a
                    Apt.dpkg_configure()
                    
                    # Fix any broken dependencies
                    Apt.fix_broken()
                    
                    # Medium cleanup
                    Cleaner.medium()
                    
                    logger.info(f"{'='*60}")
                    logger.info(f"")

                # Deep cleanup every N packages
                if i % Config.DEEP_CLEANUP_EVERY_N == 0:
                    logger.info(f"=== Milestone: {i}/{total} ===")
                    Cleaner.medium()

        except Exception as e:
            logger.error(f"Error: {e}")

        finally:
            # Final maintenance
            logger.info("Final dpkg configure...")
            Apt.dpkg_configure()
            Apt.fix_broken()
            
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
        logger.info(f"  Success Rate: {len(ok)/len(self.results)*100:.1f}%" if self.results else "N/A")
        logger.info(f"  Runtime: {elapsed/60:.1f} minutes ({elapsed/3600:.1f} hours)")
        logger.info(f"  dpkg --configure -a runs: {len(self.results) // Config.DPKG_FIX_EVERY_N}")
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
║  UBUNTU 24.04 LOAD GENERATOR v2.2                                  ║
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
║    --help        Show help                                         ║
║                                                                    ║
║  Features:                                                         ║
║    • 500+ packages install/uninstall                               ║
║    • dpkg --configure -a every 10 packages                         ║
║    • apt-get install -f to fix broken deps                         ║
║    • CPU stress workers (40%+ load)                                ║
║    • Automatic disk cleanup                                        ║
║    • Emergency cleanup on low disk                                 ║
╚════════════════════════════════════════════════════════════════════╝
""")
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
