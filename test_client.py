import warnings
from collections import OrderedDict

import flwr as fl
import torch
from torch.utils.data import DataLoader
from torchvision.datasets import CIFAR10
from torchvision.transforms import Compose, Normalize, ToTensor

from client.nettle_client import NettleClient
from model.net import Net

warnings.filterwarnings("ignore", category=UserWarning)
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

def load_data():
    """Load CIFAR-10 (training and test set)."""
    trf = Compose([ToTensor(), Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])
    trainset = CIFAR10("./data", train=True, download=True, transform=trf)
    testset = CIFAR10("./data", train=False, download=True, transform=trf)
    return DataLoader(trainset, batch_size=32, shuffle=True), DataLoader(testset)

cs_net = Net().to(DEVICE)
trainloader, testloader = load_data()

nettleClient = NettleClient(DEVICE, cs_net, trainloader, testloader)

# Start Flower client
fl.client.start_numpy_client(
    server_address="127.0.0.1:8080",
    client=nettleClient,
)
