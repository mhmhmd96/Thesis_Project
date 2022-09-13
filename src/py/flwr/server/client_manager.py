# Copyright 2020 Adap GmbH. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Flower ClientManager."""


import random
import threading
from abc import ABC, abstractmethod
from logging import INFO
from typing import Dict, List, Optional
from flwr.common.logger import log
from .client_proxy import ClientProxy
from .criterion import Criterion

import time
from flwr.common import GetPropertiesIns
import statistics
import numpy



class ClientManager(ABC):
    """Abstract base class for managing Flower clients."""

    @abstractmethod
    def num_available(self) -> int:
        """Return the number of available clients."""

    @abstractmethod
    def register(self, client: ClientProxy) -> bool:
        """Register Flower ClientProxy instance.

        Returns:
            bool: Indicating if registration was successful
        """

    @abstractmethod
    def unregister(self, client: ClientProxy) -> None:
        """Unregister Flower ClientProxy instance."""

    @abstractmethod
    def all(self) -> Dict[str, ClientProxy]:
        """Return all available clients."""

    @abstractmethod
    def wait_for(self, num_clients: int, timeout: int) -> bool:
        """Wait until at least `num_clients` are available."""

    @abstractmethod
    def sample(
        self,
        num_clients: int,
        min_num_clients: Optional[int] = None,
        criterion: Optional[Criterion] = None,
    ) -> List[ClientProxy]:
        """Sample a number of Flower ClientProxy instances."""


class SimpleClientManager(ClientManager):
    """Provides a pool of available clients."""

    def __init__(self) -> None:
        self.clients: Dict[str, ClientProxy] = {}
        self._cv = threading.Condition()

    def __len__(self) -> int:
        return len(self.clients)

    def wait_for(self, num_clients: int, timeout: int = 86400) -> bool:
        """Block until at least `num_clients` are available or until a timeout
        is reached.

        Current timeout default: 1 day.
        """
        with self._cv:
            return self._cv.wait_for(
                lambda: len(self.clients) >= num_clients, timeout=timeout
            )

    def num_available(self) -> int:
        """Return the number of available clients."""
        return len(self)

    def register(self, client: ClientProxy) -> bool:
        """Register Flower ClientProxy instance.

        Returns:
            bool: Indicating if registration was successful. False if ClientProxy is
                already registered or can not be registered for any reason
        """
        if client.cid in self.clients:
            return False

        self.clients[client.cid] = client
        with self._cv:
            self._cv.notify_all()

        return True

    def unregister(self, client: ClientProxy) -> None:
        """Unregister Flower ClientProxy instance.

        This method is idempotent.
        """
        if client.cid in self.clients:
            del self.clients[client.cid]

            with self._cv:
                self._cv.notify_all()

    def all(self) -> Dict[str, ClientProxy]:
        """Return all available clients."""
        return self.clients

    def sample(
        self,
        num_clients: int,
        min_num_clients: Optional[int] = None,
        criterion: Optional[Criterion] = None,
    ) -> List[ClientProxy]:
        """Sample a number of Flower ClientProxy instances."""
        # Block until at least num_clients are connected.
        if min_num_clients is None:
            min_num_clients = num_clients
        self.wait_for(min_num_clients)
        # Sample clients which meet the criterion
        available_cids = list(self.clients)
        threshold = self.threshold()
        if criterion is not None:
            available_cids = [
                cid for cid in available_cids if criterion.select(self.clients[cid], threshold)
            ]

        if num_clients > len(available_cids):
            log(
                INFO,
                "Sampling failed: number of available clients"
                " (%s) is less than number of requested clients (%s).",
                len(available_cids),
                num_clients,
            )
            return []

        sampled_cids = random.sample(available_cids, num_clients)
        return [self.clients[cid] for cid in sampled_cids]

    def threshold(self) -> float:
        # Define all clients (N')
        available_cids = list(self.clients)
        print("Available Clients: ", available_cids)
        # Implement get_properties for all clients to set the properties variable
        for cid in available_cids:
            send_time = time.time()
            ins = GetPropertiesIns(config={'time': send_time})
            self.clients[cid].get_properties(ins=ins, timeout=None)

        # Collect the IEs of all clients
        IEs = [self.clients[cid].properties['IE'] for cid in available_cids]

        # Average and Standard Deviation
        mean = statistics.mean(IEs)
        std = statistics.stdev(IEs)
        # Cube mean
        cube_mean = 0
        for i in IEs:
            cube_mean += (i - mean) ** 3

        # Symmetry Coefficient
        symmetry_index = cube_mean / (std ** 3)

        # Get the quartiles of all IEs
        quartiles = numpy.quantile(IEs, [0.25, 0.5, 0.75, 1])
        q1 = quartiles[0]
        q3 = quartiles[2]

        # Define the threshold of each state
        states = {'symmetric': (mean - std), 'positive_asymmetry': q1, 'negative_asymmetry': (q1 - 1.5 * (q3 - q1))}
        if symmetry_index > 0.35:
            threshold = states['positive_asymmetry']
        elif symmetry_index < -1.2:
            threshold = states['negative_asymmetry']
        else:
            threshold = states['symmetric']
        print("Threshold: ", threshold)
        return threshold
