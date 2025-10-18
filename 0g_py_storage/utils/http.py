"""
HTTP and JSON-RPC utilities.

Ported from TypeScript SDK which uses:
- open-jsonrpc-provider for RPC calls

This provides HTTP JSON-RPC client functionality.
"""
from typing import Dict, Any, Optional, List
import requests
import json
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class TLSHttpAdapter(HTTPAdapter):
    def __init__(self, ssl_min_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_2, retries: Retry | None = None, **kwargs):
        self.ssl_min_version = ssl_min_version
        super().__init__(max_retries=retries, **kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        ctx = ssl.create_default_context()
        try:
            ctx.minimum_version = self.ssl_min_version
        except Exception:
            pass
        pool_kwargs['ssl_context'] = ctx
        super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        ctx = ssl.create_default_context()
        try:
            ctx.minimum_version = self.ssl_min_version
        except Exception:
            pass
        proxy_kwargs['ssl_context'] = ctx
        return super().proxy_manager_for(proxy, **proxy_kwargs)

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
        # Avoid env proxies interfering with TLS
        self.session.trust_env = False
        # Close connections to avoid keep-alive corruption
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "0g-py-sdk/0.1",
            "Connection": "close",
        })
        retries = Retry(
            total=5,
            connect=5,
            read=5,
            backoff_factor=0.8,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        adapter = TLSHttpAdapter(retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

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
                headers={"Content-Type": "application/json"},
                verify=True,
                allow_redirects=False,
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

        except requests.exceptions.SSLError as e:
            raise Exception(f"SSL error while calling {self.url}: {str(e)}. Check OpenSSL/cert store and proxies.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"HTTP request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response: {str(e)}")

    def close(self):
        """Close HTTP session."""
        self.session.close()
