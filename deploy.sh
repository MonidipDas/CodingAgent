#!/usr/bin/env bash
set -euo pipefail
PROJECT=${1:?Provide GCP project ID}
ZONE=${2:?Provide GCP zone}
NAME=coding-agent
cd "$(dirname "$0")"
gcloud compute instances create "$NAME" --project="$PROJECT" --zone="$ZONE" --machine-type=e2-standard-2 --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud --boot-disk-size=30GB --no-service-account --no-scopes
gcloud compute scp --project="$PROJECT" --zone="$ZONE" --recurse . "$NAME:~/coding-agent"
gcloud compute ssh "$NAME" --project="$PROJECT" --zone="$ZONE" --command='set -eu; sudo apt-get update; sudo apt-get install -y docker.io python3-venv; sudo systemctl enable --now docker; python3 -m venv ~/agent-env; ~/agent-env/bin/pip install ~/coding-agent; sudo docker build -f ~/coding-agent/Dockerfile.sandbox -t coding-sandbox:local ~/coding-agent; sudo usermod -aG docker "$USER"'
printf 'Deployment installed. Reconnect over SSH to activate Docker group membership.\n'
