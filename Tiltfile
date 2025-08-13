# Build images
docker_build(
  'newsrag/api:dev', '.',
  dockerfile='Dockerfile.api',
  live_update=[
    sync('./packages', '/app/packages'),
    sync('./apps', '/app/apps'),
  ],
)

docker_build(
  'newsrag/worker:dev', '.',
  dockerfile='Dockerfile.worker',
  live_update=[
    sync('./packages', '/app/packages'),
    sync('./apps', '/app/apps'),
  ],
)

# Use the dev overlay (kustomize)
k8s_yaml(kustomize('k8s/overlays/dev'))

# Make sure changes to .env trigger a re-apply (for secretGenerator)
watch_file('.env')

# Convenience port-forward for API
k8s_resource('newsrag-api', port_forwards=['8000:80'])
