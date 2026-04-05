import json
import os
import base64
import hashlib
import logging
from typing import Dict, Any, Optional, Callable

from ...exceptions import ContractError, NetworkError
from ..contract.contract import FineTuningContract
from ..provider.provider import FineTuningProvider

logger = logging.getLogger(__name__)


class Verifier:
    def __init__(
        self,
        contract: FineTuningContract,
        provider: FineTuningProvider,
    ):
        self.contract = contract
        self.provider = provider

    def verify_service(
        self,
        provider_address: str,
        output_dir: str = ".",
        on_log: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        def log(msg: str):
            if on_log:
                on_log(msg)
            logger.info(msg)

        result = {
            "provider": provider_address,
            "quote_available": False,
            "signer_match": False,
            "compose_hash_match": None,
            "docker_images": [],
            "attestation_format": None,
            "tee_signer": None,
            "expected_signer": None,
            "is_valid": False,
            "errors": [],
        }

        # Get service from contract
        try:
            service = self.contract.get_service(provider_address)
            result["expected_signer"] = service.tee_signer_address
            log(f"Service found: {service.url}")
        except Exception as e:
            result["errors"].append(f"Failed to get service: {e}")
            return result

        # Fetch attestation quote
        try:
            quote = self.provider.get_quote(provider_address)
            result["quote_available"] = True
            log("TEE quote fetched successfully")
        except Exception as e:
            result["errors"].append(f"Failed to fetch quote: {e}")
            return result

        # Parse report
        try:
            report = json.loads(quote.raw_report)
        except (json.JSONDecodeError, TypeError):
            report = {"raw": quote.raw_report}

        # Save report to file
        try:
            os.makedirs(output_dir, exist_ok=True)
            report_path = os.path.join(
                output_dir, "fine_tuning_attestation_report.json"
            )
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)
            result["report_path"] = report_path
            log(f"Report saved to {report_path}")
        except Exception as e:
            logger.warning("Could not save report: %s", e)

        # Extract TEE signer from report_data
        tee_signer, fmt = self._extract_signer(report)
        result["tee_signer"] = tee_signer
        result["attestation_format"] = fmt

        if tee_signer:
            log(f"TEE signer extracted: {tee_signer} (format: {fmt})")
        elif fmt:
            log(f"Attestation format detected: {fmt}")

        # Signer verification
        if tee_signer and service.tee_signer_address:
            match = tee_signer.lower() == service.tee_signer_address.lower()
            result["signer_match"] = match
            if match:
                log("TEE signer matches contract")
            else:
                log("TEE signer does NOT match contract")
                result["errors"].append("Signer mismatch")
        elif tee_signer:
            result["signer_match"] = True
            log("TEE signer extracted (no contract signer to compare)")
        elif fmt in ("dstack", "gpu"):
            result["signer_match"] = True
            log(f"{fmt} attestation format verified")

        # DStack compose hash verification
        compose_match = self._verify_compose_hash(report)
        if compose_match is not None:
            result["compose_hash_match"] = compose_match
            if compose_match:
                log("Compose hash verified")
            else:
                log("Compose hash mismatch")
                result["errors"].append("Compose hash mismatch")

        # Extract Docker images
        result["docker_images"] = self._extract_docker_images(report)
        if result["docker_images"]:
            log(f"Docker images: {result['docker_images']}")

        # Overall validity
        result["is_valid"] = (
            result["quote_available"]
            and (
                (result["tee_signer"] is not None and result["signer_match"])
                or (fmt in ("dstack", "gpu") and result["signer_match"])
            )
        )

        return result

    @staticmethod
    def _extract_signer(report: dict) -> tuple:
        # Standard SGX/TDX: report_data field
        try:
            report_data = report.get("report_data")
            if report_data:
                decoded = base64.b64decode(report_data).decode("utf-8")
                signer = decoded.replace("\x00", "").strip()
                if signer:
                    return signer, "sgx_tdx"
        except Exception:
            pass

        # DStack: nested quote in evidence
        try:
            if "compose_content" in report or "evidence" in report:
                evidence = report.get("evidence")
                if evidence and isinstance(evidence, str):
                    try:
                        decoded_ev = base64.b64decode(evidence).decode(
                            "utf-8", errors="ignore"
                        )
                        ev_json = json.loads(decoded_ev)
                        if "quote" in ev_json and isinstance(ev_json["quote"], dict):
                            nested_rd = ev_json["quote"].get("report_data")
                            if nested_rd:
                                decoded = base64.b64decode(nested_rd).decode("utf-8")
                                signer = decoded.replace("\x00", "").strip()
                                if signer:
                                    return signer, "dstack"
                    except Exception:
                        pass
                return None, "dstack"
        except Exception:
            pass

        # GPU attestation
        try:
            if "gpu_evidence" in report:
                return None, "gpu"
        except Exception:
            pass

        return None, None

    @staticmethod
    def _verify_compose_hash(report: dict) -> Optional[bool]:
        try:
            tcb_info = report.get("tcb_info")
            event_log = report.get("event_log")
            app_compose = report.get("app_compose") or report.get("compose_content")

            if not tcb_info or not event_log or not app_compose:
                return None

            if isinstance(app_compose, dict):
                app_compose = json.dumps(app_compose, separators=(",", ":"))

            expected_hash = hashlib.sha256(app_compose.encode("utf-8")).hexdigest()

            if isinstance(event_log, list):
                for event in event_log:
                    if isinstance(event, dict):
                        event_type = event.get("event_type") or event.get("type", "")
                        if "compose-hash" in str(event_type).lower():
                            actual_hash = event.get("digest") or event.get("hash", "")
                            return actual_hash.lower() == expected_hash.lower()

            return None
        except Exception:
            return None

    @staticmethod
    def _extract_docker_images(report: dict) -> list:
        import re

        images = []
        try:
            tcb_info = report.get("tcb_info")
            if tcb_info:
                tcb_str = json.dumps(tcb_info) if isinstance(tcb_info, dict) else str(tcb_info)
                matches = re.findall(r'"image"\s*:\s*"([^"]+)"', tcb_str)
                images.extend(matches)
        except Exception:
            pass
        return images
