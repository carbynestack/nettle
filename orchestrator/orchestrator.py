import click

from cs_strategy import *
from concurrent import futures

import flwr as fl
import grpc
import logging
from generated import model_training_pb2
from generated import model_training_pb2_grpc

DEFAULT_NUMBER_OF_CLIENTS: int = 2


class Orchestrator(model_training_pb2_grpc.ModelTrainingServicer):

    def __init__(self, number_of_clients: int):
        print("Orchestrator initialized expecting {} client(s) to connect for training.".format(number_of_clients))
        self._number_of_clients = DEFAULT_NUMBER_OF_CLIENTS if number_of_clients is None else min(1, number_of_clients)

    def TrainModel(self, request: model_training_pb2.TrainModelParameters, context):
        print("Start training model with following parameters: {}".format(request))
        strategy: CsStrategy = CsStrategy(request.initialModelSecretId, self._number_of_clients)

        fl.server.start_server(config=fl.server.ServerConfig(num_rounds=1), strategy=strategy)

        return model_training_pb2.TrainModelResult(finalModelSecretId=strategy.amphora_model_id)


@click.command()
@click.option('--number-of-clients',
              type=int,
              required=False,
              help='Number of Nettle clients required to connect to this Orchestrator \
                    and used to run the fit as well as evaluation phase.')
def serve(number_of_clients: int):
    port = '50051'
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    model_training_pb2_grpc.add_ModelTrainingServicer_to_server(Orchestrator(number_of_clients), server)
    server.add_insecure_port('[::]:' + port)
    server.start()
    print("Orchestrator started, listening on " + port)
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    serve()
