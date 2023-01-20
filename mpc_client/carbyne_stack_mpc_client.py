#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

import ast
import uuid
from logging import DEBUG, INFO
from typing import Dict, List, Tuple

import docker
from docker.errors import DockerException
from flwr.common.logger import log

from mpc_client.mpc_client import MpcClient, MpcClientException


class Provider:
    def __init__(self, base_url: str):
        """
        Create a :class:`Provider` instance.

        :param base_url: The base URL of a Carbyne Stack provider that all other connection params derive from, e.g.,
                         `https://apollo.bocse.carbynestack.io/`
        """
        self.__base_url = base_url

    @property
    def base_url(self):
        return self.__base_url


class CarbyneStackMpcClient(MpcClient):
    def __init__(self, prime: int, r: int, r_inv: int, providers: List[Provider]):
        """
        Creates an :class:`MpcClient` talking to a Carbyne Stack virtual cloud.

        :param prime: Modulus N as used by the Carbyne Stack virtual cloud
        :param r: Auxiliary modulus R as used by the Carbyne Stack virtual cloud
        :param r_inv: Multiplicative inverse for the auxiliary modulus R as used by the Carbyne Stack virtual cloud
        :param providers: A list of Carbyne Stack virtual cloud providers
        :raises MpcClientException: If Docker is not running or there was an issue connecting to it
        """
        self.__prime = prime
        self.__r = r
        self.__r_inv = r_inv
        self.__providers = providers
        try:
            self.docker_client = docker.APIClient()
        except DockerException as de:
            raise MpcClientException(message="can't create docker client") from de
        log(
            INFO,
            "Carbyne Stack MPC Client instantiated talking to providers %s",
            str(providers),
        )

    def create_secret(
        self, values: List[int], tags: Dict[str, str] = None
    ) -> uuid.UUID:
        status_code, stdout, stderr = self.__run_container(
            entrypoint=["java", "-jar", "cs.jar", "amphora", "create-secret"]
            + self.__map_tags(tags=tags),
            stdin_open=True,
            stdin_value="\n".join(map(str, values)),
        )
        if status_code != 0:
            raise MpcClientException(message=stderr)
        else:
            secret_id = uuid.UUID(str(stdout).splitlines()[1])
            log(
                INFO,
                "%d-element Secret with identifier '%s' and tags '%s' created",
                len(values),
                secret_id,
                tags,
            )
            return secret_id

    def get_secret(self, identifier: uuid.UUID) -> Tuple[List[int], Dict[str, str]]:
        status_code, stdout, stderr = self.__run_container(
            entrypoint=[
                "java",
                "-jar",
                "cs.jar",
                "amphora",
                "get-secret",
                str(identifier),
            ]
        )
        if status_code != 0:
            raise MpcClientException(message=stderr)
        else:
            result_lines = stdout.splitlines()
            tags = {}
            if len(result_lines) > 1:
                for line_number in range(1, len(result_lines)):
                    split_line = result_lines[line_number].split("->")
                    tags[split_line[0].strip()] = split_line[1].strip()
            data = ast.literal_eval(result_lines[0])
            log(
                INFO,
                "%d-element secret with tags '%s' fetched for identifier '%s'",
                len(data),
                tags,
                identifier,
            )
            return data, tags

    def execute(
        self, inputs: List[uuid.UUID], application_name: str, timeout: int = 10
    ) -> uuid.UUID:
        status_code, stdout, stderr = self.__run_container(
            entrypoint=["ephemeral", "execute", "--timeout", str(timeout)]
            + self.__map_inputs(inputs)
            + [application_name]
        )
        if status_code != 0:
            raise MpcClientException(message=stderr)
        else:
            result_id = uuid.UUID(stdout)
            log(
                INFO,
                "Application '%s' invocation with input secrets '%s' created secret '%s'",
                application_name,
                inputs,
                result_id,
            )
            return result_id

    def __run_container(
        self, entrypoint: List[str], stdin_open=False, stdin_value=""
    ) -> Tuple[int, str, str]:
        """
        Runs the CarbyneStack CLI via the docker image and the given arguments.

        :param entrypoint: A list of arguments (e.g., ["java", "-jar", "cs.jar", "amphora", "get-secret", identifier])
        :param stdin_open: Open the STDIN to allow data to be passed (required for large arrays of secrets)
        :param stdin_value: The str that will be passed into the docker container via STDIN
        :return: A tuple of:
            1. Docker Container's Status Code
            2. the STDOUT of the container
            3. the STDERR of the container
        """
        log(
            DEBUG,
            str("Executing CLI command" + " with STDIN: %s" if stdin_open else ": %s"),
            " ".join(list(map(str, entrypoint))),
        )

        container = self.docker_client.create_container(
            "nettle/carbynestack-mpc-client",
            stdin_open=stdin_open,
            environment=self.__get_envs(),
            entrypoint=entrypoint,
        )

        self.docker_client.start(container)

        if stdin_open:
            sock = self.docker_client.attach_socket(
                container, params={"stdin": 1, "stdout": 1, "stderr": 1, "stream": 1}
            )
            sock._sock.send(str.encode(stdin_value))
            sock._sock.close()
            sock.close()

        status = self.docker_client.wait(container)
        status_code = status["StatusCode"]
        stdout = self.docker_client.logs(container, stderr=False).decode()
        stderr = self.docker_client.logs(container, stdout=False).decode()

        self.docker_client.remove_container(container)

        log(DEBUG, "Execution completed with status code: %s", str(status_code))

        return status_code, str(stdout), str(stderr)

    def __get_envs(self) -> Dict[str, str]:
        """
        Build the dictionary of Carbyne Stack CLI configuration environment variables.

        For more details about the configuration options, see: https://github.com/carbynestack/cli#configuration.

        :return: The dictionary of environment variables
        """
        envs = {
            "CS_PRIME": str(self.__prime),
            "CS_R": str(self.__r),
            "CS_R_INV": str(self.__r_inv),
            "CS_NO_SSL_VALIDATION": "true",
        }

        for i, provider in enumerate(self.__providers):
            envs["CS_VCP_{0}_BASE_URL".format(i + 1)] = provider.base_url
            envs["CS_VCP_{0}_AMPHORA_URL".format(i + 1)] = provider.base_url + "amphora"
            envs["CS_VCP_{0}_CASTOR_URL".format(i + 1)] = provider.base_url + "castor"
            envs["CS_VCP_{0}_EPHEMERAL_URL".format(i + 1)] = provider.base_url

        return envs

    @staticmethod
    def __map_tags(tags: Dict[str, str] = None) -> List[str]:
        """
        Maps the passed in dictionary of tags to a list of arguments used in docker run.

        :param tags: A list of key/value pairs to be used as tags.
        :return: A list of tag arguments for docker run, e.g., ["--tag", "message=howdy", "--tag", "type=magic"]
        """
        if tags is None:
            return []

        tag_arguments = []
        for tag_key in tags:
            tag_arguments.append("--tag")
            tag_arguments.append("{0}={1}".format(tag_key, tags[tag_key]))
        return tag_arguments

    @staticmethod
    def __map_inputs(inputs: List[uuid.UUID]) -> List[str]:
        """
        Maps the passed in list of input identifiers to a list of arguments used in docker run.

        :param inputs: A list of secret IDs (UUID) to be used as inputs for the MPC program.
        :return: A list of tag arguments for docker run, e.g.,
        ["--input", "91163E6B-AD8E-42EE-8374-5C471B5D97B5", "--input", "D97ACC22-1D5A-442C-8A52-0D26EDC55C11"]
        """
        input_arguments = []
        for input_value in inputs:
            input_arguments.append("--input")
            input_arguments.append(str(input_value))
        return input_arguments
