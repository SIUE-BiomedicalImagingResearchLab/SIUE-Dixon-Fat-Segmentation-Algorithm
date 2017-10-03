import numpy
import constants
import matplotlib.pyplot as pyplot
import SimpleITK as sitk
import time
import pyplotsitkBridge as pypitk

# Segment depots of adipose tissue given Dixon MRI images
def runSegmentation(niiFatUpper, niiFatLower, niiWaterUpper, niiWaterLower, config):
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

    # Concatenate the lower and upper image into one along the Z dimension
    fatImage = numpy.concatenate((fatLowerImage, fatUpperImage), 2)
    waterImage = numpy.concatenate((waterLowerImage, waterUpperImage), 2)

    # Normalize the fat image so that the intensities are between (0.0, 1.0)
    fatImageMin = fatImage.min()
    fatImageMax = fatImage.max()
    fatImage = (fatImage - fatImageMin) / (fatImageMax - fatImageMin)

    # Normalize the water image so that the intensities are between (0.0, 1.0)
    waterImageMin = waterImage.min()
    waterImageMax = waterImage.max()
    waterImage = (waterImage - waterImageMin) / (waterImageMax - waterImageMin)

    fatImageITK = sitk.GetImageFromArray(fatImage)
    waterImageITK = sitk.GetImageFromArray(waterImage)

    # fatImageMask = sitk.OtsuThreshold(fatImageITK, 0, 1, 200)
    # waterImageMask = sitk.OtsuThreshold(fatImageITK, 0, 1, 200)
    #
    # fatImageITK = sitk.N4BiasFieldCorrection(fatImageITK, fatImageMask)
    # waterImageITK = sitk.N4BiasFieldCorrection(waterImageITK, waterImageMask)

    # Loop through each axial slice of the image.
    # This is easier than performing operations on the entire image since many
    # image processing algorithms require a 2D image, such as morphological
    # operations
    for slice in range(0, fatImage.shape[2]):
        fatImageSlice = fatImage[:, :, slice]
        waterImageSlice = waterImage[:, :, slice]

        # Retrieve ITK images from the numpy arrays of image slice
        # TODO Switch to using GetImageViewFromArray when ITK 4.12 is available, performs soft copy
        fatImageSliceITK = sitk.GetImageFromArray(fatImageSlice)
        waterImageSliceITK = sitk.GetImageFromArray(waterImageSlice)

        # TODO Apply CLAHE for contrast

        # TODO Bias error correction in ITK

        # img_data = sitk.Cast(img, sitk.sitkFloat32)
        fatImageSliceITK = sitk.Cast(fatImageSliceITK, sitk.sitkFloat32)
        waterImageSliceITK = sitk.Cast(waterImageSliceITK, sitk.sitkFloat32)

        fatImageSliceITK = sitk.Shrink(fatImageSliceITK, (4, 4, 4))
        waterImageSliceITK = sitk.Shrink(waterImageSliceITK, (4, 4, 4))

        fatImageSliceMask = sitk.OtsuThreshold(fatImageSliceITK, 0, 1, 200)
        waterImageSliceMask = sitk.OtsuThreshold(waterImageSliceITK, 0, 1, 200)

        fatImageSliceITK = sitk.N4BiasFieldCorrection(fatImageSliceITK, fatImageSliceMask)
        waterImageSliceITK = sitk.N4BiasFieldCorrection(waterImageSliceITK, waterImageSliceMask)

        print('Done with slice %i' % (slice))

        # pypitk.imshow(fatImageSliceITK, cmap=pyplot.gray())
        # pyplot.title('Slice #%i' % (slice))
        # pyplot.pause(0.5)

        if constants.showBodyMask:
            # Show the matter slice and body mask to see how well it fits
            # Set title to slice number to record any odd slices and draw now so that it draws the title
            pyplot.imshow(fatImageSlice, cmap=pyplot.gray())
            pyplot.title('Slice #%i' % (slice))

            # TODO Get imshowpair to work in Python
            # imshowpair(waterImageSlice, bodyMask
            # {slice});

            # Sleep for 1 second to allow user to view the image
            pyplot.pause(1)

    return [1]