from typing import List, Optional, Tuple

from web3 import Web3

from ...exceptions import ContractError, ConfigurationError
from ...constants import get_contract_addresses, get_rpc_url
from ..contract.abi import FINE_TUNING_SERVING_ABI
from ..contract.contract import FineTuningContract
from ..contract.types import FineTuningService
from ..constants import get_model_config


class ReadOnlyFineTuningBroker:
    def __init__(self, web3: Web3, contract_address: str):
        self._web3 = web3
        self._contract_address = contract_address
        self._contract = web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=FINE_TUNING_SERVING_ABI,
        )

    def list_service(
        self, include_unacknowledged: bool = False
    ) -> List[FineTuningService]:
        try:
            raw_services = self._contract.functions.getAllServices().call()
            services = [self._parse_service(s) for s in raw_services]
            if not include_unacknowledged:
                services = [s for s in services if s.tee_signer_acknowledged]
            return services
        except Exception as e:
            raise ContractError("getAllServices", str(e))

    def list_model(self) -> Tuple[List[tuple], List[tuple]]:
        try:
            chain_id = self._web3.eth.chain_id
            model_config = get_model_config(chain_id)
            standard_models = list(model_config.items())

            customized_models = []
            try:
                import requests

                services = self.list_service(include_unacknowledged=True)
                for service in services:
                    try:
                        resp = requests.get(
                            f"{service.url.rstrip('/')}/v1/model", timeout=10
                        )
                        if resp.ok:
                            for item in resp.json():
                                customized_models.append(
                                    (
                                        item.get("name", ""),
                                        {
                                            "description": item.get("description", ""),
                                            "provider": service.provider,
                                        },
                                    )
                                )
                    except Exception:
                        pass
            except Exception:
                pass

            return (standard_models, customized_models)
        except Exception as e:
            raise ContractError("listModel", str(e))

    @staticmethod
    def _parse_service(raw) -> FineTuningService:
        from ..contract.types import Quota

        return FineTuningService(
            provider=raw[0],
            url=raw[1],
            quota=Quota(
                cpu_count=raw[2][0],
                node_memory=raw[2][1],
                gpu_count=raw[2][2],
                node_storage=raw[2][3],
                gpu_type=raw[2][4],
            ),
            price_per_token=raw[3],
            occupied=raw[4],
            models=list(raw[5]) if raw[5] else [],
            tee_signer_address=raw[6],
            tee_signer_acknowledged=raw[7],
        )


def create_read_only_fine_tuning_broker(
    network: Optional[str] = None,
    rpc_url: Optional[str] = None,
    chain_id: Optional[int] = None,
) -> ReadOnlyFineTuningBroker:
    try:
        if rpc_url is None:
            if network == "mainnet":
                rpc_url = get_rpc_url("mainnet")
            else:
                rpc_url = get_rpc_url("testnet")

        web3 = Web3(Web3.HTTPProvider(rpc_url))
        if not web3.is_connected():
            raise ConfigurationError(f"Failed to connect to RPC: {rpc_url}")

        if chain_id is None:
            chain_id = web3.eth.chain_id

        if network:
            addresses = get_contract_addresses(network=network)
        else:
            addresses = get_contract_addresses(chain_id=chain_id)

        return ReadOnlyFineTuningBroker(web3, addresses.fine_tuning)

    except (ConfigurationError, ContractError):
        raise
    except Exception as e:
        raise ConfigurationError(f"Failed to create read-only broker: {e}")
