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
    def select(self, client: ClientProxy, client_cid, sorted_clients, Stype, round_type='fit', ei=None) -> bool:
        """Decide whether a client should be eligible for sampling or not."""

        if round_type == 'fit':
            res = self.select_fit(client, client_cid,sorted_clients,Stype, ei)
            return res
        else:
            res = self.select_evaluate(client, client_cid,sorted_clients,Stype, ei)
            return res

    def select_fit(self, client: ClientProxy, client_cid, sorted_clients, Stype, ei=None):
        Ip_client = {'163': 'C1', '70': 'C2', '135': 'C3', '170': 'C4',
                     '171': 'C5', '188': 'C6', '17': 'C7', '251': 'C8'}

        ip = str(client_cid).split(':')[1].split('.')[-1]
        if Stype == 1:
            if client_cid in sorted_clients:
                log(INFO, Ip_client[ip] + '  is sampled, EI: ' + str(ei))
                return True

            log(INFO, Ip_client[ip] + ' is not sampled, EI: ' + str(ei))
            return False
        elif Stype == 0:
            if client_cid in sorted_clients:
                log(INFO, Ip_client[ip] + '  is sampled, Delay: ' + str(client.properties['delay']))
                return True

            log(INFO, Ip_client[ip] + ' is not sampled, Delay: ' + str(client.properties['delay']))
            return False
        else:
            if client_cid in sorted_clients:
                log(INFO, Ip_client[ip] + '  is sampled')
                return True

            log(INFO, Ip_client[ip] + ' is not sampled')
            return False

    def select_evaluate(self, client: ClientProxy, client_cid, sorted_clients, Stype):
        if client_cid in sorted_clients:
            return True
        return False

