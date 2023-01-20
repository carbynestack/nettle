#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

import shutil
import uuid
from builtins import int
from logging import DEBUG, ERROR, INFO
from pathlib import Path
from typing import List, Dict, Tuple, Union

import docker
from docker.errors import DockerException, ImageNotFound
from flwr.common.logger import log
from requests import ReadTimeout

from mpc_client.mpc_client import MpcClient, MpcClientException


class MpSpdzMpcClient(MpcClient):
    """
    A :class:`MpcClient` implementation that spawns MP-SPDZ instances locally using Docker.

    Secrets are injected as cleartext values via player 0.
    """

    def __init__(
        self, working_directory: Path = Path.home().joinpath(".nettle-mp-spdz")
    ):
        """
        Instantiates a :class:`MpSpdzMpcClient` using the given working directory.

        :param working_directory: The directory used to store secrets and programs.
        """
        self.__working_directory = working_directory
        self.__create_dirs()
        try:
            self.docker_client = docker.APIClient()
        except DockerException as docker_exception:
            raise MpcClientException(message=str(docker_exception))
        log(
            INFO,
            "Created MP-SPDZ MPC Client with working directory: %s",
            self.__working_directory,
        )

    def __create_dirs(self):
        for d in [
            self.__get_secrets_dir(),
            self.__get_executions_dir(),
            self.__get_programs_dir(),
        ]:
            self.__ensure_exists(d)

    @staticmethod
    def __ensure_exists(path):
        path.mkdir(parents=True, exist_ok=True)

    def __get_secrets_dir(self):
        return self.__working_directory.joinpath("secrets")

    def __get_executions_dir(self):
        return self.__working_directory.joinpath("executions")

    def __get_programs_dir(self):
        return self.__working_directory.joinpath("programs")

    def add_program(self, program: Union[str, Path]):
        """
        Adds a program to this MPC backend.

        :param program: The path to the MPC program.
        """
        shutil.copy(program, self.__get_programs_dir())
        log(INFO, "Program '%s' added", program)

    def create_secret(
        self, values: List[int], tags: Dict[str, str] = None
    ) -> uuid.UUID:
        if tags is not None and len(tags) != 0:
            raise ValueError("tags are not supported by this client implementation")
        secret_id = uuid.uuid4()
        try:
            with open("%s/%s" % (self.__get_secrets_dir(), secret_id), "w") as f:
                for v in values:
                    f.write(str(v) + " ")
                f.close()
        except OSError as ose:
            raise MpcClientException("can't create secret") from ose
        log(
            INFO,
            "%d-element Secret with identifier '%s' and tags '%s' created",
            len(values),
            secret_id,
            tags,
        )
        return secret_id

    def get_secret(self, identifier: uuid.UUID) -> Tuple[List[int], Dict[str, str]]:
        try:
            with open("%s/%s" % (self.__get_secrets_dir(), identifier), "r") as f:
                data, tags = [int(s) for s in f.read().split()], {}
                log(
                    INFO,
                    "%d-element secret with tags '%s' fetched for identifier '%s'",
                    len(data),
                    tags,
                    identifier,
                )
                return data, tags
        except OSError as ose:
            raise MpcClientException(
                f"secret with given identifier not found: {str(identifier)}"
            ) from ose

    def execute(
        self, inputs: List[uuid.UUID], application_name: str, timeout: int = 10
    ) -> uuid.UUID:

        # Generate working directory
        exec_id = uuid.uuid4()
        exec_dir = self.__get_executions_dir().joinpath(str(exec_id))
        log(
            DEBUG,
            "folder for execution with identifier '%s' created: %s",
            str(exec_id),
            exec_dir,
        )

        # Concatenate inputs into single input file for player 0
        player_data_path = exec_dir.joinpath("Player-Data")
        self.__ensure_exists(player_data_path)
        with open(player_data_path.joinpath("Input-P0-0"), "w") as wfd:
            for f in inputs:
                try:
                    with open(self.__get_secrets_dir().joinpath(str(f)), "r") as fd:
                        shutil.copyfileobj(fd, wfd)
                        fd.close()
                except OSError as ose:
                    raise MpcClientException(
                        f"input secret with identifier not found: {str(f)}"
                    ) from ose
            wfd.close()

        # Execute MP-SPDZ in Docker
        binds = [
            "{}:/mp-spdz/Player-Data".format(player_data_path),
            "{}:/mp-spdz/Programs/Source".format(self.__get_programs_dir()),
        ]
        try:
            container = self.docker_client.create_container(
                image="docker.io/nettle/mp-spdz-mpc-client",
                environment={"MPC_PROGRAM_NAME": application_name},
                volumes=["/mp-spdz/Player-Data", "/mp-spdz/Programs/Source"],
                host_config=self.docker_client.create_host_config(binds=binds),
            )
        except ImageNotFound as inf:
            raise MpcClientException(
                "Docker image not found. Forgot to run make?"
            ) from inf

        self.docker_client.start(container)
        try:
            status = self.docker_client.wait(container, timeout=timeout)
        except ReadTimeout as rt:
            raise MpcClientException(
                "Timeout while waiting for execution to finish"
            ) from rt
        status_code = status["StatusCode"]
        stdout = str(self.docker_client.logs(container, stderr=False).decode())
        log(DEBUG, "container stdout:\n%s", stdout)
        if status_code != 0:
            stderr = str(self.docker_client.logs(container, stdout=False).decode())
            log(ERROR, "container stderr:\n%s", stderr)
            raise MpcClientException(
                f"Container execution failed with status code: {status_code}"
            )

        self.docker_client.remove_container(container)

        # Store Output
        output_path = player_data_path.joinpath("Out-P0-0")
        exec_result_id = uuid.uuid4()
        result_path = self.__get_secrets_dir().joinpath(str(exec_result_id))
        result = open(output_path).read()
        if result[0] == "[":
            result = result[1:-2].replace(",", "")
        open(result_path, "w").write(result)
        log(
            INFO,
            "Application '%s' invocation with input secrets '%s' created secret '%s'",
            application_name,
            inputs,
            exec_result_id,
        )

        return exec_result_id
