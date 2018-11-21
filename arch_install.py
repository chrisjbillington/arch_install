# Bilbo's arch linux install script
# =================================
#
# Instructions
# ============
#
# - Boot ArchISO
# - Set keymap with loadkeys if necessary
# - Connect to wifi with wifi-menu if necessary
# - wget this script: wget https://somewhere.com/arch_install.py
# - Edit this script to set config as described below
# - Run python arch_install.py
#
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
HOSTNAME = 'bilbo-arch'
#
# Keymap. To see options, do ls /usr/share/kbd/keymaps/**/*.map.gz
KEYMAP = 'us'
#
# Locale - see /etc/locale.gen for options
LOCALE = 'en_AU.UTF-8'
#
# Localtime - must be a valid subpath within /usr/share/zoneinfo/
LOCALTIME = 'US/Eastern'
#
# Disk to install to. Check disks with 'fdisk -l' or 'lsblk'
DISK = '/dev/sda'
#
# Is the install in a virtualbox?
VIRTUALBOX = True
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
    _run('cp arch_install.log /mnt/etc')
    _run('hg add /mnt/etc/arch_install.log')
    _run(f'cp {sys.argv[0]} /mnt/etc/arch_install.py')
    _run('hg add /mnt/etc/arch_install.py')
    _run("hg commit -u root -m 'Added install script and log file' -R /mnt/etc/")

    # Unmount:
    _run('umount -R /mnt')

    # Print a message and reboot
    input("Installation complete. Remove installation media and press enter to reboot.")
    _run("reboot")


def errorquit(msg=None):
    if msg is not None:
        sys.stderr.write(msg + '\n')
    sys.stderr.write('Could not complete installation, stopping.\n')
    sys.exit(1)


def run(cmd, expect=None, timeout=5):
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
    shell.expect_exact(['# ', '$ '])  # Wait for prompt
    # Set PS1 and get prompt:
    RED = r"\[\e[1;31m\]"
    NORMAL = r"\[\e[0m\]"
    shell.sendline(fr'export PS1="{RED}$PS1{NORMAL}"')
    shell.expect_exact('$') # Skip over the $ in $PS1
    shell.expect_exact(['# ', '$ ']) # Wait for prompt
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
DISK = {DISK}
VIRTUALBOX = {VIRTUALBOX}

Configuration can be modified by editing these variables at the top of the file
containing this script.
"""
)

if not yn_choice("Install Arch Linux with the above configuration?"):
    sys.exit(1)

# Error checking
if not LOCALE in open('/etc/locale.gen').read():
    sys.stderr.write(f'Locale {LOCALE} is not listed in /etc/locale.gen.\n')
    sys.exit(1)
if not os.path.isfile(f'/usr/share/zoneinfo/{LOCALTIME}'):
    sys.stderr.write(f'Timezone {LOCALTIME} not present under /usr/share/zoneinfo/.\n')
    sys.exit(1)
for line in getoutput(f'lsblk -l').splitlines():
    name, _, _, _, _, type_, *_ = line.split()
    if f'/dev/{name}' == DISK and type_ == 'disk':
        break
else:
    sys.stderr.write(f'No such disk {DISK}.\n')
    sys.exit(1)

# Get user password:
PASSWORD = getpass(f"Choose a password for {USERNAME}: ")
if not PASSWORD or getpass(f"Confirm password for {USERNAME}: ") != PASSWORD:
    sys.stderr.write("No password or unmatching password.\n")
    sys.exit(1)

print()
_run(f'fdisk -l {DISK}')
print()
if not yn_choice(
    f"The details of {DISK} are shown above.\n"
    + "Check carefully it is the right disk, as it will be erased.\n"
    f"Are you sure you want to completely erase {DISK}?",
    default='n',
):
    sys.exit(1)

# Installation begins
print('Ensuring /mnt does not have a mounted filesystem...')
os.system('umount -R /mnt')
print('Getting packages needed for installation...')
# Sync the package database:
_run('pacman -Syy')
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

# Partition disk:
run(f'fdisk --wipe-partition always {DISK}', expect='Command')
run('g', expect='Command')
run('n', expect='Partition number')
run('1', expect="First sector")
run('', expect="Last sector")
run('+512M', expect='Created a new partition')
run('n', expect='Command')
run('2', expect='First sector')
run('', expect='Last sector')
run('', expect='Created a new partition')
run('t', expect='Partition number')
run('1', expect='Partition type')
run('1', expect='EFI System')
run('t', expect='Partition number')
run('2', expect='Partition type')
run('24', expect='Linux root (x86-64)')
run('w')

# Avoid a seeming race condition getting partitions too soon after making them:
time.sleep(.1)

# Get the partition names:
partitions = getoutput(f'lsblk -l {DISK}').splitlines()[2:4]
if len(partitions) != 2:
    errorquit("Did not find expected number of partitions")
for line in partitions:
    partition = f'/dev/{line.split()[0]}'
    if not partition.startswith(DISK):
        errorquit(f"Unexpected partition name {partition}")
    if partition.endswith('1'):
        EFI_partition = partition
    elif partition.endswith('2'):
        root_partition = partition
    else:
        errorquit(f"Unexpected partition name {partition}")

# Make filesystems:
run(f'mkfs.fat -F32 {EFI_partition}')
run(f'mkfs.ext4 {root_partition}', timeout=120)

# # Mount them:
run(f'mount {root_partition} /mnt')
run('mkdir /mnt/boot')
run(f'mount {EFI_partition} /mnt/boot')

# Backup original mirrorlist
run('cp /etc/pacman.d/mirrorlist /var/tmp/mirrorlist.orig')

# Find good mirrors:
run('reflector -l 50 --sort rate --save /etc/pacman.d/mirrorlist', timeout=120)

# Install the base system:
run('pacman -Syy', timeout=120)
# Colour and overall progress:
run("sed -i '/TotalDownload/s/^#//g' /etc/pacman.conf")
run("sed -i '/Color/s/^#//g' /etc/pacman.conf")
# We'll need hg after we leave the chroot
run('pacman -S --noconfirm mercurial', timeout=None)
run('pacstrap /mnt base base-devel', timeout=None)

# Copy original pacman mirror list, it will be saved to version control for posterity:
run('cp /var/tmp/mirrorlist.orig /mnt/var/tmp/mirrorlist.orig')

# Save the generated fstab entries to a tempfile, we will append them to fstab after
# chrooting into the new system.
run('genfstab -U /mnt > /mnt/var/tmp/fstab_entries')

# Basic system has been installed. Chroot into the new system
shell.sendline('arch-chroot /mnt')
PROMPT = set_ps1_and_get_prompt()
run('set -e')

INITIAL_PACKAGES = [
    'grub',
    'efibootmgr',
    'sudo',
    'mercurial',
    'git',
    'gnome',
    'gnome-extra',
    'xdg-utils',
    'ttf-ubuntu-font-family',
    'noto-fonts-emoji',
    'ttf-linux-libertine',
    'ttf-dejavu',
    'ttf-liberation',
    'powertop',
    'xterm',
    'tint2',
    'gnucash',
    'anki',
    'meld',
    'firefox',
    'python2-nautilus',  # needed for tortoisehg extension
    'python2-pygments',  # needed for tortoisehg syntax highlighting
]

# Backup the unmodified pacman.conf:
run('cp /etc/pacman.conf /var/tmp/pacman.conf.orig')
# Apply colour and progress config changes to pacman.conf:
run("sed -i '/TotalDownload/s/^#//g' /etc/pacman.conf")
run("sed -i '/Color/s/^#//g' /etc/pacman.conf")

# Install some more packages:
run('pacman -Syy', timeout=120)
run(f'pacman -S --noconfirm {" ".join(INITIAL_PACKAGES)}', timeout=None)

# Replace mirrorlist with the default one, so it can be added to version control for
# posterity. Back up the good one so it can be added back in a moment:
run('mv /etc/pacman.d/mirrorlist /var/tmp/mirrorlist.new')
run('mv /var/tmp/mirrorlist.orig /etc/pacman.d/mirrorlist')

# Replace pacman.conf with the default for the same reason:
run('mv /etc/pacman.conf /var/tmp/pacman.conf.new')
run('mv /var/tmp/pacman.conf.orig /etc/pacman.conf')

# Before we start configuring anything, set up a version control repo in /etc/ to track
# changes to config files we're about to create or modify.
run('hg init /etc')

# List of already-existing config files to put under version control:
ORIG_FILES = [
    '/etc/fstab',
    '/etc/pacman.d/mirrorlist',
    '/etc/pacman.conf',
    '/etc/localtime',
    '/etc/hosts',
    '/etc/locale.gen',
    '/etc/default/grub',
    '/etc/sudoers',
    '/etc/gdm/custom.conf',
    '/etc/systemd/system',  # Put this whole directory under version control
]

for path in ORIG_FILES:
    # Add to version control
    if os.path.isdir(path):
        run(f'hg add {path}/*')
    else:
        run(f'hg add {path}')

# List of not-yet-existing config files to be put under version control
NEW_FILES = ['/etc/hostname', '/etc/vconsole.conf', '/etc/adjtime']

# Commit original files:
run('hg commit -u root -m "initial default configuration" -R /etc')

# Make branch for our changes
run('hg branch custom -R /etc')

# Our optimised mirrrorlist:
run('mv /var/tmp/mirrorlist.new /etc/pacman.d/mirrorlist')

# Our fstab entries:
run('cat /var/tmp/fstab_entries >> /etc/fstab')
run('rm /var/tmp/fstab_entries')

# Our pacman config changes:
run('mv /var/tmp/pacman.conf.new /etc/pacman.conf')

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

# Install and configure grub bootloader:
run(
    'grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB',
    timeout=120,
)
run('grub-mkconfig -o /boot/grub/grub.cfg', timeout=120)

if VIRTUALBOX:
    # if in a virtualbox, workaround for bug where virtualbox forgets EFI variables:
    run('mkdir -p /boot/EFI/BOOT')
    run('cp /boot/EFI/GRUB/grubx64.efi /boot/EFI/BOOT/BOOTX64.EFI')

# Disable wayland in GDM:
run(f"sed -i '/WaylandEnable=false/s/^#//g' /etc/gdm/custom.conf")

# Enable gdm and networkmanager systemd units:
run('systemctl enable gdm.service')
run('systemctl enable NetworkManager.service')

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

# Commit all our custom configuration
for path in NEW_FILES:
    run(f'hg add {path}')
for path in ORIG_FILES:
    if os.path.isdir(path):
        # Add any new files under the directory:
        run(f'hg add {path}/*')
run('hg commit -u root -m "Initial custom configuration" -R /etc')


# Ok, onto some more custom stuff.

# Set up sublime text repo:
run('curl -o /tmp/sublimehq-pub.gpg https://download.sublimetext.com/sublimehq-pub.gpg')
run('pacman-key --add /tmp/sublimehq-pub.gpg')
run('pacman-key --lsign-key 8A8F901A')
SUBLIME_SERVER = 'https://download.sublimetext.com/arch/dev/x86_64'
run(f'echo -e "\n[sublime-text]\nServer = {SUBLIME_SERVER}" >> /etc/pacman.conf')

# Commit that change to pacman.conf:
run('hg commit -u root -m "Add sublime text server" -R /etc')

# Update pacman db and install sublime text
run('pacman -Syy', timeout=120)
run('pacman -S --noconfirm sublime-text', timeout=None)

# Install yay and AUR packages. Switch to user since makepkg can't be run as root:
shell.sendline(f'su {USERNAME}')
set_ps1_and_get_prompt()

run('git clone https://aur.archlinux.org/yay.git /tmp/yay', timeout=120)
run(
    'cd /tmp/yay && makepkg -si --noconfirm && cd -',
    expect=f"[sudo] password for {USERNAME}:",
)
run(PASSWORD, timeout=None)

AUR_PACKAGES = [
    'tortoisehg',
    'yaru-icon-theme',
    'yaru-gnome-shell-theme',
    'yaru-gtk-theme',
    'yaru-sound-theme',
    'spotify',
    'google-chrome',
]

# install the above AUR packages:
run(f'yay -S --noconfirm {" ".join(AUR_PACKAGES)}', timeout=None)

# Quit user session:
run('exit', expect='#')

# Quit chroot:
run('exit', expect='#')

# Exit bash session:
shell.sendeof()
shell.expect(pexpect.EOF)

# Add the install log to the mercurial repository. WIll commit after
# this script exits ()
print('# End of the part of the install script that can be logged.')
print('# After this, we process the log file to remove ANSI escape sequences,')
print('# commit it and this script to the repository in /etc/, unmount and reboot.')

# This script now ends, and its parent process (the little snippet of code at the top of
# this file) will do the final cleanup.


# Notes of other things to be configured in the GUI:

# run settings, set all the settings:
# Displays:
# Night light on
# Keyboard:
#    volume up: ctrl up
#    volume down: ctrl down
#    play/pause: ctrl enter
#    gnome-terminal: ctrl alt t
# Mouse and touchpad:
#    natural scrolling off
#    tap to click on

# run gnome tweak tool, set all the settings.
# Extensions -> enable user themes,
#     then restart gnome-shell with alt-f2 r and restart tweak tool
# appearance -> themes -> yaru for all
# extensions -> alternatetab
# fonts ->
#    ubuntu regular 11, ubuntu regular 11, ubuntu mono regular 13, ubuntu medium 11
# antialising -> subpixel
# keyboard and mouse -> compose key -> right alt
#   additional layout options -> capslock -> capslock is additional escape
# top bar -> battery percetage, clock -> weekday and date
# window titlebars -> buttons -> maximise, minimise
# windows -> don't attach modal dialogs, center new windows
# workspaces -> static, workspaces span displays

# Gnome shell extensions:
# system monitor
