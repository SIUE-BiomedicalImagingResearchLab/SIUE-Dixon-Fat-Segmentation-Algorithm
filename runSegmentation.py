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
    fatImage = correctBias(fatImage, shrinkFactor=constants.shrinkFactor,
                           prefix='fatImageBiasCorrection')
    waterImage = correctBias(waterImage, shrinkFactor=constants.shrinkFactor,
                             prefix='waterImageBiasCorrection')
    toc = time.perf_counter()
    print('N4ITK bias field correction took %f seconds' % (toc - tic))

    if constants.debug:
        sitk.WriteImage(fatImage, os.path.join(constants.pathDir, 'debug', 'fatImage.img'))
        sitk.WriteImage(waterImage, os.path.join(constants.pathDir, 'debug', 'waterImage.img'))


    # TODO Try doing this on a slice-by-slice basis! Could be faster

    # Segment fat/water images using K-means
    tic = time.perf_counter()
    fatImageMask = sitk.ScalarImageKmeans(fatImage, [0.0] * constants.kMeanClusters)
    waterImageMask = sitk.ScalarImageKmeans(waterImage, [0.0] * constants.kMeanClusters)
    toc = time.perf_counter()
    print('K means clustering (clusters = %i) took %f seconds' % (constants.kMeanClusters, toc - tic))

    if constants.debug:
        sitk.WriteImage(fatImageMask, os.path.join(constants.pathDir, 'debug', 'fatImageMask.img'))
        sitk.WriteImage(waterImageMask, os.path.join(constants.pathDir, 'debug', 'waterImageMask.img'))

    i = 4

    # Loop through each axial slice of the image.
    # This is easier than performing operations on the entire image since many
    # image processing algorithms require a 2D image, such as morphological
    # operations
    # for slice in range(0, fatImage.shape[2]):
    # fatImageSlice = fatImage[:, :, slice]
    # waterImageSlice = waterImage[:, :, slice]

    # fatImageSlice2 = fatImage2[:, :, slice]
    # waterImageSlice2 = waterImage2[:, :, slice]

    # Retrieve ITK images from the numpy arrays of image slice
    # TODO Switch to using GetImageViewFromArray when ITK 4.12 is available, performs soft copy
    # fatImageSliceITK = sitk.GetImageFromArray(fatImageSlice)
    # waterImageSliceITK = sitk.GetImageFromArray(waterImageSlice)

    # TODO Apply CLAHE for contrast

    # pyplot.subplot(1, 2, 1)
    # pyplot.imshow(fatImageSlice, cmap=pyplot.gray())

    # pyplot.subplot(1, 2, 2)
    # pyplot.imshow(fatImageSlice2, cmap=pyplot.gray())
    # pypitk.imshow(fatImageSliceITK, cmap=pyplot.gray())
    # pyplot.title('Slice #%i' % (slice))
    # pyplot.pause(1.0)

    # print('Done with slice %i' % (slice))

    # if constants.showBodyMask:
    # Show the matter slice and body mask to see how well it fits
    # Set title to slice number to record any odd slices and draw now so that it draws the title
    # pyplot.imshow(fatImageSlice, cmap=pyplot.gray())
    # pyplot.title('Slice #%i' % (slice))

    # TODO Get imshowpair to work in Python
    # imshowpair(waterImageSlice, bodyMask
    # {slice});

    # Sleep for 1 second to allow user to view the image
    # pyplot.pause(1)
