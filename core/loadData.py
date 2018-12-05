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
from util.util import DCMIsMultiFrame

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
    imageSeries = None

    for _, study in patient.items():
        for _, series in study.items():
            # Skip any series that do not match this name
            if series.description.lower() != 't1_fl2d_tra_p3_256':
                continue

            # Save series and break out of loop
            imageSeries = series
            break

    if imageSeries is None:
        raise ValueError('Invalid DICOM data given: Should contain series named \'t1_fl2d_tra_p3_256\'')

    # Combine the image series to get a volume (along with metadata about that volume)
    (method, space, orientation, spacing, origin, image) = pydicomext.combineSlices(imageSeries,
                                                                                    MethodType.SliceLocation)

    # Normalize the image so that the intensities are between 0.0->1.0 and also convert to float data type
    image = skimage.exposure.rescale_intensity(image.astype(float), out_range=(0.0, 1.0))

    # Image data is in Fortran memory order (rows, columns), swap axes to make it C order (x, y)
    image = np.swapaxes(image, 0, 1)

    # Set constant pathDir to be the current data path to allow writing/reading from the current directory
    constants.pathDir = dataPath

    # Create a NRRD header dictionary that will be used to save the intermediate debug NRRDs to view progress
    constants.nrrdHeaderDict = {'space': space, 'space directions': orientation * spacing[:, None],
                                'space origin': origin}

    return image, config


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

    if not (DCMIsMultiFrame(fatSeries[0]) == DCMIsMultiFrame(fatSeries[1]) == DCMIsMultiFrame(waterSeries[0]) ==
            DCMIsMultiFrame(waterSeries[1])):
        raise Exception('Fat and water series should collectively use or don\'t use the multi-frame module')

    if DCMIsMultiFrame(fatSeries[0]):
        # TODO Determine which way these should be put together, could be reversed
        fatImage = np.stack((fatSeries[0][0].pixel_array, fatSeries[1][0].pixel_array), axis=0).T
        waterImage = np.stack((waterSeries[0][0].pixel_array, waterSeries[1][0].pixel_array), axis=0).T
    else:
        # Combine the two series into one large list of images
        fatSeries = fatSeries[0] + fatSeries[1]
        waterSeries = waterSeries[0] + waterSeries[1]

        # Combine the series to get the fat and water images
        (method, space, orientation, spacing, origin, fatImage) = \
            pydicomext.combineSlices(fatSeries, MethodType.SliceLocation)
        (method, space, orientation, spacing, origin, waterImage) = \
            pydicomext.combineSlices(waterSeries, MethodType.SliceLocation)

    # Normalize the fat/water images so that the intensities are between (0.0, 1.0) and also converts to float data type
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
