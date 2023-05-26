#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

import uuid
from logging import INFO
from pathlib import Path
from typing import Tuple

import click
import torch
import torchvision.transforms as transforms
from flwr.common.logger import log
from torch.utils.data import DataLoader
from torchvision.datasets import CIFAR10
from tqdm import tqdm

from examples.cifar_10.cifar_net import Net
from model_owner.model_owner import ModelOwner
from mpc_client.carbyne_stack_mpc_client import CarbyneStackMpcClient, Provider
from mpc_client.mp_spdz_mpc_client import MpSpdzMpcClient
from mpc_client.mpc_client import MpcClient

#: Torch device to use for training and inference
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

#: The default MPC backend to use
DEFAULT_MPC_BACKEND: str = "MP-SPDZ"


def load_test_data() -> Tuple[DataLoader, int]:
    """
    Load CIFAR-10 test data.

    :return: :class:`DataLoader` instance for the test dataset and the number of contained samples
    """
    transform = transforms.Compose(
        [transforms.ToTensor(), transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))]
    )
    test_set = CIFAR10(".", train=False, download=True, transform=transform)
    test_loader = DataLoader(test_set, batch_size=32)
    num_examples = len(test_set)
    return test_loader, num_examples


def validate_model(model, test_loader):
    """
    Validates the model using the test dataset.

    :return: The average loss and the accuracy
    """
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


def run(mpc_client: MpcClient, initial_model_secret_id: uuid.UUID = None):
    """
    Performs a federated learning run.

    :param mpc_client: The :class:`MpcClient` used to talk to the MPC backend
    :param initial_model_secret_id: The identifier of the secret containing the initial model
    """
    # Instantiate our model
    model = Net(mpc_client)

    # Create the model owner that is in control of the model
    mo = ModelOwner(model.to(DEVICE), initial_model_secret_id=initial_model_secret_id)

    # Perform the distributed FL training process
    mo.train()

    # Load test data and  check the accuracy of the trained model
    loader, num_examples = load_test_data()
    loss, accuracy = validate_model(mo.model, loader)

    log(INFO, "Accuracy: %s, Loss: %s", accuracy, loss)


@click.command()
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
@click.option(
    "--initial-model-secret-id",
    required=False,
    help="Identifier of the MPC secret containing the model parameters.",
)
def model_owner(mpc_backend: MpcClient, initial_model_secret_id: str = None):
    """
    Launches a CIFAR-10 Nettle model owner
    """
    if mpc_backend == "MP-SPDZ":
        mpc_client = MpSpdzMpcClient()
        mpc_client.add_program(Path("fedavg.mp-spdz.mpc"))
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
    else:
        raise ValueError(f"unsupported MPC backend {mpc_backend}")
    param_id = (
        None if initial_model_secret_id is None else uuid.UUID(initial_model_secret_id)
    )
    run(mpc_client, param_id)


if __name__ == "__main__":
    model_owner()
