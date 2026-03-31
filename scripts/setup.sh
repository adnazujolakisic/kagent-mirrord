#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -f "$REPO_ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env"
  set +a
fi

# Supports minikube (default) or kind. Use CLUSTER=kind for kind.
CLUSTER="${CLUSTER:-minikube}"
REGISTRY_PORT="5001"
REGISTRY_ADDR="localhost:5001"

echo "==> checking prerequisites"
command -v kubectl >/dev/null || { echo "install kubectl"; exit 1; }
command -v kagent >/dev/null || { echo "install kagent: brew install kagent"; exit 1; }
command -v mirrord >/dev/null || { echo "install mirrord: brew install metalbear-co/mirrord/mirrord"; exit 1; }
command -v docker >/dev/null || { echo "install docker"; exit 1; }

[ -z "$ANTHROPIC_API_KEY" ] && {
  echo "set ANTHROPIC_API_KEY in .env or your environment (Claude for orchestrator + research-crew)."
  echo "If you still have OPENAI_API_KEY from an older checkout, rename that line to ANTHROPIC_API_KEY in .env."
  exit 1
}

if [ "$CLUSTER" = "minikube" ]; then
  command -v minikube >/dev/null || { echo "install minikube: brew install minikube"; exit 1; }

  echo "==> starting minikube"
  minikube status >/dev/null 2>&1 || minikube start
else
  command -v kind >/dev/null || { echo "install kind: brew install kind"; exit 1; }
  REGISTRY_PORT="5001"
  REGISTRY_ADDR="localhost:5001"

  echo "==> creating kind cluster with local registry"
  reg_name='kind-registry'
  if [ "$(docker inspect -f '{{.State.Running}}' "${reg_name}" 2>/dev/null || true)" != 'true' ]; then
    docker run -d --restart=always -p "127.0.0.1:${REGISTRY_PORT}:5000" --network bridge --name "${reg_name}" registry:2
  fi
  if ! kind get clusters 2>/dev/null | grep -q kind; then
    cat <<EOF | kind create cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
containerdConfigPatches:
- |-
  [plugins."io.containerd.grpc.v1.cri".registry]
    config_path = "/etc/containerd/certs.d"
EOF
    REGISTRY_DIR="/etc/containerd/certs.d/localhost:${REGISTRY_PORT}"
    for node in $(kind get nodes); do
      docker exec "${node}" mkdir -p "${REGISTRY_DIR}"
      echo '[host."http://kind-registry:5000"]' | docker exec -i "${node}" cp /dev/stdin "${REGISTRY_DIR}/hosts.toml"
    done
    docker network connect kind "${reg_name}" 2>/dev/null || true
  fi
fi

echo "==> installing kagent"
# Stale ghcr.io credentials in Helm often cause 403 "denied" on public kagent charts.
if command -v helm >/dev/null 2>&1; then
  helm registry logout ghcr.io 2>/dev/null || true
fi
kagent install --profile demo

echo "==> waiting for kagent to be ready"
kubectl wait --for=condition=ready pod -l app=kagent-engine -n kagent --timeout=120s 2>/dev/null || \
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=kagent -n kagent --timeout=120s 2>/dev/null || \
echo "kagent may use different pod labels - continuing..."

echo "==> configuring Anthropic secret + ModelConfig (declarative orchestrator uses Claude)"
kubectl create secret generic kagent-anthropic \
  --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -n kagent \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f "$REPO_ROOT/agents/claude-model-config.yaml"

echo "==> creating secrets for BYO research-crew"
kubectl create secret generic research-crew-secrets \
  --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -n kagent \
  --dry-run=client -o yaml | kubectl apply -f -

echo "==> building research-crew image"
if [ "$CLUSTER" = "minikube" ]; then
  # Host Docker build + load into minikube. Use a fixed tag (not :latest) so kubelet always
  # runs the image you just loaded; :latest often leaves two ReplicaSets (old digest + new).
  MIRRD_CREW_TAG="research-crew:mirrord-local"
  echo "==> building research-crew image (host docker -> minikube load as $MIRRD_CREW_TAG)"
  docker build -t "$MIRRD_CREW_TAG" "$REPO_ROOT/crew"
  minikube image load "$MIRRD_CREW_TAG" --overwrite=true
  sed "s|localhost:5001/research-crew:latest|$MIRRD_CREW_TAG|g" \
    "$REPO_ROOT/agents/research-crew.yaml" | kubectl apply -f -
else
  docker build -t "${REGISTRY_ADDR}/research-crew:latest" "$REPO_ROOT/crew"
  docker push "${REGISTRY_ADDR}/research-crew:latest"
  kubectl apply -f "$REPO_ROOT/agents/research-crew.yaml"
fi
kubectl apply -f "$REPO_ROOT/agents/orchestrator.yaml"

echo "==> waiting for research-crew pod"
sleep 5
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=research-crew \
  -n kagent --timeout=120s 2>/dev/null || \
kubectl wait --for=condition=ready pod \
  -l app=research-crew \
  -n kagent --timeout=120s 2>/dev/null || \
echo "Waiting for research-crew - check with: kubectl get pods -n kagent"

echo ""
echo "setup complete. verify with:"
echo "  kubectl get deploy,pods -n kagent"
echo "  kubectl get deploy research-crew -n kagent   # mirrord target must match this name"
echo ""
echo "test the chain:"
echo "  kagent invoke --agent orchestrator --task 'Research what kagent is'"
echo ""
echo "start mirrord dev session (creates/uses .venv — see requirements-local.txt):"
echo "  chmod +x scripts/mirrord-crew.sh && ./scripts/mirrord-crew.sh"
echo ""
