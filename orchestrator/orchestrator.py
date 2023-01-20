#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

import uuid
from concurrent import futures
from logging import DEBUG, INFO

import click
import flwr as fl
import grpc
from flwr.common.logger import log

import mpc_strategy
from generated import model_training_pb2
from generated import model_training_pb2_grpc
from mpc_client.carbyne_stack_mpc_client import CarbyneStackMpcClient, Provider
from mpc_client.mp_spdz_mpc_client import MpSpdzMpcClient
from mpc_client.mpc_client import MpcClient

#: The default number of clients expected by the orchestrator
DEFAULT_NUMBER_OF_CLIENTS: int = 2

#: The default number of rounds of federated learning
DEFAULT_NUMBER_OF_ROUNDS: int = 2

#: The default port the orchestrator listens on for incoming requests from model owners
DEFAULT_PORT: int = 50051

#: The default MPC backend to use
DEFAULT_MPC_BACKEND: str = "MP-SPDZ"


class Orchestrator(model_training_pb2_grpc.ModelTrainingServicer):
    """Orchestrator responsible for coordinating the federated learning process in a Nettle system."""

    def __init__(
        self,
        mpc_client: MpcClient,
        mpc_application_name: str,
        number_of_clients: int = DEFAULT_NUMBER_OF_CLIENTS,
        number_of_rounds: int = DEFAULT_NUMBER_OF_ROUNDS,
    ):
        """
        Instantiates an :class:`Orchestrator` with the MPC client.

        :param mpc_client: The :class:`MpcClient` used to talk to the MPC backend
        :param mpc_application_name: The name of the MPC application used to perform the secure aggregation
        :param number_of_clients: The number of clients expected by the orchestrator
        :param number_of_rounds: The number of rounds of federated learning to be performed
        """
        self.__mpc_client = mpc_client
        self.__mpc_application_name = mpc_application_name
        if number_of_clients < 1:
            raise ValueError("number of clients should at least 1")
        self.__number_of_clients = number_of_clients
        if number_of_rounds < 1:
            raise ValueError("number of rounds should at least 1")
        self.__number_of_rounds = number_of_rounds
        log(
            DEBUG,
            (
                "Orchestrator initialized expecting %d client(s) to connect for %d "
                "round(s) of federated learning."
            ),
            self.__number_of_clients,
            self.__number_of_rounds,
        )

    def TrainModel(self, request: model_training_pb2.TrainModelParameters, context):
        log(
            INFO,
            "Received request for initial model secret with identifier '%s'",
            request.initialModelSecretId,
        )
        strategy = mpc_strategy.MpcStrategy(
            self.__mpc_client,
            self.__mpc_application_name,
            uuid.UUID(request.initialModelSecretId),
            self.__number_of_clients,
        )

        fl.server.start_server(
            # TODO
            #  Make this port configurable. This requires coming up with some sensible names for the two interfaces
            #  the orchestrator exposes, i.e., that towards model owners and those towards Nettle / Flower clients
            server_address="localhost:50050",
            config=fl.server.ServerConfig(num_rounds=self.__number_of_rounds),
            strategy=strategy,
        )
        training_result = model_training_pb2.TrainModelResult(
            finalModelSecretId=str(strategy.amphora_model_id)
        )
        log(
            INFO,
            "Finished federated learning with final model stored in secret with identifier '%s'",
            training_result.finalModelSecretId,
        )
        return training_result


@click.command()
@click.option(
    "--number-of-clients",
    type=int,
    default=DEFAULT_NUMBER_OF_CLIENTS,
    show_default=True,
    required=False,
    help="""
    Number of Nettle clients required to connect to this Orchestrator and used to run the fit as well as the
    evaluation phase.
    """,
)
@click.option(
    "--number-of-rounds",
    type=int,
    default=DEFAULT_NUMBER_OF_ROUNDS,
    show_default=True,
    required=False,
    help="""
    Number of federated learning rounds to be performed.
    """,
)
@click.option(
    "--port",
    type=int,
    default=DEFAULT_PORT,
    show_default=True,
    required=False,
    help="""
    Port the orchestrator listens on for incoming requests from model owners.
    """,
)
@click.option(
    "--mpc-backend",
    type=click.Choice(["MP-SPDZ", "CS"], case_sensitive=False),
    default=DEFAULT_MPC_BACKEND,
    show_default=True,
    required=False,
    help="""
    MPC backend to use for performing the secure aggregation.
    """,
)
def serve(number_of_clients: int, number_of_rounds: int, port: int, mpc_backend: str):
    """
    Launches a Nettle orchestrator
    """
    server = grpc.server(futures.ThreadPoolExecutor())
    if mpc_backend == "MP-SPDZ":
        mpc_client = MpSpdzMpcClient()
        mpc_application_name = "fedavg.mp-spdz"
    elif mpc_backend == "CS":
        # TODO Make the CS parameters configurable
        mpc_client = CarbyneStackMpcClient(
            prime=198766463529478683931867765928436695041,
            r=141515903391459779531506841503331516415,
            r_inv=133854242216446749056083838363708373830,
            providers=[
                Provider(base_url="http://apollo.bocse.carbynestack.io/"),
                Provider(base_url="http://starbuck.bocse.carbynestack.io/"),
            ],
        )
        mpc_application_name = "ephemeral-generic.default"
    else:
        raise ValueError(f"unsupported MPC backend {mpc_backend}")
    model_training_pb2_grpc.add_ModelTrainingServicer_to_server(
        Orchestrator(
            mpc_client, mpc_application_name, number_of_clients, number_of_rounds
        ),
        server,
    )
    server.add_insecure_port("[::]:" + str(port))
    server.start()
    print(
        f"Orchestrator launched with {mpc_backend} MPC backend, listening on port {port}"
    )
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
