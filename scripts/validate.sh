#!/bin/bash
# Validation script - runs checks that don't require Docker/K8s
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Validating mirrord config..."
mirrord verify-config mirrord/research-crew.json

echo "==> Checking Python syntax..."
python3 -m py_compile crew/main.py crew/crew.py

echo "==> Checking prerequisites..."
for cmd in kubectl kagent mirrord docker; do
  command -v $cmd >/dev/null || { echo "Missing: $cmd"; exit 1; }
done
echo "  kubectl, kagent, mirrord, docker: OK"

echo "==> Validating YAML..."
# kubectl client dry-run when cluster exists and kagent CRDs are installed
if kubectl cluster-info &>/dev/null; then
  if kubectl get crd agents.kagent.dev &>/dev/null; then
    kubectl apply -f agents/research-crew.yaml --dry-run=client
    kubectl apply -f agents/orchestrator.yaml --dry-run=client
    echo "  Agent YAML: valid (cluster has kagent CRDs)"
  else
    echo "  (kagent CRDs not installed yet — run ./scripts/setup.sh first; skipping Agent dry-run)"
  fi
else
  echo "  (No cluster - skipping kubectl dry-run)"
fi

echo ""
echo "Validation passed."
