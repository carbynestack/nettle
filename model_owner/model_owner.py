import click
from logging import INFO
import uuid

import grpc
import torch
import torchvision.transforms as transforms
from torch.utils.data import DataLoader
from torchvision.datasets import CIFAR10

from flwr.common.logger import log
from generated import model_training_pb2
from generated import model_training_pb2_grpc
from model.net import Net
from tqdm import tqdm

DEFAULT_REUSE_PARAMETERS: bool = False
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
        log(INFO, "Using model parameters stored in Amphora secret %s", self.params_id)

        # Trigger the FL process by sending the identifier of the initial model to the orchestrator for latter use by
        # the clients.
        params = model_training_pb2.TrainModelParameters(initialModelSecretId=str(self.params_id))
        log(INFO, "Triggering orchestrator with parameters %s", params)
        with grpc.insecure_channel('localhost:50051') as channel:
            stub = model_training_pb2_grpc.ModelTrainingStub(channel)
            train_model_result = stub.TrainModel(params)

        final_model_id = train_model_result.finalModelSecretId
        # Load the final model parameters from Amphora
        log(INFO, "Loading parameters of trained model from Amphora secret %s", final_model_id)
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
        for images, labels in tqdm(test_loader):
            outputs = model(images.to(DEVICE))
            labels = labels.to(DEVICE)
            loss += criterion(outputs, labels).item()
            total += labels.size(0)
            correct += (torch.max(outputs.data, 1)[1] == labels).sum().item()
    return loss / len(test_loader.dataset), correct / total


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

    log(INFO, 'Accuracy: %s, Loss: %s', accuracy, loss)


@click.command()
@click.option('--reuse-params',
              required=False,
              default=DEFAULT_REUSE_PARAMETERS,
              help='Identifier of the Amphora secret containing the model parameters.')
def model_owner(reuse_params):
    param_id = None if reuse_params is None else uuid.UUID(reuse_params)
    run(param_id)


if __name__ == '__main__':
    model_owner()
