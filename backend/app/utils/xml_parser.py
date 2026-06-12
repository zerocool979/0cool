import xml.etree.ElementTree as ET
from typing import List, Optional
from app.models.nmap_models import HostInfo, PortInfo, ServiceInfo, OSMatch, ScriptOutput, NmapRunStats
from app.core.exceptions import NmapParseError
import logging

logger = logging.getLogger(__name__)


def parse_nmap_xml(xml_content: str) -> tuple[List[HostInfo], NmapRunStats]:
    """Parse Nmap XML output into structured data."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise NmapParseError(f"Invalid XML: {e}")

    hosts: List[HostInfo] = []
    run_stats = _parse_run_stats(root)

    for host_elem in root.findall("host"):
        host = _parse_host(host_elem)
        if host:
            hosts.append(host)

    return hosts, run_stats


def _parse_run_stats(root: ET.Element) -> NmapRunStats:
    stats = NmapRunStats()
    runstats = root.find("runstats")
    if runstats is not None:
        finished = runstats.find("finished")
        if finished is not None:
            stats.elapsed = float(finished.get("elapsed", 0))

        hosts_elem = runstats.find("hosts")
        if hosts_elem is not None:
            stats.hosts_up = int(hosts_elem.get("up", 0))
            stats.hosts_down = int(hosts_elem.get("down", 0))
            stats.hosts_total = int(hosts_elem.get("total", 0))

    return stats


def _parse_host(host_elem: ET.Element) -> Optional[HostInfo]:
    # Status
    status_elem = host_elem.find("status")
    if status_elem is None:
        return None
    status = status_elem.get("state", "unknown")

    # Address
    address = ""
    hostname = ""
    for addr in host_elem.findall("address"):
        addr_type = addr.get("addrtype", "")
        if addr_type in ("ipv4", "ipv6"):
            address = addr.get("addr", "")
        elif addr_type == "mac":
            pass  # Could store MAC too

    # Hostnames
    hostnames_elem = host_elem.find("hostnames")
    if hostnames_elem is not None:
        hn = hostnames_elem.find("hostname")
        if hn is not None:
            hostname = hn.get("name", "")

    # Ports
    ports: List[PortInfo] = []
    ports_elem = host_elem.find("ports")
    if ports_elem is not None:
        for port_elem in ports_elem.findall("port"):
            port_info = _parse_port(port_elem)
            if port_info:
                ports.append(port_info)

    # OS detection
    os_matches: List[OSMatch] = []
    os_elem = host_elem.find("os")
    if os_elem is not None:
        for osmatch in os_elem.findall("osmatch"):
            os_matches.append(OSMatch(
                name=osmatch.get("name", ""),
                accuracy=int(osmatch.get("accuracy", 0)),
                line=osmatch.get("line", "")
            ))

    # Distance
    distance_elem = host_elem.find("distance")
    distance = None
    if distance_elem is not None:
        try:
            distance = int(distance_elem.get("value", 0))
        except (ValueError, TypeError):
            pass

    return HostInfo(
        address=address,
        hostname=hostname,
        status=status,
        ports=ports,
        os_matches=os_matches,
        distance=distance
    )


def _parse_port(port_elem: ET.Element) -> Optional[PortInfo]:
    port_id = int(port_elem.get("portid", 0))
    protocol = port_elem.get("protocol", "tcp")

    state_elem = port_elem.find("state")
    if state_elem is None:
        return None
    state = state_elem.get("state", "unknown")
    reason = state_elem.get("reason", "")

    # Service
    service = ServiceInfo()
    service_elem = port_elem.find("service")
    if service_elem is not None:
        service = ServiceInfo(
            name=service_elem.get("name", ""),
            product=service_elem.get("product", ""),
            version=service_elem.get("version", ""),
            extra_info=service_elem.get("extrainfo", ""),
            cpe=[cpe.text or "" for cpe in service_elem.findall("cpe")]
        )

    # Scripts
    scripts: List[ScriptOutput] = []
    for script in port_elem.findall("script"):
        scripts.append(ScriptOutput(
            id=script.get("id", ""),
            output=script.get("output", "")
        ))

    return PortInfo(
        port=port_id,
        protocol=protocol,
        state=state,
        reason=reason,
        service=service,
        scripts=scripts
    )
