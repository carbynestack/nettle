#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#
from typing import Tuple

import click
import flwr as fl
import torch
from torch.utils.data import DataLoader
from torchvision.datasets import CIFAR10
from torchvision.transforms import Compose, Normalize, ToTensor

from client.nettle_client import NettleClient
from examples.cifar_10.cifar_net import Net
from mpc_client.carbyne_stack_mpc_client import CarbyneStackMpcClient, Provider
from mpc_client.mp_spdz_mpc_client import MpSpdzMpcClient

#: The default MPC backend to use
DEFAULT_MPC_BACKEND: str = "MP-SPDZ"

#: Torch device to use for training and inference
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


def load_data() -> Tuple[DataLoader, DataLoader]:
    """
    Load CIFAR-10 (training and test set).

    :return: :class:`DataLoader` instances for training and test dataset
    """
    trf = Compose([ToTensor(), Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])
    train_set = CIFAR10("./data", train=True, download=True, transform=trf)
    test_set = CIFAR10("./data", train=False, download=True, transform=trf)
    return DataLoader(train_set, batch_size=32, shuffle=True), DataLoader(test_set)


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
@click.command()
@click.option(
    "--request-delay",
    type=int,
    default=0,
    required=False,
    help="A non-negative delay in seconds to sleep before invoking MPC backend operations.",
)
def cifar_10_client(mpc_backend: str, request_delay: int):
    """
    Launches a CIFAR-10 Nettle client
    """
    if mpc_backend == "MP-SPDZ":
        mpc_client = MpSpdzMpcClient()
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
    net = Net(mpc_client, max(0, request_delay)).to(DEVICE)
    train_loader, test_loader = load_data()

    nettle_client = NettleClient(DEVICE, net, train_loader, test_loader)

    # Start Flower client
    fl.client.start_numpy_client(
        # TODO Make server address configurable (see also orchestrator)
        server_address="localhost:50050",
        client=nettle_client,
    )


if __name__ == "__main__":
    cifar_10_client()
