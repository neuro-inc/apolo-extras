FROM python:3.13.7-alpine3.21

LABEL org.opencontainers.image.source="https://github.com/neuro-inc/neuro-extras"

ENV LANG=C.UTF-8
ENV PYTHONUNBUFFERED=1

ARG CLOUD_SDK_VERSION=535.0.0
ENV CLOUD_SDK_VERSION=$CLOUD_SDK_VERSION

ENV PATH=/google-cloud-sdk/bin:$PATH

RUN apk add --no-cache make curl git rsync zip unzip vim wget openssh-client ca-certificates bash

# Install Google Cloud SDK
RUN wget -q https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-${CLOUD_SDK_VERSION}-linux-x86_64.tar.gz && \
    tar xzf google-cloud-sdk-${CLOUD_SDK_VERSION}-linux-x86_64.tar.gz && \
    rm google-cloud-sdk-${CLOUD_SDK_VERSION}-linux-x86_64.tar.gz && \
    ln -s /lib /lib64 && \
    gcloud config set core/disable_usage_reporting true && \
    gcloud --version

# Install rclone
RUN curl -O https://downloads.rclone.org/rclone-current-linux-amd64.zip && \
    unzip rclone-current-linux-amd64.zip && \
    rm rclone-current-linux-amd64.zip && \
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

RUN pip3 install --no-cache-dir -U pip pipx
RUN MULTIDICT_NO_EXTENSIONS=1 YARL_NO_EXTENSIONS=1 pip install --user \
    $APOLO_EXTRAS_PACKAGE && \
    # isolated env since it has conflicts with apolo-cli
    pipx install awscli
RUN apolo-extras init-aliases

RUN mkdir -p /root/.ssh
COPY files/ssh/known_hosts /root/.ssh/known_hosts

VOLUME ["/root/.config"]

WORKDIR /root

COPY docker.entrypoint.sh /var/lib/apolo/entrypoint.sh
ENTRYPOINT ["/var/lib/apolo/entrypoint.sh"]
