import os

import nibabel as nib
import numpy as np
import skimage.exposure
from lxml import etree

from util import constants
from util.enums import ScanFormat

_data = {}

def loadData(dataPath, format):
    # Load data from cache if able
    data = _data.get(dataPath)
    if data:
        print('loaded from acche')
        return data

    # Load the data normally
    if format == ScanFormat.TexasTechDixon:
        data = _loadTTUDixonData(dataPath)
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

def _loadTTUDixonData(dataPath):
    # Get the filenames for the rectified NIFTI files for current dataPath
    niiFatUpperFilename = os.path.join(dataPath, 'fatUpper.nii')
    niiFatLowerFilename = os.path.join(dataPath, 'fatLower.nii')
    niiWaterUpperFilename = os.path.join(dataPath, 'waterUpper.nii')
    niiWaterLowerFilename = os.path.join(dataPath, 'waterLower.nii')
    configFilename = os.path.join(dataPath, 'config.xml')

    if not os.path.isfile(niiFatUpperFilename) and os.path.isfile(niiFatLowerFilename) and \
            os.path.isfile(niiWaterUpperFilename) and os.path.isfile(niiWaterLowerFilename) and \
            os.path.isfile(configFilename):
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

    # TODO Why convert to float? Is this necessary
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
    raise NotImplementedError()

    # # This is for the T1 Data from WashU
    # def loadT1File(self, dataPath):
    #     dicomDir = dataPath + "/SCANS/"
    #     print(dicomDir)
    #     # Load DICOM directory and organize by patients, studies, and series
    #     patients = dicom2.loadDirectory(dicomDir)
    #     # Should only be one patient so retrieve it
    #     patient = patients.only()
    #     # Should only be one study so retrieve the one study
    #
    #     # doesn't work because of 35 studies
    #     # Double loop through studies then series (series is the images
    #     study = patient.only()
    #     #
    #     self.t1Series = []
    #     for UID, series in study.items():
    #         if series.Description.startswith('t1_'):
    #             self.t1Series.append(series)
    #
    #     # Sort cine images by the series number, looks nicer
    #     self.t1Series.sort(key=lambda x: x.Number)
    #
    #     # Loop through each t1 series
    #     for series in self.t1Series:
    #         seriesNumber = 21001
    #         sliceIndex = -1
    #
    #         sortedSeries, _, _ = dicom2.sortSlices(series, dicom2.MethodType.Unknown)
    #         if sliceIndex < 0:
    #             continue
    #         elif sliceIndex >= len(sortedSeries):
    #             QMessageBox.critical(self, 'Invalid slice index', 'Invalid slice index given for series number %i'
    #                                  % seriesNumber)
    #             return
    #
    #         print("Slices Sorted")
    #
    #     (method, type_, space, orientation, spacing, origin, volume) = \
    #         dicom2.combineSlices(sortedSeries, method=dicom2.MethodType.Unknown)
    #
    #     nrrdHeaderDict = {'space': space, 'space origin': origin,
    #                       'space directions': (np.identity(3) * np.array(spacing)).tolist()}
    #     nrrd.write(
    #         "/home/somecallmekenny/SIUE-Dixon-Fat-Segmentation-Algorithm/MRI_Data_Nrrd_Output/newOut.nrrd",
    #         volume, nrrdHeaderDict)
    #     constants.nrrdHeaderDict = {'space': 'right-anterior-superior'}
    #
    #     configFilename = os.path.join(dataPath, 'config.xml')
    #
    #     if not os.path.isfile(configFilename):
    #         print('Missing required files from source path folder. Continuing...')
    #         return None, None, None
    #     # Load config XML file
    #     config = etree.parse(configFilename)
    #
    #     # Get the root of the config XML file
    #     configRoot = config.getroot()
    #
    #     return volume, config
