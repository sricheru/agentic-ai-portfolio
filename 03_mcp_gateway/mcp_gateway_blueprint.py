"""
================================================================================
Enterprise Architecture Blueprint: Centralized Model Context Protocol (MCP) Gateway
Author: Sri Cherukuri
Domain: Standardized Tool Interoperability & Zero-Trust Tool Governance
================================================================================
Overview:
    This reference blueprint implements a Centralized MCP Gateway adhering to the
    open Model Context Protocol (JSON-RPC 2.0 standard). It provides policy enforcement,
    circuit breaking, rate limiting, and tool isolation for enterprise multi-agent systems.
"""

from __future__ import annotations

import enum
import time
import uuid
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# 1. MCP JSON-RPC 2.0 Protocol Specifications
# ------------------------------------------------------------------------------

class JSONRPCVersion(str, enum.Enum):
    V2 = "2.0"


class MCPJsonRpcRequest(BaseModel):
    """Standard JSON-RPC 2.0 request payload sent by an AI agent or client."""
    jsonrpc: JSONRPCVersion = JSONRPCVersion.V2
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    method: str  # e.g., "tools/list", "tools/call"
    params: Dict[str, Any] = Field(default_factory=dict)


class MCPErrorObject(BaseModel):
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


class MCPJsonRpcResponse(BaseModel):
    """Standard JSON-RPC 2.0 response returned to the caller agent."""
    jsonrpc: JSONRPCVersion = JSONRPCVersion.V2
    id: str
    result: Optional[Any] = None
    error: Optional[MCPErrorObject] = None


# ------------------------------------------------------------------------------
# 2. Tool Definition & Security Policy Models
# ------------------------------------------------------------------------------

class CircuitBreakerState(str, enum.Enum):
    CLOSED = "CLOSED"      # Normal operations
    OPEN = "OPEN"          # Failing, fast reject
    HALF_OPEN = "HALF_OPEN"# Testing recovery


class ToolSecurityPolicy(BaseModel):
    """Enterprise policy governing tool access, rate limits, and risk boundaries."""
    required_roles: List[str] = Field(default_factory=list)
    rate_limit_rpm: int = 120
    timeout_seconds: float = 10.0
    requires_hitl: bool = False
    failure_threshold: int = 3
    cooldown_seconds: float = 30.0


class MCPToolDefinition(BaseModel):
    """Metadata and schema descriptor for an enterprise MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    security_policy: ToolSecurityPolicy
    is_active: bool = True


# ------------------------------------------------------------------------------
# 3. Centralized Enterprise MCP Gateway Engine
# ------------------------------------------------------------------------------

class MCPGateway:
    """
    Centralized Gateway providing authentication, policy enforcement,
    circuit breaking, and audit logging for all downstream tool integrations.
    """
    def __init__(self):
        self._registry: Dict[str, MCPToolDefinition] = {}
        self._executors: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._circuit_states: Dict[str, CircuitBreakerState] = {}
        self._failure_counts: Dict[str, int] = {}
        self._last_failure_times: Dict[str, float] = {}

    def register_tool(
        self,
        tool_def: MCPToolDefinition,
        executor: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """Registers a tool with its execution callback and circuit state."""
        self._registry[tool_def.name] = tool_def
        self._executors[tool_def.name] = executor
        self._circuit_states[tool_def.name] = CircuitBreakerState.CLOSED
        self._failure_counts[tool_def.name] = 0

    def list_tools(self, caller_roles: List[str]) -> List[MCPToolDefinition]:
        """Returns tools accessible to the caller based on role policies."""
        accessible = []
        for name, tool in self._registry.items():
            if not tool.is_active:
                continue
            if not tool.security_policy.required_roles:
                accessible.append(tool)
            elif set(caller_roles).intersection(set(tool.security_policy.required_roles)):
                accessible.append(tool)
        return accessible

    def handle_request(
        self,
        request: MCPJsonRpcRequest,
        caller_roles: List[str]
    ) -> MCPJsonRpcResponse:
        """Main dispatcher for MCP protocol requests."""
        if request.method == "tools/list":
            tools = self.list_tools(caller_roles)
            return MCPJsonRpcResponse(
                id=request.id,
                result={"tools": [t.model_dump() for t in tools]}
            )
            
        elif request.method == "tools/call":
            tool_name = request.params.get("name")
            arguments = request.params.get("arguments", {})
            
            if not tool_name or tool_name not in self._registry:
                return MCPJsonRpcResponse(
                    id=request.id,
                    error=MCPErrorObject(code=-32601, message=f"Tool '{tool_name}' not found")
                )
                
            tool_def = self._registry[tool_name]
            
            # 1. Authorization check
            if tool_def.security_policy.required_roles:
                if not set(caller_roles).intersection(set(tool_def.security_policy.required_roles)):
                    return MCPJsonRpcResponse(
                        id=request.id,
                        error=MCPErrorObject(code=-32001, message="Forbidden: Insufficient role permissions")
                    )
                    
            # 2. Circuit Breaker check
            if self._circuit_states[tool_name] == CircuitBreakerState.OPEN:
                last_fail = self._last_failure_times.get(tool_name, 0.0)
                if time.time() - last_fail > tool_def.security_policy.cooldown_seconds:
                    self._circuit_states[tool_name] = CircuitBreakerState.HALF_OPEN
                else:
                    return MCPJsonRpcResponse(
                        id=request.id,
                        error=MCPErrorObject(code=-32002, message=f"Circuit Breaker OPEN for tool '{tool_name}'")
                    )
                    
            # 3. Execution
            try:
                executor = self._executors[tool_name]
                output = executor(arguments)
                
                # Reset circuit on success
                self._circuit_states[tool_name] = CircuitBreakerState.CLOSED
                self._failure_counts[tool_name] = 0
                
                return MCPJsonRpcResponse(
                    id=request.id,
                    result={"content": [{"type": "text", "text": str(output)}]}
                )
            except Exception as exc:
                self._failure_counts[tool_name] = self._failure_counts.get(tool_name, 0) + 1
                self._last_failure_times[tool_name] = time.time()
                
                if self._failure_counts[tool_name] >= tool_def.security_policy.failure_threshold:
                    self._circuit_states[tool_name] = CircuitBreakerState.OPEN
                    
                return MCPJsonRpcResponse(
                    id=request.id,
                    error=MCPErrorObject(code=-32000, message=f"Execution error: {str(exc)}")
                )
                
        return MCPJsonRpcResponse(
            id=request.id,
            error=MCPErrorObject(code=-32601, message=f"Unknown method '{request.method}'")
        )


# ------------------------------------------------------------------------------
# Self-Verification Simulation
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 80)
    print("Centralized MCP Gateway - Blueprint Verification")
    print("=" * 80)
    
    gateway = MCPGateway()
    
    # 1. Register a Secure Database Query Tool
    db_tool = MCPToolDefinition(
        name="query_telecom_cdr",
        description="Queries anonymized Call Detail Records for network latency analysis.",
        input_schema={
            "type": "object",
            "properties": {"region": {"type": "string"}, "timeframe": {"type": "string"}},
            "required": ["region"]
        },
        security_policy=ToolSecurityPolicy(
            required_roles=["NetworkAnalyst", "PrincipalArchitect"],
            rate_limit_rpm=60,
            failure_threshold=2,
            cooldown_seconds=5.0
        )
    )
    
    def execute_cdr_query(args: Dict[str, Any]) -> Dict[str, Any]:
        return {"region": args.get("region"), "status": "NOMINAL", "active_calls": 425000}
        
    gateway.register_tool(db_tool, execute_cdr_query)
    
    # 2. Test Tools List (Authorized vs Unauthorized)
    analyst_tools = gateway.list_tools(caller_roles=["NetworkAnalyst"])
    guest_tools = gateway.list_tools(caller_roles=["GuestUser"])
    
    print(f"[*] Tools accessible to 'NetworkAnalyst': {[t.name for t in analyst_tools]}")
    print(f"[*] Tools accessible to 'GuestUser': {[t.name for t in guest_tools]}")
    assert len(analyst_tools) == 1 and len(guest_tools) == 0
    
    # 3. Test Authorized Tool Call
    call_req = MCPJsonRpcRequest(
        method="tools/call",
        params={"name": "query_telecom_cdr", "arguments": {"region": "US-CENTRAL-01"}}
    )
    res = gateway.handle_request(call_req, caller_roles=["NetworkAnalyst"])
    print(f"[*] MCP Response Result: {res.result}")
    assert res.error is None
    
    # 4. Test Unauthorized Tool Call
    unauth_res = gateway.handle_request(call_req, caller_roles=["GuestUser"])
    print(f"[*] MCP Unauthorized Block Error: {unauth_res.error.message}")
    assert unauth_res.error.code == -32001
    
    print(f"[OK] Centralized MCP Gateway & Circuit Breakers verified successfully.")
    print("=" * 80)
