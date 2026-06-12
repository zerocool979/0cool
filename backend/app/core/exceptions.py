from fastapi import HTTPException
from typing import Optional


class NmapSLMException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NmapExecutionError(NmapSLMException):
    def __init__(self, message: str):
        super().__init__(f"Nmap execution error: {message}", status_code=500)


class NmapParseError(NmapSLMException):
    def __init__(self, message: str):
        super().__init__(f"Nmap parse error: {message}", status_code=422)


class InvalidCommandError(NmapSLMException):
    def __init__(self, message: str):
        super().__init__(f"Invalid command: {message}", status_code=400)


class OllamaConnectionError(NmapSLMException):
    def __init__(self, message: str = "Cannot connect to Ollama"):
        super().__init__(message, status_code=503)


class OllamaModelNotFoundError(NmapSLMException):
    def __init__(self, model: str):
        super().__init__(f"Model '{model}' not found in Ollama", status_code=404)


class ReportGenerationError(NmapSLMException):
    def __init__(self, message: str):
        super().__init__(f"Report generation error: {message}", status_code=500)


class ScanNotFoundError(NmapSLMException):
    def __init__(self, scan_id: str):
        super().__init__(f"Scan '{scan_id}' not found", status_code=404)
