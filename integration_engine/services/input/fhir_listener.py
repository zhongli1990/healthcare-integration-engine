import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl

from core.models.message import MessageEnvelope, MessageHeader, MessageBody
from core.queues.queue_manager import QueueConfig
from core.services.base_service import BaseService

logger = logging.getLogger(__name__)


class FHIRServerConfig(BaseModel):
    """Configuration for the FHIR server."""
    host: str = "0.0.0.0"
    port: int = 8080
    api_prefix: str = "/fhir"
    cors_origins: List[str] = ["*"]
    cors_methods: List[str] = ["*"]
    cors_headers: List[str] = ["*"]
    
    class Config:
        extra = "forbid"


class FHIRListenerService(BaseService):
    """Service for receiving FHIR R4 resources via HTTP."""
    
    def __init__(
        self,
        output_queue: str = "raw_messages",
        server_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(name="fhir_listener", **kwargs)
        
        # Initialize server configuration
        self.config = FHIRServerConfig(**(server_config or {}))
        self.output_queue_name = output_queue
        self.output_queue = None
        
        # Create FastAPI application
        self.app = FastAPI(
            title="FHIR R4 Listener",
            description="FHIR R4 compliant REST API for receiving healthcare data",
            version="1.0.0",
            openapi_url=f"{self.config.api_prefix}/openapi.json",
            docs_url=f"{self.config.api_prefix}/docs",
            redoc_url=f"{self.config.api_prefix}/redoc"
        )
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors_origins,
            allow_credentials=True,
            allow_methods=self.config.cors_methods,
            allow_headers=self.config.cors_headers,
        )
        
        # Register routes
        self._setup_routes()
        
        # ASGI server
        self._server = None
    
    def _setup_routes(self) -> None:
        """Set up FHIR R4 REST API routes."""
        # Root endpoint
        @self.app.get("/", include_in_schema=False)
        async def root():
            return {"status": "ok", "service": "fhir-listener"}
        
        # Health check endpoint
        @self.app.get("/health")
        async def health():
            return {"status": "ok"}
        
        # FHIR R4 API endpoints
        @self.app.post(f"{self.config.api_prefix}/{{resource_type}}")
        async def create_resource(
            resource_type: str,
            request: Request,
            response: Response
        ):
            return await self._handle_fhir_request(
                method="POST",
                resource_type=resource_type,
                request=request,
                response=response
            )
        
        @self.app.put(f"{self.config.api_prefix}/{{resource_type}}/{{resource_id}}")
        async def update_resource(
            resource_type: str,
            resource_id: str,
            request: Request,
            response: Response
        ):
            return await self._handle_fhir_request(
                method="PUT",
                resource_type=resource_type,
                resource_id=resource_id,
                request=request,
                response=response
            )
        
        @self.app.post(f"{self.config.api_prefix}/$process-message")
        async def process_message(
            request: Request,
            response: Response
        ):
            return await self._handle_fhir_request(
                method="POST",
                resource_type="Message",
                request=request,
                response=response
            )
        
        @self.app.post(f"{self.config.api_prefix}}/$process")
        async def process_batch(
            request: Request,
            response: Response
        ):
            return await self._handle_fhir_request(
                method="POST",
                resource_type="Bundle",
                request=request,
                response=response
            )
    
    async def _handle_fhir_request(
        self,
        method: str,
        resource_type: str,
        request: Request,
        response: Response,
        resource_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle incoming FHIR requests."""
        try:
            # Parse request body
            content_type = request.headers.get("content-type", "")
            
            if "application/fhir+json" in content_type or "application/json" in content_type:
                body = await request.json()
            else:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Unsupported media type: {content_type}"
                )
            
            # Create message envelope
            message_id = str(uuid.uuid4())
            source = f"{request.url.scheme}://{request.url.hostname}"
            if request.url.port:
                source += f":{request.url.port}"
            
            message = MessageEnvelope(
                header=MessageHeader(
                    message_id=message_id,
                    message_type=resource_type,
                    source=source,
                    metadata={
                        "http_method": method,
                        "received_at": datetime.utcnow().isoformat(),
                        "content_type": content_type,
                        "client_host": request.client.host if request.client else None,
                        "request_headers": dict(request.headers)
                    }
                ),
                body=MessageBody(
                    content_type="application/fhir+json",
                    content=body,
                    raw_content=json.dumps(body).encode('utf-8'),
                    metadata={
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "full_url": str(request.url)
                    }
                )
            )
            
            # Send to output queue
            await self.output_queue.publish(message)
            logger.info(f"Received FHIR {resource_type} with ID: {resource_id or 'new'}")
            
            # Return appropriate FHIR response
            if method == "POST":
                response.status_code = status.HTTP_201_CREATED
                response.headers["Location"] = f"{self.config.api_prefix}/{resource_type}/{message_id}"
                return {
                    "resourceType": "OperationOutcome",
                    "issue": [{
                        "severity": "information",
                        "code": "informational",
                        "diagnostics": f"Resource {resource_type} created with ID {message_id}"
                    }]
                }
            else:  # PUT
                response.status_code = status.HTTP_200_OK
                return body
                
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        except Exception as e:
            logger.exception("Error processing FHIR request")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    async def on_start(self) -> None:
        """Start the FHIR listener service."""
        # Create output queue
        self.output_queue = await self.queue_manager.get_queue(self.output_queue_name)
        
        # Start the HTTP server
        import uvicorn
        
        config = uvicorn.Config(
            app=self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
            loop="asyncio",
        )
        
        self._server = uvicorn.Server(config)
        self.create_task(self._server.serve())
        
        logger.info(f"FHIR R4 listener started on {self.config.host}:{self.config.port}{self.config.api_prefix}")
    
    async def on_stop(self) -> None:
        """Stop the FHIR listener service."""
        if self._server:
            self._server.should_exit = True
            logger.info("FHIR R4 listener stopped")
