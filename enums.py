# enums.py
from enum import Enum

class InventoryCategoryType(Enum):
    OTHER = 0
    COMMUTATION = 1
    ROUTER = 2
    SPLITTER = 4
    ODF = 7
    ARBITARY_DEVICE = 16
