#!/usr/bin/env python3
"""
Generate the standalone lab guide pages under lab/ from LABS below.

Run from the repo root:   python3 tools/build_labs.py
The generated pages are committed; the published site has no build step.

RHCSA Course - rhcsa.learnlinuxforwork.com
Copyright (C) 2026 Shea's Tech. Licensed under the GNU AGPL v3.0 or later.
"""
import html
import json
import io
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Every lab uses the same two hosts and the same working user, so the course
# reads as one continuous build rather than twelve unrelated exercises.
HOST_A = "servera"
HOST_B = "serverb"
USER = "shea"

LABS = [{'n': 1,
  'id': 'week-01',
  'title': 'Essential Tools and the Shell',
  'goal': 'Get fast at the commands you will use in every other week, and learn to answer your own questions '
          'from the man pages instead of a search engine.',
  'time': '2-3 hours',
  'prereqs': ['Both lab machines installed and reachable',
              'You are logged in as shea with sudo rights',
              'Use a VM console for network, boot and storage changes. Commands are guest commands, not '
              'macOS commands.',
              'Examples use shea; substitute your configured account consistently. Follow the weeks in '
              'order; shell variables must be recreated after reboot.'],
  'sections': [{'h': '1. Find your way around',
                'p': 'Start by proving to yourself where things live. The exam assumes you can navigate '
                     'without thinking about it.',
                'code': [('Essential tooling on BOTH guests',
                          'sudo dnf install -y openssh-server openssh-clients tar gzip bzip2 vim-minimal '
                          'man-db info\n'
                          'sudo systemctl enable --now sshd\n'
                          '# Resolve peer addresses before SSH; Fusion preconfigures servera/serverb in '
                          '/etc/hosts.'),
                         ('Where am I, and what is here?',
                          'pwd\nls -la /etc | head\nls -ld /var/log /usr/share/doc /home'),
                         ('Follow a file back to the package that owns it',
                          'which sshd || command -v sshd\nls -l /usr/sbin/sshd\nrpm -qf /usr/sbin/sshd')]},
               {'h': '2. Redirection and pipes',
                'p': 'Every one of these appears in the objectives by name. Run each and read the result '
                     'before moving on.',
                'code': [('Standard output, append, and standard error',
                          'ls /etc > ~/etc-list.txt\n'
                          'ls /nope 2> ~/errors.txt\n'
                          'ls /etc /nope > ~/both.txt 2>&1\n'
                          "echo 'appended line' >> ~/etc-list.txt\n"
                          'wc -l ~/etc-list.txt ~/errors.txt ~/both.txt'),
                         ('Pipe into a filter, and tee to a file while still seeing output',
                          'ps aux | wc -l\nps aux | tee ~/procs.txt | grep -c sshd'),
                         ('Throw output away when you only care about the exit status',
                          "grep -q root /etc/passwd 2>/dev/null && echo 'root exists'")]},
               {'h': '3. grep and regular expressions',
                'p': 'Anchors, character classes, and quantifiers cover almost everything the exam asks of '
                     'you.',
                'code': [('Anchors and case',
                          "grep '^shea' /etc/passwd\ngrep 'bash$' /etc/passwd\ngrep -i 'ROOT' /etc/passwd"),
                         ('Character classes and quantifiers',
                          "grep -E '^[a-z]+:x:[0-9]{4,}:' /etc/passwd\n"
                          "grep -E 'nologin|false' /etc/passwd | wc -l"),
                         ('Recursive search, with the filename and line number',
                          "sudo grep -rn 'PermitRootLogin' /etc/ssh/ 2>/dev/null")]},
               {'h': '4. Files, directories, and links',
                'p': 'Note carefully what happens to each link type when the target disappears. That '
                     'difference is testable.',
                'code': [('Create a working tree',
                          'mkdir -p ~/lab01/{src,dst}\n'
                          "echo 'original content' > ~/lab01/src/original.txt\n"
                          'cp ~/lab01/src/original.txt ~/lab01/dst/copy.txt\n'
                          'mv ~/lab01/dst/copy.txt ~/lab01/dst/renamed.txt'),
                         ('Hard link versus symbolic link',
                          'ln ~/lab01/src/original.txt ~/lab01/src/hardlink.txt\n'
                          'ln -s ~/lab01/src/original.txt ~/lab01/src/symlink.txt\n'
                          'ls -li ~/lab01/src/'),
                         ('Break the target and see which link survives',
                          'rm ~/lab01/src/original.txt\n'
                          'cat ~/lab01/src/hardlink.txt\n'
                          'cat ~/lab01/src/symlink.txt')],
                'note': 'The hard link still prints the content because it points at the same inode. The '
                        'symlink is now dangling and fails. Being able to explain that out loud is the '
                        'point.'},
               {'h': '5. Permissions',
                'p': 'Set the same permission set both ways so the octal and symbolic forms become '
                     'interchangeable in your head.',
                'code': [('Symbolic and octal, same result',
                          'touch ~/lab01/perms.txt\n'
                          'chmod u=rw,g=r,o= ~/lab01/perms.txt\n'
                          'ls -l ~/lab01/perms.txt\n'
                          'chmod 640 ~/lab01/perms.txt\n'
                          'ls -l ~/lab01/perms.txt'),
                         ('Directory permissions behave differently',
                          'mkdir ~/lab01/dir\n'
                          'chmod 700 ~/lab01/dir\n'
                          'ls -ld ~/lab01/dir\n'
                          'chmod 755 ~/lab01/dir')]},
               {'h': '6. Archives',
                'p': 'tar archives files; gzip and bzip2 compress them. Practise both extraction paths and '
                     'standalone compression.',
                'code': [('tar with gzip and with bzip2',
                          'tar -czf ~/lab01-gzip.tar.gz -C ~ lab01\n'
                          'tar -cjf ~/lab01-bzip2.tar.bz2 -C ~ lab01\n'
                          'ls -lh ~/lab01-*'),
                         ('Inspect before extracting, then extract elsewhere',
                          'tar -tzf ~/lab01-gzip.tar.gz | head\n'
                          'mkdir -p ~/restore\n'
                          'tar -xzf ~/lab01-gzip.tar.gz -C ~/restore\n'
                          'ls -R ~/restore | head')]},
               {'h': '7. Remote access and switching users',
                'p': 'You will use this connection in most later labs, so confirm it works now.',
                'code': [('Connect to the second machine and come back',
                          "ssh shea@serverb 'hostname; uptime'\n"
                          'ssh shea@serverb\n'
                          '# In the remote shell: inspect hostname, then return to servera\n'
                          'hostname\n'
                          'exit'),
                         ('Switch users properly',
                          '# Back on servera:\nsu - shea\nwhoami\nexit\nsudo -i\nwhoami\nexit\nhostname')]},
               {'h': '8. Answer your own questions',
                'p': 'This is the habit that matters most. In the exam there is no internet, only these.',
                'code': [('Search by keyword, then read the right section',
                          'man -k passwd | head\nman 5 passwd\nman 1 passwd'),
                         ('The documentation that ships with packages',
                          'ls /usr/share/doc | head -20\nls /usr/share/doc/bash* 2>/dev/null | head')]},
               {'h': '9. Edit text and use info',
                'p': 'Create and modify a file in the editor; save and quit.',
                'code': [('Editor and documentation',
                          'vi ~/lab01/editor.txt\ncat ~/lab01/editor.txt\ninfo coreutils'),
                         ('Archive and compression round trips',
                          'mkdir -p ~/restore-bzip2\n'
                          'tar -tjf ~/lab01-bzip2.tar.bz2 | head\n'
                          'tar -xjf ~/lab01-bzip2.tar.bz2 -C ~/restore-bzip2\n'
                          'tar -cf ~/lab01.tar -C ~ lab01\n'
                          'tar -tf ~/lab01.tar | head\n'
                          "printf 'compression example\\n' > ~/compress-example\n"
                          'gzip -c ~/compress-example > ~/compress-example.gz\n'
                          'gunzip -c ~/compress-example.gz\n'
                          'bzip2 -c ~/compress-example > ~/compress-example.bz2\n'
                          'bunzip2 -c ~/compress-example.bz2')]}],
  'verify': ["grep -c '' ~/etc-list.txt   # the file exists and has lines",
             'ls -li ~/lab01/src/         # hardlink shares an inode with nothing now; symlink is red/broken',
             "tar -tzf ~/lab01-gzip.tar.gz >/dev/null && echo 'archive readable'",
             "ssh shea@serverb 'echo remote ok'"],
  'breakfix': {'break': 'chmod 000 ~/lab01/dir',
               'symptom': 'You can no longer list or enter the directory, even though you own it.',
               'fix': 'chmod 755 ~/lab01/dir',
               'lesson': 'Owning a file does not grant access; the permission bits still apply to you. On '
                         "the exam, a 'diagnose and correct file permission problems' task usually looks "
                         'exactly like this.'}},
 {'n': 2,
  'id': 'week-02',
  'title': 'Users, Groups, and Privileged Access',
  'goal': 'Create and manage local accounts and groups, age passwords, and grant sudo access the way the '
          'exam expects - in a drop-in file, not by editing the main sudoers.',
  'time': '2-3 hours',
  'prereqs': ['Week 1 complete',
              'Root or sudo access on servera',
              'Use a VM console for network, boot and storage changes. Commands are guest commands, not '
              'macOS commands.',
              'Examples use shea; substitute your configured account consistently. Follow the weeks in '
              'order; shell variables must be recreated after reboot.'],
  'sections': [{'h': '1. Read the account databases first',
                'p': 'You cannot manage what you cannot read. Every field here has a meaning worth knowing.',
                'code': [('The three files that define an account',
                          'getent passwd shea\nsudo getent shadow shea\ngetent group shea'),
                         ('What the fields mean', 'man 5 passwd\nman 5 shadow\nman 5 group')]},
               {'h': '2. Create accounts',
                'p': 'Create three accounts with different characteristics so you have something to manage.',
                'code': [('A standard account, a system account, and one with a custom home',
                          "sudo useradd -c 'Standard account' analyst1\n"
                          'sudo useradd -r -s /sbin/nologin svc_backup\n'
                          "sudo useradd -d /opt/analyst2 -m -c 'Custom home' analyst2\n"
                          'getent passwd analyst1 svc_backup analyst2'),
                         ('Set passwords',
                          "echo 'ChangeMe123' | sudo passwd --stdin analyst1\nsudo passwd -l svc_backup")],
                'note': 'passwd --stdin is convenient in a lab. In the exam, plain interactive passwd is '
                        'fine and less error-prone.'},
               {'h': '3. Password aging',
                'p': 'Aging shows up in the objectives explicitly. Set it, then read it back.',
                'code': [('Force a change at first login',
                          'sudo chage -d 0 analyst1\nsudo chage -l analyst1'),
                         ('Maximum age, minimum age, and warning period',
                          'sudo chage -M 60 -m 7 -W 7 analyst1\nsudo chage -l analyst1'),
                         ('Expire an account on a fixed date',
                          'sudo chage -E 2027-01-01 analyst2\nsudo chage -l analyst2')]},
               {'h': '4. Groups and membership',
                'p': 'Use usermod -aG to add supplementary groups; -G without -a deliberately replaces the '
                     'complete supplementary list.',
                'code': [('Create groups and assign membership',
                          'sudo groupadd engineering\n'
                          'sudo groupadd -g 5000 contractors\n'
                          'sudo usermod -aG engineering analyst1\n'
                          'sudo usermod -aG engineering,contractors analyst2\n'
                          'id analyst1\n'
                          'id analyst2'),
                         ('Change a primary group', 'sudo usermod -g engineering analyst1\nid analyst1')],
                'note': 'usermod -G without -a replaces every supplementary group the user has. That single '
                        'missing letter has failed real exams.'},
               {'h': '5. A shared group directory',
                'p': 'This combines permissions, group ownership, and the set-GID bit - a very common '
                     'exam-style task.',
                'code': [('Create it and set group ownership',
                          'sudo mkdir -p /srv/engineering\n'
                          'sudo chgrp engineering /srv/engineering\n'
                          'sudo chmod 2770 /srv/engineering\n'
                          'ls -ld /srv/engineering'),
                         ('Prove the set-GID bit works',
                          'sudo -u analyst1 touch /srv/engineering/from-analyst1\nls -l /srv/engineering'),
                         ('Group write verification',
                          'sudo -u analyst1 bash -c \'umask 0002; printf "shared\\n" > '
                          "/srv/engineering/shared.txt'\n"
                          'sudo -u analyst2 bash -c \'printf "second writer\\n" >> '
                          "/srv/engineering/shared.txt'\n"
                          'cat /srv/engineering/shared.txt')],
                'note': 'Setgid provides group inheritance, not group write permission. Test the umask and '
                        'write as a second member.'},
               {'h': '6. Privileged access',
                'p': 'Always use a drop-in file. Editing /etc/sudoers directly is riskier and harder to '
                     'undo.',
                'code': [('Grant sudo to a group, safely',
                          "echo '%engineering ALL=(ALL) ALL' | sudo tee /etc/sudoers.d/engineering\n"
                          'sudo chmod 0440 /etc/sudoers.d/engineering\n'
                          'sudo visudo -c'),
                         ('Grant a single command without a password',
                          'sudo useradd -m limitedadmin\n'
                          'sudo passwd limitedadmin\n'
                          "echo 'limitedadmin ALL=(root) /usr/bin/systemctl restart sshd' | sudo tee "
                          '/etc/sudoers.d/limitedadmin\n'
                          'sudo chmod 0440 /etc/sudoers.d/limitedadmin\n'
                          'sudo visudo -c'),
                         ('Test as the user',
                          'sudo -l -U limitedadmin\n'
                          'su - limitedadmin\n'
                          'sudo /usr/bin/systemctl restart sshd\n'
                          'sudo /usr/bin/id  # must be denied\n'
                          'exit')]},
               {'h': '7. Account defaults and clean deletion',
                'p': 'Use disposable users; do not delete the earlier exercise accounts.',
                'code': [('Defaults and skeleton',
                          'useradd -D\n'
                          'sudo install -m 0644 /dev/null /etc/skel/rhcsa-welcome.txt\n'
                          'sudo useradd -m disposable\n'
                          'sudo ls -l /home/disposable/rhcsa-welcome.txt\n'
                          'sudo userdel -r disposable\n'
                          'sudo rm /etc/skel/rhcsa-welcome.txt\n'
                          'sudo groupadd disposablegroup\n'
                          'sudo groupdel disposablegroup')]}],
  'verify': ['id analyst1 analyst2',
             'sudo chage -l analyst1 | head -5',
             'ls -ld /srv/engineering   # expect drwxrws--- and group engineering',
             "sudo visudo -c            # must report 'parsed OK'"],
  'breakfix': {'break': '# FIRST keep sudo -i open in a second console for recovery.\n'
                        "echo 'this is not valid sudoers syntax' | sudo tee /etc/sudoers.d/broken",
               'symptom': 'sudo may start refusing to run at all, which can lock you out of privilege '
                          'escalation.',
               'fix': 'Recover from an existing root shell, or boot to the emergency shell as taught in Week '
                      '5, then: rm /etc/sudoers.d/broken',
               'lesson': "Always run 'visudo -c' after touching anything under /etc/sudoers.d, and keep a "
                         'root shell open in another terminal while you work. This is the one place where a '
                         'typo can lock you out of your own machine.'}},
 {'n': 3,
  'id': 'week-03',
  'title': 'Software: RPM, Repositories, and Flatpak',
  'goal': 'Install and remove software from every source the objectives name, including Flatpak, which is '
          'new to the RHEL 10 exam and missing from most older study material.',
  'time': '2-3 hours',
  'prereqs': ['Week 2 complete',
              'Network access from servera',
              'Use a VM console for network, boot and storage changes. Commands are guest commands, not '
              'macOS commands.',
              'Examples use shea; substitute your configured account consistently. Follow the weeks in '
              'order; shell variables must be recreated after reboot.'],
  'sections': [{'h': '1. Query before you install',
                'p': 'Half the software objectives are really about knowing what is already there.',
                'code': [('What is installed, and what owns a file',
                          'rpm -qa | wc -l\n'
                          'rpm -qa | grep -i openssh\n'
                          'rpm -qf /etc/ssh/sshd_config\n'
                          'rpm -ql openssh-server | head'),
                         ('Search the repositories',
                          "dnf search nmap\ndnf info nmap\ndnf provides '*/bash'")]},
               {'h': '2. Install and remove RPM packages',
                'p': 'From a repository, then from a downloaded file, so both paths are familiar.',
                'code': [('From a configured repository',
                          'sudo dnf install -y nmap\nrpm -q nmap\nsudo dnf remove -y nmap'),
                         ('Groups and updates',
                          'dnf group list\nsudo dnf check-update | head\nsudo dnf update -y'),
                         ('From a local file',
                          'sudo dnf install -y dnf-plugins-core\n'
                          'RPMDIR=$(mktemp -d)\n'
                          'dnf download --destdir="$RPMDIR" nmap\n'
                          'ls -l "$RPMDIR"\n'
                          'sudo dnf install -y "$RPMDIR"/nmap-*.rpm\n'
                          'rpm -q nmap')]},
               {'h': '3. Configure repository access',
                'p': 'Writing a .repo file by hand is explicitly in the objectives. Do it manually rather '
                     'than with a helper.',
                'code': [('Write the repo definition',
                          'sudo dnf install -y dnf-plugins-core createrepo_c\n'
                          'sudo mkdir -p /srv/rhcsa-repo\n'
                          'sudo dnf download --resolve --alldeps --destdir=/srv/rhcsa-repo nmap\n'
                          'sudo createrepo_c /srv/rhcsa-repo\n'
                          "sudo tee /etc/yum.repos.d/local-lab.repo >/dev/null <<'EOF'\n"
                          '[local-lab]\n'
                          'name=RHCSA Local Exercise\n'
                          'baseurl=file:///srv/rhcsa-repo\n'
                          'enabled=0\n'
                          'gpgcheck=0\n'
                          'EOF'),
                         ('List, enable, and disable',
                          'dnf repolist --all\n'
                          'sudo dnf config-manager --set-enabled local-lab\n'
                          "sudo dnf --disablerepo='*' --enablerepo=local-lab makecache\n"
                          'sudo dnf config-manager --set-disabled local-lab'),
                         ('Use a repository once without enabling it',
                          "sudo dnf --disablerepo='*' --enablerepo=local-lab list available")],
                'note': 'gpgcheck=0 is acceptable for a local lab repo you created. For a real remote '
                        'repository, point gpgkey at the key and leave gpgcheck=1.'},
               {'h': '4. Flatpak',
                'p': 'New in the RHEL 10 objectives. Configure a remote, then install, run, and remove an '
                     'application.',
                'code': [('Install the tooling and add a remote',
                          'sudo dnf install -y flatpak\n'
                          'flatpak remotes\n'
                          'flatpak remote-add --user --if-not-exists flathub '
                          'https://dl.flathub.org/repo/flathub.flatpakrepo\n'
                          'flatpak remotes --user'),
                         ('Search, install, list, and run',
                          'flatpak search --user texteditor | head\n'
                          'flatpak install --user -y flathub org.gnome.TextEditor\n'
                          'flatpak list --user\n'
                          'flatpak info --user org.gnome.TextEditor\n'
                          '# Running the GUI requires a graphical session; installation does not prove GUI '
                          'operation.'),
                         ('Remove it and clean up',
                          'flatpak uninstall --user -y org.gnome.TextEditor\n'
                          'flatpak uninstall --user --unused -y\n'
                          'flatpak list --user'),
                         ('Remove a remote', 'flatpak remote-delete --user flathub\nflatpak remotes --user')],
                'note': 'An RPM installs into the system as root and integrates with system libraries. A '
                        'Flatpak is a sandboxed, self-contained application bundle that can be installed '
                        'per-user. Being able to state that difference is fair game.'},
               {'h': '5. Real RHEL content access',
                'p': 'Only on RHEL, not Rocky. Use your authorized developer/organization account; do not '
                     'put credentials in commands.',
                'code': [('Registration and repository inspection',
                          'sudo subscription-manager register\n'
                          'sudo subscription-manager identity\n'
                          'sudo subscription-manager repos --list-enabled\n'
                          'sudo dnf repolist\n'
                          '# Enable the BaseOS/AppStream repositories appropriate to your RHEL '
                          'architecture/subscription if required.')]}],
  'verify': ["sudo dnf --disablerepo='*' --enablerepo=local-lab makecache",
             'rpm -q nmap',
             'flatpak remotes --user',
             'sudo dnf history | head -5'],
  'breakfix': {'break': "sudo sed -i 's|^baseurl=.*|baseurl=file:///mnt/does-not-exist|' "
                        '/etc/yum.repos.d/local-lab.repo\n'
                        "sudo dnf --disablerepo='*' --enablerepo=local-lab makecache",
               'symptom': 'The explicitly selected repository cannot load metadata. Read the named URL and '
                          'repository error.',
               'fix': "sudo sed -i 's|^baseurl=.*|baseurl=file:///srv/rhcsa-repo|' "
                      '/etc/yum.repos.d/local-lab.repo\n'
                      "sudo dnf --disablerepo='*' --enablerepo=local-lab --refresh makecache",
               'lesson': 'A repository requires packages and repodata. repolist alone does not validate '
                         'metadata; unrelated operations do not always read it.'}},
 {'n': 4,
  'id': 'week-04',
  'title': 'Processes, Tuning, and Scheduled Tasks',
  'goal': 'Find and control running processes, adjust their priority, manage tuned profiles, and schedule '
          'work three different ways.',
  'time': '2-3 hours',
  'prereqs': ['Week 3 complete',
              'Use a VM console for network, boot and storage changes. Commands are guest commands, not '
              'macOS commands.',
              'Examples use shea; substitute your configured account consistently. Follow the weeks in '
              'order; shell variables must be recreated after reboot.'],
  'sections': [{'h': '1. See what is running',
                'p': 'Learn one process listing well rather than three badly.',
                'code': [('Snapshot and live views',
                          'ps aux | head\nps -ef --forest | head -20\ntop -b -n 1 | head -15\nuptime'),
                         ('Sort by what actually matters',
                          'ps aux --sort=-%cpu | head -6\nps aux --sort=-%mem | head -6')]},
               {'h': '2. Create load, then kill it',
                'p': 'Make a process you can safely identify and terminate.',
                'code': [('Start something noisy in the background',
                          'sha256sum /dev/zero &\n'
                          'LOAD_PID=$!\n'
                          'sleep 300 &\n'
                          'SLEEP_PID=$!\n'
                          'jobs\n'
                          'ps -p "$LOAD_PID,$SLEEP_PID" -o pid,comm'),
                         ('Terminate it politely, then forcefully',
                          'kill "$LOAD_PID" "$SLEEP_PID"\n'
                          'wait "$LOAD_PID" "$SLEEP_PID" 2>/dev/null || true\n'
                          '# Send SIGKILL only to a specific lab PID still alive after SIGTERM.'),
                         ('Signals worth knowing',
                          'kill -l | head -3\n'
                          '# SIGTERM (15) asks a process to exit; SIGKILL (9) cannot be caught or ignored')]},
               {'h': '3. Scheduling priority',
                'p': 'Lower nice values mean higher priority. Only root can lower a value below zero.',
                'code': [('Start a process at a specific niceness',
                          'nice -n 10 sha256sum /dev/zero &\nNICE_PID=$!\nps -p "$NICE_PID" -o pid,ni,comm'),
                         ('Change it while running',
                          'sudo renice -n -5 -p "$NICE_PID"\n'
                          'ps -p "$NICE_PID" -o pid,ni,comm\n'
                          'kill "$NICE_PID"')]},
               {'h': '4. Tuning profiles',
                'p': 'Named directly in the objectives, and quick marks if you know the three commands.',
                'code': [('List, check, and switch',
                          'sudo dnf install -y tuned\n'
                          'sudo systemctl enable --now tuned\n'
                          'tuned-adm list\n'
                          'tuned-adm active\n'
                          'sudo tuned-adm profile throughput-performance\n'
                          'tuned-adm active'),
                         ('Let tuned choose for the hardware',
                          'sudo tuned-adm recommend\n'
                          'sudo tuned-adm profile $(sudo tuned-adm recommend)\n'
                          'tuned-adm active')]},
               {'h': '5. One-off jobs with at',
                'p': '',
                'code': [('Schedule and inspect',
                          'sudo dnf install -y at\n'
                          'sudo systemctl enable --now atd\n'
                          "echo 'date >> /tmp/at-test.log' | at now + 10 minutes\n"
                          'atq\n'
                          "read -r -p 'Job number just reported by at: ' JOB\n"
                          'if [[ $JOB =~ ^[0-9]+$ ]]; then at -c "$JOB" | tail -5; fi\n'
                          '# Optional cancellation: atrm "$JOB"; cancel only your own exercise job.'),
                         ('Wait, then confirm it ran',
                          '# After the scheduled time, inspect the result; do not block the terminal for ten '
                          'minutes.\n'
                          'cat /tmp/at-test.log\n'
                          'atq')]},
               {'h': '6. Recurring jobs with cron',
                'p': 'Both a user crontab and a system-wide job, because the exam may ask for either.',
                'code': [('Install and start cron',
                          'sudo dnf install -y cronie\nsudo systemctl enable --now crond'),
                         ('A user crontab',
                          'crontab -l 2>/dev/null\n'
                          "(crontab -l 2>/dev/null; echo '*/2 * * * * /usr/bin/date >> "
                          "/home/shea/cron-test.log') | crontab -\n"
                          'crontab -l'),
                         ('A system-wide job that runs as a specific user',
                          "sudo tee /etc/cron.d/lab-report >/dev/null <<'EOF'\n"
                          '*/5 * * * * shea /usr/bin/uptime >> /tmp/uptime-report.log\n'
                          'EOF\n'
                          'sudo systemctl status crond --no-pager | head -5')]},
               {'h': '7. systemd timers',
                'p': 'A timer needs two units: the service that does the work, and the timer that triggers '
                     'it.',
                'code': [('The service unit',
                          "sudo tee /etc/systemd/system/labreport.service >/dev/null <<'EOF'\n"
                          '[Unit]\n'
                          'Description=Write a short system report\n'
                          '\n'
                          '[Service]\n'
                          'Type=oneshot\n'
                          "ExecStart=/bin/bash -c '/usr/bin/date; /usr/bin/uptime' \n"
                          'EOF'),
                         ('The timer unit',
                          "sudo tee /etc/systemd/system/labreport.timer >/dev/null <<'EOF'\n"
                          '[Unit]\n'
                          'Description=Run labreport every 10 minutes\n'
                          '\n'
                          '[Timer]\n'
                          'OnBootSec=2min\n'
                          'OnUnitActiveSec=10min\n'
                          'Unit=labreport.service\n'
                          '\n'
                          '[Install]\n'
                          'WantedBy=timers.target\n'
                          'EOF'),
                         ('Enable and inspect',
                          'sudo systemctl daemon-reload\n'
                          'sudo systemctl enable --now labreport.timer\n'
                          'systemctl list-timers --all | grep labreport\n'
                          'sudo systemctl start labreport.service\n'
                          'sudo journalctl -u labreport.service --no-pager | tail -5')],
                'note': 'Reach for a timer over cron when you need the job tied to boot, dependent on '
                        'another unit, or logged in the journal. Cron is still fine for simple recurring '
                        'work.'}],
  'verify': ['tuned-adm active',
             'crontab -l',
             'systemctl list-timers --all | grep labreport',
             'systemctl is-enabled labreport.timer   # expect: enabled'],
  'breakfix': {'break': 'sudo cp -a /etc/systemd/system/labreport.service /root/labreport.service.backup\n'
                        "sudo sed -i 's|^ExecStart=.*|ExecStart=/usr/bin/false|' "
                        '/etc/systemd/system/labreport.service\n'
                        'sudo systemctl daemon-reload\n'
                        'sudo systemctl start labreport.service',
               'symptom': 'The service fails; the timer may still be active. Inspect systemctl status and '
                          'journalctl -u labreport.service.',
               'fix': 'sudo cp -a /root/labreport.service.backup /etc/systemd/system/labreport.service\n'
                      'sudo systemctl daemon-reload\n'
                      'sudo systemctl reset-failed labreport.service\n'
                      'sudo systemctl start labreport.service\n'
                      'sudo systemctl restart labreport.timer',
               'lesson': 'An active timer does not guarantee successful work. Invalid individual timer '
                         'values can be ignored; inspect the service result.'}},
 {'n': 5,
  'id': 'week-05',
  'title': 'Boot, Targets, Services, and Recovery',
  'goal': 'Control services and boot targets, and - most importantly - recover a system you have locked '
          'yourself out of. This is the lab that saves you in the exam.',
  'time': '3-4 hours',
  'prereqs': ['Week 4 complete',
              'Console access to the VM, not just SSH',
              'Use a VM console for network, boot and storage changes. Commands are guest commands, not '
              'macOS commands.',
              'Examples use shea; substitute your configured account consistently. Follow the weeks in '
              'order; shell variables must be recreated after reboot.'],
  'sections': [{'h': '1. Services: started versus enabled',
                'p': 'These are two separate things, and confusing them is the classic way to lose marks '
                     'after a reboot.',
                'code': [('The full lifecycle',
                          'sudo systemctl status sshd --no-pager\n'
                          'sudo systemctl stop sshd\n'
                          'sudo systemctl start sshd\n'
                          'sudo systemctl restart sshd\n'
                          'sudo systemctl reload sshd'),
                         ('Enable is about boot, start is about now',
                          'systemctl is-active sshd\n'
                          'systemctl is-enabled sshd\n'
                          'sudo systemctl disable sshd\n'
                          'systemctl is-enabled sshd\n'
                          'sudo systemctl enable --now sshd'),
                         ('What is running, and what failed',
                          'systemctl list-units --type=service --state=running | head\nsystemctl --failed')],
                'note': "'enable --now' does both in one command. If a task says a service must be running "
                        'and must come back after reboot, that is the command you want.'},
               {'h': '2. Boot targets',
                'p': '',
                'code': [('See and switch at runtime',
                          'systemctl get-default\n'
                          'systemctl list-units --type=target\n'
                          'sudo systemctl isolate multi-user.target'),
                         ('Set the default permanently',
                          'sudo systemctl set-default multi-user.target\n'
                          'systemctl get-default\n'
                          'ls -l /etc/systemd/system/default.target')]},
               {'h': '3. Interrupt the boot process',
                'p': 'Do this from the VM console, not over SSH. Take a snapshot first.',
                'code': [('At the GRUB menu',
                          '# At GRUB press e; on the linux line replace the standalone ro with rw.\n'
                          '# Remove any rd.break argument and append: init=/bin/bash enforcing=0\n'
                          '# Ctrl-X boots with this temporary change. Use the VM console.'),
                         ('In the emergency shell, remount and enter the real root',
                          '# init=/bin/bash already uses the installed root filesystem at /\n'
                          'mount -o remount,rw /'),
                         ('Reset the root password and force an SELinux relabel',
                          'passwd root\n'
                          'touch /.autorelabel\n'
                          'sync\n'
                          'exec /sbin/init\n'
                          '# Wait for relabeling and normal boot; then boot normally and verify enforcing.')],
                'note': 'RHEL/Rocky 10 initramfs may lack chroot and rd.break may require authentication. Do '
                        'not mix /sysroot and / recovery environments. enforcing=0 is temporary; keep '
                        'SELINUX=enforcing in the installed config. See Red Hat solution 7121729.'},
               {'h': '4. Boot into a different target manually',
                'p': 'A one-time change at the GRUB menu, useful when a service is preventing a normal boot.',
                'code': [('Append a target to the kernel line',
                          "# At the GRUB menu, press 'e' and append one of these to the 'linux' line:\n"
                          '#   systemd.unit=rescue.target\n'
                          '#   systemd.unit=emergency.target\n'
                          '#   systemd.unit=multi-user.target\n'
                          '# Then Ctrl-X to boot. The change applies to this boot only.')]},
               {'h': '5. Modify the bootloader',
                'p': 'Change the GRUB menu timeout, rebuild and inspect the generated configuration. This is '
                     'not a kernel argument.',
                'code': [('Edit the defaults and rebuild',
                          'sudo cp /etc/default/grub /root/grub.backup\n'
                          'sudo grep GRUB_TIMEOUT /etc/default/grub\n'
                          "sudo sed -i 's/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=10/' /etc/default/grub\n"
                          'sudo grub2-mkconfig -o /boot/grub2/grub.cfg'),
                         ('Confirm the change landed',
                          "sudo grep -nE 'timeout_style|set timeout=' /boot/grub2/grub.cfg\n"
                          'sudo grub2-editenv list\n'
                          '# If menu_auto_hide is enabled and the menu must be visible:\n'
                          '# sudo grub2-editenv - unset menu_auto_hide\n'
                          '# Verify the actual menu at the next reboot.')]},
               {'h': '6. Kernel argument round trip',
                'p': 'Use a disposable argument, inspect it after a normal reboot, then remove it.',
                'code': [('Add and inspect',
                          'sudo grubby --update-kernel=ALL --args=rhcsa_lab=1\n'
                          'sudo grubby --info=ALL | head -30\n'
                          '# Reboot normally, then: cat /proc/cmdline\n'
                          '# Remove after verification:\n'
                          '# sudo grubby --update-kernel=ALL --remove-args=rhcsa_lab=1')]}],
  'verify': ['systemctl get-default',
             'systemctl is-enabled sshd && systemctl is-active sshd',
             'grep GRUB_TIMEOUT /etc/default/grub',
             'reboot, then re-run all three and confirm nothing changed'],
  'breakfix': {'break': 'sudo systemctl disable sshd && sudo reboot',
               'symptom': 'After the reboot you cannot SSH in at all. The service exists and works, but '
                          'nothing started it.',
               'fix': 'From the VM console: sudo systemctl enable --now sshd',
               'lesson': "This is the reboot-persistence rule made concrete. In the exam a task like 'ensure "
                         "the web service is running' almost always means running now AND enabled at boot. "
                         "Get in the habit of typing 'enable --now' rather than 'start'."}},
 {'n': 6,
  'id': 'week-06',
  'title': 'Logs, Journals, and Time',
  'goal': 'Find out what a system has been doing, make that record survive a reboot, and keep the clock '
          'correct.',
  'time': '2-3 hours',
  'prereqs': ['Week 5 complete',
              'Both machines reachable',
              'Use a VM console for network, boot and storage changes. Commands are guest commands, not '
              'macOS commands.',
              'Examples use shea; substitute your configured account consistently. Follow the weeks in '
              'order; shell variables must be recreated after reboot.'],
  'sections': [{'h': '1. Read the journal',
                'p': 'journalctl is the primary tool. Learn the filters rather than scrolling.',
                'code': [('Filter by unit, priority, and time',
                          'sudo journalctl -u sshd --no-pager | tail -20\n'
                          'sudo journalctl -p err --no-pager | tail -20\n'
                          "sudo journalctl --since '1 hour ago' --no-pager | tail\n"
                          "sudo journalctl --since '2026-08-01 09:00' --until '2026-08-01 17:00' --no-pager "
                          '| tail'),
                         ('Follow live, and look at a specific boot',
                          'sudo journalctl -f    # Ctrl-C to stop\n'
                          'sudo journalctl --list-boots\n'
                          'sudo journalctl -b -1 --no-pager | head'),
                         ('Kernel messages and a specific executable',
                          'sudo journalctl -k --no-pager | tail\n'
                          'sudo journalctl /usr/sbin/sshd --no-pager | tail -5')]},
               {'h': '2. Make the journal persistent',
                'p': 'By default the journal may live only in memory and vanish at reboot. Preserving it is '
                     'an explicit objective.',
                'code': [('Create the directory and configure it',
                          'sudo mkdir -p /etc/systemd/journald.conf.d /var/log/journal\n'
                          "sudo tee /etc/systemd/journald.conf.d/99-persistent.conf >/dev/null <<'EOF'\n"
                          '[Journal]\n'
                          'Storage=persistent\n'
                          'EOF\n'
                          'sudo systemd-tmpfiles --create --prefix /var/log/journal'),
                         ('Restart and confirm',
                          'sudo systemctl restart systemd-journald\n'
                          'sudo journalctl --flush\n'
                          'sudo systemd-analyze cat-config systemd/journald.conf\n'
                          "sudo find /var/log/journal -maxdepth 2 -name '*.journal'\n"
                          "logger -t rhcsa-persistence 'marker before reboot'\n"
                          'sudo journalctl --sync\n'
                          '# After reboot: sudo journalctl -b -1 -t rhcsa-persistence --no-pager')],
                'note': "After a reboot, 'journalctl --list-boots' should show more than one entry. If it "
                        'only ever shows the current boot, persistence is not working.'},
               {'h': '3. Traditional log files',
                'p': 'rsyslog still writes plain text files that some tasks reference by name.',
                'code': [('Traditional logging prerequisites',
                          'sudo dnf install -y rsyslog\nsudo systemctl enable --now rsyslog'),
                         ('What is there',
                          'sudo ls -l /var/log/\n'
                          'sudo tail -20 /var/log/messages\n'
                          'sudo tail -20 /var/log/secure\n'
                          "sudo grep -i 'authentication failure' /var/log/secure | tail"),
                         ('Generate an entry and find it in both places',
                          "logger -p user.notice 'RHCSA lab test message from shea'\n"
                          "sudo grep 'RHCSA lab test' /var/log/messages\n"
                          "sudo journalctl --no-pager | grep 'RHCSA lab test'")]},
               {'h': '4. Time services',
                'p': 'chrony is the client. Configure it, then prove synchronisation.',
                'code': [('Install, enable, and inspect',
                          'sudo dnf install -y chrony\n'
                          'sudo systemctl enable --now chronyd\n'
                          'chronyc sources -v\n'
                          'chronyc tracking'),
                         ('Point at a specific server',
                          'sudo cp -a /etc/chrony.conf /root/chrony.conf.backup\n'
                          "sudo sed -i -E '/^[[:space:]]*(pool|server|sourcedir)[[:space:]]/d' "
                          '/etc/chrony.conf\n'
                          "echo 'server time.cloudflare.com iburst' | sudo tee -a /etc/chrony.conf\n"
                          'sudo systemctl restart chronyd\n'
                          'chronyc sources -v\n'
                          'chronyc tracking\n'
                          'chronyc waitsync 12 0.1 0 5\n'
                          '# A timeout is diagnostic; check DNS, network and NTP reachability.'),
                         ('Timezone and clocks',
                          'timedatectl\n'
                          'timedatectl list-timezones | grep -i new_york\n'
                          'sudo timedatectl set-timezone America/New_York\n'
                          'sudo timedatectl set-ntp true\n'
                          'timedatectl')]},
               {'h': '5. Secure file transfer',
                'p': 'Named in the objectives, and you will use it constantly anyway.',
                'code': [('Transfer prerequisites on BOTH hosts',
                          'sudo dnf install -y rsync openssh-clients'),
                         ('Three ways to move a file to the second machine',
                          "echo 'transfer test' > ~/transfer.txt\n"
                          'scp ~/transfer.txt shea@serverb:~/\n'
                          'rsync -av ~/lab01/ shea@serverb:~/lab01-copy/\n'
                          "sftp shea@serverb <<'EOF'\n"
                          'put ~/transfer.txt remote-via-sftp.txt\n'
                          'ls\n'
                          'bye\n'
                          'EOF'),
                         ('Confirm from the far end',
                          "ssh shea@serverb 'ls -l ~/transfer.txt ~/remote-via-sftp.txt; ls ~/lab01-copy | "
                          "head'")]}],
  'verify': ['sudo journalctl --list-boots      # more than one line after a reboot',
             'ls -d /var/log/journal/*',
             'chronyc tracking | head -3',
             "timedatectl | grep -E 'Time zone|synchronized'"],
  'breakfix': {'break': "sudo sed -i 's/^Storage=persistent/Storage=volatile/' "
                        '/etc/systemd/journald.conf.d/99-persistent.conf\n'
                        'sudo reboot\n'
                        '# After login in this volatile boot:\n'
                        "logger -t rhcsa-volatile 'volatile-only marker'\n"
                        'sudo journalctl --sync\n'
                        'sudo reboot',
               'symptom': 'After the second reboot the volatile-only marker is absent from the previous '
                          'boot. Previously persisted journals are not deleted.',
               'fix': "sudo sed -i 's/^Storage=volatile/Storage=persistent/' "
                      '/etc/systemd/journald.conf.d/99-persistent.conf\n'
                      'sudo systemctl restart systemd-journald\n'
                      'sudo journalctl --flush',
               'lesson': 'Use new markers and a complete boot cycle to distinguish volatile and persistent '
                         'storage; do not delete old evidence.'}},
 {'n': 7,
  'id': 'week-07',
  'title': 'Networking and firewalld',
  'goal': 'Configure addressing, name resolution, and a firewall that all survive a reboot without you '
          'touching anything.',
  'time': '3-4 hours',
  'prereqs': ['Week 6 complete',
              'Console access in case you cut off your own SSH session',
              'Use a VM console for network, boot and storage changes. Commands are guest commands, not '
              'macOS commands.',
              'Examples use shea; substitute your configured account consistently. Follow the weeks in '
              'order; shell variables must be recreated after reboot.'],
  'sections': [{'h': '1. Look before you change',
                'p': 'Record the current state so you can get back if something goes wrong.',
                'code': [('Current addressing and routing',
                          'ip addr show\n'
                          'ip route show\n'
                          'ip -6 addr show\n'
                          'nmcli device status\n'
                          'nmcli connection show'),
                         ('Save a copy of what works',
                          'nmcli connection show --active | tee ~/net-before.txt\n'
                          'ip addr show | tee -a ~/net-before.txt')]},
               {'h': '2. Configure a static IPv4 address',
                'p': "Use nmcli. Changes made with 'ip' alone disappear at reboot and score nothing.",
                'code': [('Identify the connection, then modify it',
                          'nmcli -f NAME,UUID,TYPE,DEVICE connection show\n'
                          'nmcli -f GENERAL.DEVICE,GENERAL.CONNECTION,GENERAL.HWADDR device show\n'
                          "read -r -p 'Host-only connection UUID (match Fusion MAC): ' CONN\n"
                          'sudo nmcli connection modify "$CONN" ipv4.method manual ipv4.addresses '
                          "192.168.56.10/24 ipv4.gateway '' ipv4.dns '' ipv4.never-default yes "
                          'ipv4.ignore-auto-dns yes connection.autoconnect yes\n'
                          '# On serverb choose its host-only UUID and use .11. NAT retains internet '
                          'routing/DNS.'),
                         ('Apply and confirm',
                          'sudo nmcli connection up "$CONN"\n'
                          'ip addr show\n'
                          'ip route show\n'
                          'cat /etc/resolv.conf')],
                'note': 'Adjust the addresses to match your own lab network. The method matters more than '
                        'the numbers: ipv4.method manual plus an explicit address is what makes it '
                        'persistent.'},
               {'h': '3. Add IPv6',
                'p': 'The objectives name IPv6 explicitly, and it is often skipped in practice.',
                'code': [('A static IPv6 address on the same connection',
                          'sudo nmcli connection modify "$CONN" ipv6.method manual ipv6.addresses '
                          '2001:db8:56::10/64 ipv6.gateway "" ipv6.never-default yes\n'
                          'sudo nmcli connection up "$CONN"\n'
                          '# Configure serverb host-only with 2001:db8:56::11/64 first.\n'
                          'ip -6 addr show\n'
                          'ping -6 -c 2 2001:db8:56::11')]},
               {'h': '4. Hostname and name resolution',
                'p': '',
                'code': [('Set the hostname permanently',
                          'hostnamectl\n'
                          'sudo hostnamectl set-hostname servera.lab.example.com\n'
                          'hostnamectl\n'
                          'hostname -f'),
                         ('Static resolution and testing',
                          'sudo dnf install -y bind-utils\n'
                          "echo '192.168.56.11 serverb serverb.lab.example.com' | sudo tee -a /etc/hosts\n"
                          'getent hosts serverb\n'
                          'ping -c 2 serverb\n'
                          'dig +short redhat.com\n'
                          '# nslookup tests DNS, not /etc/hosts.')]},
               {'h': '5. Networking at boot',
                'p': '',
                'code': [('Make sure it comes up by itself',
                          'sudo systemctl enable --now NetworkManager\n'
                          'sudo nmcli connection modify "$CONN" connection.autoconnect yes\n'
                          'nmcli -f connection.autoconnect connection show "$CONN"')]},
               {'h': '6. firewalld',
                'p': 'Select the zone actually attached to the lab adapter. Permanent edits plus reload are '
                     'one valid persistence workflow.',
                'code': [('Inspect the current state',
                          'sudo systemctl enable --now firewalld\n'
                          'sudo firewall-cmd --state\n'
                          'sudo firewall-cmd --get-active-zones\n'
                          'sudo firewall-cmd --list-all\n'
                          "read -r -p 'Active zone attached to host-only interface: ' ZONE"),
                         ('Open a named service permanently',
                          'sudo firewall-cmd --zone="$ZONE" --permanent --add-service=http\n'
                          'sudo firewall-cmd --zone="$ZONE" --permanent --add-service=https\n'
                          'sudo firewall-cmd --reload\n'
                          'sudo firewall-cmd --zone="$ZONE" --list-services'),
                         ('Open a specific port, and a port range',
                          'sudo firewall-cmd --zone="$ZONE" --permanent --add-port=8080/tcp\n'
                          'sudo firewall-cmd --zone="$ZONE" --permanent --add-port=9000-9010/udp\n'
                          'sudo firewall-cmd --reload\n'
                          'sudo firewall-cmd --zone="$ZONE" --list-ports'),
                         ('Remove something, and inspect zones',
                          'sudo firewall-cmd --zone="$ZONE" --permanent --remove-port=9000-9010/udp\n'
                          'sudo firewall-cmd --reload\n'
                          'sudo firewall-cmd --get-default-zone\n'
                          'sudo firewall-cmd --zone="$ZONE" --list-all --zone=public')],
                'note': 'Inspect runtime and permanent settings in the selected active zone; an open rule '
                        'does not prove a service is listening.'}],
  'verify': ["ip addr show | grep -E 'inet |inet6 '",
             'sudo firewall-cmd --permanent --list-all',
             'getent hosts serverb',
             'reboot, then re-run every command above and confirm nothing was lost'],
  'breakfix': {'break': 'sudo firewall-cmd --zone="$ZONE" --query-port=18080/tcp\n'
                        'sudo firewall-cmd --permanent --zone="$ZONE" --query-port=18080/tcp\n'
                        '# Proceed only when both report no.\n'
                        'sudo firewall-cmd --zone="$ZONE" --add-port=18080/tcp\n'
                        'sudo firewall-cmd --zone="$ZONE" --query-port=18080/tcp\n'
                        'sudo firewall-cmd --reload\n'
                        'sudo firewall-cmd --zone="$ZONE" --query-port=18080/tcp',
               'symptom': 'The runtime-only port disappears after reload. This tests the rule, not a '
                          'listening service.',
               'fix': 'sudo firewall-cmd --permanent --zone="$ZONE" --add-port=18080/tcp\n'
                      'sudo firewall-cmd --reload',
               'lesson': 'Choose a port absent from permanent configuration; adding HTTP again after '
                         'permanently opening it does not demonstrate loss.'}},
 {'n': 8,
  'id': 'week-08',
  'title': 'Partitions, Filesystems, and Swap',
  'goal': 'Carve up the spare disk, format it three ways, mount it persistently by UUID, and add swap - all '
          'without destroying the system.',
  'time': '3-4 hours',
  'prereqs': ['Week 7 complete',
              'A second, empty disk attached to servera',
              'A snapshot taken immediately before you start',
              'Use a VM console for network, boot and storage changes. Commands are guest commands, not '
              'macOS commands.',
              'Examples use shea; substitute your configured account consistently. Follow the weeks in '
              'order; shell variables must be recreated after reboot.'],
  'sections': [{'h': '1. Identify the right disk',
                'p': 'Get this wrong and you will reinstall. Confirm the device before every destructive '
                     'command.',
                'code': [('Which disk is spare?', 'lsblk\nsudo fdisk -l\nsudo blkid\ndf -h'),
                         ('Set a variable so you cannot mistype it later',
                          'sudo dnf install -y parted xfsprogs e2fsprogs dosfstools\n'
                          'lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS\n'
                          'sudo fdisk -l\n'
                          "read -r -p 'EXTRA lab disk path, never the system disk: ' DISK\n"
                          'case "$DISK" in /dev/*[0-9]) PART_PREFIX=${DISK}p ;; /dev/*) PART_PREFIX=$DISK ;; '
                          "*) echo 'Invalid disk path'; exit 1 ;; esac\n"
                          'P1=${PART_PREFIX}1; P2=${PART_PREFIX}2; P3=${PART_PREFIX}3; P4=${PART_PREFIX}4; '
                          'P5=${PART_PREFIX}5; P6=${PART_PREFIX}6\n'
                          'lsblk "$DISK"\n'
                          'sudo parted "$DISK" unit MiB print free\n'
                          'sudo wipefs -n "$DISK"\n'
                          '# Inspect existing partitions too. Absence of a whole-disk signature does NOT '
                          'mean empty.\n'
                          '# Stop unless this is the disposable, empty extra disk. mklabel destroys its '
                          'partition table.')],
                'note': 'If lsblk shows a mountpoint or existing data on your candidate disk, stop and pick '
                        'a different one.'},
               {'h': '2. Create GPT partitions',
                'p': '',
                'code': [('Write a GPT label and two partitions',
                          'sudo parted -s "$DISK" mklabel gpt\n'
                          'sudo parted -s "$DISK" mkpart primary 1MiB 2GiB\n'
                          'sudo parted -s "$DISK" mkpart primary 2GiB 4GiB\n'
                          'sudo parted -s "$DISK" print\n'
                          'lsblk "$DISK"'),
                         ('Make sure the kernel noticed', 'sudo partprobe "$DISK"\nlsblk "$DISK"')]},
               {'h': '3. Create filesystems',
                'p': 'All three named types appear in the objectives.',
                'code': [('XFS and ext4',
                          'sudo mkfs.xfs "$P1"\nsudo mkfs.ext4 "$P2"\nsudo blkid "$P1" "$P2"'),
                         ('Label them, which makes fstab easier to read',
                          'sudo xfs_admin -L labxfs "$P1"\n'
                          'sudo e2label "$P2" labext4\n'
                          'sudo blkid "$P1" "$P2"')]},
               {'h': '4. Mount, then make it permanent',
                'p': 'Mounting by device name is fragile - device names can change between boots. Use UUID '
                     'or label.',
                'code': [('Mount by hand first to prove it works',
                          'sudo mkdir -p /mnt/xfsdata /mnt/extdata\n'
                          'sudo mount "$P1" /mnt/xfsdata\n'
                          'sudo mount "$P2" /mnt/extdata\n'
                          'df -h | grep mnt\n'
                          'sudo umount /mnt/xfsdata /mnt/extdata'),
                         ('Add persistent entries by UUID',
                          'sudo cp /etc/fstab /root/fstab.backup\n'
                          'UUID1=$(sudo blkid -s UUID -o value "$P1")\n'
                          'UUID2=$(sudo blkid -s UUID -o value "$P2")\n'
                          'echo "UUID=$UUID1  /mnt/xfsdata  xfs   defaults  0 0" | sudo tee -a /etc/fstab\n'
                          'echo "UUID=$UUID2  /mnt/extdata  ext4  defaults  0 2" | sudo tee -a /etc/fstab\n'
                          'cat /etc/fstab'),
                         ('Test WITHOUT rebooting - this is the safety net',
                          'sudo findmnt --verify --verbose\n'
                          'sudo systemctl daemon-reload\n'
                          'sudo mount -a\n'
                          'findmnt /mnt/xfsdata\n'
                          'findmnt /mnt/extdata')],
                'note': 'Validate with findmnt --verify, mount -a and swapon -a. Already mounted filesystems '
                        'may be skipped by mount -a; reboot and inspect each mount.'},
               {'h': '5. A VFAT filesystem',
                'p': 'Named in the objectives, and quick to do with a small third partition.',
                'code': [('Add and format it',
                          'sudo parted -s "$DISK" mkpart primary fat32 4GiB 5GiB\n'
                          'sudo partprobe "$DISK"\n'
                          'sudo mkfs.vfat -n LABVFAT "$P3"\n'
                          'sudo mkdir -p /mnt/vfatdata\n'
                          'UUID3=$(sudo blkid -s UUID -o value "$P3")\n'
                          'echo "UUID=$UUID3  /mnt/vfatdata  vfat  defaults  0 0" | sudo tee -a /etc/fstab\n'
                          'sudo mount -a\n'
                          'df -h | grep vfat')]},
               {'h': '6. Add swap non-destructively',
                'p': "The objectives say 'non-destructively' - meaning without disturbing what is already "
                     'there.',
                'code': [('A swap partition',
                          'sudo parted -s "$DISK" mkpart primary linux-swap 5GiB 6GiB\n'
                          'sudo partprobe "$DISK"\n'
                          'sudo mkswap "$P4"\n'
                          'sudo swapon "$P4"\n'
                          'swapon --show\n'
                          'free -h'),
                         ('Make it permanent',
                          'UUID4=$(sudo blkid -s UUID -o value "$P4")\n'
                          'echo "UUID=$UUID4  none  swap  defaults  0 0" | sudo tee -a /etc/fstab\n'
                          'sudo swapoff "$P4" && sudo swapon -a\n'
                          'swapon --show')]},
               {'h': '7. Mount by label and delete an unused partition',
                'p': 'Do this before week 9, while space beyond 6GiB remains free.',
                'code': [('Label mount',
                          'UUID2=$(sudo blkid -s UUID -o value "$P2")\n'
                          'sudo umount /mnt/extdata\n'
                          'sudo sed -i "s/^UUID=$UUID2[[:space:]]/LABEL=labext4 /" /etc/fstab\n'
                          'sudo findmnt --verify --verbose\n'
                          'sudo systemctl daemon-reload\n'
                          'sudo mount /mnt/extdata\n'
                          'findmnt /mnt/extdata'),
                         ('Disposable partition deletion',
                          'sudo parted -s "$DISK" mkpart primary 6GiB 6500MiB\n'
                          'sudo partprobe "$DISK"\n'
                          'sudo parted "$DISK" print\n'
                          '# Confirm partition 5 is the new, unused disposable partition:\n'
                          'sudo parted -s "$DISK" rm 5\n'
                          'sudo partprobe "$DISK"\n'
                          'sudo parted "$DISK" print')]}],
  'verify': ['sudo findmnt --verify --verbose && sudo mount -a && sudo swapon -a',
             'df -h | grep /mnt',
             'swapon --show',
             'reboot, then: df -h | grep /mnt && swapon --show'],
  'breakfix': {'break': 'sudo mkdir -p /mnt/ghost\n'
                        "echo 'UUID=00000000-dead-beef-0000-000000000000  /mnt/ghost  xfs  defaults  0 0' | "
                        'sudo tee -a /etc/fstab',
               'symptom': "'mount -a' fails. Had you rebooted instead, the system would have dropped to an "
                          'emergency shell asking for the root password.',
               'fix': "sudo sed -i '/dead-beef/d' /etc/fstab && sudo mount -a",
               'lesson': 'Validate fstab before reboot. Keep a console recovery route ready; locked root may '
                         'prevent ordinary emergency authentication. Use the week-5 recovery procedure if '
                         'needed.'}},
 {'n': 9,
  'id': 'week-09',
  'title': 'LVM, NFS, and autofs',
  'goal': 'Build logical volumes you can grow on demand, share a directory over the network, and mount it '
          'automatically only when it is needed.',
  'time': '4-5 hours',
  'prereqs': ['Week 8 complete',
              'Free space or a third disk on servera',
              'serverb reachable and able to run an NFS server',
              'Use a VM console for network, boot and storage changes. Commands are guest commands, not '
              'macOS commands.',
              'Examples use shea; substitute your configured account consistently. Follow the weeks in '
              'order; shell variables must be recreated after reboot.'],
  'sections': [{'h': '1. Build the LVM stack',
                'p': 'Physical volume, then volume group, then logical volume. Always in that order.',
                'code': [('Recreate disk variables after reboot',
                          'lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS\n'
                          'sudo fdisk -l\n'
                          "read -r -p 'EXTRA lab disk path, never the system disk: ' DISK\n"
                          'case "$DISK" in /dev/*[0-9]) PART_PREFIX=${DISK}p ;; /dev/*) PART_PREFIX=$DISK ;; '
                          "*) echo 'Invalid disk path'; exit 1 ;; esac\n"
                          'P1=${PART_PREFIX}1; P2=${PART_PREFIX}2; P3=${PART_PREFIX}3; P4=${PART_PREFIX}4; '
                          'P5=${PART_PREFIX}5; P6=${PART_PREFIX}6\n'
                          'lsblk "$DISK"\n'
                          'sudo parted "$DISK" unit MiB print free\n'
                          'sudo wipefs -n "$DISK"\n'
                          '# Inspect existing partitions too. Absence of a whole-disk signature does NOT '
                          'mean empty.\n'
                          '# Stop unless this is the correct week-8 extra disk; preserve its existing '
                          'partitions. Do NOT run mklabel again.'),
                         ('Create physical volumes',
                          'sudo parted -s "$DISK" mkpart primary 6GiB 8GiB\n'
                          'sudo parted -s "$DISK" mkpart primary 8GiB 100%\n'
                          'sudo partprobe "$DISK"\n'
                          'sudo pvcreate "$P5" "$P6"\n'
                          'sudo pvs\n'
                          'sudo pvdisplay "$P5" | head'),
                         ('Create a volume group',
                          'sudo vgcreate labvg "$P5"\nsudo vgs\nsudo vgdisplay labvg | head'),
                         ('Create logical volumes - by size and by extents',
                          'sudo lvcreate -L 500M -n labdata labvg\n'
                          'sudo lvcreate -l 50%FREE -n labarchive labvg\n'
                          'sudo lvs\n'
                          'lsblk')]},
               {'h': '2. Format and mount a logical volume',
                'p': '',
                'code': [('Filesystem and persistent mount',
                          'sudo mkfs.xfs /dev/labvg/labdata\n'
                          'sudo mkdir -p /mnt/labdata\n'
                          'LVUUID=$(sudo blkid -s UUID -o value /dev/labvg/labdata)\n'
                          'echo "UUID=$LVUUID  /mnt/labdata  xfs  defaults  0 0" | sudo tee -a /etc/fstab\n'
                          'sudo mount -a\n'
                          'df -h /mnt/labdata'),
                         ('Put something in it so you can prove it survives',
                          "echo 'written before the extend' | sudo tee /mnt/labdata/before.txt\n"
                          'sudo cat /mnt/labdata/before.txt')]},
               {'h': '3. Extend a volume group and a logical volume',
                'p': 'Growing storage online without losing data is a headline objective.',
                'code': [('Add capacity to the volume group',
                          'sudo vgextend labvg "$P6"\nsudo vgs\nsudo pvs'),
                         ('Grow the logical volume and the filesystem together',
                          'df -h /mnt/labdata\n'
                          'sudo lvextend -L +800M -r /dev/labvg/labdata\n'
                          'sudo lvs\n'
                          'df -h /mnt/labdata\n'
                          'sudo cat /mnt/labdata/before.txt'),
                         ('The two-step form, for when -r is not available',
                          '# sudo lvextend -L +200M /dev/labvg/labdata\n'
                          '# XFS grows with:   sudo xfs_growfs /mnt/labdata\n'
                          '# ext4 grows with:  sudo resize2fs /dev/labvg/labdata')],
                'note': 'lvextend -r grows the filesystem along with the LV. XFS cannot shrink. Ext4 '
                        'shrinking requires an offline, checked filesystem and careful ordering; it is not '
                        'this online-growth exercise.'},
               {'h': '4. Remove volumes cleanly',
                'p': '',
                'code': [('Tear down in reverse order',
                          'sudo lvremove -y labvg/labarchive\n'
                          'sudo lvs\n'
                          '# to remove the whole stack later:\n'
                          '#   Remove the labdata UUID entry from /etc/fstab first and run daemon-reload.\n'
                          '#   sudo umount /mnt/labdata\n'
                          '#   sudo lvremove -y labvg/labdata\n'
                          '#   sudo vgremove -y labvg\n'
                          '#   sudo pvremove "$P5" "$P6"')]},
               {'h': '5. Export a directory over NFS',
                'p': 'Run this section on serverb.',
                'code': [('On serverb - install, export, and open the firewall',
                          'sudo dnf install -y nfs-utils\n'
                          'sudo mkdir -p /srv/nfsshare\n'
                          'sudo chmod 755 /srv/nfsshare\n'
                          "echo 'exported from serverb' | sudo tee /srv/nfsshare/hello.txt\n"
                          'sudo mkdir -p /etc/exports.d\n'
                          "echo '/srv/nfsshare 192.168.56.10(ro,sync,root_squash)' | sudo tee "
                          '/etc/exports.d/rhcsa.exports\n'
                          'sudo exportfs -rav\n'
                          'sudo systemctl enable --now nfs-server\n'
                          'sudo firewall-cmd --get-active-zones\n'
                          "read -r -p 'Active lab-interface zone: ' NFSZONE\n"
                          'sudo firewall-cmd --permanent --zone="$NFSZONE" --add-service=nfs\n'
                          'sudo firewall-cmd --permanent --zone="$NFSZONE" --add-service=mountd\n'
                          'sudo firewall-cmd --permanent --zone="$NFSZONE" --add-service=rpc-bind\n'
                          'sudo firewall-cmd --reload')]},
               {'h': '6. Mount the NFS share',
                'p': 'Back on servera.',
                'code': [('Discover and mount by hand',
                          'sudo dnf install -y nfs-utils\n'
                          'showmount -e serverb\n'
                          'sudo mkdir -p /mnt/nfsshare\n'
                          'sudo mount -t nfs serverb:/srv/nfsshare /mnt/nfsshare\n'
                          'df -h | grep nfs\n'
                          'cat /mnt/nfsshare/hello.txt'),
                         ('Make it persistent',
                          'sudo umount /mnt/nfsshare\n'
                          "echo 'serverb:/srv/nfsshare  /mnt/nfsshare  nfs  defaults,_netdev  0 0' | sudo "
                          'tee -a /etc/fstab\n'
                          'sudo mount -a\n'
                          'df -h | grep nfs')],
                'note': 'NFS is automatically recognized as a network filesystem by systemd. _netdev is '
                        'allowed but does not guarantee server availability. Boot serverb before testing the '
                        'client.'},
               {'h': '7. autofs',
                'p': 'Mount on access, unmount when idle. Named explicitly in the objectives.',
                'code': [('Remove the static mount first',
                          'sudo umount /mnt/nfsshare\n'
                          "sudo sed -i '\\|serverb:/srv/nfsshare|d' /etc/fstab\n"
                          "grep nfs /etc/fstab || echo 'static NFS entry removed'"),
                         ('Configure the maps',
                          'sudo dnf install -y autofs\n'
                          "echo '/-  /etc/auto.direct' | sudo tee -a /etc/auto.master\n"
                          "echo '/mnt/nfsshare  -rw,sync  serverb:/srv/nfsshare' | sudo tee "
                          '/etc/auto.direct\n'
                          'sudo systemctl enable --now autofs\n'
                          'sudo systemctl restart autofs'),
                         ('Prove on-demand behaviour',
                          'findmnt -t nfs,nfs4\n'
                          'ls /mnt/nfsshare\n'
                          'findmnt -t nfs,nfs4\n'
                          '# Leave the directory and close open files; wait for the configured autofs '
                          'timeout.\n'
                          '# Inspect findmnt again without accessing the mounted path.')]},
               {'h': '8. Diagnose a permission problem',
                'p': 'An explicit objective, and the diagnosis method matters more than the fix.',
                'code': [('Create the problem, then work it out',
                          'sudo mkdir -p /srv/shared-data\n'
                          'sudo chown root:root /srv/shared-data\n'
                          'sudo chmod 700 /srv/shared-data\n'
                          'sudo -u analyst1 ls /srv/shared-data   # fails\n'
                          'ls -ld /srv/shared-data\n'
                          'id analyst1'),
                         ('Fix it properly with a group, not with 777',
                          'sudo chgrp engineering /srv/shared-data\n'
                          'sudo chmod 2775 /srv/shared-data\n'
                          'sudo -u analyst1 touch /srv/shared-data/works.txt\n'
                          'ls -l /srv/shared-data')]}],
  'verify': ['sudo lvs && sudo vgs && sudo pvs',
             'df -h /mnt/labdata   # should show the extended size',
             'ls /mnt/nfsshare     # triggers the autofs mount',
             "reboot, then confirm /mnt/labdata is mounted and 'ls /mnt/nfsshare' still works"],
  'breakfix': {'break': 'sudo lvextend -L +5G /dev/labvg/labdata',
               'symptom': 'The requested +5GiB exceeds VFree; free space need not be zero.',
               'fix': 'Inspect sudo vgs. Attach a third disposable disk and initialize a new PV, then '
                      'vgextend; or choose a growth smaller than VFree. Do not repartition existing data. '
                      'After adding capacity use lvextend -r to grow both LV and filesystem.',
               'lesson': 'LVM is a stack, and you can only grow a layer if the one beneath it has room. When '
                         "an lvextend fails, check 'vgs' before anything else - the answer is almost always "
                         'there in the VFree column.'}},
 {'n': 10,
  'id': 'week-10',
  'title': 'SELinux, SSH Keys, and Default Permissions',
  'goal': 'Work with SELinux modes, labels, ports and booleans, verify SSH keys, and control default '
          'permissions.',
  'time': '4-5 hours',
  'prereqs': ['Week 9 complete',
              'Both machines reachable',
              'A snapshot before you start',
              'Use a VM console for network, boot and storage changes. Commands are guest commands, not '
              'macOS commands.',
              'Examples use shea; substitute your configured account consistently. Follow the weeks in '
              'order; shell variables must be recreated after reboot.'],
  'sections': [{'h': '1. Modes',
                'p': 'Enforcing blocks and logs. Permissive only logs. Disabled does neither - and is never '
                     'the right answer on the exam.',
                'code': [('Check and switch at runtime',
                          'getenforce\n'
                          'sestatus\n'
                          'sudo setenforce 0\n'
                          'getenforce\n'
                          'sudo setenforce 1\n'
                          'getenforce'),
                         ('Make the mode persistent',
                          "sudo cat /etc/selinux/config | grep -v '^#'\n"
                          "sudo sed -i 's/^SELINUX=.*/SELINUX=enforcing/' /etc/selinux/config\n"
                          "grep '^SELINUX=' /etc/selinux/config")],
                'note': 'setenforce changes the current mode only. The file is what applies at boot. A task '
                        "that says 'SELinux must be enforcing' means both."},
               {'h': '2. Read contexts',
                'p': 'SELinux contexts are user:role:type:level. The third field is the type.',
                'code': [('Install inspection tools',
                          'sudo dnf install -y policycoreutils-python-utils audit'),
                         ('Files, processes, ports, and users',
                          'ls -Z /var/www/html 2>/dev/null || sudo mkdir -p /var/www/html && ls -Zd '
                          '/var/www/html\n'
                          'ps -eZ | grep sshd | head -3\n'
                          'id -Z\n'
                          'sudo semanage port -l | grep -w http_port_t')]},
               {'h': '3. Fix a context the right way',
                'p': 'This is the classic exam scenario: content served from a non-default location.',
                'code': [('Set up a web server with content in the wrong place',
                          'sudo dnf install -y httpd\n'
                          'sudo systemctl enable --now httpd\n'
                          'sudo firewall-cmd --permanent --add-service=http && sudo firewall-cmd --reload\n'
                          'sudo mkdir -p /srv/mysite\n'
                          "echo '<h1>Lab site</h1>' | sudo tee /srv/mysite/index.html\n"
                          'ls -Zd /srv/mysite'),
                         ('Point httpd at it and watch it fail',
                          "sudo tee /etc/httpd/conf.d/rhcsa-mysite.conf >/dev/null <<'EOF'\n"
                          '<Directory "/srv/mysite">\n'
                          '    AllowOverride None\n'
                          '    Require all granted\n'
                          '</Directory>\n'
                          'EOF\n'
                          'sudo sed -i \'s|^DocumentRoot .*|DocumentRoot "/srv/mysite"|\' '
                          '/etc/httpd/conf/httpd.conf\n'
                          'sudo apachectl configtest\n'
                          'sudo systemctl restart httpd\n'
                          "curl -s -o /dev/null -w '%{http_code}\\n' http://localhost/\n"
                          'sudo journalctl -t setroubleshoot --no-pager | tail -5\n'
                          'sudo ausearch -m AVC -ts recent 2>/dev/null | tail -20'),
                         ('Fix it permanently with semanage plus restorecon',
                          'sudo semanage fcontext -l -C\n'
                          '# New exercise path, no previous rule:\n'
                          "sudo semanage fcontext -a -t httpd_sys_content_t '/srv/mysite(/.*)?'\n"
                          '# On a repeated run, use -m for an existing incorrect rule, or leave a correct '
                          'rule unchanged.\n'
                          'sudo restorecon -Rv /srv/mysite\n'
                          'ls -Zd /srv/mysite\n'
                          "curl -sS -o /tmp/rhcsa-page -w '%{http_code}\\n' http://localhost/\n"
                          'cat /tmp/rhcsa-page')],
                'note': 'chcon would also have worked right now - and would be wiped by the next relabel. '
                        'semanage fcontext writes the rule into policy; restorecon applies it. That pairing '
                        'is the correct, persistent answer.'},
               {'h': '4. Port labels',
                'p': 'First inspect existing port labels. A previously allowed port may not fail; adding an '
                     'already defined port needs deliberate modification rather than -a.',
                'code': [('Move httpd to port 8888',
                          'sudo semanage port -l | grep -E "8888|http_port_t"\n'
                          "sudo sed -i 's/^Listen 80$/Listen 8888/' /etc/httpd/conf/httpd.conf\n"
                          'sudo systemctl restart httpd   # may fail if the port is not allowed\n'
                          'sudo systemctl status httpd --no-pager | tail -5'),
                         ('Label the port, then it starts',
                          'sudo semanage port -l | grep -w http_port_t\n'
                          '# Inspect ALL policy labels for 8888. Then run exactly one appropriate command:\n'
                          '# Unassigned: sudo semanage port -a -t http_port_t -p tcp 8888\n'
                          '# Assigned to another type, after checking impact: sudo semanage port -m -t '
                          'http_port_t -p tcp 8888\n'
                          '# Already http_port_t: no policy change is needed.\n'
                          "read -r -p 'Inspect the labels and apply the appropriate command in another "
                          "console; Enter when done: ' _\n"
                          'sudo systemctl restart httpd\n'
                          'sudo firewall-cmd --get-active-zones\n'
                          "read -r -p 'Active lab-interface zone: ' WEBZONE\n"
                          'sudo firewall-cmd --permanent --zone="$WEBZONE" --add-port=8888/tcp\n'
                          'sudo firewall-cmd --reload\n'
                          "curl -sS -o /tmp/rhcsa-page -w '%{http_code}\\n' http://localhost:8888/\n"
                          'cat /tmp/rhcsa-page')]},
               {'h': '5. Booleans',
                'p': 'Booleans switch predefined policy behaviour on and off. -P makes the change survive a '
                     'reboot.',
                'code': [('Find and set one',
                          'getsebool -a | head\n'
                          'getsebool -a | grep httpd | head -10\n'
                          'getsebool httpd_enable_homedirs\n'
                          'sudo setsebool -P httpd_enable_homedirs on\n'
                          'getsebool httpd_enable_homedirs'),
                         ('See what a boolean actually does',
                          'sudo semanage boolean -l | grep httpd_enable_homedirs')],
                'note': 'Use -P for a persistent boolean change. Inspect current and persistent state and '
                        'follow the requested target mode.'},
               {'h': '6. Read a denial',
                'p': 'Being able to interpret the log is the skill; the fix follows from it.',
                'code': [('Find and translate',
                          'sudo ausearch -m AVC -ts today 2>/dev/null | tail -20\n'
                          'sudo journalctl -t setroubleshoot --no-pager | tail\n'
                          '# sealert gives a plain-English explanation when setroubleshoot is installed:\n'
                          'sudo dnf install -y setroubleshoot-server 2>/dev/null\n'
                          'sudo sealert -a /var/log/audit/audit.log 2>/dev/null | head -30')]},
               {'h': '7. Key-based SSH authentication',
                'p': '',
                'code': [('Generate a key and install it',
                          "ssh-keygen -t ed25519 -C 'shea@servera' -f ~/.ssh/id_ed25519 -N ''\n"
                          'ls -l ~/.ssh/\n'
                          'ssh-copy-id shea@serverb\n'
                          "ssh shea@serverb 'echo key auth works; hostname'"),
                         ('Confirm the permissions SSH insists on',
                          "ssh -o BatchMode=yes -o PasswordAuthentication=no shea@serverb 'echo key auth "
                          "works; hostname'\n"
                          "ssh shea@serverb 'ls -ld ~/.ssh; ls -l ~/.ssh/authorized_keys'\n"
                          '# 700/600 are recommended; correct ownership and no unsafe write permissions '
                          'matter.'),
                         ('Optionally disable password authentication',
                          'ssh -t shea@serverb\n'
                          '# In the remote shell, first keep this session open while testing another.\n'
                          "sudo tee /etc/ssh/sshd_config.d/00-rhcsa-auth.conf >/dev/null <<'EOF'\n"
                          'PasswordAuthentication no\n'
                          'EOF\n'
                          'sudo sshd -t\n'
                          "sudo sshd -T | grep '^passwordauthentication'\n"
                          '# If output still says yes, inspect earlier settings and Match blocks before '
                          'proceeding.\n'
                          'sudo systemctl reload sshd\n'
                          'exit\n'
                          "ssh -o BatchMode=yes -o PasswordAuthentication=no shea@serverb 'hostname'")]},
               {'h': '8. Default permissions with umask',
                'p': '',
                'code': [('See the effect',
                          'umask\n'
                          'touch ~/umask-default.txt\n'
                          'mkdir ~/umask-default-dir\n'
                          'ls -l ~/umask-default.txt\n'
                          'ls -ld ~/umask-default-dir'),
                         ('Change it for this shell, then persistently',
                          'umask 0077\n'
                          'touch ~/umask-private.txt\n'
                          'ls -l ~/umask-private.txt\n'
                          "echo 'umask 0077' >> ~/.bashrc"),
                         ('System-wide default',
                          "sudo tee /etc/profile.d/rhcsa-umask.sh >/dev/null <<'EOF'\n"
                          'umask 0077\n'
                          'EOF\n'
                          'su - shea -c \'umask; d=$(mktemp -d); touch "$d/file"; mkdir "$d/subdir"; ls -ld '
                          '"$d/file" "$d/subdir"; rm -r "$d"\'\n'
                          '# This profile controls login shells; services have separate UMask settings.')],
                'note': 'umask clears permission bits from the requested mode; it is not arithmetic '
                        'subtraction. 0077 gives 600/700; 0033 gives a normal new file 644. Use new files '
                        'when testing.'}],
  'verify': ['getenforce   # must say Enforcing',
             "grep '^SELINUX=' /etc/selinux/config",
             'ls -Zd /srv/mysite | grep httpd_sys_content_t',
             'sudo semanage port -l | grep -w http_port_t | grep 8888',
             'getsebool httpd_enable_homedirs',
             'After a normal reboot, re-run the checks above'],
  'breakfix': {'break': 'sudo chcon -t user_home_t /srv/mysite/index.html && sudo restorecon -Rv /srv/mysite',
               'symptom': 'You set a context with chcon, then restorecon immediately reverted it - because '
                          'policy disagreed with you.',
               'fix': 'The existing policy rule is already correct: sudo restorecon -Rv /srv/mysite. Use '
                      'semanage fcontext -m only when an existing rule itself needs changing.',
               'lesson': 'chcon changes the current label. restorecon and relabel apply policy; a reboot '
                         'alone does not always undo chcon.'}},
 {'n': 11,
  'id': 'week-11',
  'title': 'Shell Scripting',
  'goal': 'Write the small, practical scripts the exam asks for: conditionals, loops, arguments, and command '
          'substitution. Nothing exotic is tested.',
  'time': '3-4 hours',
  'prereqs': ['Weeks 1-10 complete',
              'Use a VM console for network, boot and storage changes. Commands are guest commands, not '
              'macOS commands.',
              'Examples use shea; substitute your configured account consistently. Follow the weeks in '
              'order; shell variables must be recreated after reboot.'],
  'sections': [{'h': '1. The skeleton',
                'p': 'Every script starts the same way.',
                'code': [('Create, make executable, run',
                          'mkdir -p ~/bin && cd ~/bin\n'
                          "cat > hello.sh <<'EOF'\n"
                          '#!/bin/bash\n'
                          'echo "Hello from $(hostname), running as $(whoami)"\n'
                          'EOF\n'
                          'chmod +x hello.sh\n'
                          './hello.sh')]},
               {'h': '2. Conditionals',
                'p': 'if with test or [ ]. Know the file, string, and numeric operators.',
                'code': [('Branch on a condition',
                          "cat > check.sh <<'EOF'\n"
                          '#!/bin/bash\n'
                          'TARGET="/etc/passwd"\n'
                          '\n'
                          'if [ -f "$TARGET" ]; then\n'
                          '    echo "$TARGET is a regular file"\n'
                          'elif [ -d "$TARGET" ]; then\n'
                          '    echo "$TARGET is a directory"\n'
                          'else\n'
                          '    echo "$TARGET does not exist"\n'
                          'fi\n'
                          'EOF\n'
                          'chmod +x check.sh && ./check.sh'),
                         ('The operators worth memorising',
                          '# Files:    -f (file)  -d (directory)  -e (exists)  -r -w -x '
                          '(readable/writable/executable)\n'
                          '# Strings:  = (equal)  != (not equal)  -z (empty)  -n (not empty)\n'
                          '# Numbers:  -eq -ne -lt -le -gt -ge\n'
                          'man test | head -40'),
                         ('Numeric and string comparison side by side',
                          "cat > compare.sh <<'EOF'\n"
                          '#!/bin/bash\n'
                          'COUNT=$(who | wc -l)\n'
                          '\n'
                          'if [ "$COUNT" -gt 1 ]; then\n'
                          '    echo "$COUNT users are logged in"\n'
                          'else\n'
                          '    echo "Zero or one session"\n'
                          'fi\n'
                          '\n'
                          'if [ "$(whoami)" = "root" ]; then\n'
                          '    echo "Running as root"\n'
                          'else\n'
                          '    echo "Not root"\n'
                          'fi\n'
                          'EOF\n'
                          'chmod +x compare.sh && ./compare.sh')]},
               {'h': '3. Loops',
                'p': 'for over a list, a glob, and command output; while for reading input.',
                'code': [('for, three ways',
                          "cat > loops.sh <<'EOF'\n"
                          '#!/bin/bash\n'
                          '\n'
                          'for SERVICE in sshd chronyd firewalld; do\n'
                          '    printf \'%-12s %s\\n\' "$SERVICE" "$(systemctl is-active $SERVICE)"\n'
                          'done\n'
                          '\n'
                          'for FILE in /etc/*.conf; do\n'
                          '    [ -f "$FILE" ] && [ -r "$FILE" ] || continue\n'
                          '    echo "$(basename -- "$FILE") has $(wc -l < "$FILE") lines"\n'
                          'done\n'
                          '\n'
                          "for USERNAME in $(getent passwd | awk -F: '$3 >= 1000 && $3 < 65534 {print $1}'); "
                          'do\n'
                          '    echo "Regular user: $USERNAME"\n'
                          'done\n'
                          'EOF\n'
                          'chmod +x loops.sh && ./loops.sh'),
                         ('while, reading a file line by line',
                          "cat > readfile.sh <<'EOF'\n"
                          '#!/bin/bash\n'
                          'while IFS= read -r LINE; do\n'
                          '    case "$LINE" in\n'
                          '        \\#*|"") continue ;;\n'
                          '    esac\n'
                          '    echo "config line: $LINE"\n'
                          'done < /etc/chrony.conf\n'
                          'EOF\n'
                          'chmod +x readfile.sh && ./readfile.sh | head')]},
               {'h': '4. Script arguments',
                'p': 'Explicitly in the objectives. Handle them, and fail cleanly when they are missing.',
                'code': [('Positional parameters with validation',
                          "cat > args.sh <<'EOF'\n"
                          '#!/bin/bash\n'
                          'if (( $# != 2 )); then\n'
                          '    printf \'Usage: %s <name> <count 1..1000>\\n\' "$(basename -- "$0")" >&2\n'
                          '    exit 1\n'
                          'fi\n'
                          'name=$1\n'
                          'count=$2\n'
                          'if [[ ! $count =~ ^[1-9][0-9]{0,3}$ ]]; then\n'
                          "    printf 'count moet een positief geheel getal zijn\\n' >&2\n"
                          '    exit 1\n'
                          'fi\n'
                          'if (( count > 1000 )); then\n'
                          "    printf 'count mag maximaal 1000 zijn\\n' >&2\n"
                          '    exit 1\n'
                          'fi\n'
                          'for (( i=1; i<=count; i++ )); do\n'
                          '    printf \'%d. Hello, %s\\n\' "$i" "$name"\n'
                          'done\n'
                          'exit 0\n'
                          'EOF\n'
                          'chmod +x args.sh\n'
                          "./args.sh 'Siebe Test' 2\n"
                          './args.sh Siebe wrong\n'
                          'echo "invalid input exit: $?"')]},
               {'h': '5. Using command output',
                'p': 'Command substitution with $( ). Backticks work too but nest badly - use the modern '
                     'form.',
                'code': [('Capture and act on output',
                          "cat > report.sh <<'EOF'\n"
                          '#!/bin/bash\n'
                          '\n'
                          'HOST=$(hostname -s)\n'
                          "WHEN=$(date '+%Y-%m-%d %H:%M')\n"
                          "USED=$(df -h / | awk 'NR==2 {print $5}')\n"
                          "LOAD=$(LC_ALL=C uptime | awk -F'load average:' '{print $2}')\n"
                          "USERS=$(getent passwd | awk -F: '$3 >= 1000 && $3 < 65534' | wc -l)\n"
                          '\n'
                          'echo "===== $HOST at $WHEN ====="\n'
                          'echo "Root filesystem used: $USED"\n'
                          'echo "Load average:        $LOAD"\n'
                          'echo "Regular users:       $USERS"\n'
                          '\n'
                          'if [ "${USED%\\%}" -gt 80 ]; then\n'
                          '    echo "WARNING: root filesystem above 80 percent"\n'
                          '    exit 2\n'
                          'fi\n'
                          '\n'
                          'exit 0\n'
                          'EOF\n'
                          'chmod +x report.sh && ./report.sh\n'
                          'echo "exit status: $?"')]},
               {'h': '6. Exit statuses',
                'p': 'Zero means success. Anything else means failure. Your scripts should follow that '
                     'convention.',
                'code': [('Check and return meaningfully',
                          "grep -q '^root:' /etc/passwd\n"
                          'echo "grep found it, status: $?"\n'
                          "grep -q '^nosuchuser:' /etc/passwd\n"
                          'echo "grep did not find it, status: $?"\n'
                          '\n'
                          "systemctl is-active --quiet sshd && echo 'sshd is up' || echo 'sshd is down'")]},
               {'h': '7. Final objective sweep',
                'p': 'Before Week 12, go back to the source.',
                'code': [('Re-read the official list and be honest',
                          '# Open the EX200 objectives and read every bullet.\n'
                          '# For each one, ask: could I do this right now, on a fresh machine, with no '
                          'notes?\n'
                          "# Write down every 'no' or 'probably'. That list drives Week 12.")]}],
  'verify': ['cd ~/bin && for s in *.sh; do bash -n "$s" && echo "$s: syntax ok"; done',
             './args.sh shea 2',
             './report.sh; echo "exit: $?"'],
  'breakfix': {'break': 'cp ~/bin/args.sh ~/bin/args.sh.backup\n'
                        "sed -i 's/)); then/)) then/' ~/bin/args.sh\n"
                        'bash -n ~/bin/args.sh',
               'symptom': 'The script fails with a syntax error near an unexpected token.',
               'fix': 'cp ~/bin/args.sh.backup ~/bin/args.sh; bash -n ~/bin/args.sh',
               'lesson': "'bash -n script.sh' parses without executing and is the fastest way to find a "
                         'syntax error. Also note the quoting: "$#" and "$1" in quotes protects you from '
                         'empty or space-containing values - a habit worth having before the exam.'}},
 {'n': 12,
  'id': 'week-12',
  'title': 'Mock Exam, Remediation, and Exam Day',
  'goal': 'Find out whether you are actually ready, fix what the mock exposes, and walk into the real exam '
          'having already sat it once.',
  'time': '6-8 hours across the week',
  'prereqs': ['Weeks 1-11 complete',
              'Both lab machines rolled back to a clean snapshot',
              'Use a VM console for network, boot and storage changes. Commands are guest commands, not '
              'macOS commands.',
              'Examples use shea; substitute your configured account consistently. Follow the weeks in '
              'order; shell variables must be recreated after reboot.'],
  'sections': [{'h': '1. Set the conditions honestly',
                'p': 'This is a self-designed practice exam, not an official replica or guarantee of '
                     'complete coverage.',
                'code': [('Before you start the timer',
                          "# 1. Roll both machines back to the 'clean' snapshot\n"
                          '# 2. Close every browser tab except a clock\n'
                          '# 3. No notes, no lab guides, no search engine\n'
                          '# 4. Allowed: man, info, /usr/share/doc - nothing else\n'
                          '# 5. Set a timer. Do not pause it for any reason.')]},
               {'h': '2. A self-built mock',
                'p': 'Work these from a cold machine, in any order, in under three hours. They are written '
                     'the way exam tasks are written - the outcome is specified, the method is not.',
                'code': [('Users, groups, and access',
                          "# 1. Create user 'auditor' with UID 3200 and a shell of /bin/bash.\n"
                          "# 2. Create group 'audit' with GID 3300; make auditor a supplementary member.\n"
                          "# 3. auditor's password must expire every 30 days with a 5-day warning.\n"
                          "# 4. Members of 'audit' may run any command with sudo."),
                         ('Storage',
                          '# 5. Create a 1 GiB partition on the spare disk, format it XFS,\n'
                          '#    and mount it permanently at /data/reports using its UUID.\n'
                          "# 6. Create a volume group 'appvg' and a 400 MiB logical volume 'applv'.\n"
                          '# 7. Format applv ext4, mount it at /data/app, then grow it to 700 MiB\n'
                          '#    without losing its contents.\n'
                          '# 8. Add 512 MiB of swap that activates automatically at boot.'),
                         ('Services, networking, and security',
                          '# 9.  Install and enable httpd. Serve content from /srv/reports\n'
                          '#     instead of the default location. It must work with SELinux enforcing.\n'
                          '# 10. httpd must listen on port 8404 and be reachable through the firewall.\n'
                          '# 11. Set a static IPv4 address that survives a reboot.\n'
                          '# 12. Configure key-based SSH from servera to serverb for user shea.'),
                         ('Automation and recovery',
                          '# 13. Write /usr/local/bin/diskcheck.sh that takes a mount point as $1,\n'
                          '#     prints its usage percentage, and exits 2 if usage exceeds 80 percent.\n'
                          '# 14. Run that script every 15 minutes via a systemd timer.\n'
                          '# 15. Make the journal persistent across reboots.\n'
                          '# 16. Set the system to boot into multi-user.target by default.'),
                         ('Then, and only then',
                          'sudo reboot\n'
                          '# Our practice rubric counts only verified persistent outcomes; it is not the '
                          'official exam scoring scheme.')]},
               {'h': '3. Score and remediate',
                'p': 'The score matters far less than the list it produces.',
                'code': [('Turn failures into a study plan',
                          '# For every task you missed or had to look up:\n'
                          '#   - Which objective domain does it belong to?\n'
                          '#   - Rebuild that lab from scratch, untimed, from the Week guide.\n'
                          '#   - Then do it again from memory, timed.\n'
                          '# Anything in the security or storage domains gets double attention -\n'
                          '# they contain dependencies that are useful to troubleshoot; official weights are '
                          'not asserted.')]},
               {'h': '4. The second mock',
                'p': 'Later in the week, on a clean snapshot again.',
                'code': [('Use a source you have not seen',
                          '# Sit a timed, hands-on mock you did not write yourself, so you\n'
                          '# cannot unconsciously remember the answers:\n'
                          '#   https://linuxcert.guru/\n'
                          '# Same rules: clean machines, timer running, man pages only, reboot at the '
                          'end.')]},
               {'h': '5. Book it',
                'p': '',
                'code': [('While the second mock is still fresh',
                          '# Book EX200 within two weeks of a clean mock pass:\n'
                          '#   '
                          'https://www.redhat.com/en/services/training/ex200-red-hat-certified-system-administrator-rhcsa-exam\n'
                          '# Check your ID matches your Red Hat account name exactly.\n'
                          '# Test your machine against the proctoring requirements the day before.')]},
               {'h': '6. Additional objective checks',
                'p': 'Complete these on another clean snapshot; use the earlier labs for independent '
                     'verification, not during the timed attempt.',
                'code': [('Additional tasks',
                          '# Configure a real RPM repository and install/remove a Flatpak from a user '
                          'remote.\n'
                          '# Configure and verify IPv6 connectivity to serverb.\n'
                          '# Configure chrony and prove a selected synchronized source.\n'
                          '# Mount a scoped NFS export with autofs and prove mount-on-access.\n'
                          '# Mount a filesystem by LABEL and delete a disposable unused GPT partition.\n'
                          '# Compress/decompress standalone files and use info/editor documentation.')]}],
  'verify': ['Every mock task re-checked AFTER a reboot',
             'A written list of every objective you had to look up',
             'A second timed mock passed cleanly',
             'Exam booked, ID checked, environment tested'],
  'breakfix': {'break': 'Skip the reboot at the end of the mock.',
               'symptom': 'You score yourself 15/16 and feel ready. On the real exam you score far lower, '
                          'because several configurations never persisted.',
               'fix': 'Always reboot before scoring. Always.',
               'lesson': 'This is the whole course in one sentence: the exam grades the state of the machine '
                         'after a reboot, not the commands you typed. If you have internalised that by now, '
                         'you are in good shape.'}}]

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lab {n}: {title} — RHCSA Course</title>
<meta name="description" content="{goal_attr}">
<meta name="color-scheme" content="light dark">
<link rel="icon" href="../assets/img/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="../assets/css/style.css">
<style>
  .lab-wrap {{ max-width: 860px; margin: 0 auto; padding: 30px 22px 90px; }}
  .lab-back {{ font-size: 13px; color: var(--text-3); display: inline-block; margin-bottom: 18px; }}
  .lab-h {{ margin-bottom: 22px; }}
  .lab-h h1 {{ font-size: 27px; letter-spacing: -.02em; margin-bottom: 6px; }}
  .lab-meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 0; }}
  .step {{ margin: 30px 0 0; }}
  .step h2 {{ font-size: 17px; margin-bottom: 6px; }}
  .step > p {{ color: var(--text-2); font-size: 14px; max-width: 72ch; }}
  .cmd {{ margin: 14px 0; border: 1px solid var(--border); border-radius: var(--radius);
          overflow: hidden; background: var(--bg-elev); box-shadow: var(--shadow); }}
  .cmd__t {{ font-size: 12.5px; font-weight: 600; color: var(--text-2);
             padding: 9px 14px; background: var(--bg-sunken); border-bottom: 1px solid var(--border); }}
  .cmd pre {{ margin: 0; padding: 14px; overflow-x: auto; font-family: var(--mono);
              font-size: 12.8px; line-height: 1.65; color: var(--text); }}
  .lab-nav {{ display: flex; justify-content: space-between; gap: 12px;
              margin-top: 44px; padding-top: 20px; border-top: 1px solid var(--border); }}
  ol.verify {{ font-family: var(--mono); font-size: 12.8px; }}
  ol.verify li {{ margin-bottom: 6px; color: var(--text-2); }}
  @media print {{ .lab-back, .lab-nav, .header {{ display: none !important; }} }}
</style>
<script>
  (function () {{
    try {{
      var t = localStorage.getItem("rhcsa.theme.v1");
      if (t === "light" || t === "dark") document.documentElement.setAttribute("data-theme", t);
    }} catch (e) {{}}
  }})();
</script>
</head>
<body>
<header class="header">
  <a class="brand" href="../index.html">
    <span class="brand__mark">ST</span>
    <span class="brand__text">
      <span class="brand__title">RHCSA Course</span>
      <span class="brand__sub">From Learn Linux For Work · Lab {n} of 12</span>
    </span>
  </a>
  <span class="header__spacer"></span>
  <button class="btn btn--icon" data-theme-toggle title="Toggle dark / light mode" aria-label="Toggle dark or light mode">
    <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4.5"/><line x1="12" y1="1.5" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="22.5"/><line x1="4.2" y1="4.2" x2="6" y2="6"/><line x1="18" y1="18" x2="19.8" y2="19.8"/><line x1="1.5" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="22.5" y2="12"/><line x1="4.2" y1="19.8" x2="6" y2="18"/><line x1="18" y1="6" x2="19.8" y2="4.2"/></svg>
    <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
  </button>
</header>

<div class="lab-wrap">
  <a class="lab-back" href="../index.html#{id}">&larr; Back to Week {n}</a>

  <div class="lab-h">
    <div class="section__eyebrow">Lab guide {n}</div>
    <h1>{title}</h1>
    <p style="color:var(--text-2);font-size:14.5px;max-width:74ch">{goal}</p>
    <div class="lab-meta">
      <span class="chip chip--accent">{time}</span>
      {prereq_chips}
    </div>
  </div>

  <div class="callout"><div class="callout__title">Before you start</div>
    <ul>{prereqs}<li>Take a snapshot of both machines. You will break things on purpose.</li></ul>
  </div>

  {sections}

  <div class="step">
    <h2>Verify your work</h2>
    <p>Run these before you consider the lab finished.</p>
    <ol class="verify">{verify}</ol>
  </div>

  <div class="callout callout--warn">
    <div class="callout__title">Break it, then fix it</div>
    <p><strong>Break:</strong></p>
    <div class="cmd"><pre>{bf_break}</pre></div>
    <p><strong>What you'll see:</strong> {bf_symptom}</p>
    <p><strong>Fix:</strong></p>
    <div class="cmd"><pre>{bf_fix}</pre></div>
    <p><strong>Why it matters:</strong> {bf_lesson}</p>
  </div>

  <div class="callout callout--danger">
    <div class="callout__title">Now reboot</div>
    <p>Run <code>sudo reboot</code>, then re-run every command in the verify list above. Check every persistent configuration after a normal boot. This is our practice validation,
    not an assertion about official exam scoring. Fix it now, while you can still
    see what you did.</p>
  </div>

  <div class="lab-nav">
    <span>{prev}</span>
    <span>{next}</span>
  </div>
</div>

<footer class="footer">
  <div class="footer__inner">
    <div><strong>RHCSA Course</strong> — rhcsa.learnlinuxforwork.com<br>
    Written by Shea. Licensed under the
    <a href="https://learnlinuxforwork.com/license" target="_blank" rel="noopener noreferrer">GNU AGPL v3.0 or later</a>.</div>
    <div class="footer__links">
      <a href="../index.html">Course home</a>
      <a href="https://www.learnlinuxforwork.com" target="_blank" rel="noopener noreferrer">Linux training</a>
      <a href="https://linuxcert.guru/" target="_blank" rel="noopener noreferrer">RHCSA mocks</a>
    </div>
  </div>
</footer>

<script src="../assets/js/lab.js"></script>
</body>
</html>
"""


def e(s):
    return html.escape(str(s), quote=False)


def build():
    outdir = os.path.join(HERE, "lab")
    os.makedirs(outdir, exist_ok=True)
    for i, lab in enumerate(LABS):
        secs = []
        for s in lab["sections"]:
            blocks = ""
            for title, code in s["code"]:
                blocks += ('<div class="cmd"><div class="cmd__t">' + e(title) +
                           "</div><pre>" + e(code) + "</pre></div>")
            note = ""
            if s.get("note"):
                note = ('<div class="callout"><div class="callout__title">Worth knowing</div><p>' +
                        s["note"] + "</p></div>")
            secs.append('<div class="step"><h2>' + e(s["h"]) + "</h2>" +
                        ("<p>" + e(s["p"]) + "</p>" if s.get("p") else "") +
                        blocks + note + "</div>")

        prev_l = ('<a class="btn" href="' + LABS[i - 1]["id"] + '.html">&larr; Lab ' +
                  str(LABS[i - 1]["n"]) + "</a>") if i > 0 else ""
        next_l = ('<a class="btn btn--primary" href="' + LABS[i + 1]["id"] + '.html">Lab ' +
                  str(LABS[i + 1]["n"]) + " &rarr;</a>") if i < len(LABS) - 1 else \
                 '<a class="btn btn--primary" href="../index.html#exam-day">Exam day &rarr;</a>'

        page = PAGE.format(
            n=lab["n"], id=lab["id"], title=e(lab["title"]),
            goal=e(lab["goal"]), goal_attr=html.escape(lab["goal"], quote=True),
            time=e(lab["time"]),
            prereq_chips="".join('<span class="chip">' + e(p) + "</span>" for p in lab["prereqs"][:1]),
            prereqs="".join("<li>" + e(p) + "</li>" for p in lab["prereqs"]),
            sections="".join(secs),
            verify="".join("<li>" + e(v) + "</li>" for v in lab["verify"]),
            bf_break=e(lab["breakfix"]["break"]),
            bf_symptom=e(lab["breakfix"]["symptom"]),
            bf_fix=e(lab["breakfix"]["fix"]),
            bf_lesson=e(lab["breakfix"]["lesson"]),
            prev=prev_l, next=next_l,
        )
        io.open(os.path.join(outdir, lab["id"] + ".html"), "w", encoding="utf-8").write(page)
        print("wrote lab/%s.html  (%d sections)" % (lab["id"], len(lab["sections"])))

    print("\n%d lab guides generated." % len(LABS))


if __name__ == "__main__":
    build()
