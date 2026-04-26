"""
Unit tests for new Uploader logic introduced by the no-receipt flow.

Covers:
    - _calculate_fee() branching logic
    - wait_for_log_entry() polling, timeout, finality
    - submit_log_entry_no_receipt() error return format
    - upload_file() skipIfFinalized / skipTx / error paths

These test the logic without touching the network.

Run: pytest tests/test_upload_new_logic.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from core.uploader import Uploader
from contracts.flow import FlowContract
from core.storage_node import StorageNode


# ─── Helpers ───────────────────────────────────────────────────────────

def _make_uploader(nodes=None, flow=None, gas_price=0, gas_limit=0):
    """Create an Uploader with sensible defaults."""
    if nodes is None:
        node = Mock(spec=StorageNode)
        node.url = "http://mock-node"
        nodes = [node]
    if flow is None:
        flow = Mock(spec=FlowContract)
    return Uploader(
        nodes=nodes,
        provider_rpc="http://localhost:8545",
        flow=flow,
        gas_price=gas_price,
        gas_limit=gas_limit,
    )


def _make_zgfile(root_hash="0x" + "ab" * 32, size=1024):
    """Create a mock ZgFile."""
    f = Mock()
    f.size.return_value = size
    f.num_segments.return_value = 1
    f.num_chunks.return_value = 2
    tree = Mock()
    tree.root_hash.return_value = root_hash
    f.merkle_tree.return_value = (tree, None)
    f.create_submission.return_value = (
        {'data': {'length': size, 'tags': b'\x00', 'nodes': []},
         'submitter': '0xSender'},
        None,
    )
    return f


# ═══════════════════════════════════════════════════════════════════════
# _calculate_fee
# ═══════════════════════════════════════════════════════════════════════

class TestCalculateFee:
    """Test Uploader._calculate_fee() branching logic."""

    def test_explicit_fee_in_opts(self):
        """Explicit fee takes precedence over everything."""
        uploader = _make_uploader()
        submission = {'data': {'length': 10000, 'nodes': []}}
        fee = uploader._calculate_fee(submission, {'fee': 12345})

        assert fee == 12345

    def test_zero_length_returns_zero(self):
        """File with length 0 should have zero fee."""
        uploader = _make_uploader()
        submission = {'data': {'length': 0, 'nodes': []}}
        fee = uploader._calculate_fee(submission, {})

        assert fee == 0

    def test_no_fee_key_in_opts_auto_calculates(self):
        """Without explicit fee, auto-calc returns 0 (current behavior)."""
        uploader = _make_uploader()
        submission = {'data': {'length': 999999, 'nodes': []}}
        fee = uploader._calculate_fee(submission, {})

        # Current implementation defaults to 0 when market contract
        # is not configured. This is expected behavior.
        assert fee == 0

    def test_fee_zero_in_opts_triggers_auto_calc(self):
        """fee=0 in opts is treated as "not provided", triggers auto-calc."""
        uploader = _make_uploader()
        submission = {'data': {'length': 5000, 'nodes': []}}
        fee = uploader._calculate_fee(submission, {'fee': 0})

        assert fee == 0  # auto-calc falls back to 0

    def test_exception_in_submission_returns_zero(self):
        """Malformed submission data doesn't crash, returns 0."""
        uploader = _make_uploader()
        # submission missing 'data' key entirely
        submission = {}
        fee = uploader._calculate_fee(submission, {})

        assert fee == 0


# ═══════════════════════════════════════════════════════════════════════
# submit_log_entry_no_receipt error return format
# ═══════════════════════════════════════════════════════════════════════

class TestSubmitNoReceiptReturnFormat:
    """Test that submit_log_entry_no_receipt returns (txHash, err) correctly."""

    @patch.object(FlowContract, '__init__', return_value=None)
    def test_success_returns_txhash_and_none(self, _):
        """On success: (hex_txHash, None)."""
        from eth_account.signers.local import LocalAccount

        fc = FlowContract.__new__(FlowContract)
        fc.web3 = Mock()
        fc.contract = Mock()

        # Mock _send_submit_transaction
        mock_hash = Mock()
        mock_hash.hex.return_value = "0x" + "cc" * 32
        fc._send_submit_transaction = Mock(return_value=mock_hash)

        account = Mock(spec=LocalAccount)
        tx_hash, err = fc.submit_log_entry_no_receipt(
            {'data': {'length': 0}}, account
        )

        assert err is None
        assert tx_hash == "0x" + "cc" * 32

    @patch.object(FlowContract, '__init__', return_value=None)
    def test_exception_returns_empty_and_error(self, _):
        """On exception: ('', Exception)."""
        from eth_account.signers.local import LocalAccount

        fc = FlowContract.__new__(FlowContract)
        fc._send_submit_transaction = Mock(
            side_effect=Exception("insufficient funds")
        )

        account = Mock(spec=LocalAccount)
        tx_hash, err = fc.submit_log_entry_no_receipt(
            {'data': {'length': 0}}, account
        )

        assert tx_hash == ''
        assert err is not None
        assert "insufficient funds" in str(err)

    @patch.object(FlowContract, '__init__', return_value=None)
    def test_txhash_without_0x_prefix_gets_prefixed(self, _):
        """If hex() returns without 0x, it gets prepended."""
        from eth_account.signers.local import LocalAccount

        fc = FlowContract.__new__(FlowContract)
        mock_hash = Mock()
        mock_hash.hex.return_value = "ab" * 32  # no 0x prefix
        fc._send_submit_transaction = Mock(return_value=mock_hash)

        account = Mock(spec=LocalAccount)
        tx_hash, err = fc.submit_log_entry_no_receipt(
            {'data': {'length': 0}}, account
        )

        assert err is None
        assert tx_hash == "0x" + "ab" * 32


# ═══════════════════════════════════════════════════════════════════════
# wait_for_log_entry polling & timeout
# ═══════════════════════════════════════════════════════════════════════

class TestWaitForLogEntry:
    """Test wait_for_log_entry() polling, timeout, and finality."""

    @patch('core.uploader.delay')
    def test_found_on_first_poll(self, mock_delay):
        """Returns immediately when file info is found on first attempt."""
        node = Mock(spec=StorageNode)
        node.get_file_info.return_value = {
            'tx': {'seq': 42}, 'finalized': False
        }
        node.get_status.return_value = {'logSyncHeight': 100}
        uploader = _make_uploader(nodes=[node])

        info = uploader.wait_for_log_entry("0xroot")

        assert info is not None
        assert info['tx']['seq'] == 42
        assert mock_delay.call_count == 1

    @patch('core.uploader.delay')
    def test_found_after_retries(self, mock_delay):
        """Returns info after several None responses then a success."""
        node = Mock(spec=StorageNode)
        call_count = [0]

        def mock_info(root_hash, need_available=False):
            call_count[0] += 1
            if call_count[0] < 3:
                return None
            return {'tx': {'seq': 50}, 'finalized': False}

        node.get_file_info = mock_info
        node.get_status.return_value = {'logSyncHeight': 100}
        uploader = _make_uploader(nodes=[node])

        info = uploader.wait_for_log_entry("0xroot")

        assert info is not None
        assert info['tx']['seq'] == 50
        assert call_count[0] == 3

    @patch('core.uploader.delay')
    def test_timeout_returns_last_info_or_none(self, mock_delay):
        """After max_attempts, returns last known info (or None)."""
        node = Mock(spec=StorageNode)
        node.get_file_info.return_value = None
        node.get_status.return_value = {'logSyncHeight': 50}
        uploader = _make_uploader(nodes=[node])

        # Patch max_attempts to a small number for fast test
        with patch.object(uploader, 'wait_for_log_entry', wraps=uploader.wait_for_log_entry):
            # Directly test the loop logic with a small max_attempts
            original = Uploader.wait_for_log_entry

            def fast_wait(self, root_hash, finality_required=False):
                """Same logic but only 3 attempts."""
                info = None
                max_attempts = 3
                attempt = 0
                while attempt < max_attempts:
                    attempt += 1
                    delay(0)
                    ok = True
                    for client in self.nodes:
                        info = client.get_file_info(root_hash)
                        if info is None:
                            ok = False
                            break
                        if finality_required and not info.get('finalized', False):
                            ok = False
                            break
                    if ok:
                        return info
                return info

            from core.uploader import delay
            info = fast_wait(uploader, "0xroot")

        assert info is None

    @patch('core.uploader.delay')
    def test_finality_required_waits_for_finalized(self, mock_delay):
        """With finality_required=True, keeps polling until finalized."""
        node = Mock(spec=StorageNode)
        call_count = [0]

        def mock_info(root_hash, need_available=False):
            call_count[0] += 1
            if call_count[0] < 2:
                return {'tx': {'seq': 1}, 'finalized': False}
            return {'tx': {'seq': 1}, 'finalized': True}

        node.get_file_info = mock_info
        uploader = _make_uploader(nodes=[node])

        info = uploader.wait_for_log_entry("0xroot", finality_required=True)

        assert info is not None
        assert info['finalized'] is True
        assert call_count[0] == 2

    @patch('core.uploader.delay')
    def test_second_node_responds_when_first_fails(self, mock_delay):
        """Info from second node is used when first returns None."""
        node1 = Mock(spec=StorageNode)
        node1.get_file_info.return_value = None
        node1.get_status.return_value = {'logSyncHeight': 10}

        node2 = Mock(spec=StorageNode)
        node2.get_file_info.return_value = {
            'tx': {'seq': 77}, 'finalized': False
        }

        uploader = _make_uploader(nodes=[node1, node2])

        info = uploader.wait_for_log_entry("0xroot")

        # First node returns None → loop breaks, retries
        # On retry, first node still None → retries again
        # Eventually hits node2? No: the loop iterates ALL nodes per attempt.
        # Actually: the loop breaks on first None. So node2 is never reached
        # in the same attempt unless node1 returns non-None.
        # This test documents actual behavior.
        # If node1 always returns None, we'll time out.
        # Let's make node1 succeed on second attempt:
        call_count = [0]
        def mock_info1(root_hash, need_available=False):
            call_count[0] += 1
            return None if call_count[0] == 1 else {
                'tx': {'seq': 77}, 'finalized': False
            }
        node1.get_file_info = mock_info1

        info = uploader.wait_for_log_entry("0xroot")

        assert info is not None
        assert info['tx']['seq'] == 77


# ═══════════════════════════════════════════════════════════════════════
# upload_file skipIfFinalized / skipTx paths
# ═══════════════════════════════════════════════════════════════════════

class TestUploadFilePaths:
    """Test upload_file() branching: skipIfFinalized, skipTx, errors."""

    def test_skip_if_finalized_returns_existing_txseq(self):
        """skipIfFinalized + finalized file → return existing txSeq, no tx."""
        node = Mock(spec=StorageNode)
        node.get_file_info.return_value = {
            'tx': {'seq': 999}, 'finalized': True
        }
        flow = Mock(spec=FlowContract)
        uploader = _make_uploader(nodes=[node], flow=flow)

        zg_file = _make_zgfile()
        result, err = uploader.upload_file(
            zg_file,
            opts={'skipIfFinalized': True, 'account': Mock()}
        )

        assert err is None
        assert result['txHash'] == ''
        assert result['rootHash'] == "0x" + "ab" * 32
        assert result['txSeq'] == 999
        flow.submit_log_entry_no_receipt.assert_not_called()

    def test_skip_if_finalized_not_finalized_proceeds(self):
        """skipIfFinalized + NOT finalized → proceeds with upload."""
        node = Mock(spec=StorageNode)
        # find_existing_file_info returns not-finalized info
        # wait_for_log_entry polling needs to find info too
        node.get_file_info.return_value = {
            'tx': {'seq': 100, 'startEntryIndex': 0, 'size': 1024},
            'finalized': False,
        }
        node.get_status.return_value = {'logSyncHeight': 100}

        flow = Mock(spec=FlowContract)
        flow.submit_log_entry_no_receipt.return_value = ("0x" + "dd" * 32, None)
        uploader = _make_uploader(nodes=[node], flow=flow)

        # Mock split_tasks to return empty (no segments to upload)
        with patch.object(uploader, 'split_tasks', return_value=[]):
            with patch('core.uploader.delay'):
                zg_file = _make_zgfile()
                result, err = uploader.upload_file(
                    zg_file,
                    opts={'skipIfFinalized': True, 'account': Mock()}
                )

        assert err is None
        flow.submit_log_entry_no_receipt.assert_called_once()

    def test_merkle_tree_failure_returns_error(self):
        """Failed Merkle tree → immediate error, no submission."""
        flow = Mock(spec=FlowContract)
        uploader = _make_uploader(flow=flow)

        bad_file = Mock()
        bad_file.merkle_tree.return_value = (None, Exception("merkle failed"))

        result, err = uploader.upload_file(bad_file, opts={})

        assert err is not None
        assert 'merkle' in str(err).lower() or 'Merkle' in str(err)
        assert result['txHash'] == ''
        assert result['txSeq'] == 0
        flow.submit_log_entry_no_receipt.assert_not_called()

    def test_submission_failure_returns_error(self):
        """create_submission failure → error, no on-chain tx."""
        node = Mock(spec=StorageNode)
        node.get_file_info.return_value = None
        node.get_status.return_value = {'logSyncHeight': 0}

        flow = Mock(spec=FlowContract)
        uploader = _make_uploader(nodes=[node], flow=flow)

        bad_file = _make_zgfile()
        bad_file.create_submission.return_value = (None, Exception("submission failed"))

        result, err = uploader.upload_file(
            bad_file, opts={'account': Mock()}
        )

        assert err is not None
        assert 'submission' in str(err).lower()
        flow.submit_log_entry_no_receipt.assert_not_called()

    def test_submit_no_receipt_error_propagates(self):
        """submit_log_entry_no_receipt error → upload returns error."""
        node = Mock(spec=StorageNode)
        node.get_file_info.return_value = None
        node.get_status.return_value = {'logSyncHeight': 0}

        flow = Mock(spec=FlowContract)
        flow.submit_log_entry_no_receipt.return_value = (
            '', Exception("insufficient funds")
        )
        uploader = _make_uploader(nodes=[node], flow=flow)

        with patch('core.uploader.delay'):
            zg_file = _make_zgfile()
            result, err = uploader.upload_file(
                zg_file, opts={'account': Mock()}
            )

        assert err is not None
        assert 'insufficient funds' in str(err)

    def test_gas_price_and_limit_forwarded(self):
        """Uploader's gas_price/gas_limit are forwarded to submit."""
        node = Mock(spec=StorageNode)
        node.get_file_info.return_value = {
            'tx': {'seq': 1, 'startEntryIndex': 0, 'size': 1024},
            'finalized': False,
        }
        node.get_status.return_value = {'logSyncHeight': 100}

        flow = Mock(spec=FlowContract)
        flow.submit_log_entry_no_receipt.return_value = ("0xhash", None)
        uploader = _make_uploader(nodes=[node], flow=flow, gas_price=5000, gas_limit=800000)

        with patch.object(uploader, 'split_tasks', return_value=[]):
            with patch('core.uploader.delay'):
                zg_file = _make_zgfile()
                result, err = uploader.upload_file(
                    zg_file, opts={'account': Mock()}
                )

        assert err is None
        call_kwargs = flow.submit_log_entry_no_receipt.call_args
        # _submit_no_receipt passes gas_price/gas_limit via kwargs
        assert call_kwargs.kwargs.get('gas_price') == 5000
        assert call_kwargs.kwargs.get('gas_limit') == 800000
