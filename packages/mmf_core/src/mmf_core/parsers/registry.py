"""Parser Registry and BaseParser architecture."""
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Dict, Any, Type
from ..models import Artifact, TimelineEvent

class BaseParser(ABC):
    """Abstract base class for all forensic artifact parsers."""
    parser_id: str = "base_parser"
    name: str = "Base Parser"
    version: str = "1.0.0"
    platform: str = "generic"
    target_files: List[str] = []

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if parser can process the target file."""
        pass

    @abstractmethod
    def parse(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        """Parse source file into normalized artifacts and timeline events."""
        pass

class ParserRegistry:
    """Registry managing available artifact parsers and dispatch."""
    
    def __init__(self):
        self._parsers: Dict[str, BaseParser] = {}

    def register(self, parser: BaseParser):
        self._parsers[parser.parser_id] = parser

    def get_parser(self, parser_id: str) -> BaseParser:
        return self._parsers.get(parser_id)

    def list_parsers(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": p.parser_id,
                "name": p.name,
                "version": p.version,
                "platform": p.platform,
                "target_files": p.target_files
            }
            for p in self._parsers.values()
        ]

    def find_parsers_for_file(self, file_path: Path) -> List[BaseParser]:
        matching = []
        for p in self._parsers.values():
            try:
                if p.can_parse(file_path):
                    matching.append(p)
            except Exception:
                continue
        return matching

    def parse_file(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        all_artifacts = []
        all_timeline = []
        parsers = self.find_parsers_for_file(file_path)
        for parser in parsers:
            try:
                artifacts, timeline = parser.parse(file_path, evidence_id, case_id)
                all_artifacts.extend(artifacts)
                all_timeline.extend(timeline)
            except Exception as e:
                # Log parser error without crashing entire analysis
                continue
        return all_artifacts, all_timeline

    def parse_directory(self, dir_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        """Walk extracted working copy directory and parse all supported files."""
        all_artifacts = []
        all_timeline = []
        if not dir_path.is_dir():
            return all_artifacts, all_timeline

        for root, _, files in os.walk(dir_path):
            for file in files:
                f_path = Path(root) / file
                artifacts, timeline = self.parse_file(f_path, evidence_id, case_id)
                all_artifacts.extend(artifacts)
                all_timeline.extend(timeline)
                
        return all_artifacts, all_timeline
