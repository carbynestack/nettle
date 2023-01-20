#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

FROM ghcr.io/carbynestack/openjdk:jre8-20210827
ENV CLI_VERSION="0.2-SNAPSHOT-2336890983-14-a4260ab"

# required config file, even though we override all these values via environment variables
COPY config /root/.cs/config

RUN apk add curl
RUN curl -o cs.jar -L https://github.com/carbynestack/cli/releases/download/$CLI_VERSION/cli-$CLI_VERSION-jar-with-dependencies.jar

ENTRYPOINT ["java","-jar","cs.jar"]
