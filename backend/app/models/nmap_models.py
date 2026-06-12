from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PortState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"
    OPEN_FILTERED = "open|filtered"
    CLOSED_FILTERED = "closed|filtered"
    UNFILTERED = "unfiltered"


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ServiceInfo(BaseModel):
    name: str = ""
    product: str = ""
    version: str = ""
    extra_info: str = ""
    cpe: List[str] = Field(default_factory=list)


class ScriptOutput(BaseModel):
    id: str
    output: str


class PortInfo(BaseModel):
    port: int
    protocol: str = "tcp"
    state: str
    reason: str = ""
    service: ServiceInfo = Field(default_factory=ServiceInfo)
    scripts: List[ScriptOutput] = Field(default_factory=list)


class OSMatch(BaseModel):
    name: str
    accuracy: int
    line: str = ""


class HostInfo(BaseModel):
    address: str
    hostname: str = ""
    status: str = "up"
    os_matches: List[OSMatch] = Field(default_factory=list)
    ports: List[PortInfo] = Field(default_factory=list)
    uptime: Optional[str] = None
    distance: Optional[int] = None
    trace: List[str] = Field(default_factory=list)


class NmapRunStats(BaseModel):
    elapsed: float = 0.0
    hosts_up: int = 0
    hosts_down: int = 0
    hosts_total: int = 0


class NmapScanResult(BaseModel):
    scan_id: str
    command: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: ScanStatus
    hosts: List[HostInfo] = Field(default_factory=list)
    raw_output: str = ""
    run_stats: NmapRunStats = Field(default_factory=NmapRunStats)
    error_message: Optional[str] = None


class PortRisk(BaseModel):
    port: int
    protocol: str
    service: str
    risk_level: RiskLevel
    description: str
    recommendation: str


class ScanAnalysis(BaseModel):
    scan_id: str
    summary: str
    total_hosts: int
    open_ports_count: int
    risk_assessment: RiskLevel
    port_risks: List[PortRisk] = Field(default_factory=list)
    vulnerabilities: List[str] = Field(default_factory=list)
    ai_analysis: str = ""
    recommendations: List[str] = Field(default_factory=list)
    next_commands: List[str] = Field(default_factory=list)
    legal_notice: str = ""
    report_markdown: str = ""
    generated_at: datetime = Field(default_factory=datetime.now)


class ScanRequest(BaseModel):
    command: str = Field(
        ...,
        description="Full nmap command, e.g. 'nmap -sV 192.168.1.1'",
        examples=["nmap -sV 192.168.1.1", "nmap -sS -p 1-1000 10.0.0.0/24"]
    )


class ScanResponse(BaseModel):
    scan_id: str
    status: ScanStatus
    message: str


class ScanStatusResponse(BaseModel):
    scan_id: str
    status: ScanStatus
    progress: float = 0.0
    message: str = ""
    result: Optional[NmapScanResult] = None
    analysis: Optional[ScanAnalysis] = None
