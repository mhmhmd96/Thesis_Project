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
    def select(self, client: ClientProxy, client_cid, sorted_clients, Stype, round_type='fit') -> bool:
        """Decide whether a client should be eligible for sampling or not."""

        if round_type == 'fit':
            res = self.select_fit(client, client_cid,sorted_clients,Stype)
            return res
        else:
            res = self.select_evaluate(client, client_cid,sorted_clients,Stype)
            return res

    def select_fit(self, client: ClientProxy, client_cid, sorted_clients, Stype, round_type='fit'):
        Ip_client = {'8': 'C1', '112': 'C2', '27': 'C3', '21': 'C4',
                     '53': 'C5', '167': 'C6', '219': 'C7', '153': 'C8'}

        ip = str(client_cid).split(':')[1].split('.')[-1]
        if Stype == 2:
            if client_cid in sorted_clients:
                log(INFO, Ip_client[ip] + '  is sampled')
                return True

            log(INFO, Ip_client[ip] + ' is not sampled')
            return False
        else:
            if client_cid in sorted_clients:
                log(INFO, Ip_client[ip] + '  is sampled, Delay: ' + str(client.properties['delay']))
                return True

            log(INFO, Ip_client[ip] + ' is not sampled, Delay: ' + str(client.properties['delay']))
            return False

    def select_evaluate(self, client: ClientProxy, client_cid, sorted_clients, Stype):
        if client_cid in sorted_clients:
            return True
        return False

