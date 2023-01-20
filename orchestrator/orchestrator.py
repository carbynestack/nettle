import click

import cs_strategy
from concurrent import futures

import flwr as fl
import grpc
from logging import DEBUG
from flwr.common.logger import log
from generated import model_training_pb2
from generated import model_training_pb2_grpc

DEFAULT_NUMBER_OF_CLIENTS: int = 2
DEFAULT_NUMBER_OF_ROUNDS: int = 3


class Orchestrator(model_training_pb2_grpc.ModelTrainingServicer):
    def __init__(self, number_of_clients: int, number_of_rounds: int):
        self._number_of_clients = (
            DEFAULT_NUMBER_OF_CLIENTS
            if number_of_clients is None
            else max(1, number_of_clients)
        )
        self._number_of_rounds = (
            DEFAULT_NUMBER_OF_ROUNDS
            if number_of_rounds is None
            else max(1, number_of_rounds)
        )
        log(
            DEBUG,
            (
                "Orchestrator initialized expecting %d client(s) to connect for %d"
                " round(s) of training."
            ),
            self._number_of_clients,
            self._number_of_rounds,
        )

    def TrainModel(self, request: model_training_pb2.TrainModelParameters, context):
        log(DEBUG, "Start training model with following parameters: %s", request)
        strategy: cs_strategy.CsStrategy = cs_strategy.CsStrategy(
            request.initialModelSecretId, self._number_of_clients
        )

        fl.server.start_server(
            config=fl.server.ServerConfig(num_rounds=self._number_of_rounds),
            strategy=strategy,
        )
        training_result = model_training_pb2.TrainModelResult(
            finalModelSecretId=strategy.amphora_model_id
        )
        log(DEBUG, "Finished with training result: %s", training_result)
        return training_result


@click.command()
@click.option(
    "--number-of-clients",
    type=int,
    default=DEFAULT_NUMBER_OF_CLIENTS,
    required=False,
    help=(
        "Number of Nettle clients required to connect to this Orchestrator             "
        "        and used to run the fit as well as evaluation phase."
    ),
)
@click.option(
    "--number-of-rounds",
    type=int,
    default=DEFAULT_NUMBER_OF_ROUNDS,
    required=False,
    help="Number of training rounds.",
)
def serve(number_of_clients: int, number_of_rounds: int):
    port = "50051"
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    model_training_pb2_grpc.add_ModelTrainingServicer_to_server(
        Orchestrator(number_of_clients, number_of_rounds), server
    )
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Orchestrator started, listening on " + port)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
