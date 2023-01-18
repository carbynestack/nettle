import click
import logging
import uuid

import grpc
import torch
from torch.distributions import transforms
from torch.utils.data import DataLoader
from torchvision.datasets import CIFAR10

from generated import model_training_pb2
from generated import model_training_pb2_grpc
from model.net import Net

DEVICE = torch.device("cpu")


class ModelOwner:
    """The Model Owner own a NN model in a FL process."""

    def __init__(self, model, params_id: uuid.UUID = None) -> None:
        self.model = model.to(DEVICE)
        self.params_id = params_id

    def train(self):
        if self.params_id is None:
            # Store the model in Amphora
            self.params_id = self.model.store()

        # Trigger the FL process by sending the identifier of the initial model to the orchestrator for latter use by
        # the clients.
        params = model_training_pb2.TrainModelParameters(initialModelSecretId=str(self.params_id))
        with grpc.insecure_channel('localhost:50051') as channel:
            stub = model_training_pb2_grpc.ModelTrainingStub(channel)
            final_model_id = stub.TrainModel(params)

        # Load the final model parameters from Amphora
        self.model.load(final_model_id)


def load_test_data():
    """Load CIFAR-10 test data."""
    transform = transforms.Compose(
        [transforms.ToTensor(), transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))]
    )
    test_set = CIFAR10(".", train=False, download=True, transform=transform)
    test_loader = DataLoader(test_set, batch_size=32)
    num_examples = len(test_set)
    return test_loader, num_examples


def validate_model(model, test_loader):
    """Validate the network on the test set."""
    criterion = torch.nn.CrossEntropyLoss()
    correct, total, loss = 0, 0, 0.0
    with torch.no_grad():
        for data in test_loader:
            images, labels = data[0].to(DEVICE), data[1].to(DEVICE)
            outputs = model(images)
            loss += criterion(outputs, labels).item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    accuracy = correct / total
    return loss, accuracy


def run(param_id: uuid.UUID = None):
    # Instantiate our model
    model = Net()

    # Create the model owner that is in control of the model
    mo = ModelOwner(model, params_id=param_id)

    # Perform the distributed FL training process
    mo.train()

    # Load test data and  check the accuracy of the trained model
    loader, num_examples = load_test_data()
    loss, accuracy = validate_model(mo.model, loader)
    logging.info('Accuracy: %d, Loss: %d', accuracy, loss)


@click.command()
@click.option('--reuse-params', required=False, help='Identifier of the Amphora secret containing the model parameters.')
def model_owner(reuse_params):
    param_id = reuse_params is None if None else uuid.UUID(reuse_params)
    run(param_id)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    model_owner()
