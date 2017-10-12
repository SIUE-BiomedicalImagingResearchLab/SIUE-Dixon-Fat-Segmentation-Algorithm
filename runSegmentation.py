import time

import SimpleITKutils as sitku
from biasCorrection import *


# Segment depots of adipose tissue given Dixon MRI images
def runSegmentation(niiFatUpper, niiFatLower, niiWaterUpper, niiWaterLower, config):
    # If debug is turned on, then create the directory where the debug files will be saved
    # The makedirs command is in try/catch because if it already exists, it will throw an exception and we just want
    # to continue in that case
    if constants.debug:
        try:
            os.makedirs(os.path.join(constants.pathDir, 'debug'))
        except:
            pass

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
    fatUpperImage = niiFatUpper[:, :, imageUpperInferiorSlice:imageUpperSuperiorSlice]
    fatLowerImage = niiFatLower[:, :, imageLowerInferiorSlice:imageLowerSuperiorSlice]
    waterUpperImage = niiWaterUpper[:, :, imageUpperInferiorSlice:imageUpperSuperiorSlice]
    waterLowerImage = niiWaterLower[:, :, imageLowerInferiorSlice:imageLowerSuperiorSlice]

    # # TODO Do all of this numpy operations with ITK so I can just be consistent
    # Cast the four images to 32-bit floats
    fatUpperImage = sitk.Cast(fatUpperImage, sitk.sitkFloat32)
    fatLowerImage = sitk.Cast(fatLowerImage, sitk.sitkFloat32)
    waterUpperImage = sitk.Cast(waterUpperImage, sitk.sitkFloat32)
    waterLowerImage = sitk.Cast(waterLowerImage, sitk.sitkFloat32)

    # Concatenate the lower and upper image into one along the Z dimension
    # TODO Consider removing this and performing segmentation on upper/lower pieces separately
    fatImage = sitku.concatenate((fatLowerImage, fatUpperImage), 2)
    waterImage = sitku.concatenate((waterLowerImage, waterUpperImage), 2)

    # TODO Create procedural function for MinimumMaximumImageFilter in SimpleITK
    # TODO Add option to specify parameters like Function(image, param=Value) to SimpleITK
    # Todo create procedural function for StatisticsImageFilter in SimpleITK
    # Normalize the fat/water images so that the intensities are between (0.0, 1.0)
    fatImage = sitk.RescaleIntensity(fatImage, 0.0, 1.0)
    waterImage = sitk.RescaleIntensity(waterImage, 0.0, 1.0)

    # Perform bias correction on MRI images to remove inhomogeneity
    tic = time.perf_counter()
    if os.path.exists(os.path.join(constants.pathDir, 'debug', 'fatImage.img')) and \
            os.path.exists(os.path.join(constants.pathDir, 'debug', 'waterImage.img')):
        fatImage = sitk.ReadImage(os.path.join(constants.pathDir, 'debug', 'fatImage.img'))
        waterImage = sitk.ReadImage(os.path.join(constants.pathDir, 'debug', 'waterImage.img'))
    else:
        fatImage = correctBias(fatImage, shrinkFactor=constants.shrinkFactor,
                               prefix='fatImageBiasCorrection')
        waterImage = correctBias(waterImage, shrinkFactor=constants.shrinkFactor,
                                 prefix='waterImageBiasCorrection')
    toc = time.perf_counter()
    print('N4ITK bias field correction took %f seconds' % (toc - tic))

    # Print out the fat and water image after bias correction
    if constants.debug:
        sitk.WriteImage(fatImage, os.path.join(constants.pathDir, 'debug', 'fatImage.img'))
        sitk.WriteImage(waterImage, os.path.join(constants.pathDir, 'debug', 'waterImage.img'))

    # Create empty arrays that will contain slice-by-slice intermediate images when processing the images
    # These are used to print the entire 3D volume out for debugging afterwards
    blankImage = sitk.Image(fatImage.GetWidth(), fatImage.GetHeight(), sitk.sitkUInt8)
    blankImage.CopyInformation(fatImage[:, :, 0])
    fatImageMasks = [blankImage] * fatImage.GetDepth()
    waterImageMasks = [blankImage] * fatImage.GetDepth()
    totalImageMasks = [blankImage] * fatImage.GetDepth()

    for slice in range(0, fatImage.GetDepth() // 3):
        tic = time.perf_counter()

        fatImageSlice = fatImage[:, :, slice]
        waterImageSlice = waterImage[:, :, slice]

        # Segment fat/water images using K-means
        # The value 1 indicates background object so invert it by setting all 0 values to 1
        fatImageMask = sitk.ScalarImageKmeans(fatImageSlice, [0.0] * constants.kMeanClusters) == 0
        waterImageMask = sitk.ScalarImageKmeans(waterImageSlice, [0.0] * constants.kMeanClusters) == 0
        fatImageMasks[slice] = fatImageMask
        waterImageMasks[slice] = waterImageMask

        totalImageMask = fatImageMask | waterImageMask
        totalImageMasks[slice] = totalImageMask

        toc = time.perf_counter()
        print('Completed slice %i in %f seconds' % (slice, toc - tic))

    if constants.debug:
        sitk.WriteImage(sitk.JoinSeries(fatImageMasks), os.path.join(constants.pathDir, 'debug', 'fatImageMask.img'))
        sitk.WriteImage(sitk.JoinSeries(waterImageMasks), os.path.join(constants.pathDir, 'debug',
                                                                       'waterImageMask.img'))
        sitk.WriteImage(sitk.JoinSeries(totalImageMasks), os.path.join(constants.pathDir, 'debug',
                                                                       'totalImageMask.img'))

