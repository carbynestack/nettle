#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

import string
import uuid
from logging import INFO

import grpc
from flwr.common.logger import log

from generated import model_training_pb2
from generated import model_training_pb2_grpc
from model.mpc_model import MpcModule


class ModelOwner:
    """Model Owner that owns the NN model in a Nettle FL system."""

    def __init__(
        self,
        model: MpcModule,
        host: string = "localhost",
        port: int = 50051,
        initial_model_secret_id: uuid.UUID = None,
    ) -> None:
        """
        Instantiates a :class:`ModelOwner` with the given model.

        :param host: The hostname or IP address of the orchestrator
        :param port: The port on which the orchestrator listens for incoming connections
        :param model: The model owned by this :class:`ModelOwner`
        :param initial_model_secret_id: The identifier of the secret containing the initial model
        """
        self.__model = model
        self.__host = host
        self.__port = port
        self.__model_secret_id = initial_model_secret_id
        log(
            INFO,
            "Model owner instantiated talking to orchestrator at `%s:%d` using initial model stored as secret with "
            "identifier `%s`",
            self.__host,
            self.__port,
            str(self.__model_secret_id),
        )

    @property
    def model(self) -> MpcModule:
        """
        Retrieve the model owned by this :class:`ModelOwner`.

        :return: The owned model
        """
        return self.__model

    def train(self):
        """
        Triggers the FL training process.
        """
        if self.__model_secret_id is None:
            # Store the model in the MPC backend
            self.__model_secret_id = self.__model.store()
        log(
            INFO,
            "Using model parameters stored in MPC backend secret '%s'",
            self.__model_secret_id,
        )

        # Trigger the FL process by sending the identifier of the initial model to the orchestrator for latter use by
        # the clients.
        args = model_training_pb2.TrainModelParameters(
            initialModelSecretId=str(self.__model_secret_id)
        )
        log(INFO, "Triggering orchestrator with arguments '%s'", args)
        with grpc.insecure_channel(f"{self.__host}:{self.__port}") as channel:
            stub = model_training_pb2_grpc.ModelTrainingStub(channel)
            train_model_result = stub.TrainModel(args)

        # Load the final model parameters from the MPC backend
        final_model_id = train_model_result.finalModelSecretId
        log(
            INFO,
            "Loading parameters of trained model from secret '%s' stored in MPC backend",
            final_model_id,
        )
        self.__model.load(final_model_id)
