#!/usr/bin/env python3
"""
===============================================================================
  UBUNTU 24.04 LTS ULTIMATE LOAD GENERATOR v2.0
  500+ packages | 40%+ CPU Load | Background Execution
  Optimized for: 512MB RAM, 7GB free storage (EC2 t2.micro/t3.micro)
===============================================================================
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
import json
import atexit
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# ============================================================================
#                              CONFIGURATION
# ============================================================================

class Config:
    """Central configuration"""
    LOG_FILE = Path('/tmp/load_test.log')
    PID_FILE = Path('/tmp/load_test.pid')
    STATE_FILE = Path('/tmp/load_test_state.json')
    STATS_FILE = Path('/tmp/load_test_stats.json')
    
    # Resource thresholds
    MIN_DISK_GB = 1.5
    EMERGENCY_DISK_GB = 1.0
    MIN_MEMORY_MB = 100
    
    # CPU stress settings
    TARGET_CPU_PERCENT = 45
    CPU_WORKER_INTENSITY = 0.7
    
    # Timeouts (seconds)
    INSTALL_TIMEOUT = 180
    UNINSTALL_TIMEOUT = 120
    CLEANUP_TIMEOUT = 60
    APT_UPDATE_TIMEOUT = 180
    
    # Cleanup intervals
    CLEANUP_EVERY_N_PACKAGES = 15
    DEEP_CLEANUP_EVERY_N_PACKAGES = 50
    
    # Delays (seconds)
    POST_INSTALL_DELAY = 1
    POST_CLEANUP_DELAY = 0.5


class Status(Enum):
    """Package processing status"""
    PENDING = "pending"
    INSTALLING = "installing"
    INSTALLED = "installed"
    UNINSTALLING = "uninstalling"
    COMPLETED = "completed"
    INSTALL_FAILED = "install_failed"
    UNINSTALL_FAILED = "uninstall_failed"
    SKIPPED = "skipped"


@dataclass
class PackageResult:
    """Result of package processing"""
    name: str
    status: Status
    install_time: float = 0.0
    uninstall_time: float = 0.0
    error: str = ""


@dataclass
class SystemStats:
    """System statistics snapshot"""
    timestamp: str
    cpu_percent: float
    memory_used_mb: int
    memory_total_mb: int
    memory_available_mb: int
    disk_used_gb: int
    disk_available_gb: int
    packages_processed: int
    packages_total: int
    success_rate: float


# ============================================================================
#                              PACKAGE LIST (850+)
# ============================================================================

PACKAGES = [
    # ==================== TEXT EDITORS (1-35) ====================
    "nano", "vim", "vim-tiny", "vim-nox", "emacs-nox", "joe", "jed", "ne", 
    "micro", "ed", "nvi", "elvis-tiny", "zile", "mg", "jupp", "le", "fte", 
    "hexedit", "dhex", "tweak", "ht", "bvi", "beav", "ncurses-hexedit", 
    "vile", "neovim", "kakoune", "vis", "mle", "tilde", "dte", "sand",
    "amp", "ox", "zee",

    # ==================== SHELLS & TERMINAL (36-75) ====================
    "zsh", "fish", "tcsh", "ksh", "mksh", "dash", "busybox", "posh", "rc",
    "yash", "elvish", "xonsh", "screen", "tmux", "byobu", "dvtm", "abduco",
    "dtach", "reptyr", "tmate", "asciinema", "ttyrec", "termrec", "fbterm",
    "jfbterm", "kmscon", "agetty", "mingetty", "mgetty", "vlock", "physlock",
    "kbd", "console-setup", "console-data", "console-tools", "gpm",
    "beep", "setterm", "tput", "infocmp",

    # ==================== FILE MANAGERS (76-110) ====================
    "mc", "ranger", "vifm", "nnn", "lf", "fff", "broot", "lfm", "clex",
    "gentoo", "worker", "pcmanfm", "thunar", "spacefm", "rox-filer",
    "xfe", "emelfm2", "tuxcmd", "gnome-commander", "sunflower",
    "doublecmd-gtk", "doublecmd-qt", "krusader", "polo-file-manager",
    "caja", "nemo", "nautilus", "dolphin", "konqueror", "thunar-volman",
    "pcmanfm-qt", "lxqt-archiver", "engrampa", "file-roller",

    # ==================== SYSTEM MONITORING (111-175) ====================
    "htop", "btop", "atop", "iotop", "iftop", "nethogs", "nload", "bmon",
    "vnstat", "dstat", "sysstat", "sar", "iostat", "mpstat", "pidstat",
    "procps", "psmisc", "lsof", "strace", "ltrace", "fatrace", "blktrace",
    "inotify-tools", "incron", "glances", "nmon", "collectl", "tiptop",
    "linux-tools-common", "cpustat", "numactl", "hwloc", "likwid",
    "stress", "stress-ng", "sysbench", "fio", "iozone3", "bonnie++",
    "dbench", "tiobench", "postmark", "filebench", "fs-mark", "ioping",
    "interbench", "rt-tests", "hackbench", "cyclictest", "schedtool",
    "cpulimit", "cputool", "cpufrequtils", "cpupower", "irqbalance",
    "numad", "oprofile", "perf-tools-unstable", "trace-cmd", "kernelshark",
    "slabtop", "smem", "memstat", "vmtouch", "fincore", "pcstat",

    # ==================== NETWORK TOOLS (176-280) ====================
    "net-tools", "iproute2", "iputils-ping", "iputils-tracepath",
    "iputils-arping", "iputils-clockdiff", "traceroute", "mtr-tiny", "mtr",
    "tcpdump", "nmap", "zenmap", "netcat-openbsd", "netcat-traditional",
    "socat", "telnet", "telnetd", "ftp", "lftp", "ncftp", "yafc",
    "wget", "wget2", "curl", "aria2", "axel", "prozilla", "httpie",
    "links", "links2", "lynx", "w3m", "elinks", "html2text", "surfraw",
    "ddgr", "googler", "whois", "jwhois", "dnsutils", "bind9-host",
    "bind9-dnsutils", "ldnsutils", "knot-dnsutils", "unbound-host",
    "avahi-utils", "avahi-daemon", "libnss-mdns", "smbclient", "samba-common",
    "cifs-utils", "nfs-common", "nfs-kernel-server", "autofs",
    "rsync", "rclone", "iperf", "iperf3", "netperf", "nuttcp",
    "speedtest-cli", "fast", "ethtool", "mii-tool", "mii-diag",
    "bridge-utils", "vlan", "vconfig", "ifenslave", "bonding",
    "wpasupplicant", "wireless-tools", "iw", "rfkill", "crda",
    "bluez", "bluez-tools", "bluez-hcidump", "obexftp", "ussp-push",
    "netdiag", "hping3", "arping", "fping", "arp-scan", "arpwatch",
    "masscan", "zmap", "unicornscan", "netdiscover", "nbtscan",
    "onesixtyone", "snmp", "snmpd", "snmptrapd", "libsnmp-dev",
    "tshark", "termshark", "ngrep", "tcpflow", "tcpreplay", "tcpstat",
    "darkstat", "bandwidthd", "ntopng", "mrtg", "rrdtool", "cacti",
    "nagios-nrpe-server", "collectd", "telegraf", "prometheus-node-exporter",

    # ==================== COMPRESSION TOOLS (281-340) ====================
    "gzip", "pigz", "bzip2", "lbzip2", "pbzip2", "xz-utils", "pixz", "pxz",
    "lzma", "lzip", "plzip", "lzop", "zstd", "lz4", "lz4json", "brotli",
    "zip", "unzip", "p7zip", "p7zip-full", "p7zip-rar", "unrar-free",
    "rar", "arj", "unarj", "lhasa", "lha", "zoo", "unzoo",
    "sharutils", "uudeview", "cabextract", "unace", "unalz",
    "rpm2cpio", "cpio", "afio", "pax", "tar", "star", "libarchive-tools",
    "genisoimage", "xorriso", "wodim", "cdrdao", "cdrkit-doc",
    "mtools", "dosfstools", "hfsplus", "hfsprogs", "hfsutils",
    "squashfs-tools", "erofs-utils", "cramfsswap", "genromfs",
    "makebootfat", "syslinux", "extlinux", "isolinux", "pxelinux",

    # ==================== DEVELOPMENT TOOLS (341-500) ====================
    "build-essential", "gcc", "g++", "gfortran", "gccgo", "gdc", "gnat",
    "clang", "llvm", "lld", "lldb", "clang-format", "clang-tidy",
    "make", "remake", "bmake", "cmake", "cmake-curses-gui", "ccmake",
    "ninja-build", "meson", "autoconf", "automake", "libtool", "libtool-bin",
    "pkg-config", "pkgconf", "bison", "byacc", "flex", "reflex",
    "gawk", "mawk", "nawk", "m4", "patch", "patchutils", "quilt",
    "diffutils", "diffstat", "wiggle", "colordiff", "icdiff", "delta",
    "git", "git-lfs", "git-annex", "git-crypt", "git-secret", "git-flow",
    "git-cola", "gitg", "tig", "lazygit", "gitui", "grv",
    "subversion", "mercurial", "cvs", "rcs", "darcs", "fossil", "bazaar",
    "indent", "astyle", "uncrustify", "artistic-style",
    "universal-ctags", "exuberant-ctags", "cscope", "global", "idutils",
    "gdb", "gdbserver", "cgdb", "ddd", "nemiver", "valgrind", "kcachegrind",
    "binutils", "binutils-dev", "elfutils", "patchelf", "chrpath", "rpath",
    "readelf", "objdump", "objcopy", "nm", "strip", "addr2line", "c++filt",
    "python3", "python3-pip", "python3-venv", "python3-dev", "python3-dbg",
    "python3-setuptools", "python3-wheel", "python3-virtualenv", "pipx",
    "python3-numpy", "python3-scipy", "python3-pandas", "python3-matplotlib",
    "python3-requests", "python3-flask", "python3-django", "python3-sqlalchemy",
    "python3-pytest", "python3-nose", "python3-coverage", "python3-pylint",
    "python3-mypy", "python3-black", "python3-isort", "python3-autopep8",
    "ruby", "ruby-dev", "ruby-full", "rubygems", "bundler", "rake",
    "perl", "perl-doc", "perl-modules", "libperl-dev", "cpanminus",
    "lua5.4", "luajit", "liblua5.4-dev", "luarocks",
    "tcl", "tcl-dev", "tk", "tk-dev", "expect",
    "php-cli", "php-common", "php-json", "php-xml", "php-curl", "php-mbstring",
    "php-mysql", "php-pgsql", "php-sqlite3", "php-gd", "php-zip", "composer",
    "nodejs", "npm", "yarn", "pnpm",
    "golang-go", "golang-doc",
    "rustc", "cargo", "rustfmt", "clippy",
    "default-jdk", "default-jre", "openjdk-11-jdk", "openjdk-17-jdk",
    "ant", "maven", "gradle",
    "scala", "groovy", "kotlin", "clojure", "leiningen",
    "sbcl", "clisp", "ecl", "gcl", "cmucl",
    "racket", "guile-3.0", "chicken-bin", "gambit-c", "stalin",
    "gprolog", "swi-prolog", "yap", "gnu-prolog",
    "erlang", "elixir", "rebar3",
    "ghc", "cabal-install", "stack", "haskell-platform",
    "ocaml", "opam", "dune", "ocamlbuild",
    "fsharp", "mono-complete", "nuget",
    "nasm", "yasm", "fasm", "gas",
    "gforth", "pforth", "bigforth",

    # ==================== TEXT PROCESSING (501-560) ====================
    "sed", "ssed", "sd", "grep", "agrep", "tre-agrep", "sgrep", "pcregrep",
    "ripgrep", "silversearcher-ag", "ack", "ugrep", "grepcidr",
    "findutils", "mlocate", "plocate", "fd-find", "fzf", "peco", "percol",
    "coreutils", "moreutils", "parallel", "xargs", "gparallel",
    "wdiff", "dwdiff", "xxdiff", "kdiff3", "meld", "vimdiff",
    "xxd", "od", "hexdump", "hd", "hexyl",
    "cut", "gcut", "paste", "join", "sort", "msort", "uniq", "huniq",
    "comm", "tsort", "ptx", "nl", "pr", "fmt", "fold", "column",
    "rev", "tac", "head", "tail", "split", "csplit", "shuf",
    "tr", "expand", "unexpand", "dos2unix", "unix2dos", "recode", "iconv",
    "pandoc", "asciidoc", "asciidoctor", "docbook-utils", "docbook-xsl",
    "xmlto", "xsltproc", "txt2html", "txt2man", "txt2tags",
    "markdown", "discount", "cmark", "cmark-gfm", "lowdown", "mmark",
    "groff", "troff", "nroff", "eqn", "tbl", "pic", "refer",

    # ==================== SECURITY TOOLS (561-640) ====================
    "openssl", "gnutls-bin", "nss-tools", "mbedtls-utils", "libressl",
    "gnupg", "gnupg2", "gpg", "gpgv", "gpgsm", "gpg-agent", "scdaemon",
    "pinentry-curses", "pinentry-tty", "pinentry-gtk2", "pinentry-gnome3",
    "pass", "gopass", "passage", "pa", "kpcli", "keepassxc",
    "pwgen", "apg", "makepasswd", "diceware", "xkcdpass", "genpass",
    "age", "sops", "tomb", "zulucrypt-cli", "veracrypt",
    "keychain", "ssh-agent", "ssh-add", "seahorse", "gnome-keyring",
    "checksec", "hardening-check", "debsums", "debsecan", "debsig-verify",
    "aide", "aide-common", "tripwire", "samhain", "ossec-hids-agent",
    "rkhunter", "chkrootkit", "unhide", "unhide-tcp",
    "lynis", "tiger", "bastille", "buck-security",
    "fail2ban", "sshguard", "denyhosts", "blockhosts",
    "ufw", "gufw", "iptables", "iptables-persistent", "netfilter-persistent",
    "nftables", "firewalld", "shorewall", "firehol", "ferm",
    "ipset", "ipset-persistent", "conntrack", "conntrackd",
    "ebtables", "arptables", "fwbuilder",
    "apparmor", "apparmor-utils", "apparmor-profiles", "apparmor-profiles-extra",
    "selinux-basics", "selinux-policy-default", "selinux-utils",
    "firejail", "bubblewrap", "nsjail", "minijail",
    "clamav", "clamav-daemon", "clamav-freshclam", "clamtk", "clamdscan",
    "john", "john-data", "hashcat", "hashcat-utils", "hashid",

    # ==================== SYSTEM UTILITIES (641-740) ====================
    "cron", "anacron", "at", "batch", "fcron", "bcron", "dcron",
    "logrotate", "rsyslog", "syslog-ng", "journalctl", "systemd-journal-remote",
    "acl", "attr", "facl", "fattr", "getfacl", "setfacl", "chacl",
    "quota", "quotatool", "repquota", "edquota", "quotacheck",
    "hdparm", "sdparm", "blktool", "blockdev", "sg3-utils", "sdparm",
    "smartmontools", "smartctl", "nvme-cli", "nvmetcli",
    "lvm2", "thin-provisioning-tools", "device-mapper-multipath",
    "mdadm", "dmraid", "dmsetup", "kpartx",
    "cryptsetup", "cryptsetup-bin", "cryptmount", "ecryptfs-utils",
    "multipath-tools", "open-iscsi", "iscsitarget", "tgt", "targetcli-fb",
    "parted", "gparted", "gdisk", "cgdisk", "sgdisk", "fixparts",
    "fdisk", "sfdisk", "cfdisk", "util-linux",
    "blkid", "lsblk", "findmnt", "mountpoint", "blockdev",
    "fuse3", "fuse2fs", "sshfs", "curlftpfs", "s3fs", "rclone-browser",
    "bindfs", "unionfs-fuse", "mergerfs", "mhddfs", "aufs-tools", "overlayroot",
    "e2fsprogs", "e2fsck", "mke2fs", "resize2fs", "tune2fs", "dumpe2fs",
    "debugfs", "e2image", "e2label", "e2undo", "logsave",
    "xfsprogs", "xfs_repair", "xfs_growfs", "xfsdump", "xfsrestore",
    "btrfs-progs", "btrfs-compsize", "duperemove", "btrbk",
    "bcache-tools", "zfs-fuse", "zfsutils-linux",
    "exfatprogs", "exfat-fuse", "ntfs-3g", "ntfsprogs",
    "dosfstools", "mtools", "fatattr", "fatsort",
    "jfsutils", "reiserfsprogs", "reiser4progs",
    "f2fs-tools", "nilfs-tools", "udftools",
    "initramfs-tools", "initramfs-tools-core", "dracut", "dracut-core",
    "update-grub", "grub-common", "grub-pc-bin", "grub-efi-amd64-bin",
    "efibootmgr", "mokutil", "sbsigntool", "pesign", "shim-signed",
    "acpid", "acpi", "acpitool", "acpi-support",
    "lm-sensors", "fancontrol", "sensord", "i2c-tools",
    "hddtemp", "udisks2", "usbutils", "pciutils", "dmidecode",
    "powertop", "tlp", "tlp-rdw", "laptop-mode-tools",
    "cpufrequtils", "cpupower", "thermald",

    # ==================== MISC UTILITIES (741-800) ====================
    "bc", "dc", "calc", "qalc", "wcalc", "units", "gnu-units",
    "dateutils", "ddate", "remind", "calcurse", "when", "pal", "wyrd",
    "taskwarrior", "todo.txt-cli", "devtodo", "tdl", "tudu", "yokadi",
    "fortune-mod", "fortunes", "fortunes-min", "cowsay", "xcowsay",
    "figlet", "toilet", "boxes", "banner", "sysvbanner", "printerbanner",
    "lolcat", "cmatrix", "tty-clock", "sl", "oneko", "xeyes",
    "linuxlogo", "neofetch", "screenfetch", "archey4", "ufetch",
    "inxi", "hardinfo", "lshw", "lshw-gtk", "hwinfo",
    "tree", "pstree", "lstree", "as-tree",
    "pv", "progress", "cv", "pipemeter",
    "most", "less", "more", "pg",
    "highlight", "source-highlight", "pygmentize",
    "bat", "ccat", "vimcat", "mdcat",
    "exa", "lsd", "colorls", "natls",
    "jq", "jid", "jless", "fx",
    "yq", "xq", "tomlq", "htmlq",
    "xmlstarlet", "xmllint", "html-xml-utils", "tidy", "pup",

    # ==================== DATABASES & SERVERS (801-850) ====================
    "sqlite3", "sqlite3-doc", "libsqlite3-dev", "sqlitebrowser",
    "mariadb-client", "mariadb-server", "mysql-client", "mycli",
    "postgresql-client", "postgresql", "pgcli", "pgtop",
    "redis-tools", "redis-server", "redis-sentinel",
    "memcached", "libmemcached-tools",
    "mongodb-clients", "mongodb-org-shell",
    "ldap-utils", "slapd", "ldapvi", "ldapsearch",
    "apache2", "apache2-utils", "libapache2-mod-php",
    "nginx", "nginx-common", "nginx-full", "nginx-extras",
    "lighttpd", "lighttpd-mod-webdav",
    "thttpd", "mini-httpd", "micro-httpd", "webfs", "darkhttpd",
    "squid", "squid-common", "squidclient",
    "haproxy", "pound", "pen", "balance",
    "varnish", "varnish-modules",
    "uwsgi", "uwsgi-core", "uwsgi-plugin-python3",
    "gunicorn", "python3-gunicorn",
    "supervisor", "circus", "runit", "runit-init",
    "s6", "s6-rc", "66", "dinit",
    "monit", "god", "bluepill",

    # ==================== ADDITIONAL EXTRAS (851-900+) ====================
    "mutt", "neomutt", "alpine", "cone", "nmh", "mailutils",
    "procmail", "maildrop", "sieve-connect", "imapfilter",
    "offlineimap", "isync", "mbsync", "fetchmail", "getmail6", "fdm",
    "notmuch", "notmuch-mutt", "alot", "astroid",
    "abook", "khard", "goobook",
    "calcurse", "khal", "vdirsyncer", "todoman",
    "newsboat", "snownews", "rawdog", "rsstail",
    "irssi", "weechat", "bitlbee", "znc", "quassel-core",
    "toot", "tootstream", "rainbowstream",
    "rtorrent", "transmission-cli", "aria2", "deluge-console",
    "youtube-dl", "yt-dlp", "streamlink", "you-get",
    "mpv", "mplayer", "vlc-nox", "ffplay",
    "cmus", "moc", "mpd", "ncmpcpp", "vimpc",
    "feh", "sxiv", "imv", "chafa", "catimg", "tiv",
    "w3m-img", "ueberzug", "sixel-tmux",
]


# ============================================================================
#                              LOGGING SETUP
# ============================================================================

class ColorFormatter(logging.Formatter):
    """Colored log formatter"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # File handler
    file_handler = logging.FileHandler(Config.LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    
    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(ColorFormatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    ))
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logging.getLogger(__name__)


logger = setup_logging()


# ============================================================================
#                              SYSTEM UTILITIES
# ============================================================================

class SystemMonitor:
    """System resource monitoring"""
    
    @staticmethod
    def get_cpu_usage() -> float:
        """Get current CPU usage percentage"""
        try:
            with open('/proc/stat', 'r') as f:
                line1 = f.readline()
            values1 = [int(v) for v in line1.split()[1:8]]
            
            time.sleep(0.1)
            
            with open('/proc/stat', 'r') as f:
                line2 = f.readline()
            values2 = [int(v) for v in line2.split()[1:8]]
            
            idle_delta = values2[3] - values1[3]
            total_delta = sum(values2) - sum(values1)
            
            if total_delta > 0:
                return round(100.0 * (1.0 - idle_delta / total_delta), 1)
        except Exception:
            pass
        return 0.0
    
    @staticmethod
    def get_memory_usage() -> Tuple[int, int, int]:
        """Get memory usage (used_mb, available_mb, total_mb)"""
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
            
            meminfo = {}
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(':')
                    value = int(parts[1]) // 1024  # Convert KB to MB
                    meminfo[key] = value
            
            total = meminfo.get('MemTotal', 0)
            available = meminfo.get('MemAvailable', 0)
            used = total - available
            
            return used, available, total
        except Exception:
            pass
        return 0, 0, 0
    
    @staticmethod
    def get_disk_usage() -> Tuple[int, int]:
        """Get disk usage (used_gb, available_gb)"""
        try:
            stat = os.statvfs('/')
            total = (stat.f_blocks * stat.f_frsize) // (1024**3)
            available = (stat.f_bavail * stat.f_frsize) // (1024**3)
            used = total - available
            return used, available
        except Exception:
            pass
        return 0, 0
    
    @staticmethod
    def get_load_average() -> Tuple[float, float, float]:
        """Get system load average"""
        try:
            return os.getloadavg()
        except Exception:
            return 0.0, 0.0, 0.0
    
    @classmethod
    def get_stats(cls, packages_processed: int = 0, packages_total: int = 0) -> SystemStats:
        """Get complete system statistics"""
        mem_used, mem_avail, mem_total = cls.get_memory_usage()
        disk_used, disk_avail = cls.get_disk_usage()
        
        success_rate = (packages_processed / packages_total * 100) if packages_total > 0 else 0
        
        return SystemStats(
            timestamp=datetime.now().isoformat(),
            cpu_percent=cls.get_cpu_usage(),
            memory_used_mb=mem_used,
            memory_total_mb=mem_total,
            memory_available_mb=mem_avail,
            disk_used_gb=disk_used,
            disk_available_gb=disk_avail,
            packages_processed=packages_processed,
            packages_total=packages_total,
            success_rate=success_rate
        )
    
    @classmethod
    def check_resources(cls) -> Tuple[bool, str]:
        """Check if system has enough resources to continue"""
        _, mem_avail, _ = cls.get_memory_usage()
        _, disk_avail = cls.get_disk_usage()
        
        if disk_avail < Config.EMERGENCY_DISK_GB:
            return False, f"Critical: Only {disk_avail}GB disk space"
        
        if mem_avail < Config.MIN_MEMORY_MB:
            return False, f"Critical: Only {mem_avail}MB memory available"
        
        if disk_avail < Config.MIN_DISK_GB:
            return True, f"Warning: Low disk space ({disk_avail}GB)"
        
        return True, "OK"


# ============================================================================
#                              COMMAND EXECUTION
# ============================================================================

class CommandRunner:
    """Execute system commands safely"""
    
    @staticmethod
    def run(cmd: str, timeout: int = 300, sudo: bool = True) -> Tuple[bool, str, str]:
        """Run a shell command with timeout"""
        if sudo and not cmd.startswith('sudo'):
            cmd = f"sudo {cmd}"
        
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
            logger.warning(f"Command timed out: {cmd[:60]}...")
            return False, "", "Timeout"
        except Exception as e:
            logger.error(f"Command error: {e}")
            return False, "", str(e)
    
    @staticmethod
    def run_silent(cmd: str, timeout: int = 60) -> bool:
        """Run command without logging output"""
        try:
            result = subprocess.run(
                f"sudo {cmd}",
                shell=True,
                capture_output=True,
                timeout=timeout,
                env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'}
            )
            return result.returncode == 0
        except Exception:
            return False


# ============================================================================
#                              CPU STRESS WORKERS
# ============================================================================

class CPUStressManager:
    """Manage CPU stress workers"""
    
    def __init__(self):
        self.workers: List[threading.Thread] = []
        self.stop_flag = threading.Event()
        self.intensity = Config.CPU_WORKER_INTENSITY
    
    def _cpu_worker(self, worker_id: int):
        """CPU intensive worker thread"""
        logger.debug(f"CPU Worker {worker_id} started")
        
        while not self.stop_flag.is_set():
            # Work phase
            work_start = time.time()
            work_duration = 0.1 * self.intensity
            
            while (time.time() - work_start) < work_duration and not self.stop_flag.is_set():
                x = 0.0
                for i in range(10000):
                    x += math.sqrt(i) * math.sin(i) * math.cos(i)
                    x += math.log(i + 1) * math.exp(i % 10)
                    x += math.tan(i % 89 + 1) * math.atan(i)
                    x += math.pow(i % 100 + 1, 0.5) * math.factorial(min(i % 10, 8))
            
            # Sleep phase
            sleep_duration = 0.1 * (1 - self.intensity)
            if sleep_duration > 0:
                time.sleep(sleep_duration)
        
        logger.debug(f"CPU Worker {worker_id} stopped")
    
    def _io_worker(self):
        """I/O stress worker"""
        logger.debug("I/O Worker started")
        temp_file = Path('/tmp/io_stress.tmp')
        
        while not self.stop_flag.is_set():
            try:
                # Write
                with open(temp_file, 'wb') as f:
                    for _ in range(50):
                        if self.stop_flag.is_set():
                            break
                        f.write(os.urandom(8192))
                        f.flush()
                
                # Read
                if temp_file.exists():
                    with open(temp_file, 'rb') as f:
                        while f.read(8192) and not self.stop_flag.is_set():
                            pass
                
                # Cleanup
                if temp_file.exists():
                    temp_file.unlink()
                
                time.sleep(0.5)
            except Exception:
                time.sleep(1)
        
        if temp_file.exists():
            temp_file.unlink()
        
        logger.debug("I/O Worker stopped")
    
    def start(self):
        """Start all stress workers"""
        self.stop_flag.clear()
        
        cpu_count = multiprocessing.cpu_count()
        num_workers = max(1, int(cpu_count * 0.6))
        
        logger.info(f"Starting {num_workers} CPU workers + 1 I/O worker")
        
        # CPU workers
        for i in range(num_workers):
            worker = threading.Thread(target=self._cpu_worker, args=(i,), daemon=True)
            worker.start()
            self.workers.append(worker)
        
        # I/O worker
        io_worker = threading.Thread(target=self._io_worker, daemon=True)
        io_worker.start()
        self.workers.append(io_worker)
        
        # Wait and verify
        time.sleep(2)
        cpu_usage = SystemMonitor.get_cpu_usage()
        logger.info(f"CPU load after starting workers: {cpu_usage}%")
    
    def stop(self):
        """Stop all stress workers"""
        logger.info("Stopping stress workers...")
        self.stop_flag.set()
        
        for worker in self.workers:
            worker.join(timeout=2)
        
        self.workers.clear()
        logger.info("All stress workers stopped")
    
    def adjust_intensity(self, target_cpu: float):
        """Dynamically adjust intensity to match target CPU"""
        current_cpu = SystemMonitor.get_cpu_usage()
        
        if current_cpu < target_cpu - 10:
            self.intensity = min(0.95, self.intensity + 0.05)
        elif current_cpu > target_cpu + 10:
            self.intensity = max(0.3, self.intensity - 0.05)


# ============================================================================
#                              SYSTEM CLEANUP
# ============================================================================

class SystemCleaner:
    """System cleanup utilities"""
    
    CLEANUP_COMMANDS = [
        "apt-get clean -y",
        "apt-get autoclean -y",
        "rm -rf /var/cache/apt/archives/*.deb",
        "rm -rf /var/cache/apt/archives/partial/*",
        "rm -rf /var/tmp/*",
        "rm -rf /tmp/*.tmp",
        "rm -rf /tmp/apt-*",
    ]
    
    DEEP_CLEANUP_COMMANDS = [
        "apt-get autoremove -y --purge",
        "journalctl --vacuum-time=1h",
        "journalctl --vacuum-size=50M",
        "rm -rf /var/log/*.gz",
        "rm -rf /var/log/*.1",
        "rm -rf /var/log/*.old",
        "rm -rf /var/log/apt/*",
        "rm -rf /var/lib/apt/lists/*",
        "apt-get update -y",
    ]
    
    @classmethod
    def quick_cleanup(cls):
        """Quick cleanup after package operations"""
        logger.debug("Quick cleanup...")
        for cmd in cls.CLEANUP_COMMANDS:
            CommandRunner.run_silent(cmd, timeout=30)
        
        # Clear memory cache
        CommandRunner.run_silent("sh -c 'echo 1 > /proc/sys/vm/drop_caches'", timeout=5)
        time.sleep(Config.POST_CLEANUP_DELAY)
    
    @classmethod
    def deep_cleanup(cls):
        """Deep cleanup to free maximum space"""
        logger.info("Performing deep cleanup...")
        
        # First do quick cleanup
        cls.quick_cleanup()
        
        # Then deep cleanup
        for cmd in cls.DEEP_CLEANUP_COMMANDS:
            CommandRunner.run_silent(cmd, timeout=Config.CLEANUP_TIMEOUT)
        
        # Aggressive memory cleanup
        CommandRunner.run_silent("sh -c 'echo 3 > /proc/sys/vm/drop_caches'", timeout=5)
        CommandRunner.run_silent("sync", timeout=10)
        
        _, disk_avail = SystemMonitor.get_disk_usage()
        logger.info(f"After deep cleanup: {disk_avail}GB available")
    
    @classmethod
    def emergency_cleanup(cls):
        """Emergency cleanup when critically low on resources"""
        logger.warning("EMERGENCY CLEANUP TRIGGERED!")
        
        emergency_commands = [
            "apt-get clean -y",
            "apt-get autoremove -y --purge",
            "rm -rf /var/cache/*",
            "rm -rf /var/tmp/*",
            "rm -rf /tmp/*",
            "journalctl --vacuum-size=10M",
            "rm -rf /var/log/*",
        ]
        
        for cmd in emergency_commands:
            CommandRunner.run_silent(cmd, timeout=60)
        
        CommandRunner.run_silent("sh -c 'echo 3 > /proc/sys/vm/drop_caches'", timeout=5)
        
        _, disk_avail = SystemMonitor.get_disk_usage()
        logger.warning(f"After emergency cleanup: {disk_avail}GB available")


# ============================================================================
#                              PACKAGE MANAGER
# ============================================================================

class PackageManager:
    """APT package management"""
    
    @staticmethod
    def update_cache() -> bool:
        """Update apt package cache"""
        logger.info("Updating apt cache...")
        success, _, stderr = CommandRunner.run(
            "apt-get update -y",
            timeout=Config.APT_UPDATE_TIMEOUT
        )
        if not success:
            logger.warning(f"apt update had issues: {stderr[:100]}")
        return True  # Continue even with warnings
    
    @staticmethod
    def install(package: str) -> Tuple[bool, float, str]:
        """Install a package, returns (success, time_taken, error)"""
        start = time.time()
        
        cmd = f"apt-get install -y --no-install-recommends {package}"
        success, _, stderr = CommandRunner.run(cmd, timeout=Config.INSTALL_TIMEOUT)
        
        elapsed = time.time() - start
        error = stderr[:200] if not success else ""
        
        return success, elapsed, error
    
    @staticmethod
    def uninstall(package: str) -> Tuple[bool, float, str]:
        """Uninstall a package, returns (success, time_taken, error)"""
        start = time.time()
        
        cmd = f"apt-get remove -y --purge {package}"
        success, _, stderr = CommandRunner.run(cmd, timeout=Config.UNINSTALL_TIMEOUT)
        
        elapsed = time.time() - start
        error = stderr[:200] if not success else ""
        
        return success, elapsed, error
    
    @staticmethod
    def is_installed(package: str) -> bool:
        """Check if package is installed"""
        success, _, _ = CommandRunner.run(
            f"dpkg -l {package} 2>/dev/null | grep -q '^ii'",
            timeout=10,
            sudo=False
        )
        return success


# ============================================================================
#                              STATE MANAGEMENT
# ============================================================================

class StateManager:
    """Manage test state for resume capability"""
    
    @staticmethod
    def save_state(current_index: int, results: List[PackageResult]):
        """Save current state to file"""
        state = {
            'current_index': current_index,
            'timestamp': datetime.now().isoformat(),
            'results': [
                {
                    'name': r.name,
                    'status': r.status.value,
                    'install_time': r.install_time,
                    'uninstall_time': r.uninstall_time,
                    'error': r.error
                }
                for r in results
            ]
        }
        
        with open(Config.STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    
    @staticmethod
    def load_state() -> Tuple[int, List[PackageResult]]:
        """Load state from file"""
        if not Config.STATE_FILE.exists():
            return 0, []
        
        try:
            with open(Config.STATE_FILE, 'r') as f:
                state = json.load(f)
            
            results = [
                PackageResult(
                    name=r['name'],
                    status=Status(r['status']),
                    install_time=r.get('install_time', 0),
                    uninstall_time=r.get('uninstall_time', 0),
                    error=r.get('error', '')
                )
                for r in state.get('results', [])
            ]
            
            return state.get('current_index', 0), results
        except Exception as e:
            logger.warning(f"Could not load state: {e}")
            return 0, []
    
    @staticmethod
    def clear_state():
        """Clear saved state"""
        if Config.STATE_FILE.exists():
            Config.STATE_FILE.unlink()
    
    @staticmethod
    def save_stats(stats: SystemStats):
        """Append stats to stats file"""
        stats_list = []
        
        if Config.STATS_FILE.exists():
            try:
                with open(Config.STATS_FILE, 'r') as f:
                    stats_list = json.load(f)
            except Exception:
                pass
        
        stats_list.append(asdict(stats))
        
        # Keep only last 1000 entries
        if len(stats_list) > 1000:
            stats_list = stats_list[-1000:]
        
        with open(Config.STATS_FILE, 'w') as f:
            json.dump(stats_list, f)


# ============================================================================
#                              PROCESS MANAGEMENT
# ============================================================================

class ProcessManager:
    """Manage daemon process"""
    
    @staticmethod
    def write_pid():
        """Write PID to file"""
        Config.PID_FILE.write_text(str(os.getpid()))
    
    @staticmethod
    def remove_pid():
        """Remove PID file"""
        if Config.PID_FILE.exists():
            Config.PID_FILE.unlink()
    
    @staticmethod
    def get_pid() -> Optional[int]:
        """Get PID from file"""
        if Config.PID_FILE.exists():
            try:
                return int(Config.PID_FILE.read_text().strip())
            except Exception:
                pass
        return None
    
    @staticmethod
    def is_running() -> bool:
        """Check if process is running"""
        pid = ProcessManager.get_pid()
        if pid:
            try:
                os.kill(pid, 0)
                return True
            except ProcessLookupError:
                return False
            except PermissionError:
                return True
        return False
    
    @staticmethod
    def daemonize():
        """Daemonize the process"""
        # First fork
        try:
            pid = os.fork()
            if pid > 0:
                # Print info and exit parent
                print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    LOAD TEST STARTED IN BACKGROUND                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  PID         : {pid:<63}║
║  Log File    : {str(Config.LOG_FILE):<63}║
║  PID File    : {str(Config.PID_FILE):<63}║
║  State File  : {str(Config.STATE_FILE):<63}║
╠══════════════════════════════════════════════════════════════════════════════╣
║  COMMANDS:                                                                   ║
║    Monitor   : tail -f {str(Config.LOG_FILE):<53}║
║    Status    : python3 {sys.argv[0]} --status{' '*41}║
║    Stop      : python3 {sys.argv[0]} --stop{' '*43}║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
                sys.exit(0)
        except OSError as e:
            logger.error(f"Fork #1 failed: {e}")
            sys.exit(1)
        
        os.chdir('/')
        os.setsid()
        os.umask(0)
        
        # Second fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            logger.error(f"Fork #2 failed: {e}")
            sys.exit(1)
        
        # Redirect streams
        sys.stdout.flush()
        sys.stderr.flush()
        
        with open('/dev/null', 'r') as devnull:
            os.dup2(devnull.fileno(), sys.stdin.fileno())
        
        with open(Config.LOG_FILE, 'a') as log:
            os.dup2(log.fileno(), sys.stdout.fileno())
            os.dup2(log.fileno(), sys.stderr.fileno())
        
        ProcessManager.write_pid()


# ============================================================================
#                              DISPLAY UTILITIES
# ============================================================================

class Display:
    """Display utilities"""
    
    @staticmethod
    def print_header():
        """Print application header"""
        logger.info("=" * 78)
        logger.info("  UBUNTU 24.04 ULTIMATE LOAD GENERATOR v2.0")
        logger.info("=" * 78)
        logger.info(f"  Total Packages    : {len(PACKAGES)}")
        logger.info(f"  Target CPU Load   : {Config.TARGET_CPU_PERCENT}%+")
        logger.info(f"  PID               : {os.getpid()}")
        logger.info(f"  Start Time        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 78)
    
    @staticmethod
    def print_status(current: int, total: int, package: str, 
                     start_time: float, results: List[PackageResult]):
        """Print current status"""
        elapsed = time.time() - start_time
        stats = SystemMonitor.get_stats(current, total)
        load1, load5, load15 = SystemMonitor.get_load_average()
        
        # Calculate ETA
        if current > 0:
            avg_time = elapsed / current
            eta_seconds = avg_time * (total - current)
            eta = str(timedelta(seconds=int(eta_seconds)))
        else:
            eta = "calculating..."
        
        # Count successes/failures
        successes = sum(1 for r in results if r.status == Status.COMPLETED)
        failures = sum(1 for r in results if r.status in [Status.INSTALL_FAILED, Status.UNINSTALL_FAILED])
        
        progress_pct = (current / total) * 100
        progress_bar = "█" * int(progress_pct / 5) + "░" * (20 - int(progress_pct / 5))
        
        status = f"""
┌──────────────────────────────────────────────────────────────────────────────┐
│  LOAD TEST STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^56} │
├──────────────────────────────────────────────────────────────────────────────┤
│  Progress  : [{progress_bar}] {progress_pct:>5.1f}%{' '*27}│
│  Package   : {current:>4}/{total:<4} - {package[:50]:<50} │
├──────────────────────────────────────────────────────────────────────────────┤
│  CPU Usage : {stats.cpu_percent:>5.1f}%        Load Avg: {load1:.2f} / {load5:.2f} / {load15:.2f}{' '*18}│
│  Memory    : {stats.memory_used_mb:>5}MB / {stats.memory_total_mb}MB ({stats.memory_available_mb}MB free){' '*24}│
│  Disk      : {stats.disk_available_gb:>5}GB available{' '*47}│
├──────────────────────────────────────────────────────────────────────────────┤
│  Success   : {successes:>5}          Failures: {failures:<5}{' '*36}│
│  Elapsed   : {str(timedelta(seconds=int(elapsed))):>12}     ETA: {eta:<15}{' '*22}│
└──────────────────────────────────────────────────────────────────────────────┘
"""
        # Log compact version
        logger.info(f"[{current}/{total}] {progress_pct:.1f}% | CPU:{stats.cpu_percent:.0f}% | "
                   f"Mem:{stats.memory_used_mb}MB | Disk:{stats.disk_available_gb}GB | "
                   f"OK:{successes} FAIL:{failures} | {package}")
        
        # Save stats periodically
        if current % 10 == 0:
            StateManager.save_stats(stats)
    
    @staticmethod
    def print_final_report(results: List[PackageResult], start_time: float):
        """Print final report"""
        elapsed = time.time() - start_time
        
        completed = [r for r in results if r.status == Status.COMPLETED]
        install_failed = [r for r in results if r.status == Status.INSTALL_FAILED]
        uninstall_failed = [r for r in results if r.status == Status.UNINSTALL_FAILED]
        skipped = [r for r in results if r.status == Status.SKIPPED]
        
        total_install_time = sum(r.install_time for r in results)
        total_uninstall_time = sum(r.uninstall_time for r in results)
        
        avg_install = total_install_time / len(results) if results else 0
        avg_uninstall = total_uninstall_time / len(completed) if completed else 0
        
        stats = SystemMonitor.get_stats()
        
        report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                              FINAL REPORT                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  SUMMARY                                                                     ║
║  ───────────────────────────────────────────────────────────────────────     ║
║  Total Packages      : {len(results):<55}║
║  Completed           : {len(completed):<55}║
║  Install Failed      : {len(install_failed):<55}║
║  Uninstall Failed    : {len(uninstall_failed):<55}║
║  Skipped             : {len(skipped):<55}║
║  Success Rate        : {(len(completed)/len(results)*100) if results else 0:.1f}%{' '*51}║
╠══════════════════════════════════════════════════════════════════════════════╣
║  TIMING                                                                      ║
║  ───────────────────────────────────────────────────────────────────────     ║
║  Total Runtime       : {str(timedelta(seconds=int(elapsed))):<55}║
║  Avg Install Time    : {avg_install:.2f}s{' '*52}║
║  Avg Uninstall Time  : {avg_uninstall:.2f}s{' '*52}║
║  Packages/Hour       : {(len(results)/elapsed*3600):.1f}{' '*52}║
╠══════════════════════════════════════════════════════════════════════════════╣
║  FINAL SYSTEM STATE                                                          ║
║  ───────────────────────────────────────────────────────────────────────     ║
║  CPU Usage           : {stats.cpu_percent}%{' '*53}║
║  Memory              : {stats.memory_used_mb}MB / {stats.memory_total_mb}MB{' '*42}║
║  Disk Available      : {stats.disk_available_gb}GB{' '*53}║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        logger.info(report)
        
        # Log failed packages
        if install_failed:
            logger.info(f"Install failures: {', '.join(r.name for r in install_failed[:20])}")
            if len(install_failed) > 20:
                logger.info(f"... and {len(install_failed) - 20} more")
        
        if uninstall_failed:
            logger.info(f"Uninstall failures: {', '.join(r.name for r in uninstall_failed[:10])}")


# ============================================================================
#                              MAIN LOAD TESTER
# ============================================================================

class LoadTester:
    """Main load testing orchestrator"""
    
    def __init__(self, resume: bool = False):
        self.stress_manager = CPUStressManager()
        self.results: List[PackageResult] = []
        self.start_index = 0
        self.start_time = 0.0
        self.running = True
        
        if resume:
            self.start_index, self.results = StateManager.load_state()
            if self.start_index > 0:
                logger.info(f"Resuming from package {self.start_index}")
    
    def setup_signals(self):
        """Setup signal handlers"""
        def handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.running = False
        
        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)
    
    def cleanup_on_exit(self):
        """Cleanup function for atexit"""
        self.stress_manager.stop()
        SystemCleaner.deep_cleanup()
        ProcessManager.remove_pid()
    
    def process_package(self, package: str) -> PackageResult:
        """Process a single package (install then uninstall)"""
        result = PackageResult(name=package, status=Status.PENDING)
        
        # Check resources before proceeding
        ok, msg = SystemMonitor.check_resources()
        if not ok:
            logger.error(f"Skipping {package}: {msg}")
            SystemCleaner.emergency_cleanup()
            ok, _ = SystemMonitor.check_resources()
            if not ok:
                result.status = Status.SKIPPED
                result.error = msg
                return result
        
        # Install
        result.status = Status.INSTALLING
        success, elapsed, error = PackageManager.install(package)
        result.install_time = elapsed
        
        if not success:
            result.status = Status.INSTALL_FAILED
            result.error = error
            logger.warning(f"✗ Install failed: {package}")
            return result
        
        logger.info(f"✓ Installed: {package} ({elapsed:.1f}s)")
        time.sleep(Config.POST_INSTALL_DELAY)
        
        # Uninstall
        result.status = Status.UNINSTALLING
        success, elapsed, error = PackageManager.uninstall(package)
        result.uninstall_time = elapsed
        
        if not success:
            result.status = Status.UNINSTALL_FAILED
            result.error = error
            logger.warning(f"✗ Uninstall failed: {package}")
            return result
        
        logger.info(f"✓ Removed: {package} ({elapsed:.1f}s)")
        result.status = Status.COMPLETED
        
        return result
    
    def run(self):
        """Run the load test"""
        self.setup_signals()
        atexit.register(self.cleanup_on_exit)
        
        # Print header and system info
        Display.print_header()
        
        stats = SystemMonitor.get_stats()
        logger.info(f"Initial - CPU: {stats.cpu_percent}% | "
                   f"Memory: {stats.memory_used_mb}MB/{stats.memory_total_mb}MB | "
                   f"Disk: {stats.disk_available_gb}GB")
        
        # Initial cleanup
        SystemCleaner.deep_cleanup()
        
        # Update apt cache
        PackageManager.update_cache()
        
        # Start CPU stress workers
        self.stress_manager.start()
        
        self.start_time = time.time()
        total = len(PACKAGES)
        
        try:
            for i, package in enumerate(PACKAGES[self.start_index:], self.start_index + 1):
                if not self.running:
                    logger.info("Shutdown requested, saving state...")
                    StateManager.save_state(i - 1, self.results)
                    break
                
                # Display status
                Display.print_status(i, total, package, self.start_time, self.results)
                
                # Process package
                result = self.process_package(package)
                self.results.append(result)
                
                # Cleanup after each package
                SystemCleaner.quick_cleanup()
                
                # Periodic deep cleanup
                if i % Config.CLEANUP_EVERY_N_PACKAGES == 0:
                    SystemCleaner.quick_cleanup()
                    
                    # Adjust CPU intensity
                    self.stress_manager.adjust_intensity(Config.TARGET_CPU_PERCENT)
                
                if i % Config.DEEP_CLEANUP_EVERY_N_PACKAGES == 0:
                    logger.info(f"=== Milestone: {i}/{total} packages ===")
                    SystemCleaner.deep_cleanup()
                    StateManager.save_state(i, self.results)
                
                # Emergency check
                _, disk_avail = SystemMonitor.get_disk_usage()
                if disk_avail < Config.EMERGENCY_DISK_GB:
                    SystemCleaner.emergency_cleanup()
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            StateManager.save_state(len(self.results), self.results)
        
        finally:
            # Final report and cleanup
            Display.print_final_report(self.results, self.start_time)
            self.stress_manager.stop()
            SystemCleaner.deep_cleanup()
            StateManager.clear_state()
            ProcessManager.remove_pid()
            
            logger.info("=" * 78)
            logger.info("  LOAD TEST COMPLETED!")
            logger.info("=" * 78)


# ============================================================================
#                              CLI INTERFACE
# ============================================================================

def print_help():
    """Print help message"""
    help_text = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    UBUNTU 24.04 ULTIMATE LOAD GENERATOR v2.0                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  USAGE:                                                                      ║
║    sudo python3 load_test.py [OPTIONS]                                       ║
║                                                                              ║
║  OPTIONS:                                                                    ║
║    (none)          Run in background (daemonized)                            ║
║    --foreground    Run in foreground (see all output)                        ║
║    --resume        Resume from last saved state                              ║
║    --status        Show current process status                               ║
║    --stop          Stop running process gracefully                           ║
║    --kill          Force kill running process                                ║
║    --logs          Show last 50 log lines                                    ║
║    --follow        Follow logs in real-time (tail -f)                        ║
║    --stats         Show collected statistics                                 ║
║    --clean         Clean up all temp files and state                         ║
║    --help          Show this help message                                    ║
║                                                                              ║
║  EXAMPLES:                                                                   ║
║    sudo python3 load_test.py                    # Start in background        ║
║    sudo python3 load_test.py --foreground       # Start in foreground        ║
║    sudo python3 load_test.py --resume           # Resume interrupted test    ║
║    python3 load_test.py --status                # Check if running           ║
║    python3 load_test.py --follow                # Watch logs live            ║
║                                                                              ║
║  FEATURES:                                                                   ║
║    • 900+ packages install/uninstall cycle                                   ║
║    • Background CPU stress (40%+ load)                                       ║
║    • I/O stress worker                                                       ║
║    • Automatic resource monitoring                                           ║
║    • Emergency cleanup on low disk                                           ║
║    • Resume capability after interruption                                    ║
║    • Detailed logging and statistics                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(help_text)


def cmd_status():
    """Show process status"""
    if ProcessManager.is_running():
        pid = ProcessManager.get_pid()
        print(f"\n✓ Load test is RUNNING (PID: {pid})")
        
        # Show process info
        os.system(f"ps -p {pid} -o pid,ppid,%cpu,%mem,etime,comm 2>/dev/null")
        
        # Show last few log lines
        print(f"\nRecent activity:")
        os.system(f"tail -5 {Config.LOG_FILE} 2>/dev/null")
    else:
        print("\n✗ Load test is NOT running")
        
        if Config.STATE_FILE.exists():
            print(f"\n  State file exists: {Config.STATE_FILE}")
            print("  Use --resume to continue from last checkpoint")


def cmd_stop():
    """Stop running process"""
    pid = ProcessManager.get_pid()
    if pid and ProcessManager.is_running():
        print(f"Sending SIGTERM to PID {pid}...")
        os.kill(pid, signal.SIGTERM)
        
        # Wait for graceful shutdown
        for _ in range(10):
            time.sleep(1)
            if not ProcessManager.is_running():
                print("✓ Process stopped gracefully")
                return
        
        print("Process still running, use --kill for force stop")
    else:
        print("No running process found")


def cmd_kill():
    """Force kill process"""
    pid = ProcessManager.get_pid()
    if pid:
        print(f"Force killing PID {pid}...")
        try:
            os.kill(pid, signal.SIGKILL)
            ProcessManager.remove_pid()
            print("✓ Process killed")
        except ProcessLookupError:
            print("Process not found")
            ProcessManager.remove_pid()
    else:
        print("No PID file found")


def cmd_logs():
    """Show recent logs"""
    if Config.LOG_FILE.exists():
        os.system(f"tail -50 {Config.LOG_FILE}")
    else:
        print("No log file found")


def cmd_follow():
    """Follow logs in real-time"""
    if Config.LOG_FILE.exists():
        print(f"Following {Config.LOG_FILE} (Ctrl+C to stop)...")
        os.system(f"tail -f {Config.LOG_FILE}")
    else:
        print("No log file found")


def cmd_stats():
    """Show statistics"""
    if Config.STATS_FILE.exists():
        try:
            with open(Config.STATS_FILE, 'r') as f:
                stats = json.load(f)
            
            if stats:
                print(f"\nCollected {len(stats)} stat samples")
                
                # Show last few entries
                print("\nRecent stats:")
                for s in stats[-5:]:
                    print(f"  {s['timestamp']}: CPU={s['cpu_percent']}% "
                          f"MEM={s['memory_used_mb']}MB "
                          f"DISK={s['disk_available_gb']}GB "
                          f"Progress={s['packages_processed']}/{s['packages_total']}")
        except Exception as e:
            print(f"Error reading stats: {e}")
    else:
        print("No statistics file found")


def cmd_clean():
    """Clean up all files"""
    files = [Config.LOG_FILE, Config.PID_FILE, Config.STATE_FILE, Config.STATS_FILE]
    
    for f in files:
        if f.exists():
            f.unlink()
            print(f"Removed: {f}")
    
    print("✓ Cleanup complete")


def main():
    """Main entry point"""
    args = sys.argv[1:]
    
    # Handle commands
    if '--help' in args or '-h' in args:
        print_help()
        sys.exit(0)
    
    if '--status' in args:
        cmd_status()
        sys.exit(0)
    
    if '--stop' in args:
        cmd_stop()
        sys.exit(0)
    
    if '--kill' in args:
        cmd_kill()
        sys.exit(0)
    
    if '--logs' in args:
        cmd_logs()
        sys.exit(0)
    
    if '--follow' in args:
        cmd_follow()
        sys.exit(0)
    
    if '--stats' in args:
        cmd_stats()
        sys.exit(0)
    
    if '--clean' in args:
        cmd_clean()
        sys.exit(0)
    
    # Check if already running
    if ProcessManager.is_running():
        print("Load test is already running!")
        print("Use --status to check, --stop to stop, or --follow to watch logs")
        sys.exit(1)
    
    # Check for root
    if os.geteuid() != 0:
        print("This script requires root privileges. Please run with sudo.")
        sys.exit(1)
    
    # Parse options
    foreground = '--foreground' in args
    resume = '--resume' in args
    
    # Daemonize unless foreground
    if not foreground:
        ProcessManager.daemonize()
    
    # Run the test
    tester = LoadTester(resume=resume)
    tester.run()


if __name__ == "__main__":
    main()
