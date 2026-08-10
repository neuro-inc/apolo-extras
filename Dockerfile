FROM python:3.15.0rc1-alpine3.23

LABEL org.opencontainers.image.source="https://github.com/neuro-inc/apolo-extras"

ENV LANG=C.UTF-8
ENV PYTHONUNBUFFERED=1

ARG CLOUD_SDK_VERSION=577.0.0
ENV CLOUD_SDK_VERSION=$CLOUD_SDK_VERSION

ENV PATH=/google-cloud-sdk/bin:$PATH

RUN apk add --no-cache make curl git rsync zip unzip vim wget openssh-client ca-certificates bash

# Install Google Cloud SDK
RUN CLOUD_SDK_ARCHIVE="google-cloud-cli-${CLOUD_SDK_VERSION}-linux-x86_64.tar.gz" && \
    wget -q "https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/${CLOUD_SDK_ARCHIVE}" && \
    tar xzf "$CLOUD_SDK_ARCHIVE" && \
    rm "$CLOUD_SDK_ARCHIVE" && \
    ln -s /lib /lib64 && \
    gcloud config set core/disable_usage_reporting true && \
    gcloud --version

# Install rclone
RUN RCLONE_ARCHIVE="rclone-current-linux-amd64.zip" && \
    curl --fail --location --remote-name "https://downloads.rclone.org/${RCLONE_ARCHIVE}" && \
    unzip "$RCLONE_ARCHIVE" && \
    rm "$RCLONE_ARCHIVE" && \
    cp rclone-*-linux-amd64/rclone /usr/bin/ && \
    rm -rf rclone-*-linux-amd64 && \
    chmod 755 /usr/bin/rclone

# Install kubectl
# y.s. (23.08.2025) we seem to not need it anymore, drop later if confirmed
# RUN cd /usr/local/bin && \
#     wget https://dl.k8s.io/release/v1.33.4/bin/linux/amd64/kubectl && \
#     chmod +x ./kubectl && \
#     kubectl version --client

# package version is to be overloaded with exact version
ARG APOLO_EXTRAS_PACKAGE=apolo-extras

ENV PATH=/root/.local/bin:$PATH

RUN python -m pip install --no-cache-dir --upgrade pip pipx
RUN MULTIDICT_NO_EXTENSIONS=1 YARL_NO_EXTENSIONS=1 python -m pip install \
    --no-cache-dir --user "$APOLO_EXTRAS_PACKAGE" && \
    # isolated env since it has conflicts with apolo-cli
    pipx install awscli
RUN apolo-extras init-aliases

RUN mkdir -p /root/.ssh
COPY files/ssh/known_hosts /root/.ssh/known_hosts

VOLUME ["/root/.config"]

WORKDIR /root

COPY docker.entrypoint.sh /var/lib/apolo/entrypoint.sh
ENTRYPOINT ["/var/lib/apolo/entrypoint.sh"]
