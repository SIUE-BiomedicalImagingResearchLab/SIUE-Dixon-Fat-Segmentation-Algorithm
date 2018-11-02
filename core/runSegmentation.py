from core.runSegmentation_TexasTechDixon import runSegmentation as runSegmentationTexasTechDixon
from core.runSegmentation_WashUDixon import runSegmentation as runSegmentationWashUDixon
from core.runSegmentation_WashUUnknown import runSegmentation as runSegmentationWashUUnknown
from util.enums import ScanFormat


def runSegmentation(data, format):
    if format == ScanFormat.TexasTechDixon:
        runSegmentationTexasTechDixon(data)
    elif format == ScanFormat.WashUUnknown:
        runSegmentationWashUUnknown(data)
    elif format == ScanFormat.WashUDixon:
        runSegmentationWashUDixon(data)
    else:
        raise ValueError('Format parameter must be a valid ScanFormat option')
