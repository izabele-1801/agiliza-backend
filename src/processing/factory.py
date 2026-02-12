"""Factory para selecionar e instanciar processadores."""

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
from .labotrat_processor import LabotratProcessor
from .pdf_processor import PDFProcessor
from .txt_processor import TXTProcessor
from .excel_processor import ExcelProcessor
from .image_processor import ImageProcessor


PROCESSOR_CLASSES = {
    'biomaxfarma': BioMaxFarmaProcessor,
    'cotefacil': CotefacilProcessor,
    'crescer': CrescerProcessor,
    'dsgfarma': DSGFarmaProcessor,
    'oceanica': OceanicaProcessor,
    'kimberly': KimberlyProcessor,
    'loreal': LorealProcessor,
    'natusfarma': NatusFarmaProcessor,
    'poupaminas': PoupaminasProcessor,
    'prudence': PrudenceProcessor,
    'unilever': UnileverProcessor,
    'siage': SiageProcessor,
    'labotrat': LabotratProcessor,
    'pdf': PDFProcessor,
    'txt': TXTProcessor,
    'excel': ExcelProcessor,
    'image': ImageProcessor,
}


def get_processor(processor_name: str) -> FileProcessor | None:
    """
    Obtém instância do processador pelo nome.
    
    Args:
        processor_name: Nome do processador (ex: 'biomaxfarma', 'excel', 'pdf')
    
    Returns:
        Instância do processador ou None se não encontrado
    """
    processor_class = PROCESSOR_CLASSES.get(processor_name.lower())
    if processor_class:
        return processor_class()
    return None


def get_available_processors() -> list:
    """Retorna lista de processadores disponíveis."""
    return list(PROCESSOR_CLASSES.keys())
