import logging
import grpc

from generated.model_training_pb2 import TrainModelParameters
from generated.model_training_pb2_grpc import ModelTrainingStub


def train_model(stub):
    params = TrainModelParameters()
    final_model_id = stub.TrainModel(params)
    print('Received model ID {}'.format(final_model_id))


def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = ModelTrainingStub(channel)
        train_model(stub)


if __name__ == '__main__':
    logging.basicConfig()
    run()
