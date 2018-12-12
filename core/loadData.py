import logging
import os
import re

import nibabel as nib
import numpy as np
import skimage.exposure
import yaml
from lxml import etree

from util import constants
from util import pydicomext
from util.enums import ScanFormat
from util.pydicomext import MethodType

logger = logging.getLogger(__name__)

_data = {}


def loadData(dataPath, format, saveCache=True):
    # Load data from cache if able
    data = _data.get(dataPath)
    if data:
        return data

    # Load the data normally
    if format == ScanFormat.TexasTechDixon:
        data = _loadTexasTechDixonData(dataPath)
    elif format == ScanFormat.WashUUnknown:
        data = _loadWashUUnknownData(dataPath)
    elif format == ScanFormat.WashUDixon:
        data = _loadWashUDixonData(dataPath)
    else:
        raise ValueError('Format parameter must be a valid ScanFormat option')

    # Save the data to cache if saveCache is True
    if saveCache:
        _data[dataPath] = data

    return data


def updateCachedData(dataPath, data):
    # Update cached data or add if not available
    _data[dataPath] = data


def _loadTexasTechDixonData(dataPath):
    # Get the filenames for the rectified NIFTI files for current dataPath
    niiFatUpperFilename = os.path.join(dataPath, 'fatUpper.nii')
    niiFatLowerFilename = os.path.join(dataPath, 'fatLower.nii')
    niiWaterUpperFilename = os.path.join(dataPath, 'waterUpper.nii')
    niiWaterLowerFilename = os.path.join(dataPath, 'waterLower.nii')
    configFilename = os.path.join(dataPath, 'config.xml')

    if not (os.path.isfile(niiFatUpperFilename) and os.path.isfile(niiFatLowerFilename) and \
            os.path.isfile(niiWaterUpperFilename) and os.path.isfile(niiWaterLowerFilename) and \
            os.path.isfile(configFilename)):
        raise Exception('Missing required files from source path folder.')

    # Load unrectified NIFTI files for the current dataPath
    niiFatUpper = nib.load(niiFatUpperFilename)
    niiFatLower = nib.load(niiFatLowerFilename)
    niiWaterUpper = nib.load(niiWaterUpperFilename)
    niiWaterLower = nib.load(niiWaterLowerFilename)

    # Load config XML file
    config = etree.parse(configFilename)

    # Get the root of the config XML file
    configRoot = config.getroot()

    # Piece together upper and lower images for fat and water
    # Retrieve the inferior and superior axial slice from config file for upper and lower images
    imageUpperTag = configRoot.find('imageUpper')
    imageLowerTag = configRoot.find('imageLower')
    imageUpperInferiorSlice = int(imageUpperTag.attrib['inferiorSlice'])
    imageUpperSuperiorSlice = int(imageUpperTag.attrib['superiorSlice'])
    imageLowerInferiorSlice = int(imageLowerTag.attrib['inferiorSlice'])
    imageLowerSuperiorSlice = int(imageLowerTag.attrib['superiorSlice'])

    # Use inferior and superior axial slice to obtain the valid portion of the upper and lower fat and water images
    fatUpperImage = niiFatUpper.get_data()[:, :, imageUpperInferiorSlice:imageUpperSuperiorSlice]
    fatLowerImage = niiFatLower.get_data()[:, :, imageLowerInferiorSlice:imageLowerSuperiorSlice]
    waterUpperImage = niiWaterUpper.get_data()[:, :, imageUpperInferiorSlice:imageUpperSuperiorSlice]
    waterLowerImage = niiWaterLower.get_data()[:, :, imageLowerInferiorSlice:imageLowerSuperiorSlice]

    # Piece together the upper and lower parts of the fat and water images into one volume
    fatImage = np.concatenate((fatLowerImage.T, fatUpperImage.T), axis=0)
    waterImage = np.concatenate((waterLowerImage.T, waterUpperImage.T), axis=0)

    # Normalize the fat/water images so that the intensities are between (0.0, 1.0) and also converts to float data type
    fatImage = skimage.exposure.rescale_intensity(fatImage.astype(float), out_range=(0.0, 1.0))
    waterImage = skimage.exposure.rescale_intensity(waterImage.astype(float), out_range=(0.0, 1.0))

    # Set constant pathDir to be the current data path to allow writing/reading from the current directory
    constants.pathDir = dataPath

    # Create a NRRD header dictionary that will be used to save the intermediate debug NRRDs to view progress
    constants.nrrdHeaderDict = {'space': 'right-anterior-superior'}
    constants.nrrdHeaderDict['space directions'] = np.hstack((niiFatUpper.header['srow_x'][0:-1, None],
                                                              niiFatUpper.header['srow_y'][0:-1, None],
                                                              niiFatUpper.header['srow_z'][0:-1, None]))

    constants.nrrdHeaderDict['space origin'] = (niiFatUpper.header['srow_x'][-1],
                                                niiFatUpper.header['srow_y'][-1],
                                                niiFatUpper.header['srow_z'][-1])

    return fatImage, waterImage, config


def _loadWashUUnknownData(dataPath):
    # Create necessary filenames, one for DICOM directory and another for the configuration file
    dicomDirectory = os.path.join(dataPath, 'SCANS')
    configFilename = os.path.join(dataPath, 'config.yml')

    # Load the configuration file if it exists
    if os.path.exists(configFilename):
        with open(configFilename, 'r') as fh:
            config = yaml.load(fh)
    else:
        # Otherwise create the config as an empty dictionary
        config = {}

    # Load DICOM data
    dicomDir = pydicomext.loadDirectory(dicomDirectory)

    # Should only be one patient
    patient = dicomDir.only()

    # Series for unknown sequence containing abdominal information
    series = None

    for _, study in patient.items():
        for _, series_ in study.items():
            # Skip any series that do not match this name
            if series_.description.lower() != 't1_fl2d_tra_p3_256':
                continue

            # Save series and break out of loop
            series = series_
            break

    if series is None:
        logger.debug(series)
        raise ValueError('Invalid DICOM data given: Should contain series named \'t1_fl2d_tra_p3_256\'')

    # Combine the series to get a volume
    volume = series.combine(methods=MethodType.SliceLocation)

    # Get Numpy array from volume
    data = volume.data

    # Normalize the image so that the intensities are between 0.0->1.0 and also convert to float data type
    data = skimage.exposure.rescale_intensity(data.astype(float), out_range=(0.0, 1.0))

    # Set constant pathDir to be the current data path to allow writing/reading from the current directory
    constants.pathDir = dataPath

    # Create a NRRD header dictionary that will be used to save the intermediate debug NRRDs to view progress
    constants.nrrdHeaderDict = {
        'space': volume.space,
        'space directions': volume.orientation * volume.spacing[::-1, None],
        'space origin': volume.origin
    }

    return data, config


def _loadWashUDixonData(dataPath):
    # Create necessary filenames, one for DICOM directory and another for the configuration file
    dicomDirectory = os.path.join(dataPath, 'SCANS')
    configFilename = os.path.join(dataPath, 'config.yml')

    # Load the configuration file if it exists
    if os.path.exists(configFilename):
        with open(configFilename, 'r') as fh:
            config = yaml.load(fh)
    else:
        # Otherwise create the config as an empty dictionary
        config = {}

    # Load DICOM data
    dicomDir = pydicomext.loadDirectory(dicomDirectory)

    # Should only be one patient
    patient = dicomDir.only()

    # Thoracic and abdominal series will be stored for the fat/water scans here
    fatSeries, waterSeries = [], []

    for _, study in patient.items():
        for _, series in study.items():
            match = re.match(r'(^T1 VIBE DIXON ABD [\d]*mm_([FW])$)|(^t1_vibe_dixon_tra_p3_bh_([FW])$)',
                             series.description)

            # Skip if match not found
            if not match:
                continue

            # Retrieve 2nd or 4th group whichever is present
            if match.group(2):
                imageType = match.group(2)
            elif match.group(4):
                imageType = match.group(4)
            else:
                imageType = None

            # Throw an error if its not F or W prefix
            if imageType not in ['F', 'W']:
                raise ValueError('Invalid image type (F or W)')

            # Append to fat or water series depending on series description
            fatSeries.append(series) if imageType == 'F' else waterSeries.append(series)

    if len(fatSeries) != 2 or len(waterSeries) != 2:
        raise Exception('Invalid DICOM data given: Should only be an abdominal and thoracic fat and water image.')

    if not (fatSeries[0].isMultiFrame == fatSeries[1].isMultiFrame == waterSeries[0].isMultiFrame ==
            waterSeries[1].isMultiFrame):
        raise Exception('Fat and water series should collectively use or don\'t use the multi-frame module')

    # Merge the two fat/water series into one series
    fatSeries = pydicomext.mergeSeries(fatSeries)
    waterSeries = pydicomext.mergeSeries(waterSeries)

    # Use the following method to combine the fat and water series
    # Use slice location for standard DICOM but for enhanced DICOM use patient location
    method = MethodType.MFPatientLocation if fatSeries.isMultiFrame else MethodType.SliceLocation

    # Combine the fat and water series into a volume
    fatVolume = fatSeries.combine(methods=method)
    waterVolume = waterSeries.combine(methods=method)

    # Normalize the fat/water images so that the intensities are between (0.0, 1.0) and also converts to float data type
    fatImage = skimage.exposure.rescale_intensity(fatVolume.data.astype(float), out_range=(0.0, 1.0))
    waterImage = skimage.exposure.rescale_intensity(waterVolume.data.astype(float), out_range=(0.0, 1.0))

    # Set constant pathDir to be the current data path to allow writing/reading from the current directory
    constants.pathDir = dataPath

    # Create a NRRD header dictionary that will be used to save the intermediate debug NRRDs to view progress
    constants.nrrdHeaderDict = {
        'space': fatVolume.space,
        'space directions': fatVolume.orientation * fatVolume.spacing[::-1, None],
        'space origin': fatVolume.origin
    }

    return fatImage, waterImage, config
