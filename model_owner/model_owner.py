import logging

import grpc
import torch
from torch.distributions import transforms
from torch.utils.data import DataLoader
from torchvision.datasets import CIFAR10

from generated import model_training_pb2
from generated import model_training_pb2_grpc
from model.net import Net
from utils.cli import CLI, Provider
from utils.spdz_pytorch_conversion import float32_tensor_to_sfloat_array, sfloat_array_to_float32_tensor


def flatten(l):
    return [item for sublist in l for item in sublist]


def length(tensor):
    l = 1
    for dim in tensor.shape:
        l *= dim
    return l


DEVICE = torch.device("cpu")


class ModelOwner:
    def __init__(self) -> None:
        self.model = Net().to(DEVICE)
        self.cli = CLI(
            prime="198766463529478683931867765928436695041",
            r="141515903391459779531506841503331516415",
            r_inv="133854242216446749056083838363708373830",
            providers=[
                Provider(base_url="http://apollo.bocse.carbynestack.io/"),
                Provider(base_url="http://starbuck.bocse.carbynestack.io/")
            ])

    def upload_model(self):
        """Serializes the model into a MP-SPDZ sfloat array and uploads that to Amphora."""
        data = []
        items = self.model.state_dict().items()
        for layer, params in items:
            logging.info("Collecting %d parameters for layer '%s'", length(params), layer)
            data += flatten(float32_tensor_to_sfloat_array(params, shift=True))
        secret_id = self.cli.create_secret(values=data)
        logging.info('Uploaded %d-element model to Amphora with ID: %s', len(data), secret_id)
        return secret_id

    def update_model(self, data):
        """Updates the model from the provided data which is expected to be a 1d array of MP-SPDZ sfloat parameters."""

        # "Reshape" to get an array of 4-element arrays (one for each MP-SPDZ sfloat).
        remaining = []
        for i in range(len(data) // 4):
            remaining.append(data[i * 4:(i + 1) * 4])

        # Traverse layers one by one updating the parameters
        for layer, params in self.model.state_dict().items():
            logging.info("Processing layer %s of shape %s", layer, params.shape)
            d = remaining[:length(params)]
            remaining = remaining[length(params):]
            t = sfloat_array_to_float32_tensor(d, params.shape, shift=True)
            params.copy_(t)
            logging.info("Copied %d parameters to layer %s", len(t), layer)

    def download_model(self, secret_id):
        values, _ = self.cli.get_secret(secret_id)
        return values

    def train(self):
        initialModelId = self.upload_model()
        params = model_training_pb2.TrainModelParameters(initialModelSecretId=initialModelId)
        with grpc.insecure_channel('localhost:50051') as channel:
            stub = model_training_pb2_grpc.ModelTrainingStub(channel)
            final_model_id = stub.TrainModel(params)
        model_params = self.download_model(final_model_id)
        self.update_model(model_params)


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


def run():
    mo = ModelOwner()
    mo.train()
    loader, num_examples = load_test_data()
    loss, accuracy = validate_model(mo.model, loader)
    logging.info('Accuracy: %d, Loss: %d', accuracy, loss)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    run()
