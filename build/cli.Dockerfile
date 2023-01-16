FROM openjdk:8-jdk-alpine
ENV CLI_VERSION="0.2-SNAPSHOT-2336890983-14-a4260ab"

# required config file, even though we override all these values via environment variables
COPY config /root/.cs/config

RUN apk add curl
RUN curl -o cs.jar -L https://github.com/carbynestack/cli/releases/download/$CLI_VERSION/cli-$CLI_VERSION-jar-with-dependencies.jar

ENTRYPOINT ["java","-jar","cs.jar"]