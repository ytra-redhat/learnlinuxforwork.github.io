#!/usr/bin/env bash
#
# build-podman-lab.sh — a two-"machine" RHCSA practice lab in Rocky Linux
#                       containers, for when you have no spare RAM at all.
#
# RHCSA Course — rhcsa.learnlinuxforwork.com
# Copyright (C) 2026 Shea's Tech. Licensed under the GNU AGPL v3.0 or later.
#
# HONEST LIMITATIONS — read this first
#   Containers share the host kernel. That means these are a partial practice environment, not an equivalent exam system:
#
#     Works well    users and groups, permissions, ACLs, sudo, dnf/RPM, Flatpak
#                   basics, processes, scripting, text tools, limited context inspection, cron syntax, archives, SSH between the two
#     Does NOT work partitioning, LVM, filesystems, swap, fstab, the bootloader,
#                   boot targets, rd.break recovery, kernel tuning, real
#                   firewalld, NetworkManager
#
#   Use this to drill Weeks 1-4, 10 (partly), and 11 on a low-spec machine.
#   You still need real VMs for Weeks 5-9. There is no way around that, and
#   anyone who tells you otherwise has not sat the exam.
#
# USAGE
#   ./build-podman-lab.sh           # create servera + serverb containers
#   ./build-podman-lab.sh --shell   # drop into servera
#   ./build-podman-lab.sh --destroy
#
set -euo pipefail

NET="rhcsa-net"
A="servera"; B="serverb"
IMAGE="${RHCSA_IMAGE:-docker.io/rockylinux/rockylinux:10}"
USER_NAME="shea"
OWNER_LABEL="org.learnlinuxforwork.rhcsa"
owned() { [ "$(podman inspect --format '{{index .Config.Labels "org.learnlinuxforwork.rhcsa"}}' "$1")" = "true" ]; }

c()  { printf '\033[1;31m%s\033[0m\n' "$*"; }
ok() { printf '  \033[0;32mok\033[0m  %s\n' "$*"; }
die(){ printf '\n\033[1;31mSTOPPED:\033[0m %s\n' "$*"; exit 1; }

command -v podman >/dev/null || die "podman not installed.
  Fedora/RHEL/Rocky:  sudo dnf install -y podman
  Debian/Ubuntu:      sudo apt install -y podman
  macOS:              brew install podman && podman machine init && podman machine start"

case "${1:-}" in
  --destroy)
    for node in "$A" "$B"; do
      podman container exists "$node" || continue
      owned "$node" || die "Unowned container preserved: $node"
      podman rm -f "$node"
    done
    ok "owned containers removed"
    if podman network exists "$NET"; then
      [ "$(podman network inspect --format '{{index .Labels "org.learnlinuxforwork.rhcsa"}}' "$NET")" = true ] || die "Unowned network preserved: $NET"
      podman network rm "$NET"
    fi
    exit 0 ;;
  --shell)
    exec podman exec -it "$A" /bin/bash ;;
esac

c "Creating the lab network"
if podman network exists "$NET"; then
  [ "$(podman network inspect --format '{{index .Labels "org.learnlinuxforwork.rhcsa"}}' "$NET")" = true ] || die "Unowned network preserved: $NET"
else
  podman network create --label "$OWNER_LABEL=true" "$NET" >/dev/null
fi
ok "$NET"

c "Pulling $IMAGE"
podman pull "$IMAGE" >/dev/null || die "Could not pull $IMAGE"
ok "image ready"

make_node() {
  local NAME=$1
  if podman container exists "$NAME"; then
    owned "$NAME" || die "Unowned container preserved: $NAME"
    die "Owned container already exists: $NAME. Use --shell, or explicitly --destroy before rebuilding."
  fi
  c "Creating $NAME"
  # The image must contain init/systemd and the host must support its cgroups.
  # --systemd=always configures integration; health is checked after provisioning.
  podman run -d --name "$NAME" --hostname "$NAME" --network "$NET" \
    --label "$OWNER_LABEL=true" --systemd=always \
    "$IMAGE" /sbin/init >/dev/null || die "Could not start $NAME"

  # Give it the tools the early weeks need.
  podman exec "$NAME" bash -lc '
    set -euo pipefail
    dnf -y install --setopt=install_weak_deps=False \
      passwd sudo openssh-server openssh-clients procps-ng iproute \
      cronie tar gzip bzip2 findutils grep sed gawk vim-minimal \
      policycoreutils policycoreutils-python-utils man-db man-pages
    ssh-keygen -A >/dev/null 2>&1
    systemctl enable --now sshd crond
    systemctl is-active --quiet sshd crond
  '

  # Create the working user used throughout the course.
  podman exec "$NAME" bash -lc "
    set -euo pipefail
    useradd -m -s /bin/bash $USER_NAME
    echo '$USER_NAME:rhcsa' | chpasswd
    echo '$USER_NAME ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/$USER_NAME
    chmod 0440 /etc/sudoers.d/$USER_NAME
  "
  ok "$NAME up — user '$USER_NAME', password 'rhcsa'"
}

make_node "$A"
make_node "$B"

for node in "$A" "$B"; do
  podman exec "$node" systemctl is-active --quiet sshd crond || die "$node services are not ready"
done
c "Checking the two nodes can reach each other"
podman exec "$A" bash -lc "getent hosts $B >/dev/null && echo reachable" || die "Peer name resolution failed"

cat <<EOF

$(c "Container lab ready.")

  Enter servera:     podman exec -it $A /bin/bash
  Enter serverb:     podman exec -it $B /bin/bash
  As the course user: podman exec -it -u $USER_NAME $A /bin/bash
  Stop for now:      podman stop $A $B
  Start again:       podman start $A $B
  Remove entirely:   $0 --destroy

$(c "What to practise here")

  Week 1   shell, redirection, grep, links, permissions, archives
  Week 2   users, groups, password aging, sudo drop-in files
  Week 3   dnf, rpm queries, repository files
  Week 4   processes, signals, nice/renice, cron
  Week 10  umask and SSH keys; use a VM for actual SELinux-policy exercises
  Week 11  all of the shell scripting

$(c "What you still need real VMs for")

  Weeks 5-9: boot targets, rd.break recovery, the bootloader, partitioning,
  LVM, filesystems, swap, fstab, NFS, autofs, firewalld, NetworkManager.

  Build those with:   ./build-local-lab.sh
  Or in the cloud:    ./build-cloud-lab.sh gcp

  Or use the browser-based hands-on labs, which need no setup at all:
      https://www.learnlinuxforwork.com
      https://www.redhat.com/en/interactive-labs
EOF
