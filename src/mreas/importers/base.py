from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple

from mreas.core.models import Source, Chunk

class BaseImporter(ABC):
    """
    Abstract base class for all importers.
    An importer parses an input (like a file or directory) and yields Source and Chunk models.
    """
    
    @abstractmethod
    def parse(self, path: Path) -> Tuple[list[Source], list[Chunk]]:
        """
        Parse the given path and return a list of sources and a list of chunks.
        
        Args:
            path: Path to the input file or directory to parse.
            
        Returns:
            Tuple containing (sources_list, chunks_list).
        """
        pass
