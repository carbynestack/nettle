from cs_strategy import *
from concurrent import futures

import flwr as fl
import grpc
import uuid
import logging
from generated import model_training_pb2
from generated import model_training_pb2_grpc


class Orchestrator(model_training_pb2_grpc.ModelTrainingServicer):
    def TrainModel(self, request, context):
        strategy: CsStrategy = CsStrategy()
        strategy.amphora_model_id = str(uuid.uuid4())

        fl.server.start_server(config=fl.server.ServerConfig(num_rounds=1), strategy=strategy)

        return model_training_pb2.TrainModelResult(finalModelSecretId=strategy.amphora_model_id)


def serve():
    port = '50051'
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    model_training_pb2_grpc.add_ModelTrainingServicer_to_server(Orchestrator(), server)
    server.add_insecure_port('[::]:' + port)
    server.start()
    print("Orchestrator started, listening on " + port)
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    serve()
