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
    configFilename = os.path.join(dataPath, 'config.yml')

    if not (os.path.isfile(niiFatUpperFilename) and os.path.isfile(niiFatLowerFilename) and
            os.path.isfile(niiWaterUpperFilename) and os.path.isfile(niiWaterLowerFilename)):
        raise Exception('Missing required files from source path folder.')

    # Load the configuration file if it exists
    if os.path.exists(configFilename):
        with open(configFilename, 'r') as fh:
            config = yaml.load(fh)
    else:
        # Otherwise create the config as an empty dictionary
        config = {}

    # Load unrectified NIFTI files for the current dataPath
    niiFatUpper = nib.load(niiFatUpperFilename)
    niiFatLower = nib.load(niiFatLowerFilename)
    niiWaterUpper = nib.load(niiWaterUpperFilename)
    niiWaterLower = nib.load(niiWaterLowerFilename)

    # Affine matrix, origin & spacing for upper image. Fat & water should have same info
    upperAffineMatrixWT = niiFatUpper.header.get_best_affine()
    upperAffineMatrix = np.array(upperAffineMatrixWT[:-1, :-1])
    upperOrigin = np.array(upperAffineMatrixWT[:-1, -1])
    spacing = np.linalg.norm(upperAffineMatrix, axis=1)

    # -1 for flipped axes and 1 for non-flipped axes (RAS)
    axesFlipped = np.where(np.diag(upperAffineMatrix) > 0, 1, -1)

    # Odd hacks here to get the right amount of offset, this only applies to the listed subjects
    # No idea why
    # Toggle the axes flipped from 1 to -1 or -1 to 1. This way it will shift the opposite direction
    if os.path.basename(dataPath) in ['Subject0003_Final', 'Subject0003_Initial']:
        axesFlipped[0] *= -1

    # Affine matrix, origin & spacing for lower image. Fat & water should have same info
    lowerAffineMatrixWT = niiFatLower.header.get_best_affine()
    lowerAffineMatrix = np.array(lowerAffineMatrixWT[:-1, :-1])
    lowerOrigin = np.array(lowerAffineMatrixWT[:-1, -1])

    # Use inferior and superior axial slice to obtain the valid portion of the upper and lower fat and water images
    fatUpperImage, fatLowerImage = niiFatUpper.get_data(), niiFatLower.get_data()
    waterUpperImage, waterLowerImage = niiWaterUpper.get_data(), niiWaterLower.get_data()

    # Take lower origin and subtract from the upper origin and divide by spacing
    # For the Z dimension we want to add the fat lower shape to get the amount of slices that overlap
    # Then convert to integer after rounding down to get the number of indices to shift to align
    misalignedIndexAmount = np.floor((lowerOrigin - upperOrigin) / (spacing * axesFlipped) +
                                     (0, 0, fatLowerImage.shape[2])).astype(int)

    if misalignedIndexAmount[2] > 0:
        fatLowerImage = fatLowerImage[:, :, :-misalignedIndexAmount[2]]
        waterLowerImage = waterLowerImage[:, :, :-misalignedIndexAmount[2]]

    if misalignedIndexAmount[1] != 0:
        # Roll the fat upper image back the difference amount to align better to lower image
        fatLowerImage = np.roll(fatLowerImage, misalignedIndexAmount[1], axis=1)
        waterLowerImage = np.roll(waterLowerImage, misalignedIndexAmount[1], axis=1)

    if misalignedIndexAmount[0] != 0:
        # Roll the fat upper image back the difference amount to align better to lower image
        fatLowerImage = np.roll(fatLowerImage, misalignedIndexAmount[0], axis=0)
        waterLowerImage = np.roll(waterLowerImage, misalignedIndexAmount[0], axis=0)

    # Piece together the upper and lower parts of the fat and water images into one volume
    fatImage = np.concatenate((fatLowerImage.T, fatUpperImage.T), axis=0)
    waterImage = np.concatenate((waterLowerImage.T, waterUpperImage.T), axis=0)

    # Normalize the fat/water images so that the intensities are between (0.0, 1.0) and also converts to float data type
    fatImage = skimage.exposure.rescale_intensity(fatImage.astype(float), out_range=(0.0, 1.0))
    waterImage = skimage.exposure.rescale_intensity(waterImage.astype(float), out_range=(0.0, 1.0))

    # Set constant pathDir to be the current data path to allow writing/reading from the current directory
    constants.pathDir = dataPath

    # Create a NRRD header dictionary that will be used to save the intermediate debug NRRDs to view progress
    constants.nrrdHeaderDict = {
        'space': 'right-anterior-superior',
        'space directions': upperAffineMatrix,
        'space origin': lowerOrigin
    }

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
        'space directions': volume.orientation * volume.spacing[:, None],
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
        'space directions': fatVolume.orientation * fatVolume.spacing[:, None],
        'space origin': fatVolume.origin
    }

    return fatImage, waterImage, config
