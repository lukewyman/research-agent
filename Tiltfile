# Tiltfile
k8s_yaml(['k8s/overlays/dev/kustomization.yaml'])

# Build API image
docker_build('research/api:dev', '.', dockerfile='Dockerfile.api', live_update=[
  sync('./packages', '/app/packages'),
  sync('./apps', '/app/apps'),
])

# Build worker image
docker_build('research/worker:dev', '.', dockerfile='Dockerfile.worker', live_update=[
  sync('./packages', '/app/packages'),
  sync('./apps', '/app/apps'),
])

k8s_resource('research-api', port_forwards=['8000:80'])
