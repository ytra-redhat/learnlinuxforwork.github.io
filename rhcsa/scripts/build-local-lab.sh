#!/usr/bin/env bash
#
# build-local-lab.sh — create the two-machine RHCSA lab
#                      using VirtualBox, Workstation or Fusion on Apple Silicon.
#
# RHCSA Course — rhcsa.learnlinuxforwork.com
# Copyright (C) 2026 Shea's Tech. Licensed under the GNU AGPL v3.0 or later.
#
# WHAT IT DOES
#   1. macOS: creates bundles in $HOME/Virtual Machines.localized
#      and finds Rocky aarch64 DVD ISOs in $HOME/Downloads/Images
#   2. Creates two VMs — servera (primary) and serverb (secondary)
#   3. Gives servera a second 10 GB disk for the Week 8 and 9 storage labs
#   4. Puts both on a private host-only network plus NAT for package installs
#   5. macOS/Fusion: installs Rocky 10 aarch64 automatically (see FUSION.md)
#      Other providers: boots the original interactive installer
#
# USAGE
#   ./build-local-lab.sh                    # VirtualBox, auto-detect ISO
#   ./build-local-lab.sh --provider vmware  # VMware Fusion on macOS / Workstation on Linux
#   ./build-local-lab.sh --iso "$HOME/Downloads/Images/Rocky-10.2-aarch64-dvd1.iso"
#   ./build-local-lab.sh --destroy          # remove the VMs and start over
#
# WHERE TO GET THE ISO  (download it yourself, choose aarch64; put it in $HOME/Downloads/Images)
#   RHEL 10   https://developers.redhat.com/products/rhel/download
#   Rocky 10  https://rockylinux.org/download
#
set -euo pipefail

# macOS uses the native Fusion/Kickstart workflow. Other hosts retain the
# original provider workflow below. No Podman or Linux loop devices are used.
if [ "$(uname -s)" = Darwin ]; then
  command -v python3 >/dev/null 2>&1 || {
    printf '%s\n' 'Python 3 is required: brew install python' >&2
    exit 1
  }
  SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
  exec python3 "$SCRIPT_DIR/fusion-local-lab.py" "$@"
fi

LAB_DIR="$HOME/rhcsa-labs"
ISO_DIR="$HOME/Downloads/Images"
PROVIDER="virtualbox"
DESTROY=0
ISO=""
NET="rhcsalab"
NET_CIDR="192.168.56"
VM_A="servera"; VM_B="serverb"
RAM_A=4096; CPU_A=2; DISK_A=20480; DISK_EXTRA=10240
RAM_B=2048; CPU_B=1; DISK_B=20480

c()  { printf '\033[1;31m%s\033[0m\n' "$*"; }
ok() { printf '  \033[0;32mok\033[0m  %s\n' "$*"; }
die(){ printf '\n\033[1;31mSTOPPED:\033[0m %s\n' "$*"; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --provider) [ "$#" -ge 2 ] && [ -n "$2" ] || die "--provider requires a value"; PROVIDER="$2"; shift 2 ;;
    --iso)      [ "$#" -ge 2 ] && [ -n "$2" ] || die "--iso requires a value"; ISO="$2"; shift 2 ;;
    --destroy)  DESTROY=1; shift ;;
    -h|--help)  sed -n '2,30p' "$0"; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

# Linux hypervisors in this builder virtualize x86_64 guests. Fusion has
# already delegated above; never apply the Apple Silicon ISO rule here.
[ "$(uname -m)" = x86_64 ] || die "This Linux builder supports x86_64 hosts only. Use Fusion on Apple Silicon."
case "$PROVIDER" in virtualbox|vbox|vmware|ws) ;; *) die "Unknown provider: $PROVIDER" ;; esac
if [ "$DESTROY" = 1 ]; then
  case "$PROVIDER" in
    virtualbox|vbox)
      command -v VBoxManage >/dev/null || die "VBoxManage is missing"
      for vm in "$VM_A" "$VM_B"; do
        VBoxManage showvminfo "$vm" >/dev/null 2>&1 || continue
        VBoxManage getextradata "$vm" RHCSAOwner | grep -q 'Value: learnlinuxforwork' || die "Refusing to delete an unowned VM: $vm"
        VBoxManage showvminfo "$vm" --machinereadable | grep -q '^VMState="poweroff"$' || die "Power off $vm first"
        VBoxManage unregistervm "$vm" --delete
      done ;;
    vmware|ws)
      command -v vmrun >/dev/null || die "vmrun is missing"
      for vm in "$VM_A" "$VM_B"; do
        directory="$LAB_DIR/vmware/$vm"
        [ -d "$directory" ] || continue
        [ -f "$directory/.rhcsa-owned" ] || die "Refusing to delete unowned directory: $directory"
        if vmrun -T ws list | grep -Fxq "$directory/$vm.vmx"; then die "Power off $vm first"; fi
        find "$directory" -name '*.lck' -print -quit | grep -q . && die "VM lock exists: $directory"
        rm -r -- "$directory"
      done ;;
  esac
  exit 0
fi

# ---------------------------------------------------------------- lab dir --
if [ ! -d "$LAB_DIR" ]; then
  c "Creating $LAB_DIR"
  mkdir -p "$LAB_DIR" || die "Could not create $LAB_DIR"
  ok "$LAB_DIR created by $(id -un):$(id -gn)"
fi

if [ -z "$ISO" ]; then
  for DIR in "$ISO_DIR" "$LAB_DIR"; do
    [ -d "$DIR" ] || continue
    ISO=$(find "$DIR" -maxdepth 1 -type f -iname '*x86_64*.iso' ! -iname '*aarch64*' | head -1)
    [ -n "$ISO" ] && break
  done
fi

if [ -z "$ISO" ] || [ ! -f "$ISO" ]; then
  cat <<EOF

No x86_64 ISO found in $ISO_DIR or $LAB_DIR (or --iso does not exist).

Download one of these, save the x86_64 version into $ISO_DIR, then run this script again:

  RHEL 10   https://developers.redhat.com/products/rhel/download
            (free Developer Subscription — covers 16 systems)
  Rocky 10  https://rockylinux.org/download

Download the aarch64 Rocky DVD ISO with:

  mkdir -p "$ISO_DIR"
  cd "$ISO_DIR"
  curl -LO https://download.rockylinux.org/pub/rocky/10/isos/x86_64/Rocky-10-latest-x86_64-dvd.iso

EOF
  exit 1
fi
case "$(basename "$ISO" | tr '[:upper:]' '[:lower:]')" in
  *aarch64*) die "Linux x86_64 requires an x86_64 ISO: $ISO" ;;
  *x86_64*.iso) ;;
  *) die "Choose an x86_64 ISO: $ISO" ;;
esac
# VMX files need an absolute ISO path, including when --iso is relative.
ISO="$(cd "$(dirname "$ISO")" && pwd)/$(basename "$ISO")"
ok "Using ISO: $ISO"

# ============================================================== VIRTUALBOX ==
build_virtualbox() {
  command -v VBoxManage >/dev/null || die "VBoxManage not found. Install VirtualBox: https://www.virtualbox.org/"

  if [ "${DESTROY:-0}" = "1" ]; then
    for vm in "$VM_A" "$VM_B"; do
      VBoxManage unregistervm "$vm" --delete 2>/dev/null && ok "removed $vm"
    done
    exit 0
  fi

  # private network for servera <-> serverb
  if ! VBoxManage list hostonlyifs | grep -q "$NET_CIDR"; then
    c "Creating host-only network"
    IF=$(VBoxManage hostonlyif create 2>/dev/null | sed -n "s/.*'\(.*\)'.*/\1/p")
    VBoxManage hostonlyif ipconfig "$IF" --ip "${NET_CIDR}.1" --netmask 255.255.255.0
    ok "host-only network $IF at ${NET_CIDR}.1"
  fi
  HOSTIF=$(VBoxManage list hostonlyifs | awk '/^Name:/{n=$2} /IPAddress:/{if($2 ~ /'"$NET_CIDR"'/) print n}' | head -1)

  make_vm() {
    local NAME=$1 RAM=$2 CPU=$3 DISK=$4 EXTRA=${5:-0} IP4=$6
    if VBoxManage showvminfo "$NAME" >/dev/null 2>&1; then
      VBoxManage getextradata "$NAME" RHCSAOwner | grep -q 'Value: learnlinuxforwork' || die "Existing VM is not owned by this builder: $NAME"
      ok "$NAME already exists — preserving it"; return
    fi
    c "Creating $NAME"
    VBoxManage createvm --name "$NAME" --ostype RedHat_64 --register >/dev/null
    VBoxManage setextradata "$NAME" RHCSAOwner learnlinuxforwork
    VBoxManage modifyvm "$NAME" --memory "$RAM" --cpus "$CPU" --firmware efi \
      --nic1 nat --nic2 hostonly --hostonlyadapter2 "$HOSTIF" \
      --graphicscontroller vmsvga --vram 16 --audio-driver none >/dev/null
    VBoxManage storagectl "$NAME" --name SATA --add sata --controller IntelAhci --portcount 4 >/dev/null
    local DIR; DIR=$(VBoxManage showvminfo "$NAME" --machinereadable | sed -n 's/^CfgFile="\(.*\)\/.*/\1/p')
    VBoxManage createmedium disk --filename "$DIR/${NAME}.vdi" --size "$DISK" --format VDI >/dev/null
    VBoxManage storageattach "$NAME" --storagectl SATA --port 0 --device 0 --type hdd \
      --medium "$DIR/${NAME}.vdi" >/dev/null
    if [ "$EXTRA" -gt 0 ]; then
      VBoxManage createmedium disk --filename "$DIR/${NAME}-extra.vdi" --size "$EXTRA" --format VDI >/dev/null
      VBoxManage storageattach "$NAME" --storagectl SATA --port 1 --device 0 --type hdd \
        --medium "$DIR/${NAME}-extra.vdi" >/dev/null
      ok "$NAME: added ${EXTRA}MB spare disk for the Week 8 and 9 storage labs"
    fi
    VBoxManage storageattach "$NAME" --storagectl SATA --port 3 --device 0 --type dvddrive --medium "$ISO" >/dev/null
    VBoxManage modifyvm "$NAME" --boot1 dvd --boot2 disk >/dev/null
    ok "$NAME created — ${RAM}MB RAM, ${CPU} vCPU, static IP to set: ${IP4}"
  }

  make_vm "$VM_A" "$RAM_A" "$CPU_A" "$DISK_A" "$DISK_EXTRA" "${NET_CIDR}.10"
  make_vm "$VM_B" "$RAM_B" "$CPU_B" "$DISK_B" 0            "${NET_CIDR}.11"

  c "Starting both VMs so you can run the installer"
  VBoxManage startvm "$VM_A" --type gui >/dev/null 2>&1 || true
  VBoxManage startvm "$VM_B" --type gui >/dev/null 2>&1 || true
}

# ================================================================= VMWARE ===
build_vmware() {
  command -v vmrun >/dev/null || die "vmrun not found. Install VMware Workstation Pro (free for personal use): https://www.vmware.com/products/desktop-hypervisor/workstation-and-fusion"
  mkdir -p "$LAB_DIR/vmware"

  write_vmx() {
    local NAME=$1 RAM=$2 CPU=$3 DISK_GB=$4 EXTRA_GB=${5:-0}
    local D="$LAB_DIR/vmware/$NAME"
    [ ! -e "$D" ] || die "Existing directory preserved: $D. Inspect it or explicitly --destroy owned VMs."
    command -v vmware-vdiskmanager >/dev/null || die "vmware-vdiskmanager is missing"
    mkdir -p "$D"
    touch "$D/.rhcsa-owned"
    vmware-vdiskmanager -c -s "${DISK_GB}GB" -a lsilogic -t 1 "$D/${NAME}.vmdk"
    if [ "$EXTRA_GB" -gt 0 ]; then vmware-vdiskmanager -c -s "${EXTRA_GB}GB" -a lsilogic -t 1 "$D/${NAME}-extra.vmdk"; fi
    cat > "$D/${NAME}.vmx" <<VMX
.encoding = "UTF-8"
config.version = "8"
virtualHW.version = "19"
displayName = "$NAME"
guestOS = "rhel9-64"
firmware = "efi"
memsize = "$RAM"
numvcpus = "$CPU"
scsi0.present = "TRUE"
scsi0.virtualDev = "lsilogic"
scsi0:0.present = "TRUE"
scsi0:0.fileName = "${NAME}.vmdk"
$( [ "$EXTRA_GB" -gt 0 ] && printf 'scsi0:1.present = "TRUE"\nscsi0:1.fileName = "%s-extra.vmdk"\n' "$NAME" )
ide1:0.present = "TRUE"
ide1:0.deviceType = "cdrom-image"
ide1:0.fileName = "$ISO"
ethernet0.present = "TRUE"
ethernet0.connectionType = "nat"
ethernet0.virtualDev = "e1000e"
ethernet1.present = "TRUE"
ethernet1.connectionType = "hostonly"
ethernet1.virtualDev = "e1000e"
usb.present = "TRUE"
sound.present = "FALSE"
VMX
    ok "$NAME.vmx written to $D"
    vmrun -T ws start "$D/${NAME}.vmx" nogui >/dev/null 2>&1 || \
      echo "     start it from the Workstation UI: $D/${NAME}.vmx"
  }

  write_vmx "$VM_A" "$RAM_A" "$CPU_A" 20 10
  write_vmx "$VM_B" "$RAM_B" "$CPU_B" 20 0
}

case "$PROVIDER" in
  virtualbox|vbox) build_virtualbox ;;
  vmware|ws)       build_vmware ;;
  *) die "Unknown provider '$PROVIDER'. Use: virtualbox | vmware" ;;
esac

cat <<EOF

$(c "Lab created. Now finish the install by hand:")

  1. In each VM's installer choose Server or Minimal Install — never Workstation.
  2. Set hostnames: $VM_A  and  $VM_B
  3. Create a user called 'shea' and give it administrator/sudo rights.
  4. After first boot, set the private addresses on the second adapter:

       servera:  sudo nmcli con mod <conn> ipv4.method manual \\
                   ipv4.addresses ${NET_CIDR}.10/24 && sudo nmcli con up <conn>
       serverb:  sudo nmcli con mod <conn> ipv4.method manual \\
                   ipv4.addresses ${NET_CIDR}.11/24 && sudo nmcli con up <conn>

  5. Add each host to the other's /etc/hosts, then confirm: ssh shea@serverb
  6. Snapshot BOTH machines and name the snapshot 'clean'.

Then start Lab Guide 1: https://rhcsa.learnlinuxforwork.com/lab/week-01.html
EOF
