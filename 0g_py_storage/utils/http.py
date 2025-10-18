"""
HTTP and JSON-RPC utilities.

Ported from TypeScript SDK which uses:
- open-jsonrpc-provider for RPC calls

This provides HTTP JSON-RPC client functionality.
"""
from typing import Dict, Any, Optional, List
import requests
import json


class HttpProvider:
    """
    HTTP JSON-RPC provider.

    Matches behavior of open-jsonrpc-provider HttpProvider
    used by TypeScript SDK.
    """

    def __init__(self, url: str, timeout: int = 30):
        """
        Initialize HTTP provider.

        Args:
            url: RPC endpoint URL
            timeout: Request timeout in seconds
        """
        self.url = url
        self.timeout = timeout
        self.session = requests.Session()

    def request(
        self,
        method: str,
        params: Optional[List[Any]] = None
    ) -> Any:
        """
        Make JSON-RPC request.

        Matches TS SDK super.request() behavior.

        Args:
            method: RPC method name
            params: Optional parameters list

        Returns:
            Response result

        Raises:
            Exception: If request fails
        """
        # Build JSON-RPC request
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
        }

        if params is not None:
            payload["params"] = params

        # Make request
        try:
            response = self.session.post(
                self.url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            # Parse response
            result = response.json()

            # Check for JSON-RPC error
            if "error" in result:
                error = result["error"]
                raise Exception(f"RPC Error: {error.get('message', str(error))}")

            # Return result
            return result.get("result")

        except requests.exceptions.RequestException as e:
            raise Exception(f"HTTP request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response: {str(e)}")

    def close(self):
        """Close HTTP session."""
        self.session.close()
