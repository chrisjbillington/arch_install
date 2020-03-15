# Bilbo's arch linux install script
# =================================
#
# Instructions
# ============
#
# - Boot ArchISO
# - Set keymap with loadkeys if necessary
# - Connect to wifi with wifi-menu if necessary
# - wget this script:
#       wget https://bitbucket.org/cbillington/arch_install/raw/default/arch_install.py
# - Edit this script to set config as described below
# - Run python arch_install.py
#
######################################################################
#
# Configuration
# =============
#
# Username
USERNAME = 'bilbo'
#
# Computer hostname
HOSTNAME = 'bilbo-server'
#
# Keymap. To see options, do ls /usr/share/kbd/keymaps/**/*.map.gz
KEYMAP = 'us'
#
# Locale - see /etc/locale.gen for options
LOCALE = 'en_AU.UTF-8'
#
# Localtime - must be a valid subpath within /usr/share/zoneinfo/
LOCALTIME = 'Australia/Melbourne'
#
# Disk(s) to install to. Check disks with 'fdisk -l' or 'lsblk'. Comma-separated list
# for multiple disks, used for RAID
DISKS = '/dev/sda,/dev/sdb,/dev/sdc,/dev/sdd'
#
# Raid scheme, None or 5 only supported. If 5, DISKS must be a comma-separated list of
# identically-sized disks.
RAID = 5
#
# Whether to install as BIOS or UEFI - generally you want UEFI = True unless it's an old
# system that doesn't support UEFI. If UEFI, will use GPT partition table, otherwise
# will use MBR.
UEFI = False
#
# Is the install in a virtualbox?
VIRTUALBOX = False
#
######################################################################


import sys
import os
from subprocess import getoutput
import time
from getpass import getpass
import re


def _run(cmd):
    """Print and run a command, and quit if it fails"""
    print(f'# {cmd}')
    if os.system(cmd):
        sys.exit(1)


def clean_terminal_output(text):
    r"""Turn the output of the 'script' command into a readable log file by: Removing
    ANSI escape codes, making all newlines \n, and erasing text preceding backspace
    characters \b and carriage returns \r appropriately to get the final text as would
    be seen by the user on the terminal."""

    # Change any number of \r followed by a \n to a \n:
    newlines = re.compile(r'\r\r*?\n')
    text = newlines.sub('\n', text)

    # Delete data in each line preceding a carriage return \r':
    text = '\n'.join(line.split('\r')[-1] for line in text.split('\n'))

    # Remove ANSI escape sequences:
    ansi_escape = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
    text = ansi_escape.sub('', text)

    # Remove backspaces \b and characters preceding them on a per-line basis:
    lines = []
    backspaces = re.compile('^\x08|[^\x08]\x08')
    for line in text.split('\n'):
        while '\b' in line:
            line = backspaces.sub('', line)
        lines.append(line)
    text = '\n'.join(lines)

    return text


if '_' not in sys.argv:
    # Run this script as a child process, but log its output to a file:
    rc = os.system(f'script -e -c \'python {" ".join(sys.argv)} _\' arch_install.log')

    # Turn the output of the 'script' command into a readable log file:
    with open('arch_install.log', 'rb') as f:
        log = f.read().decode('utf8')
    log = clean_terminal_output(log)
    with open('arch_install.log', 'wb') as f:
        f.write(log.encode('utf8'))

    if rc:
        # Quit if the install was not successful
        sys.exit(1)

    # If install was successful, add the log file and install script to version control:
    _run('mkdir -p /mnt/var/log/install_log')
    _run('cp arch_install.log /mnt/var/log/install_log/arch_install.log')
    _run(f'cp {sys.argv[0]} /mnt/var/log/install_log/arch_install.py')

    # Unmount:
    _run('umount -R /mnt')

    # Print a message and reboot
    input("Installation complete. Press enter to reboot.")
    _run("reboot")


def errorquit(msg=None):
    if msg is not None:
        sys.stderr.write(msg + '\n')
    sys.stderr.write('Could not complete installation, stopping.\n')
    sys.exit(1)


def run(cmd, expect=None, timeout=30):
    if isinstance(cmd, (list, tuple)):
        cmd = ' '.join(cmd)
    if expect is None:
        expect = PROMPT
    # Run the command:
    shell.sendline(cmd)
    # Wait for prompt or for us to have exited
    try:
        shell.expect_exact([expect, pexpect.EOF], timeout=timeout)
    except pexpect.TIMEOUT:
        errorquit("Timeout or unexpected output.")
    if shell.after == pexpect.EOF:
        errorquit()


def yn_choice(message, default='y'):
    try:
        choices = 'Y/n' if default.lower() in ('y', 'yes') else 'y/N'
        choice = input("%s\n(%s): " % (message, choices))
        values = ('y', 'yes', '') if default == 'y' else ('y', 'yes')
        return choice.strip().lower() in values
    except (KeyboardInterrupt, EOFError):
        sys.exit(1)


def set_ps1_and_get_prompt():
    shell.expect_exact(['#', '$'])  # Wait for prompt
    # Set PS1 and get prompt:
    RED = r"\[\e[1;31m\]"
    NORMAL = r"\[\e[0m\]"
    shell.sendline(fr'export PS1="{RED}$PS1{NORMAL}"')
    shell.expect_exact('$')  # Skip over the $ in $PS1
    shell.expect_exact(['# ', '$ '])  # Wait for prompt
    return (shell.before + shell.after).split(b'\n')[-1]


_run('clear')

print(
    f"""Welcome to bilbo's Arch Linux install script! This script will install Arch
Linux just the way I like it. Current configuration is:

USERNAME = {USERNAME}
HOSTNAME = {HOSTNAME}
KEYMAP = {KEYMAP}
LOCALE = {LOCALE}
LOCALTIME = {LOCALTIME}
DISKS = {DISKS}
RAID = {RAID}
VIRTUALBOX = {VIRTUALBOX}

Configuration can be modified by editing these variables at the top of the file
containing this script.
"""
)

if not yn_choice("Install Arch Linux with the above configuration?"):
    sys.exit(1)

disks = [s.strip() for s in DISKS.split(',')]

# Error checking
if not LOCALE in open('/etc/locale.gen').read():
    sys.stderr.write(f'Locale {LOCALE} is not listed in /etc/locale.gen.\n')
    sys.exit(1)
if not os.path.isfile(f'/usr/share/zoneinfo/{LOCALTIME}'):
    sys.stderr.write(f'Timezone {LOCALTIME} not present under /usr/share/zoneinfo/.\n')
    sys.exit(1)
for disk in disks:
    for line in getoutput(f'lsblk -l').splitlines():
        name, _, _, _, _, type_, *_ = line.split()
        if f'/dev/{name}' == disk and type_ == 'disk':
            break
    else:
        sys.stderr.write(f'No such disk {disk}.\n')
        sys.exit(1)
if RAID not in [None, 5]:
    sys.stderr.write(f"RAID must be None or 5, not {RAID}")
    sys.exit(1)
if len(disks) > 1 and RAID is None:
    sys.stderr.write(f"Can only install to one disk if not using RAID")
    sys.exit(1)

# Get user password:
PASSWORD = getpass(f"Choose a password for {USERNAME}: ")
if not PASSWORD or getpass(f"Confirm password for {USERNAME}: ") != PASSWORD:
    sys.stderr.write("No password or unmatching password.\n")
    sys.exit(1)

# We will be destroying any existing RAID arrays that use the disks:
mdstat = getoutput('cat /proc/mdstat')
md_devices = set()
md_disks = set()
for line in mdstat.splitlines():
    for disk in disks:
        if  disk.rsplit('/', 1)[-1] in line:
            md_devices.add(line.split()[0])
            md_disks.add(disk)

if md_devices:
    print()
    print(mdstat)
    print()

if md_devices:
    if not yn_choice(
        "The output of 'cat /proc/mdstat' is shown above.\n"
        + f"Some of the disks {DISKS} are in use by existing RAID arrays.\n"
        + f"If you continue, the RAID arrays {md_devices} will be erased.\n"
        + "Check carefully. "
        f"Are you sure you want to completely erase the RAID arrays {md_devices}?",
        default='n',
    ):
        sys.exit(1)

print()
for disk in disks:
    _run(f'fdisk -l {disk}')
print()
if not yn_choice(
    f"The details of {DISKS} are shown above.\n"
    + "Check carefully it is correct, as these disk(s) will be erased.\n"
    f"Are you sure you want to completely erase {DISKS}?",
    default='n',
):
    sys.exit(1)

# Installation begins
print('Ensuring /mnt does not have a mounted filesystem...')
os.system('umount -R /mnt')
print('Getting packages needed for installation...')
# Sync the package database:
_run('pacman -Sy')
_run('pacman -S --noconfirm python-pexpect reflector')
import pexpect

ts = os.get_terminal_size()
shell = pexpect.spawn('bash', dimensions=(ts.lines, ts.columns))
shell.logfile_read = sys.stdout.buffer

time.sleep(.1)
PROMPT = set_ps1_and_get_prompt()
run('set -e')
run(f'loadkeys {KEYMAP}')
run('timedatectl set-ntp true')

# Stop any existing RAID arrays using the given disks:
for md_device in md_devices:
    run(f"mdadm --stop /dev/{md_device}")
    time.sleep(.5)

# Wipe existing filesystems off the given disks:
for disk in disks:
    run(f'wipefs --all {disk}')
    time.sleep(.5)

# Partition disks:
for disk in disks:
    run(f'fdisk --wipe-partition always {disk}', expect='Command')
    
    run('g', expect='Command') # GPT
    run('n', expect='Partition number')
    run('1', expect="First sector")
    run('', expect="Last sector")
    if UEFI:
        run('+512M', expect='Created a new partition')
    else:
        run('+2M', expect='Created a new partition')
    run('n', expect='Command')
    run('2', expect='First sector')
    run('', expect='Last sector')
    run('', expect='Created a new partition')
    run('t', expect='Partition number')
    run('1', expect='Partition type')
    if UEFI:
        run('1', expect='EFI System')
    else:
        run('4', expect='BIOS boot')
    run('t', expect='Partition number')
    run('2', expect='Partition type')
    if RAID is None:
        run('24', expect='Linux root (x86-64)')
    else:
        run('29', expect='Linux RAID')
    run('w')

    # Avoid a seeming race condition getting partitions too soon after making them:
    time.sleep(.5)

    # Get the partition names:
    partitions = getoutput(f'lsblk -l {disk}').splitlines()[2:4]
    if len(partitions) != 2:
        errorquit("Did not find expected number of partitions")
    for line in partitions:
        partition = f'/dev/{line.split()[0]}'
        if not partition.startswith(disk):
            errorquit(f"Unexpected partition name {partition}")
        if partition.endswith('1'):
            boot_partition = partition
        elif partition.endswith('2'):
            root_partition = partition
        else:
            errorquit(f"Unexpected partition name {partition}")

def make_raid_array(number, level, disks, partnum):
    run(
        [
            'mdadm',
            '--create',
            '--verbose',
            f'--level={level}',
            f'--raid-devices={len(disks)}',
            f'--homehost={HOSTNAME}',
            f'/dev/md{number}',
        ]
        + [f"{disk}{partnum}" for disk in disks]
    )

if RAID is not None:
    if UEFI:
        # UEFI partition is RAID 1. This way, the individual partitions are valid FAT32
        # parititons in their own right, and can be read by UEFI firmware:
        make_raid_array(number=0, level=1, disks=disks, partnum=1)
        time.sleep(1)
        make_raid_array(number=1, level=5, disks=disks, partnum=2)
        boot_partition = '/dev/md0'
        root_partition = '/dev/md1'
    else:
        # BIOS boot partitions, one per disk, are not RAIDed. GRUB will be installed to
        # all of them.
        make_raid_array(number=0, level=5, disks=disks, partnum=2)
        root_partition = '/dev/md0'

# Make filesystems:
if UEFI:
    run(f'yes | mkfs.fat -F32 {boot_partition}')
run(f'yes | mkfs.ext4 {root_partition}', timeout=120)

# Mount them:
run(f'mount {root_partition} /mnt')
if UEFI:
    run('mkdir /mnt/boot')
    run(f'mount {boot_partition} /mnt/boot')

# Find good mirrors:
run('reflector -l 50 --sort rate --save /etc/pacman.d/mirrorlist', timeout=120)

# Install the base system:
run('pacman -Syy', timeout=120)
# Colour and overall progress:
run("sed -i '/TotalDownload/s/^#//g' /etc/pacman.conf")
run("sed -i '/Color/s/^#//g' /etc/pacman.conf")
run('pacstrap /mnt base base-devel', timeout=600)

# Copy the mirrorlist:
run('cp /etc/pacman.d/mirrorlist /mnt/etc/pacman.d/mirrorlist')

# Add fstab entries:
run('genfstab -U /mnt >> /mnt/etc/fstab')

# Basic system has been installed. Chroot into the new system
shell.sendline('arch-chroot /mnt')
PROMPT = set_ps1_and_get_prompt()
run('set -e')

INITIAL_PACKAGES = [
    'grub',
    'go',
    'linux-firmware',
    'openssh',
    'nano',
    'devtools',
    # Specific to server:
    'linux-lts',
    'linux-lts-headers',
    'broadcom-wl-dkms',
    'mdadm',
    'netctl',
    'wpa_supplicant'
    'dialog',
    'dhcpcd',
]

if UEFI:
    INITIAL_PACKAGES.append('efibootmgr')

# Apply colour and progress config changes to pacman.conf:
run("sed -i '/TotalDownload/s/^#//g' /etc/pacman.conf")
run("sed -i '/Color/s/^#//g' /etc/pacman.conf")

# Our hostfile:
shell.sendline('echo "127.0.0.1  localhost')
shell.sendline('::1        localhost')
shell.sendline(f'127.0.1.1  {HOSTNAME}.localdomain  {HOSTNAME}" >> /etc/hosts')
shell.expect_exact(PROMPT)

# Our hostname:
run(f'echo {HOSTNAME} > /etc/hostname')

# Our keyboard map:
run(f'echo KEYMAP={KEYMAP} > /etc/vconsole.conf')

# Our localtime:
run(f'ln -sf ../usr/share/zoneinfo/{LOCALTIME} /etc/localtime')

# Configure updating the hwclock, creating /etc/adjtime:
run('hwclock --systohc')

# Our locale:
run(f"sed -i '/{LOCALE}/s/^#//g' etc/locale.gen")
run('locale-gen')

# Our LANG variable:
run(f'echo LANG={LOCALE} > /etc/locale.conf')

if VIRTUALBOX:
    # if in a virtualbox, workaround for bug where virtualbox forgets EFI variables:
    run('mkdir -p /boot/EFI/BOOT')
    run('cp /boot/EFI/GRUB/grubx64.efi /boot/EFI/BOOT/BOOTX64.EFI')


# Create user account and set password
run(f'useradd -m -G wheel,storage {USERNAME}')
run(f'passwd {USERNAME}', expect='New password:')
run(PASSWORD, expect="Retype new password:")
run(PASSWORD)

# Allow sudo rights to anyone in the wheel group:
run(rf"sed '/%wheel ALL=(ALL) ALL/s/^# //g' /etc/sudoers > /tmp/sudoers.new")
run('EDITOR="cp /tmp/sudoers.new" visudo')

# Lock the root acount:
run('passwd -l root')

# Enable network time. This is equivalent to 'timedatectl set-ntp true', except doesn't
# start the service immediately, which doesn't work within the chroot:
run('systemctl enable systemd-timesyncd.service')

# Install initial packages:
run('pacman -Syy', timeout=120)
run(f'pacman -S --noconfirm {" ".join(INITIAL_PACKAGES)}', timeout=600)

# Install and configure grub bootloader:
if UEFI:
    run(
        'grub-install --verbose '
        + '--target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB',
        timeout=600,
    )
else:
    for disk in disks:
        run(f'grub-install --verbose --target=i386-pc {disk}', timeout=600)

if RAID is not None:
    # Add entries to /etc/mdadm.conf:
    run('mdadm --detail --scan >> /etc/mdadm.conf')

    # Edit mkinitcpio.conf and regenerate initramfs
    print("# Editing /etc/mkinitcpio.conf to insert mdadm_udev in HOOKS")
    PATTERN = '\nHOOKS=(base udev autodetect modconf block'
    NEW_TEXT = ' mdadm_udev'
    # /mnt prefix since the script where this code is running is not in the chroot:
    with open('/mnt/etc/mkinitcpio.conf', 'r+') as f:
        text = f.read()
        loc = text.find(PATTERN) + len(PATTERN)
        f.seek(0)
        f.truncate()
        f.write(text[:loc] + NEW_TEXT + text[loc:])

    run('mkinitcpio -p linux-lts', timeout=600)

run('grub-mkconfig -o /boot/grub/grub.cfg', timeout=600)

# Install the AUR helper 'yay'. To build it, switch to user since makepkg can't be run
# as root:
shell.sendline(f'su {USERNAME}')
root_prompt = PROMPT
PROMPT = set_ps1_and_get_prompt()
run(f'git clone https://aur.archlinux.org/yay.git /tmp/yay', timeout=600)
run(f'cd /tmp/yay && makepkg && cd -', timeout=600)
# Back to root:
PROMPT = root_prompt
shell.sendline('exit')

# Install with pacman:
run(f'pacman -U --noconfirm /tmp/yay/yay-*.pkg.*', timeout=600)

# Quit user session:
run('exit', expect='#')

# Quit chroot:
run('exit', expect='#')

# Exit bash session:
shell.sendeof()
shell.expect(pexpect.EOF)

print('# End of the part of the install script that can be logged.')
print('# After this, we process the log file to remove ANSI escape sequences,')
print('# copy it and this script to /etc/, unmount and reboot.')

# This script now ends, and its parent process (the little snippet of code at the top of
# this file) will do the final cleanup.
