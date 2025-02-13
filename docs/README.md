## Apolo Extras Documentation
A set of tools and commands to extend the functionality of Apolo platform CLI client.

## Image Operations

### Copying Images
Images can be copied between different projects, organizations, and clusters using the apolo-extras image transfer command.

#### Between Projects:

```bash
# Copy image from project1 to project2 within the same cluster
apolo-extras image transfer \
  image:/project/image:tag \
  image:/target-project/image:tag
```

```bash
# Force overwrite existing image
apolo-extras image transfer -F \
  image:/project/image:tag \
  image:/target-project/image:tag
```

#### Between Clusters:
You need to image the image's full path including cluster, organization and project to be able to copy between clusters.

```bash
# Copy image between different clusters
apolo-extras image transfer \
  image://cluster/organization/project/image:tag \
  image://target-cluster/target-organization/target-project/image:tag
```

###  Building Images
The platform provides two methods for building images: remote building using Kaniko (build) and local building using Docker (local-build).

#### Remote Build with layers cache:

```bash
# Basic build with default cache settings
apolo-extras image build ./context image:<image-name>:<tag>
```

```bash
# Disable build cache
apolo-extras image build --no-cache ./context image:<image-name>:<tag>
```

```bash
# Advanced cache control using Kaniko arguments
apolo-extras image build --extra-kaniko-args="--cache-dir=/cache --cache-ttl=24h" ./context image:<image-name>:<tag>
```

```bash
# Build with custom Dockerfile and build arguments
apolo-extras image build -f custom.Dockerfile --build-arg VERSION=1.0 ./context image:<image-name>:<tag>
```

```bash
# Build images using a specific hardware preset available in the cluster
apolo-extras image build --preset <preset> ./context image:<image-name>:<tag>
```

#### Local Build:
```bash
# Basic local build
apolo-extras image local-build ./context image:<image-name>:<tag>
```

```bash
# Build with custom Dockerfile and verbose output
apolo-extras image local-build -f custom.Dockerfile --verbose ./context image:<image-name>:<tag>
```

#### Working with External Registries
To work with external private registries, you'll need to configure authentication first.

##### Setting Up Registry Authentication:
You can generate an authentication config.json file for external registries using a username and password

```bash
apolo-extras config build-registy-auth registry.external.com username password > docker.config.json
```

You can then use this config file to build images remotely and push to a private external registry
```bash
apolo secret add registry_token @docker.config.json
apolo-extras image build --preset cpu-small -e \
  NE_REGISTRY_AUTH=secret:registry_token \
  ./context \
  <registry.external>/<project>/image:tag
```

You can also use your existing Docker Hub authentication to push images to a private Docker Hub repository.

```bash
apolo secret add registry_token @${HOME}/.docker/config.json
apolo-extras image build --preset cpu-small -e \
  NE_REGISTRY_AUTH=secret:registry_token \
  ./context \
  <registry.external>/<project>/image:latest
```

It is possible to push images from your local machine to Apolo Platform Registry. Use the following command to save a config.json file with the authentication credentials.

```bash
apolo-extras config save-registry-auth ${HOME}/.docker/config.json --cluster default
```


## Data Operations
### Data Transfer Between Projects
The apolo-extras data transfer command facilitates data movement between different internal storage locations. This is not supported with regular Apolo CLI apolo cp.

Between directories in the same project:
```bash
# Copy data between directories on the same project
apolo-extras data transfer storage:folder1 storage:folder2
```

Between Projects:
```bash
# Copy data between projects on the same cluster
apolo-extras data transfer storage:/project1/data storage:/project2/data

# Copy data between disks
apolo-extras data transfer disk:disk1:/data disk:disk2:/data
```

Between Clusters:
```bash
# Copy data between clusters
apolo-extras data transfer \
  storage://cluster1/organization/project/directory \
  storage://cluster2/organization/project/directory
```

### External Storage Operations
The platform supports various external storage systems with different authentication methods.

#### Google Cloud Storage (GCS)
Create a Apolo Secret containing GCP service account credentials to access the data on GCP.

```bash
apolo secret add gcp-creds @path/to/credentials/file.json
```

You can then use it to start copy jobs to and from Google Cloud Storage.

```bash
# Download and extract from GCS
apolo-extras data cp -x -t \
  -v secret:gcp-creds:/gcp-creds.txt \
  -e GOOGLE_APPLICATION_CREDENTIALS=/gcp-creds.txt \
  gs://bucket-name/dataset.tar.gz \
  storage:/project/dataset

# Upload to GCS with compression
apolo-extras data cp -c \
  -v secret:gcp-creds:/gcp-creds.txt \
  -e GOOGLE_APPLICATION_CREDENTIALS=/gcp-creds.txt \
  storage:/project/dataset \
  gs://bucket-name/dataset.tar.gz
```

#### AWS S3
Create a Apolo Secret containing AWS CLI tool credentials to access the data on AWS S3.

```bash
apolo secret add s3-creds @path/to/credentials/file.json
```

You can then use it to start copy jobs to and from AWS S3.
```bash
# Download and extract from S3
apolo-extras data cp -x -t \
  -v secret:s3-creds:/s3-creds.txt \
  -e AWS_SHARED_CREDENTIALS_FILE=/s3-creds.txt \
  s3://bucket-name/dataset.tar.gz \
  disk:disk-name:/project/dataset

# Upload to S3 with compression
apolo-extras data cp -c \
  -v secret:s3-creds:/s3-creds.txt \
  -e AWS_SHARED_CREDENTIALS_FILE=/s3-creds.txt \
  disk:disk-name:/project/dataset \
  s3://bucket-name/dataset.tar.gz
```


#### Azure Blob Storage
Create a Apolo Secret containing credentials to access the data on Azure Blob Storage.

```bash
apolo secret add azure-sas-token @path/to/credentials/file.json
```

You can then use it to start copy jobs to and from Azure Blob Storage.
```bash
# Download and extract from Azure
apolo-extras data cp -x -t \
  -e AZURE_SAS_TOKEN=secret:azure-sas-token \
  azure+https://storage-account.blob.core.windows.net/container/dataset.tar.gz \
  storage:/project/dataset

# Upload to Azure with compression
apolo-extras data cp -c \
  -e AZURE_SAS_TOKEN=secret:azure-sas-token \
  storage:/project/dataset \
  azure+https://storage-account.blob.core.windows.net/container/dataset.tar.gz
```

#### HTTP/HTTPS Sources
```bash
# Download and extract from HTTP source
apolo-extras data cp -x -t \
  https://example.org/dataset.tar.gz \
  disk:disk-name:/project/dataset

# Download with custom preset for resource allocation
apolo-extras data cp -s large-memory \
  https://example.org/large-dataset.tar.gz \
  storage:/project/dataset
```

### Advanced Data Transfer Options
Using Presets and Lifespans:

```bash
# Use preset for resource allocation
apolo-extras data cp -s high-bandwidth source destination

# Set job lifespan
apolo-extras data cp -l 3600 source destination

# Combine preset and lifespan
apolo-extras data cp -s high-bandwidth -l 7200 source destination
```

Working with Archives:
```bash
# Extract specific archive types
apolo-extras data cp -x source.tar.gz destination/   # For .tar.gz
apolo-extras data cp -x source.zip destination/      # For .zip
apolo-extras data cp -x source.tar.bz2 destination/  # For .tar.bz2

# Create archives with specific formats
apolo-extras data cp -c source/ destination.tar.gz   # Create .tar.gz
apolo-extras data cp -c source/ destination.zip      # Create .zip
apolo-extras data cp -c source/ destination.tar.bz2  # Create .tar.bz2
```