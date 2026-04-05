from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Quota:
    cpu_count: int
    node_memory: int
    gpu_count: int
    node_storage: int
    gpu_type: str


@dataclass
class FineTuningRefund:
    index: int
    amount: int
    created_at: int
    deprecated_processed: bool


@dataclass
class Deliverable:
    id: str
    model_root_hash: bytes
    encrypted_secret: bytes
    acknowledged: bool
    timestamp: int
    settled: bool


@dataclass
class FineTuningAccountDetails:
    user: str
    provider: str
    nonce: int
    balance: int
    pending_refund: int
    refunds: List[FineTuningRefund] = field(default_factory=list)
    additional_info: str = ""
    deliverables: List[Deliverable] = field(default_factory=list)
    valid_refunds_length: int = 0
    deliverables_head: int = 0
    deliverables_count: int = 0
    acknowledged: bool = False

    @property
    def locked_balance(self) -> int:
        return self.balance - self.pending_refund


@dataclass
class FineTuningAccountDetail:
    account: FineTuningAccountDetails
    refunds: List[dict] = field(default_factory=list)


@dataclass
class FineTuningService:
    provider: str
    url: str
    quota: Quota
    price_per_token: int
    occupied: bool
    models: List[str] = field(default_factory=list)
    tee_signer_address: str = ""
    tee_signer_acknowledged: bool = False


@dataclass
class Task:
    id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    user_address: str = ""
    pre_trained_model_hash: str = ""
    dataset_hash: str = ""
    training_params: str = ""
    fee: str = "0"
    nonce: str = ""
    signature: str = ""
    progress: Optional[str] = None
    deliver_index: Optional[str] = None
    wait: bool = False

    def to_dict(self) -> dict:
        d = {
            "userAddress": self.user_address,
            "preTrainedModelHash": self.pre_trained_model_hash,
            "datasetHash": self.dataset_hash,
            "trainingParams": self.training_params,
            "fee": self.fee,
            "nonce": self.nonce,
            "signature": self.signature,
            "wait": self.wait,
        }
        if self.id is not None:
            d["id"] = self.id
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            id=data.get("id"),
            created_at=data.get("createdAt"),
            updated_at=data.get("updatedAt"),
            user_address=data.get("userAddress", ""),
            pre_trained_model_hash=data.get("preTrainedModelHash", ""),
            dataset_hash=data.get("datasetHash", ""),
            training_params=data.get("trainingParams", ""),
            fee=data.get("fee", "0"),
            nonce=data.get("nonce", ""),
            signature=data.get("signature", ""),
            progress=data.get("progress"),
            deliver_index=data.get("deliverIndex"),
            wait=data.get("wait", False),
        )


@dataclass
class CustomizedModel:
    name: str
    hash: str
    image: str = ""
    data_type: str = ""
    training_script: str = ""
    description: str = ""
    tokenizer: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "CustomizedModel":
        return cls(
            name=data.get("name", ""),
            hash=data.get("hash", ""),
            image=data.get("image", ""),
            data_type=data.get("dataType", ""),
            training_script=data.get("trainingScript", ""),
            description=data.get("description", ""),
            tokenizer=data.get("tokenizer", ""),
        )


@dataclass
class TdxQuoteResponse:
    raw_report: str
    signing_address: str
