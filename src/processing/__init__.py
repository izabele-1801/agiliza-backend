"""Imports para processadores de arquivo."""

from .base import FileProcessor
from .biomaxfarma_processor import BioMaxFarmaProcessor
from .cotefacil_processor import CotefacilProcessor
from .crescer_processor import CrescerProcessor
from .dsgfarma_processor import DSGFarmaProcessor
from .oceanica_processor import OceanicaProcessor
from .kimberly_processor import KimberlyProcessor
from .loreal_processor import LorealProcessor
from .natusfarma_processor import NatusFarmaProcessor
from .poupaminas_processor import PoupaminasProcessor
from .prudence_processor import PrudenceProcessor
from .unilever_processor import UnileverProcessor
from .siage_processor import SiageProcessor

__all__ = [
    'FileProcessor',
    'BioMaxFarmaProcessor',
    'CotefacilProcessor',
    'CrescerProcessor',
    'DSGFarmaProcessor',
    'OceanicaProcessor',
    'KimberlyProcessor',
    'LorealProcessor',
    'NatusFarmaProcessor',
    'PoupaminasProcessor',
    'PrudenceProcessor',
    'UnileverProcessor',
    'SiageProcessor',
]
