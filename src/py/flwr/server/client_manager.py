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
import random
import numpy


number_of_clients = 6
#0: sort, 1: hetergenous, 2: random ,3: normal (c1,c2,c5,c6,c7,c8)
selcectType = 1

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
        type: str = 'fit',

    ) -> List[ClientProxy]:
        """Sample a number of Flower ClientProxy instances."""
        # Block until at least num_clients are connected.
        if min_num_clients is None:
            min_num_clients = num_clients
        self.wait_for(min_num_clients)
        # Sample clients which meet the criterion
        available_cids = list(self.clients)

        sorted_cids = []
        print("Available Clients: ", available_cids)
        if criterion is not None:
            if selcectType== 0:
                sorted_cleint = self.sort_clients(available_cids, min_num_clients)
                for i in sorted_cleint:
                    sorted_cids.append(i[0])
                available_cids = [
                    cid for cid in available_cids if criterion.select(self.clients[cid], cid, sorted_cids, selcectType, type)
                ]
            elif selcectType== 1:
                sorted_cleint, eis = self.heter_clients(available_cids, min_num_clients)
                for i in sorted_cleint:
                    sorted_cids.append(i[0])
                available_cids = [
                    cid for cid in available_cids if criterion.select(self.clients[cid], cid, sorted_cids, selcectType, type, eis[cid])
                ]
            elif selcectType== 2:
                sorted_cleint = self.random_clients(available_cids, min_num_clients)
                for i in sorted_cleint:
                    sorted_cids.append(i[0])
                available_cids = [
                    cid for cid in available_cids if criterion.select(self.clients[cid], cid, sorted_cids, selcectType, type)
                ]
            else:
                sorted_cleint = self.normal_clients(available_cids)
                sorted_cids = sorted_cleint
                available_cids = [
                    cid for cid in available_cids if criterion.select(self.clients[cid], cid, sorted_cids, selcectType, type)
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

    def sort_clients(self, available_cids, min_clients):

        # Implement get_properties for all clients to set the properties variable
        for cid in available_cids:
            ins = GetPropertiesIns(config={})
            self.clients[cid].get_properties(ins=ins, timeout=None)

        # Collect the delay of all clients
        delays = {cid: self.clients[cid].properties['delay'] for cid in available_cids}

        # List of delays sorted asceding
        delays = sorted(delays.items(), key=lambda x: x[1])
        # Return the best number_of_clients of delays
        sorted_clients = delays[:number_of_clients]

        return sorted_clients

    def random_clients(self, available_cids, min_clients) :

        # Implement get_properties for all clients to set the properties variable
        for cid in available_cids:
            ins = GetPropertiesIns(config={})
            self.clients[cid].get_properties(ins=ins, timeout=None)

        # Collect the delay of all clients
        delays = {cid: self.clients[cid].properties['delay'] for cid in available_cids}

        # List of delays sorted asceding
        delays = sorted(delays.items(), key=lambda x: x[1])
        # Return the best number_of_clients of delays
        sorted_clients = random.sample(delays, number_of_clients)

        return sorted_clients

    def normal_clients(self, available_cids) :

        # Implement get_properties for all clients to set the properties variable
        for cid in available_cids:
            ins = GetPropertiesIns(config={})
            self.clients[cid].get_properties(ins=ins, timeout=None)

        sorted_clients = []
        normal_clients = [8, 112, 53, 167, 219, 153]
        # Return the best number_of_clients of delays
        for i in available_cids:
            client = i.split(":")[1].split(".")[-1]
            if int(client) in normal_clients:
                sorted_clients.append(i)

        print('sorted: ', sorted_clients)
        return sorted_clients
    def heter_clients(self, available_cids, min_clients):
        alpha = 0.5
        beta = 0.5
        maxDelay = 200
        maxCPU = 4
        maxMEM = 4
        # Implement get_properties for all clients to set the properties variable
        for cid in available_cids:
            #send_time = time.time()
            ins = GetPropertiesIns(config={})
            self.clients[cid].get_properties(ins=ins, timeout=None)

        # Collect the Performance Index of all clients
        pi = {}
        for cid in available_cids:
            properties = self.clients[cid].properties
            freeMEM = properties['freeMEM']
            usedCPU = properties['usedCPU']
            numCPU = properties['numCPU']
            delay = properties['delay']
            ei = self.EI(freeMEM=freeMEM, usedCPU=usedCPU, numCPU=numCPU, delay=delay,
                         maxMEM=maxMEM, maxCPU=maxCPU, maxDelay=maxDelay,
                         alpha=alpha, beta=beta)
            pi[cid] = ei

        # List of delays sorted asceding
        eis = sorted(pi.items(), key=lambda x: x[1], reverse=True)
        # Return the best number_of_clients of delays
        clients = eis[:number_of_clients]

        return clients, pi

    def EI(self, freeMEM, usedCPU, numCPU, delay, maxMEM=8, maxCPU=8, maxDelay=200, alpha=0.5, beta=0.5):
        # Delay
        if delay > maxDelay:
            delay = maxDelay
        delay_percent = (delay/maxDelay)
        delay_percent_inv = 1 - delay_percent

        # RAM
        # RAM in GB
        ram_gb = freeMEM / 1e+9
        available_ram = ram_gb / maxMEM

        # CPU
        available_cpu = (numCPU/maxCPU) * (1-usedCPU/100)

        # Computational Index

        ci = beta * (available_cpu) + (1-beta) * available_ram

        # Evaluation Index
        ei = alpha * ci + (1-alpha) * delay_percent_inv
        ei = ei * 100
        return ei
