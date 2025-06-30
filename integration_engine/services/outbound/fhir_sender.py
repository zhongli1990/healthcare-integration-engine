import asyncio
import json
import logging
from typing import Any, Dict, Optional, Tuple, Union

import aiohttp
from pydantic import BaseModel, HttpUrl

from core.models.message import MessageEnvelope
from core.queues.queue_manager import QueueConfig
from integration_engine.services.outbound.base_sender import BaseOutboundSender

logger = logging.getLogger(__name__)


class FHIRServerConfig(BaseModel):
    """Configuration for a FHIR server connection."""
    base_url: HttpUrl
    auth_type: str = "none"  # none, basic, oauth2, token
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    token_url: Optional[HttpUrl] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    scope: Optional[str] = None
    timeout: int = 30
    verify_ssl: bool = True
    
    class Config:
        extra = "forbid"


class FHIROperation(BaseModel):
    """Represents a FHIR operation to perform."""
    method: str  # GET, POST, PUT, PATCH, DELETE
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    operation: Optional[str] = None  # For operations like $validate, $everything, etc.
    parameters: Dict[str, Any] = {}
    headers: Dict[str, str] = {}
    
    class Config:
        extra = "forbid"


class FHIROperationResult(BaseModel):
    """Represents the result of a FHIR operation."""
    success: bool
    status_code: int
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    operation: Optional[FHIROperation] = None


class FHIROutboundSender(BaseOutboundSender):
    """
    Sends FHIR resources to a FHIR server using RESTful API.
    """
    
    def __init__(
        self,
        server_config: Union[Dict[str, Any], FHIRServerConfig],
        default_operation: Optional[FHIROperation] = None,
        input_queue: str = "outbound_fhir_messages",
        error_queue: str = "outbound_fhir_errors",
        max_retries: int = 3,
        retry_delay: int = 5,
        **kwargs
    ):
        """
        Initialize the FHIR outbound sender.
        
        Args:
            server_config: Configuration for the FHIR server
            default_operation: Default operation to perform if not specified in message metadata
            input_queue: The name of the input queue to consume messages from
            error_queue: The name of the error queue for failed messages
            max_retries: Maximum number of retry attempts for failed requests
            retry_delay: Delay between retry attempts in seconds
            **kwargs: Additional keyword arguments for BaseOutboundSender
        """
        super().__init__(
            name=f"fhir_sender_{server_config.get('base_url', 'default')}",
            input_queue=input_queue,
            error_queue=error_queue,
            **kwargs
        )
        
        # Parse server config
        if isinstance(server_config, dict):
            self.server_config = FHIRServerConfig(**server_config)
        else:
            self.server_config = server_config
        
        self.default_operation = default_operation or FHIROperation(
            method="POST",
            resource_type=None,  # Will be determined from message content
            operation=None
        )
        
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Session for making HTTP requests
        self._session = None
        self._session_lock = asyncio.Lock()
        self._token_info = {}
    
    async def on_start(self) -> None:
        """Initialize the sender service."""
        await super().on_start()
        
        # Initialize the HTTP session
        await self._ensure_session()
    
    async def on_stop(self) -> None:
        """Clean up resources."""
        await super().on_stop()
        
        # Close the HTTP session
        await self._close_session()
    
    async def _ensure_session(self) -> None:
        """Ensure we have a valid HTTP session."""
        if self._session is None or self._session.closed:
            async with self._session_lock:
                if self._session is None or self._session.closed:
                    # Create a new session with default timeout
                    timeout = aiohttp.ClientTimeout(total=self.server_config.timeout)
                    connector = aiohttp.TCPConnector(ssl=self.server_config.verify_ssl)
                    self._session = aiohttp.ClientSession(
                        timeout=timeout,
                        connector=connector,
                        headers={
                            "Accept": "application/fhir+json",
                            "Content-Type": "application/fhir+json; charset=utf-8",
                            "User-Agent": "IntegrationEngine/FHIRSender/1.0"
                        }
                    )
                    
                    # Authenticate if needed
                    if self.server_config.auth_type == "oauth2" and self.server_config.token_url:
                        await self._get_oauth_token()
    
    async def _close_session(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def _get_oauth_token(self) -> None:
        """Get an OAuth 2.0 token for authentication."""
        if not self.server_config.token_url:
            raise ValueError("Token URL is required for OAuth 2.0 authentication")
        
        # Check if we have a valid token
        if self._token_info and self._token_info.get("expires_at", 0) > time.time() + 60:
            return self._token_info["access_token"]
        
        # Request a new token
        auth = None
        data = {
            "grant_type": "client_credentials",
            "scope": self.server_config.scope or ""
        }
        
        if self.server_config.client_id and self.server_config.client_secret:
            auth = aiohttp.BasicAuth(
                self.server_config.client_id,
                self.server_config.client_secret
            )
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                str(self.server_config.token_url),
                data=data,
                auth=auth
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to get OAuth token: {response.status} - {error_text}")
                
                token_data = await response.json()
                
                # Calculate token expiration
                expires_in = token_data.get("expires_in", 3600)
                self._token_info = {
                    "access_token": token_data["access_token"],
                    "token_type": token_data.get("token_type", "Bearer"),
                    "expires_at": time.time() + expires_in - 60,  # 1 minute buffer
                    "refresh_token": token_data.get("refresh_token"),
                    "scope": token_data.get("scope", "")
                }
                
                # Update session headers
                self._session.headers["Authorization"] = f"{self._token_info['token_type']} {self._token_info['access_token']}"
    
    async def send_message(self, message: MessageEnvelope) -> Tuple[bool, Optional[str]]:
        """
        Send a FHIR resource to the FHIR server.
        
        Args:
            message: The message to send
            
        Returns:
            A tuple of (success, error_message)
        """
        if not message.body.content:
            return False, "Message has no content"
        
        # Get the operation from message metadata or use default
        operation_data = message.header.metadata.get("fhir_operation")
        if operation_data:
            operation = FHIROperation(**(operation_data if isinstance(operation_data, dict) else {}))
        else:
            operation = self.default_operation.model_copy(deep=True)
        
        # Determine resource type from message if not specified in operation
        if not operation.resource_type and isinstance(message.body.content, dict):
            operation.resource_type = message.body.content.get("resourceType")
        
        if not operation.resource_type and not operation.operation:
            return False, "No resource type or operation specified"
        
        # Prepare the request
        url = self._build_request_url(operation)
        headers = self._prepare_headers(operation)
        
        # Prepare the request body
        body = None
        if operation.method in ("POST", "PUT", "PATCH"):
            body = self._prepare_request_body(message, operation)
        
        # Make the request with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                # Ensure we have a valid session
                await self._ensure_session()
                
                # Make the request
                async with self._session.request(
                    method=operation.method,
                    url=url,
                    headers=headers,
                    json=body,
                    params=operation.parameters
                ) as response:
                    response_data = await self._parse_response(response)
                    
                    # Check for FHIR OperationOutcome
                    if isinstance(response_data, dict) and response_data.get("resourceType") == "OperationOutcome":
                        issues = response_data.get("issue", [])
                        if issues and issues[0].get("severity") in ("error", "fatal"):
                            error_details = "; ".join(
                                f"{issue.get('diagnostics') or issue.get('details', {}).get('text') or 'Unknown error'}" 
                                for issue in issues
                            )
                            raise Exception(f"FHIR OperationOutcome: {error_details}")
                    
                    # Check for success status code
                    if response.status in (200, 201, 204):
                        # Update message with response if needed
                        if isinstance(response_data, dict):
                            message.body.content = response_data
                        return True, None
                    else:
                        raise Exception(f"HTTP {response.status}: {response.reason}")
                
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1} failed: {last_error}")
                
                # Don't retry on client errors (4xx) except 429 (Too Many Requests)
                if isinstance(e, aiohttp.ClientResponseError) and 400 <= e.status < 500 and e.status != 429:
                    break
                
                # Wait before retry
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                last_error = str(e)
                logger.exception("Unexpected error in FHIR request")
                break
        
        return False, f"Failed after {self.max_retries} attempts: {last_error}"
    
    def _build_request_url(self, operation: FHIROperation) -> str:
        """Build the request URL for the FHIR operation."""
        base_url = str(self.server_config.base_url).rstrip("/")
        
        if operation.operation:
            # Operation URL (e.g., /Patient/$export or /$export)
            if operation.resource_type:
                return f"{base_url}/{operation.resource_type}/{operation.operation}"
            else:
                return f"{base_url}/{operation.operation}"
        elif operation.resource_type:
            # Resource URL (e.g., /Patient or /Patient/123)
            if operation.resource_id:
                return f"{base_url}/{operation.resource_type}/{operation.resource_id}"
            else:
                return f"{base_url}/{operation.resource_type}"
        else:
            raise ValueError("Either resource_type or operation must be specified")
    
    def _prepare_headers(self, operation: FHIROperation) -> Dict[str, str]:
        """Prepare the request headers."""
        headers = {}
        
        # Add auth header if using token auth
        if self.server_config.auth_type == "token" and self.server_config.token:
            headers["Authorization"] = f"Bearer {self.server_config.token}"
        elif self.server_config.auth_type == "basic" and self.server_config.username and self.server_config.password:
            import base64
            credentials = f"{self.server_config.username}:{self.server_config.password}"
            encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {encoded_credentials}"
        
        # Add custom headers from operation
        headers.update(operation.headers or {})
        
        # Ensure content type is set for requests with body
        if operation.method in ("POST", "PUT", "PATCH"):
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/fhir+json; charset=utf-8"
        
        # Ensure accept header is set
        if "Accept" not in headers:
            headers["Accept"] = "application/fhir+json"
        
        return headers
    
    def _prepare_request_body(
        self,
        message: MessageEnvelope,
        operation: FHIROperation
    ) -> Optional[Dict[str, Any]]:
        """Prepare the request body from the message."""
        if not message.body.content:
            return None
        
        # If content is already a dict, use it as is
        if isinstance(message.body.content, dict):
            return message.body.content
        
        # If content is a string, try to parse it as JSON
        if isinstance(message.body.content, str):
            try:
                return json.loads(message.body.content)
            except json.JSONDecodeError:
                # If it's not JSON, treat it as raw data
                return {"resourceType": "Binary", "contentType": "text/plain", "data": message.body.content}
        
        # For other types, convert to string representation
        return {"resourceType": "Binary", "contentType": "text/plain", "data": str(message.body.content)}
    
    async def _parse_response(self, response: aiohttp.ClientResponse) -> Any:
        """Parse the response from the FHIR server."""
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
        
        if not content_type or "application/fhir+json" in content_type or "application/json" in content_type:
            try:
                return await response.json()
            except (json.JSONDecodeError, aiohttp.ContentTypeError):
                text = await response.text()
                return {"text": text}
        else:
            # For non-JSON responses, return as text
            return await response.text()
