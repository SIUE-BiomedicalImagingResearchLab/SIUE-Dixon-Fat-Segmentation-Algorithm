import os
import re

import nibabel as nib
import numpy as np
import skimage.exposure
import yaml
from lxml import etree

from util import constants
from util import dicom2
from util.enums import ScanFormat

_data = {}


def loadData(dataPath, format):
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

    # Save the data to cache
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
    fatImage = np.concatenate((fatLowerImage, fatUpperImage), axis=2)
    waterImage = np.concatenate((waterLowerImage, waterUpperImage), axis=2)

    # Normalize the fat/water images so that the intensities are between (0.0, 1.0) and also converts to float data type
    fatImage = skimage.exposure.rescale_intensity(fatImage.astype(float), out_range=(0.0, 1.0))
    waterImage = skimage.exposure.rescale_intensity(waterImage.astype(float), out_range=(0.0, 1.0))

    # Set constant pathDir to be the current data path to allow writing/reading from the current directory
    constants.pathDir = dataPath

    # Create a NRRD header dictionary that will be used to save the intermediate debug NRRDs to view progress
    constants.nrrdHeaderDict = {'space': 'right-anterior-superior'}
    constants.nrrdHeaderDict['space directions'] = (niiFatUpper.header['srow_x'][0:-1],
                                                    niiFatUpper.header['srow_y'][0:-1],
                                                    niiFatUpper.header['srow_z'][0:-1])

    constants.nrrdHeaderDict['space origin'] = (niiFatUpper.header['srow_x'][-1],
                                                niiFatUpper.header['srow_y'][-1],
                                                niiFatUpper.header['srow_z'][-1])

    return fatImage, waterImage, config


def _loadWashUUnknownData(dataPath):
    raise NotImplementedError()


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
    patients = dicom2.loadDirectory(dicomDirectory)

    # Should only be one patient
    patient = patients.only()

    # Thoracic and abdominal series will be stored for the fat/water scans here
    fatSeries, waterSeries = [], []

    for _, study in patient.items():
        for _, series in study.items():
            match = re.match(r'^T1 VIBE DIXON ABD [\d]*mm_([FW])$', series.Description)
            # Skip if match not found
            if not match:
                continue

            # Append to fat or water series depending on series description
            fatSeries.append(series) if match.group(1) == 'F' else waterSeries.append(series)

    if len(fatSeries) != 2 or len(waterSeries) != 2:
        raise Exception('Invalid DICOM data given: Should only be an abdominal and thoracic fat and water image.')

    # Combine the two series into one large list of images
    fatSeries = fatSeries[0] + fatSeries[1]
    waterSeries = waterSeries[0] + waterSeries[1]

    # Combine the series to get the fat and water images
    (method, space, orientation, spacing, origin, fatImage) = \
        dicom2.combineSlices(fatSeries, dicom2.MethodType.SliceLocation)
    (method, space, orientation, spacing, origin, waterImage) = \
        dicom2.combineSlices(waterSeries, dicom2.MethodType.SliceLocation)

    # Normalize the fat/water images so that the intensities are between (0.0, 1.0) and also converts to float data type
    # Also take the transpose of the fat and water images to get it such that the first dimension is x & second y
    # instead of rows & columns
    fatImage = skimage.exposure.rescale_intensity(fatImage.astype(float), out_range=(0.0, 1.0))
    waterImage = skimage.exposure.rescale_intensity(waterImage.astype(float), out_range=(0.0, 1.0))

    # Image data is in Fortran memory order (rows, columns), swap axes to make it C order (x, y)
    fatImage, waterImage = np.swapaxes(fatImage, 0, 1), np.swapaxes(waterImage, 0, 1)

    # Set constant pathDir to be the current data path to allow writing/reading from the current directory
    constants.pathDir = dataPath

    # Create a NRRD header dictionary that will be used to save the intermediate debug NRRDs to view progress
    constants.nrrdHeaderDict = {'space': space, 'space directions': orientation * spacing[:, None],
                                'space origin': origin}

    return fatImage, waterImage, config
