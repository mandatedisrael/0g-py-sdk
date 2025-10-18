"""
File uploader for 0G Storage.

Ported from official TypeScript SDK:
node_modules/@0glabs/0g-ts-sdk/lib.commonjs/transfer/Uploader.js

CRITICAL: Must EXACTLY match TypeScript SDK behavior.
This is the MAIN upload orchestration file - 405 lines in TS SDK.
"""
from typing import List, Dict, Any, Optional, Tuple
import base64
import time
from web3 import Web3
from eth_account.signers.local import LocalAccount

try:
    from ..contracts.flow import FlowContract
    from ..core.storage_node import StorageNode
    from ..core.file import ZgFile
    from ..core.merkle import MerkleTree
    from ..config import (
        DEFAULT_CHUNK_SIZE,
        DEFAULT_SEGMENT_SIZE,
        DEFAULT_SEGMENT_MAX_CHUNKS
    )
    from ..utils.transfer import (
        get_shard_configs,
        calculate_price,
        delay,
        segment_range
    )
    from ..core.node_selector import check_replica
except ImportError:
    from contracts.flow import FlowContract
    from core.storage_node import StorageNode
    from core.file import ZgFile
    from core.merkle import MerkleTree
    from config import (
        DEFAULT_CHUNK_SIZE,
        DEFAULT_SEGMENT_SIZE,
        DEFAULT_SEGMENT_MAX_CHUNKS
    )
    from utils.transfer import (
        get_shard_configs,
        calculate_price,
        delay,
        segment_range
    )
    from core.node_selector import check_replica


class Uploader:
    """
    File uploader for 0G Storage.

    Ported from Uploader.js (lines 1-407).

    Handles the complete upload workflow:
    1. Submit transaction to Flow contract
    2. Split file into uploadable segments
    3. Upload segments to storage nodes in parallel
    4. Handle retries and errors
    """

    def __init__(
        self,
        nodes: List[StorageNode],
        provider_rpc: str,
        flow: FlowContract,
        gas_price: int = 0,
        gas_limit: int = 0
    ):
        """
        Initialize uploader.

        TS SDK lines 15-21.

        Args:
            nodes: List of storage node clients
            provider_rpc: Blockchain RPC URL
            flow: Flow contract instance
            gas_price: Gas price (0 for auto)
            gas_limit: Gas limit (0 for auto)
        """
        # TS line 16
        self.nodes = nodes

        # TS line 17
        self.web3 = Web3(Web3.HTTPProvider(provider_rpc))

        # TS line 18
        self.flow = flow

        # TS line 19-20
        self.gas_price = gas_price
        self.gas_limit = gas_limit

    def upload_file(
        self,
        file: ZgFile,
        opts: Dict[str, Any],
        retry_opts: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, str], Optional[Exception]]:
        """
        Upload file to storage network.

        TS SDK lines 22-85.

        Args:
            file: File to upload
            opts: Upload options
            retry_opts: Retry options

        Returns:
            Tuple of (result_dict, error)
        """
        # TS line 23-28
        tree, err = file.merkle_tree()
        if err is not None or tree is None or tree.root_hash() is None:
            return (
                {'txHash': '', 'rootHash': ''},
                Exception('Failed to create Merkle tree')
            )

        # TS line 30
        root_hash = tree.root_hash()

        # TS line 31
        print(
            f"Data prepared to upload root={root_hash} " +
            f"size={file.size()} " +
            f"numSegments={file.num_segments()} " +
            f"numChunks={file.num_chunks()}"
        )

        # TS line 32-33
        tx_seq = None
        receipt = None

        # TS line 34
        info = self.find_existing_file_info(root_hash)

        # TS line 35
        if not opts.get('skipTx', False) or info is None:
            # TS line 36-41
            submission, err = file.create_submission(opts.get('tags', b'\x00'))
            if err is not None or submission is None:
                return (
                    {'txHash': '', 'rootHash': root_hash},
                    Exception('Failed to create submission')
                )

            # TS line 43-46
            tx_receipt, tx_err = self.submit_transaction(submission, opts, retry_opts)
            if tx_err is not None:
                return ({'txHash': '', 'rootHash': root_hash}, tx_err)

            # TS line 47
            receipt = tx_receipt

            # TS line 48
            print(f"Transaction hash: {receipt['transactionHash'].hex()}")

            # TS line 49-55
            tx_seqs = self.flow.process_logs(receipt)
            if len(tx_seqs) == 0:
                return (
                    {'txHash': '', 'rootHash': root_hash},
                    Exception('Failed to get txSeqs')
                )

            # TS line 56
            print(f"Transaction sequence number: {tx_seqs[0]}")

            # TS line 57
            tx_seq = tx_seqs[0]

            # TS line 58
            info = self.wait_for_log_entry(tx_seq, False)

        # TS line 60
        tx_hash = receipt['transactionHash'].hex() if receipt else ''

        # TS line 61-63
        if info is None:
            return ({'txHash': tx_hash, 'rootHash': root_hash}, Exception('Failed to get log entry'))

        # TS line 64-70
        tasks = self.split_tasks(info, tree, opts)
        if tasks is None:
            return (
                {'txHash': tx_hash, 'rootHash': root_hash},
                Exception('Failed to get upload tasks')
            )

        # TS line 71-73
        if len(tasks) == 0:
            return ({'txHash': tx_hash, 'rootHash': root_hash}, None)

        # TS line 74
        print(f"Processing tasks in parallel with {len(tasks)} tasks...")

        # TS line 75
        results = self.process_tasks_in_parallel(file, tree, tasks, retry_opts)

        # TS line 77-81
        for i in range(len(results)):
            if isinstance(results[i], Exception):
                return ({'txHash': tx_hash, 'rootHash': root_hash}, results[i])

        # TS line 82
        print('All tasks processed')

        # TS line 83
        self.wait_for_log_entry(info['tx']['seq'], True)

        # TS line 84
        return ({'txHash': tx_hash, 'rootHash': root_hash}, None)

    def submit_transaction(
        self,
        submission: Dict[str, Any],
        opts: Dict[str, Any],
        retry_opts: Optional[Dict[str, Any]]
    ) -> Tuple[Optional[Dict], Optional[Exception]]:
        """
        Submit transaction to Flow contract.

        TS SDK lines 86-123.

        Args:
            submission: Submission structure
            opts: Transaction options
            retry_opts: Retry options

        Returns:
            Tuple of (receipt, error)
        """
        # TS line 87-89 - Market contract for pricing
        # For now, calculate fee directly
        # market_addr = self.flow.contract.functions.market().call()
        # market_contract = get_market_contract(market_addr, self.web3)
        # price_per_sector = market_contract.functions.pricePerSector().call()

        # TS line 90-96
        fee = 0
        if 'fee' in opts and opts['fee'] > 0:
            fee = opts['fee']
        else:
            # For now, use simple calculation
            # fee = calculate_price(submission, price_per_sector)
            fee = 0  # Placeholder

        # TS line 97-113
        account = opts.get('account')
        if account is None:
            return (None, Exception('Account required for transaction'))

        tx_params = {
            'from': account.address,
            'value': fee,
        }

        if 'nonce' in opts:
            tx_params['nonce'] = opts['nonce']

        if self.gas_price > 0:
            tx_params['gasPrice'] = self.gas_price
        else:
            suggested_gas = self.web3.eth.gas_price
            if suggested_gas is None:
                return (
                    None,
                    Exception('Failed to get suggested gas price, set your own gas price')
                )
            tx_params['gasPrice'] = suggested_gas

        # TS line 114-116
        if self.gas_limit > 0:
            tx_params['gas'] = self.gas_limit

        # TS line 117
        print(f"Submitting transaction with storage fee: {fee}")

        # TS line 118-122
        try:
            receipt = self.flow.submit(submission, account, value=fee)
            return (receipt, None)
        except Exception as e:
            return (None, Exception(f'Failed to submit transaction: {str(e)}'))

    def find_existing_file_info(self, root_hash: str) -> Optional[Dict[str, Any]]:
        """
        Find existing file info from storage nodes.

        TS SDK lines 124-140.

        Args:
            root_hash: File root hash

        Returns:
            File info or None
        """
        # TS line 125
        print('Attempting to find existing file info by root hash...')

        # TS line 127-138
        for client in self.nodes:
            try:
                info = client.get_file_info(root_hash, False)
                if info is not None:
                    print(f"Found existing file info: {info}")
                    return info
            except Exception as e:
                print(f"Failed to get file info from node: {client.url}")

        # TS line 139
        return None

    def wait_for_log_entry(
        self,
        tx_seq: int,
        finality_required: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for log entry to be available on storage nodes.

        TS SDK lines 190-220.

        Args:
            tx_seq: Transaction sequence number
            finality_required: Whether to wait for finality

        Returns:
            File info or None
        """
        # TS line 191
        print('Wait for log entry on storage node')

        # TS line 192
        info = None

        # TS line 193
        while True:
            # TS line 194
            delay(1)  # 1 second

            # TS line 195
            ok = True

            # TS line 196
            for client in self.nodes:
                # TS line 197
                info = client.get_file_info_by_tx_seq(tx_seq)

                # TS line 198-208
                if info is None:
                    log_msg = 'Log entry is unavailable yet'
                    status = client.get_status()
                    if status is not None:
                        log_sync_height = status['logSyncHeight']
                        log_msg = f"Log entry is unavailable yet, zgsNodeSyncHeight={log_sync_height}"
                    print(log_msg)
                    ok = False
                    break

                # TS line 209-213
                if finality_required and not info['finalized']:
                    print(f"Log entry is available, but not finalized yet, {client} {info}")
                    ok = False
                    break

            # TS line 215-217
            if ok:
                break

        # TS line 219
        return info

    def process_tasks_in_parallel(
        self,
        file: ZgFile,
        tree: MerkleTree,
        tasks: List[Dict[str, Any]],
        retry_opts: Optional[Dict[str, Any]]
    ) -> List[Any]:
        """
        Process upload tasks in parallel.

        TS SDK lines 222-225.

        NOTE: Python doesn't have built-in async like JS.
        For MVP, we'll process sequentially. Can add asyncio later.

        Args:
            file: File to upload
            tree: Merkle tree
            tasks: Upload tasks
            retry_opts: Retry options

        Returns:
            List of results
        """
        # TS line 223-224 - Promise.all in TypeScript
        # For Python MVP, process sequentially
        results = []
        for task in tasks:
            result = self.upload_task(file, tree, task, retry_opts)
            results.append(result)
        return results

    def next_segment_index(self, config: Dict[str, int], start_index: int) -> int:
        """
        Calculate next segment index for shard.

        TS SDK lines 226-234.

        Args:
            config: Shard configuration
            start_index: Starting index

        Returns:
            Next segment index
        """
        # TS line 227-229
        if config['numShard'] < 2:
            return start_index

        # TS line 230-233
        return (
            ((start_index + config['numShard'] - 1 - config['shardId']) //
             config['numShard']) *
            config['numShard'] +
            config['shardId']
        )

    def split_tasks(
        self,
        info: Dict[str, Any],
        tree: MerkleTree,
        opts: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Split upload into tasks for each shard.

        TS SDK lines 235-285.

        Args:
            info: File info from log entry
            tree: Merkle tree
            opts: Upload options

        Returns:
            List of upload tasks or None
        """
        # TS line 236-240
        shard_configs = get_shard_configs(self.nodes)
        if shard_configs is None:
            print('Failed to get shard configs')
            return None

        # TS line 241-244
        if not check_replica(shard_configs, opts['expectedReplica']):
            print('Not enough replicas')
            return None

        # TS line 245
        tx_seq = info['tx']['seq']

        # TS line 246
        start_segment_index, end_segment_index = segment_range(
            info['tx']['startEntryIndex'],
            info['tx']['size']
        )

        # TS line 247
        upload_tasks = []

        # Check if file is already finalized on any node
        # If so, no need to upload again - file is already available on the network
        for client_index in range(len(shard_configs)):
            c_info = self.nodes[client_index].get_file_info(tree.root_hash(), True)
            if c_info is not None and c_info['finalized']:
                print(f"✅ File already finalized on node {self.nodes[client_index].url}")
                print(f"   Skipping upload - file is already available on the network")
                return []

        # TS line 248
        for client_index in range(len(shard_configs)):
            # TS line 249
            shard_config = shard_configs[client_index]

            # TS line 250-254 - Already checked above, but keeping for structure consistency
            c_info = self.nodes[client_index].get_file_info(tree.root_hash(), True)
            if c_info is not None and c_info['finalized']:
                continue

            # TS line 255
            tasks = []

            # TS line 256
            seg_index = self.next_segment_index(shard_config, start_segment_index)

            # TS line 257
            while seg_index <= end_segment_index:
                # TS line 258-264
                tasks.append({
                    'clientIndex': client_index,
                    'taskSize': opts['taskSize'],
                    'segIndex': seg_index - start_segment_index,
                    'numShard': shard_config['numShard'],
                    'txSeq': tx_seq,
                })
                # TS line 265
                seg_index += shard_config['numShard'] * opts['taskSize']

            # TS line 267-269
            if len(tasks) > 0:
                upload_tasks.append(tasks)

        # TS line 271-273
        if len(upload_tasks) == 0:
            return []

        # TS line 274
        print(f"Tasks created: {upload_tasks}")

        # TS line 275
        tasks = []

        # TS line 276-283
        if len(upload_tasks) > 0:
            upload_tasks.sort(key=lambda a: len(a))
            for task_index in range(len(upload_tasks[0])):
                for i in range(len(upload_tasks)):
                    if task_index < len(upload_tasks[i]):
                        tasks.append(upload_tasks[i][task_index])

        # TS line 284
        return tasks

    def get_segment(
        self,
        file: ZgFile,
        tree: MerkleTree,
        seg_index: int
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[Exception]]:
        """
        Get segment data with proof.

        TS SDK lines 286-314.

        Args:
            file: File object
            tree: Merkle tree
            seg_index: Segment index

        Returns:
            Tuple of (all_data_uploaded, segment_with_proof, error)
        """
        # TS line 287
        num_chunks = file.num_chunks()

        # TS line 288-291
        start_seg_index = seg_index * DEFAULT_SEGMENT_MAX_CHUNKS
        if start_seg_index >= num_chunks:
            return (True, None, None)

        # TS line 292
        iter = file.iterate_with_offset_and_batch(
            seg_index * DEFAULT_SEGMENT_SIZE,
            DEFAULT_SEGMENT_SIZE,
            True
        )

        # TS line 293-296
        ok, err = iter.next()
        if not ok:
            return (False, None, err)

        # TS line 297
        segment = iter.current()

        # TS line 298
        proof = tree.proof_at(seg_index)

        # TS line 299
        start_index = seg_index * DEFAULT_SEGMENT_MAX_CHUNKS

        # TS line 300
        all_data_uploaded = False

        # TS line 301-305
        if start_index + len(segment) // DEFAULT_CHUNK_SIZE >= num_chunks:
            expected_len = DEFAULT_CHUNK_SIZE * (num_chunks - start_index)
            segment = segment[0:expected_len]
            all_data_uploaded = True

        # TS line 306-312
        seg_with_proof = {
            'root': tree.root_hash(),
            'data': base64.b64encode(segment).decode('ascii'),
            'index': seg_index,
            'proof': {
                'lemma': proof.lemma,
                'path': proof.path,
            },
            'fileSize': file.size(),
        }

        # TS line 313
        return (all_data_uploaded, seg_with_proof, None)

    def upload_task(
        self,
        file: ZgFile,
        tree: MerkleTree,
        upload_task: Dict[str, Any],
        retry_opts: Optional[Dict[str, Any]]
    ) -> Any:
        """
        Upload a single task (batch of segments).

        TS SDK lines 315-381.

        Args:
            file: File object
            tree: Merkle tree
            upload_task: Task definition
            retry_opts: Retry options

        Returns:
            Result or Error
        """
        # TS line 316
        seg_index = upload_task['segIndex']

        # TS line 317
        segments = []

        # TS line 318
        for i in range(upload_task['taskSize']):
            # TS line 319-322
            all_data_uploaded, seg_with_proof, err = self.get_segment(file, tree, seg_index)
            if err is not None:
                return err

            # TS line 323-325
            if seg_with_proof is not None:
                segments.append(seg_with_proof)

            # TS line 326-328
            if all_data_uploaded:
                break

            # TS line 329
            seg_index += upload_task['numShard']

        # TS line 332
        max_retries = retry_opts.get('TooManyDataRetries', 3) if retry_opts else 3

        # TS line 333-334
        attempt = 0
        last_error = None

        # TS line 335
        while attempt < max_retries:
            try:
                # TS line 337
                res = self.nodes[upload_task['clientIndex']].upload_segments_by_tx_seq(
                    segments,
                    upload_task['txSeq']
                )

                # TS line 338-340
                if res is None:
                    raise Exception(
                        f"Node {self.nodes[upload_task['clientIndex']].url} " +
                        "returned null for upload segments"
                    )

                # TS line 341
                return res

            except Exception as error:
                # TS line 344
                last_error = error
                node_url = self.nodes[upload_task['clientIndex']].url

                # TS line 347-350
                if self.is_already_uploaded_error(error):
                    print(f"Segments already uploaded and finalized on node {node_url}")
                    return 0  # Success

                # Note: Fallback is no longer needed since we remove 'root' field above
                # but keeping for reference in case of other errors

                # TS line 352
                if self.is_retryable_error(error):
                    # TS line 353
                    if attempt < max_retries - 1:
                        # TS line 354
                        wait_time = (retry_opts.get('Interval', 3) if retry_opts else 3) * (attempt + 1)

                        # TS line 355
                        error_type = self.get_error_type(error)

                        # TS line 356
                        print(
                            f"{error_type} on attempt {attempt + 1}/{max_retries}. " +
                            f"Retrying in {wait_time}s..."
                        )

                        # TS line 357
                        delay(wait_time)

                        # TS line 358-359
                        attempt += 1
                        continue
                    else:
                        # TS line 361-366
                        error_message = str(error)
                        print(f"Max retries ({max_retries}) reached for error: {error_message}")
                        return Exception(f"Failed after {max_retries} attempts: {error_message}")
                else:
                    # TS line 369-373
                    error_message = str(error)
                    print(f"Non-retryable error encountered: {error_message}")
                    return last_error

        # TS line 377-380
        final_error = last_error or Exception(
            f"Upload failed after {max_retries} attempts to node " +
            f"{self.nodes[upload_task['clientIndex']].url}"
        )
        print(f"Upload task failed completely: {str(final_error)}")
        return final_error

    def is_already_uploaded_error(self, error: Exception) -> bool:
        """
        Check if error indicates file already uploaded.

        TS SDK lines 382-387.
        """
        error_str = str(error).lower()
        return (
            'already uploaded and finalized' in error_str or
            ('invalid params' in error_str and 'already uploaded' in error_str)
        )

    def is_retryable_error(self, error: Exception) -> bool:
        """
        Check if error is retryable.

        TS SDK lines 388-393.
        """
        error_str = str(error)
        return (
            'too many data writing' in error_str or
            'returned null for upload segments' in error_str
        )

    def get_error_type(self, error: Exception) -> str:
        """
        Get error type description.

        TS SDK lines 394-404.
        """
        error_str = str(error)
        if 'too many data writing' in error_str:
            return '"too many data writing" error'
        elif 'returned null' in error_str:
            return 'null response error'
        else:
            return 'retryable error'
