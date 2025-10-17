"""
Transaction-related models.

Ported from official TypeScript SDK:
0g_py_inference/node_modules/@0glabs/0g-ts-sdk/lib.commonjs/types.d.ts
0g_py_inference/node_modules/@0glabs/0g-ts-sdk/lib.commonjs/indexer/types.d.ts
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class RetryOpts:
    """
    Retry options for transactions.

    TypeScript definition:
    export type RetryOpts = {
        Retries: number;
        Interval: number;
        MaxGasPrice: number;
        TooManyDataRetries?: number;
    };
    """
    Retries: int
    Interval: int
    MaxGasPrice: int
    TooManyDataRetries: Optional[int] = None


@dataclass
class TransactionOptions:
    """
    Transaction options.

    TypeScript definition:
    export interface TransactionOptions {
        gasPrice?: bigint;
        gasLimit?: bigint;
    }
    """
    gasPrice: Optional[int] = None
    gasLimit: Optional[int] = None
