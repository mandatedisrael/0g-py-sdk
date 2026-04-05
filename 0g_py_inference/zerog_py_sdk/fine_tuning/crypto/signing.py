import time

from web3 import Web3
from eth_account.messages import encode_defunct
from eth_account.signers.local import LocalAccount


def get_nonce() -> int:
    return int(time.time() * 1000) * 10000 + 40


def sign_request(
    account: LocalAccount,
    user_address: str,
    nonce: int,
    dataset_root_hash: str,
) -> str:
    message_hash = Web3.solidity_keccak(
        ["address", "uint256", "string"],
        [Web3.to_checksum_address(user_address), nonce, dataset_root_hash],
    )
    signable = encode_defunct(primitive=message_hash)
    signed = account.sign_message(signable)
    return "0x" + signed.signature.hex()


def sign_task_id(account: LocalAccount, task_id: str) -> str:
    task_id_hex = "0x" + task_id.replace("-", "")
    message_hash = Web3.solidity_keccak(["bytes"], [task_id_hex])
    signable = encode_defunct(primitive=message_hash)
    signed = account.sign_message(signable)
    return "0x" + signed.signature.hex()


def sign_dataset_upload(
    account: LocalAccount, user_address: str, timestamp: int
) -> str:
    message = user_address + str(timestamp)
    message_hash = Web3.keccak(text=message)
    signable = encode_defunct(primitive=message_hash)
    signed = account.sign_message(signable)
    return "0x" + signed.signature.hex()
