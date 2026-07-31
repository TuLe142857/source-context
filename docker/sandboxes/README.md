# Dockerfile Sandboxes
- Container Dockerfiles providing sandbox environment to run scip indexer
- Every Dockerfile must:
  - Install language scip indexer
  - Setup language environment(compiler, interpreter, build tool, ...)
  - Create default directories: 
    - /sandbox/projects/
    - /sandbox/output/
