from enum import IntEnum

class ScanFormat(IntEnum):
    TexasTechDixon = 0
    WashUUnknown = 1
    WashUDixon = 2

    def __str__(self):
        if self == ScanFormat.TexasTechDixon:
            return 'Texas Tech Dixon'
        elif self == ScanFormat.WashUUnknown:
            return 'WashU Unknown'
        elif self == ScanFormat.WashUDixon:
            return 'WashU Dixon'
