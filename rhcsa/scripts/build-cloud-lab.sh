#!/usr/bin/env bash
#
# build-cloud-lab.sh — stand the same two-machine RHCSA lab up in the cloud,
#                      for when your laptop can't spare the RAM.
#
# RHCSA Course — rhcsa.learnlinuxforwork.com
# Copyright (C) 2026 Shea's Tech. Licensed under the GNU AGPL v3.0 or later.
#
# SUPPORTED
#   gcp     Google Cloud Platform   https://console.cloud.google.com/
#   do      DigitalOcean            https://cloud.digitalocean.com/
#   aws     Amazon Web Services     https://console.aws.amazon.com/
#   vultr   Vultr                   https://my.vultr.com/
#
# USAGE
#   ./build-cloud-lab.sh gcp
#   ./build-cloud-lab.sh do
#   ./build-cloud-lab.sh aws
#   ./build-cloud-lab.sh vultr
#   ./build-cloud-lab.sh <provider> --destroy
#
# COST WARNING
#   These are billable. Use provider pricing calculators; no fixed monthly cost is promised. If you
#   leave them on. DESTROY THEM when you are not labbing:
#       ./build-cloud-lab.sh <provider> --destroy
#   Set a billing alert on day one. Every provider offers one, free.
#
set -Eeuo pipefail

VM_A=""; VM_B=""
LAB_TAG=""
SSH_KEY="${RHCSA_SSH_KEY:-$HOME/.ssh/id_ed25519.pub}"

c()  { printf '\033[1;31m%s\033[0m\n' "$*"; }
ok() { printf '  \033[0;32mok\033[0m  %s\n' "$*"; }
die(){ printf '\n\033[1;31mSTOPPED:\033[0m %s\n' "$*"; exit 1; }

PROVIDER="${1:-}"; shift || true
DESTROY=0
[ "${1:-}" = "--destroy" ] && DESTROY=1

command -v python3 >/dev/null || die "Python 3 is required"
case "$PROVIDER" in digitalocean) PROVIDER=do ;; gcp|do|aws|vultr) ;; *) die "Usage: $0 gcp|do|aws|vultr [--destroy]" ;; esac
[ "$#" -le 1 ] || die "Unexpected arguments"
[ "$#" -eq 0 ] || [ "$1" = --destroy ] || die "Unknown option: $1"
umask 077
STATE_DIR="${RHCSA_CLOUD_STATE:-$HOME/.local/state/rhcsa-cloud}/$PROVIDER"
[ ! -L "$STATE_DIR" ] || die "State directory may not be a symlink"
mkdir -p "$STATE_DIR"
chmod 700 "$STATE_DIR"
if [ "$DESTROY" = 1 ]; then
  [ -f "$STATE_DIR/token" ] || die "No owned lab state found; refusing name-based deletion"
else
  [ ! -f "$STATE_DIR/token" ] || die "Existing lab state preserved. Inspect it or use --destroy before another create."
  [ -f "$SSH_KEY" ] || die "Missing public SSH key: $SSH_KEY"
  [ -n "${RHCSA_SSH_CIDR:-}" ] || die "Set RHCSA_SSH_CIDR to your public IPv4/32 before creating cloud hosts"
  python3 -c 'import ipaddress,sys; n=ipaddress.ip_network(sys.argv[1],strict=True); assert n.version==4 and n.prefixlen==32' "$RHCSA_SSH_CIDR" || die "SSH CIDR must be one IPv4 /32"
  case "$PROVIDER" in
    gcp) command -v gcloud >/dev/null || die "gcloud missing" ;;
    aws) command -v aws >/dev/null || die "AWS CLI missing" ;;
    do) command -v doctl >/dev/null || die "doctl missing"; [ -n "${DO_KEY_ID:-}" ] || die "Set DO_KEY_ID to the registered ID matching your local SSH key" ;;
    vultr) command -v vultr-cli >/dev/null || die "vultr-cli missing"; [ -n "${VULTR_KEY_ID:-}" ] && [ -n "${VULTR_OS_ID:-}" ] && [ -n "${VULTR_FIREWALL_GROUP:-}" ] || die "Set VULTR_KEY_ID matching your SSH key, verified Rocky10 VULTR_OS_ID and preconfigured VULTR_FIREWALL_GROUP" ;;
  esac
  python3 -c 'import secrets; print(secrets.token_hex(6))' > "$STATE_DIR/token"
  case "$PROVIDER" in
    gcp) printf '%s\n' "${GCP_ZONE:-us-east1-b}" ;;
    aws) printf '%s\n' "${AWS_REGION:-us-east-1}" ;;
    do) printf '%s\n' "${DO_REGION:-nyc3}" ;;
    vultr) printf '%s\n' "${VULTR_REGION:-ewr}" ;;
  esac > "$STATE_DIR/location"
fi
TOKEN=$(cat "$STATE_DIR/token")
[[ "$TOKEN" =~ ^[a-f0-9]{12}$ ]] || die "Invalid ownership token"
LOCATION=$(cat "$STATE_DIR/location")
[[ "$LOCATION" =~ ^[a-z0-9-]+$ ]] || die "Invalid saved location"
LAB_TAG="rhcsa-$TOKEN"
VM_A="servera-$TOKEN"; VM_B="serverb-$TOKEN"
trap 'printf "Failed at line %s; owned-resource state preserved at %s. Inspect provider resources before retrying cleanup.\n" "$LINENO" "$STATE_DIR" >&2' ERR
json_id() {
  python3 -c 'import json,sys
x=json.load(sys.stdin)
def ids(o):
 if isinstance(o,dict):
  if "id" in o: yield str(o["id"])
  else:
   for v in o.values(): yield from ids(v)
 elif isinstance(o,list):
  for v in o: yield from ids(v)
a=list(ids(x)); assert len(a)==1, "Expected one returned resource ID"; print(a[0])'
}

# ==================================================================== GCP ===
gcp() {
  command -v gcloud >/dev/null || die "gcloud not installed.
Install the SDK: https://cloud.google.com/sdk/docs/install
Then:  gcloud init && gcloud auth login"

  local ZONE="$LOCATION"
  local REGION="${ZONE%-*}"
  local NETWORK="${LAB_TAG}-net"
  local SUBNET="${LAB_TAG}-subnet"
  local TYPE="${GCP_TYPE:-e2-medium}"
  # Rocky Linux 10 is published in the rocky-linux-cloud project.
  local IMAGE_FAMILY="rocky-linux-10"
  local IMAGE_PROJECT="rocky-linux-cloud"

  if [ "$DESTROY" = "1" ]; then
    for node in "$VM_A" "$VM_B"; do
      if [ -f "$STATE_DIR/$node" ]; then
        gcloud compute instances delete "$node" --zone "$ZONE" --quiet
        rm "$STATE_DIR/$node"
      fi
    done
    for kind in internal ssh; do
      if [ -f "$STATE_DIR/firewall-$kind" ]; then
        gcloud compute firewall-rules delete "${LAB_TAG}-$kind" --quiet
        rm "$STATE_DIR/firewall-$kind"
      fi
    done
    if [ -f "$STATE_DIR/subnet" ]; then gcloud compute networks subnets delete "$SUBNET" --region "$REGION" --quiet; rm "$STATE_DIR/subnet"; fi
    if [ -f "$STATE_DIR/network" ]; then gcloud compute networks delete "$NETWORK" --quiet; rm "$STATE_DIR/network"; fi
    return
  fi

  gcloud compute networks create "$NETWORK" --subnet-mode custom
  touch "$STATE_DIR/network"
  gcloud compute networks subnets create "$SUBNET" --network "$NETWORK" --region "$REGION" --range 192.168.56.0/24
  touch "$STATE_DIR/subnet"
  gcloud compute firewall-rules create "${LAB_TAG}-ssh" --network "$NETWORK" --allow tcp:22 --source-ranges "$RHCSA_SSH_CIDR" --target-tags "$LAB_TAG"
  touch "$STATE_DIR/firewall-ssh"
  c "Creating the lab network rules"
  gcloud compute firewall-rules create "${LAB_TAG}-internal" \
    --network "$NETWORK" --allow tcp,udp,icmp --source-tags "$LAB_TAG" --target-tags "$LAB_TAG" \
    --description "Owned RHCSA lab: $TOKEN"
  touch "$STATE_DIR/firewall-internal"

  c "Creating $VM_A (with the spare disk for the storage labs)"
  gcloud compute instances create "$VM_A" \
    --zone "$ZONE" --network "$NETWORK" --subnet "$SUBNET" --machine-type "$TYPE" \
    --image-family "$IMAGE_FAMILY" --image-project "$IMAGE_PROJECT" \
    --boot-disk-size 20GB --boot-disk-type pd-balanced \
    --create-disk=name=${VM_A}-extra,size=10GB,type=pd-balanced,auto-delete=yes \
    --tags "$LAB_TAG" \
    --metadata ssh-keys="shea:$(cat "$SSH_KEY")"
  touch "$STATE_DIR/$VM_A"

  c "Creating $VM_B"
  gcloud compute instances create "$VM_B" \
    --zone "$ZONE" --network "$NETWORK" --subnet "$SUBNET" --machine-type e2-small \
    --image-family "$IMAGE_FAMILY" --image-project "$IMAGE_PROJECT" \
    --boot-disk-size 20GB --tags "$LAB_TAG" \
    --metadata ssh-keys="shea:$(cat "$SSH_KEY")"
  touch "$STATE_DIR/$VM_B"

  gcloud compute instances list --filter="tags.items=$LAB_TAG"
  cat <<EOF

Connect:   gcloud compute ssh shea@$VM_A --zone $ZONE
           gcloud compute ssh shea@$VM_B --zone $ZONE

Console:   https://console.cloud.google.com/compute/instances

STOP THEM when you finish for the day (you still pay for disks):
           gcloud compute instances stop $VM_A $VM_B --zone $ZONE
DESTROY:   $0 gcp --destroy
EOF
}

# =========================================================== DIGITALOCEAN ===
digitalocean() {
  command -v doctl >/dev/null || die "doctl not installed.
Install: https://docs.digitalocean.com/reference/doctl/how-to/install/
Then:  doctl auth init"

  local REGION="$LOCATION"
  local SIZE="${DO_SIZE:-s-2vcpu-4gb}"
  local IMAGE="rockylinux-10-x64"

  if [ "$DESTROY" = "1" ]; then
    for node in "$VM_A" "$VM_B"; do
      if [ -s "$STATE_DIR/$node" ]; then doctl compute droplet delete "$(cat "$STATE_DIR/$node")" --force; rm "$STATE_DIR/$node"; fi
    done
    if [ -f "$STATE_DIR/volume" ]; then doctl compute volume delete "$(cat "$STATE_DIR/volume")" --force; rm "$STATE_DIR/volume"; fi
    if [ -f "$STATE_DIR/firewall" ]; then doctl compute firewall delete "$(cat "$STATE_DIR/firewall")" --force; rm "$STATE_DIR/firewall"; fi
    if [ -f "$STATE_DIR/tag" ]; then doctl compute tag delete "$LAB_TAG" --force; rm "$STATE_DIR/tag"; fi
    return
  fi

  local KEYID
  KEYID="$DO_KEY_ID"
  doctl compute ssh-key get "$KEYID" >/dev/null
  [ -n "$KEYID" ] || die "No SSH key registered with DigitalOcean.
Add it:  doctl compute ssh-key import rhcsa --public-key-file $SSH_KEY"

  doctl compute tag create "$LAB_TAG"
  touch "$STATE_DIR/tag"
  doctl compute firewall create --name "$LAB_TAG" --tag-names "$LAB_TAG" \
    --inbound-rules "protocol:tcp,ports:22,address:$RHCSA_SSH_CIDR protocol:tcp,ports:1-65535,tag:$LAB_TAG protocol:udp,ports:1-65535,tag:$LAB_TAG protocol:icmp,tag:$LAB_TAG" \
    --outbound-rules "protocol:tcp,ports:1-65535,address:0.0.0.0/0 protocol:udp,ports:1-65535,address:0.0.0.0/0 protocol:icmp,address:0.0.0.0/0" \
    --output json | json_id > "$STATE_DIR/firewall"
  c "Creating $VM_A"
  doctl compute droplet create "$VM_A" --region "$REGION" --size "$SIZE" \
    --image "$IMAGE" --ssh-keys "$KEYID" --tag-name "$LAB_TAG" --wait --format ID --no-header > "$STATE_DIR/$VM_A"

  c "Creating $VM_B"
  doctl compute droplet create "$VM_B" --region "$REGION" --size s-1vcpu-2gb \
    --image "$IMAGE" --ssh-keys "$KEYID" --tag-name "$LAB_TAG" --wait --format ID --no-header > "$STATE_DIR/$VM_B"

  c "Adding a 10 GB volume to $VM_A for the storage labs"
  doctl compute volume create "${VM_A}-extra" --region "$REGION" --size 10GiB --output json | json_id > "$STATE_DIR/volume"
  local VOLID DROPID
  VOLID=$(cat "$STATE_DIR/volume")
  DROPID=$(cat "$STATE_DIR/$VM_A")
  [ -n "$VOLID" ] && doctl compute volume-action attach "$VOLID" "$DROPID" --wait && ok "volume attached"

  doctl compute droplet list --format Name,PublicIPv4,PrivateIPv4,Status
  cat <<EOF

Connect:   ssh root@<public-ip>
Console:   https://cloud.digitalocean.com/droplets

DESTROY:   $0 do --destroy
EOF
}

# ==================================================================== AWS ===
aws_ec2() {
  command -v aws >/dev/null || die "AWS CLI not installed.
Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
Then:  aws configure"

  local REGION="$LOCATION"
  local TYPE="${AWS_TYPE:-t3.medium}"

  if [ "$DESTROY" = "1" ]; then
    local IDS
    IDS=$(aws ec2 describe-instances --region "$REGION" \
      --filters "Name=tag:Project,Values=$LAB_TAG" "Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down" \
      --query 'Reservations[].Instances[].InstanceId' --output text)
    [ -n "$IDS" ] && aws ec2 terminate-instances --region "$REGION" --instance-ids $IDS && ok "instances terminated"
    if [ -n "$IDS" ]; then aws ec2 wait instance-terminated --region "$REGION" --instance-ids $IDS; fi
    if [ -f "$STATE_DIR/security-group" ]; then aws ec2 delete-security-group --region "$REGION" --group-id "$(cat "$STATE_DIR/security-group")"; rm "$STATE_DIR/security-group"; fi
    if [ -f "$STATE_DIR/key-created" ]; then aws ec2 delete-key-pair --region "$REGION" --key-name "$LAB_TAG"; rm "$STATE_DIR/key-created"; fi
    return
  fi

  c "Finding the latest Rocky Linux 10 AMI"
  local AMI
  AMI=$(aws ec2 describe-images --region "$REGION" --owners 792107900819 \
    --filters "Name=name,Values=Rocky-10-EC2-Base*x86_64*" "Name=state,Values=available" \
    --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text)
  [ "$AMI" != "None" ] && [ -n "$AMI" ] || die "Could not find a Rocky 10 AMI in $REGION.
Browse manually: https://console.aws.amazon.com/ec2/home#Images"
  ok "AMI: $AMI"

  aws ec2 import-key-pair --region "$REGION" --key-name "$LAB_TAG" \
    --public-key-material "fileb://$SSH_KEY"
  touch "$STATE_DIR/key-created"

  aws ec2 create-security-group --region "$REGION" --group-name "$LAB_TAG" \
    --description "Owned RHCSA lab $TOKEN"
  local SG
  SG=$(aws ec2 describe-security-groups --region "$REGION" --group-names "$LAB_TAG" \
    --query 'SecurityGroups[0].GroupId' --output text)
  printf '%s\n' "$SG" > "$STATE_DIR/security-group"
  aws ec2 authorize-security-group-ingress --region "$REGION" --group-id "$SG" \
    --protocol tcp --port 22 --cidr "$RHCSA_SSH_CIDR"
  aws ec2 authorize-security-group-ingress --region "$REGION" --group-id "$SG" \
    --protocol -1 --source-group "$SG"
  ok "security group $SG — SSH from your IP only, plus full traffic between lab hosts"

  c "Launching $VM_A with a 10 GB spare volume"
  aws ec2 run-instances --region "$REGION" --image-id "$AMI" --instance-type "$TYPE" \
    --key-name "$LAB_TAG" --security-group-ids "$SG" --count 1 \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":20}},{"DeviceName":"/dev/sdb","Ebs":{"VolumeSize":10,"DeleteOnTermination":true}}]' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$VM_A},{Key=Project,Value=$LAB_TAG}]" \
    --query 'Instances[0].InstanceId' --output text

  c "Launching $VM_B"
  aws ec2 run-instances --region "$REGION" --image-id "$AMI" --instance-type t3.small \
    --key-name "$LAB_TAG" --security-group-ids "$SG" --count 1 \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$VM_B},{Key=Project,Value=$LAB_TAG}]" \
    --query 'Instances[0].InstanceId' --output text

  cat <<EOF

List:      aws ec2 describe-instances --region $REGION \\
             --filters "Name=tag:Project,Values=$LAB_TAG" \\
             --query 'Reservations[].Instances[].[Tags[?Key==\`Name\`].Value|[0],PublicIpAddress,State.Name]' --output table
Connect:   ssh rocky@<public-ip>
Console:   https://console.aws.amazon.com/ec2/

STOP (cheaper than running, still pays for storage):
           aws ec2 stop-instances --region $REGION --instance-ids <ids>
DESTROY:   $0 aws --destroy
EOF
}

# ================================================================== VULTR ===
vultr() {
  command -v vultr-cli >/dev/null || die "vultr-cli not installed.
Install: https://github.com/vultr/vultr-cli#installation
Then export your API key:  export VULTR_API_KEY=...
Get one at: https://my.vultr.com/settings/#settingsapi"

  local REGION="$LOCATION"
  local PLAN="${VULTR_PLAN:-vc2-2c-4gb}"

  if [ "$DESTROY" = "1" ]; then
    for n in "$VM_A" "$VM_B"; do
      if [ -s "$STATE_DIR/$n" ]; then
        local ID; ID=$(cat "$STATE_DIR/$n")
        vultr-cli instance delete "$ID"
        rm "$STATE_DIR/$n"
        ok "$n deleted"
      fi
    done
    if [ -f "$STATE_DIR/volume" ]; then vultr-cli block-storage delete "$(cat "$STATE_DIR/volume")"; rm "$STATE_DIR/volume"; fi
    return
  fi

  c "Finding the Rocky Linux 10 OS id"
  vultr-cli os list | grep -i "rocky" || true
  local OSID="${VULTR_OS_ID:-}"
  [ -n "$OSID" ] || die "Set the OS id from the list above, then re-run:
  export VULTR_OS_ID=<id> && $0 vultr"

  local KEYID; KEYID="$VULTR_KEY_ID"
  [ -n "$KEYID" ] || die "No SSH key on Vultr. Add it:
  vultr-cli ssh-key create --name rhcsa --key \"\$(cat $SSH_KEY)\""

  [ -n "${VULTR_FIREWALL_GROUP:-}" ] || die "Set VULTR_FIREWALL_GROUP to your preconfigured SSH-/32 and peer-network firewall group; it remains yours after destroy"
  c "Creating $VM_A"
  vultr-cli instance create --region "$REGION" --plan "$PLAN" --os "$OSID" \
    --label "$VM_A" --host "$VM_A" --ssh-keys "$KEYID" --tags "$LAB_TAG" --firewall-group "$VULTR_FIREWALL_GROUP" --output json | json_id > "$STATE_DIR/$VM_A"
  c "Creating $VM_B"
  vultr-cli instance create --region "$REGION" --plan vc2-1c-2gb --os "$OSID" \
    --label "$VM_B" --host "$VM_B" --ssh-keys "$KEYID" --tags "$LAB_TAG" --firewall-group "$VULTR_FIREWALL_GROUP" --output json | json_id > "$STATE_DIR/$VM_B"

  vultr-cli block-storage create --region "$REGION" --size 10 --label "${VM_A}-extra" --output json | json_id > "$STATE_DIR/volume"
  vultr-cli block-storage attach "$(cat "$STATE_DIR/volume")" --instance "$(cat "$STATE_DIR/$VM_A")"
  vultr-cli instance list
  cat <<EOF

The extra volume has been created and attachment requested. Check its presence in the guest before partitioning.

Connect:   ssh root@<ip>
Console:   https://my.vultr.com/
DESTROY:   $0 vultr --destroy
EOF
}

case "$PROVIDER" in
  gcp)   gcp ;;
  do|digitalocean) digitalocean ;;
  aws)   aws_ec2 ;;
  vultr) vultr ;;
  *) sed -n '2,30p' "$0"; exit 1 ;;
esac

if [ "$DESTROY" = 1 ]; then
  for record in "$STATE_DIR"/volume "$STATE_DIR"/firewall "$STATE_DIR"/"$VM_A" "$STATE_DIR"/"$VM_B"; do
    [ ! -f "$record" ] || die "Unresolved resource record: $record. Check the provider before marking cleanup complete."
  done
  mv "$STATE_DIR" "${STATE_DIR}.removed-$(date +%s)"
else
  touch "$STATE_DIR/created"
fi

cat <<'EOF'

REMEMBER: cloud instances bill by the hour. Destroy them when you are done for
the week, and rebuild with this script when you come back. Rebuilding from
scratch is itself good RHCSA practice.
EOF
