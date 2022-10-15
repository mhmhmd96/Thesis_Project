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
"""Abstract class for criterion sampling."""


from abc import ABC, abstractmethod
from .client_proxy import ClientProxy
from logging import INFO
from flwr.common.logger import log



class Criterion(ABC):
    """Abstract class which allows subclasses to implement criterion
    sampling."""

    @abstractmethod
    def select(self, client: ClientProxy) -> bool:
        """Decide whether a client should be eligible for sampling or not."""


class CriterionImplemented (Criterion):
    def select(self, client: ClientProxy, client_cid, sorted_clients) -> bool:
        """Decide whether a client should be eligible for sampling or not."""
        sorted_cids = []
        for i in sorted_clients:
            sorted_cids.append(i[0])
        if client_cid in sorted_cids:
            log(INFO, 'A device is sampled, Delay: ' + str(client.properties['delay']))
            return True

        log(INFO, 'A device was not sampled, Delay: ' + str(client.properties['delay']))
        return False
