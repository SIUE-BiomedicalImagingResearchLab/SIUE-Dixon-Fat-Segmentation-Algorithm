import os
import time

import SimpleITK as sitk
import cv2
import matplotlib.pyplot as plt
import numpy as np

import constants
from biasCorrection import correctBias


# Get resulting path for debug files
def getDebugPath(str):
    return os.path.join(constants.pathDir, 'debug', str)


# Segment depots of adipose tissue given Dixon MRI images
def runSegmentation(niiFatUpper, niiFatLower, niiWaterUpper, niiWaterLower, config):
    # If debug is turned on, then create the directory where the debug files will be saved
    # The makedirs command is in try/catch because if it already exists, it will throw an exception and we just want
    # to continue in that case
    if constants.debug:
        try:
            os.makedirs(getDebugPath(''))
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
    fatUpperImage = niiFatUpper.get_data()[:, :, imageUpperInferiorSlice:imageUpperSuperiorSlice]
    fatLowerImage = niiFatLower.get_data()[:, :, imageLowerInferiorSlice:imageLowerSuperiorSlice]
    waterUpperImage = niiWaterUpper.get_data()[:, :, imageUpperInferiorSlice:imageUpperSuperiorSlice]
    waterLowerImage = niiWaterLower.get_data()[:, :, imageLowerInferiorSlice:imageLowerSuperiorSlice]

    # Concatenate the lower and upper image into one along the Z dimension
    # TODO Consider removing this and performing segmentation on upper/lower pieces separately
    fatImage = np.concatenate((fatLowerImage, fatUpperImage), axis=2)
    waterImage = np.concatenate((waterLowerImage, waterUpperImage), axis=2)

    # Normalize the fat/water images so that the intensities are between (0.0, 1.0)
    fatImage = (fatImage - fatImage.min()) / (fatImage.max() - fatImage.min())
    waterImage = (waterImage - waterImage.min()) / (waterImage.max() - waterImage.min())

    # Perform bias correction on MRI images to remove inhomogeneity
    tic = time.perf_counter()
    if os.path.exists(getDebugPath('fatImage.img')) and os.path.exists(getDebugPath('waterImage.img')):
        fatImage = np.load(getDebugPath('fatImage.npy'))
        waterImage = np.load(getDebugPath('waterImage.npy'))
    else:
        fatImage = correctBias(fatImage, shrinkFactor=constants.shrinkFactor,
                               prefix='fatImageBiasCorrection')
        waterImage = correctBias(waterImage, shrinkFactor=constants.shrinkFactor,
                                 prefix='waterImageBiasCorrection')
    toc = time.perf_counter()
    print('N4ITK bias field correction took %f seconds' % (toc - tic))

    # Print out the fat and water image after bias correction
    if constants.debug:
        np.save(getDebugPath('fatImage.npy'), fatImage)
        np.save(getDebugPath('waterImage.npy'), waterImage)

    # Create empty arrays that will contain slice-by-slice intermediate images when processing the images
    # These are used to print the entire 3D volume out for debugging afterwards
    blankImage = sitk.Image(fatImage.GetWidth(), fatImage.GetHeight(), sitk.sitkUInt8)
    blankImage.CopyInformation(fatImage[:, :, 0])
    fatImageMasks = [blankImage] * fatImage.GetDepth()
    waterImageMasks = [blankImage] * fatImage.GetDepth()
    bodyMasks = [blankImage] * fatImage.GetDepth()
    VATMasks = [blankImage] * fatImage.GetDepth()

    filledImages = [blankImage] * fatImage.GetDepth()

    # gradientMagImages = [sitk.Cast(blankImage, sitk.sitkFloat32)] * fatImage.GetDepth()
    # sigGradientMagImages = [sitk.Cast(blankImage, sitk.sitkFloat32)] * fatImage.GetDepth()
    # initialContours = [sitk.Cast(blankImage, sitk.sitkFloat32)] * fatImage.GetDepth()
    # finalContours = [sitk.Cast(blankImage, sitk.sitkFloat32)] * fatImage.GetDepth()

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

        # Consider after N4 Bias correction switching to NumPy and ski image for algorithms...

        # Get body mask by combining fat and water masks
        # Apply some closing to the image mask to connect any small gaps (such as at umbilical cord)
        # Fill all holes which will create a solid body mask
        # Remove small objects that are artifacts from segmentation
        bodyMask = fatImageMask | waterImageMask
        bodyMask = sitk.BinaryMorphologicalClosing(bodyMask, 3, sitk.sitkBall)
        bodyMask = sitk.BinaryFillhole(bodyMask)

        # TODO Determine why BinaryMinMaxCurvativeFlow requires real types for a binary image?
        bodyMasks[slice] = bodyMask

        # TODO Seriously, it may be better to have 0->255 for the min/max intension. 0->1 isn't the greatest

        # More testing here
        # Fill holes in the fat image mask and invert it to get the background
        # Fill in the background for fatImageMask and then invert intensity to make
        # the holes inside of the object become the new object
        # Remove small objects from holesImage by morphological opening
        # Connect all objects from the resulting image by morphological closing
        # Finally, fill holes in image to get the VAT mask
        backgroundImage = sitk.InvertIntensity(sitk.BinaryFillhole(fatImageMask), 1)
        holesImage = sitk.InvertIntensity(backgroundImage | fatImageMask, 1)
        holesImage2 = sitk.BinaryMorphologicalOpening(holesImage, 3, sitk.sitkBall)
        holesImage3 = sitk.RescaleIntensity(holesImage2, 0, 255)

        # holesImage3 = sitk.BinaryMorphologicalClosing(holesImage2, 15, sitk.sitkBall)
        # VATMask = sitk.BinaryFillhole(holesImage2)

        numpyAr = sitk.GetArrayViewFromImage(holesImage3)
        image, contours, hierarchy = cv2.findContours(numpyAr, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        combinedContours = np.vstack(contours)
        hullContour = cv2.convexHull(combinedContours)

        VATMask = np.zeros(numpyAr.shape, np.uint8)
        VATMask = cv2.drawContours(VATMask, [hullContour], 0, 255, -1)

        plt.imshow(VATMask)
        plt.show()

        # # Select contours 9->13, these can be seen in the figure below
        # # Draw the contours onto contourImage to show what contours were found
        # selectedContours = contours[9:13]
        # contourImage = cv2.drawContours(cv2.cvtColor(binaryImage, cv2.COLOR_GRAY2BGR), selectedContours, -1,
        #                                 (255, 0, 0), 3)

        # For calculating convex hull, we want to combine the selected contour list into one numpy array of vertices

        # Calculate the convex hull contour, which is a list of points for the convex hull

        #
        # # Draw the convex hull image on top of the contour image in green
        # hullContourImage = cv2.drawContours(contourImage, [hullContour], 0, (0, 255, 0), 3)

        # hull = cv2.convexHull(numpyAr.astype(int))
        # img = np.zeros(numpyAr.shape, dtype=np.uint8)
        # VATMask = cv2.fillConvexPoly(img, hull, 255)

        VATMasks[slice] = holesImage3
        # filledImages[slice] = filledImage

        # # Testing with Geodesic Active Contour
        # waterImageMask # FIll background and invert intensity
        # gradientMagImage = sitk.GradientMagnitude(waterImageMask)
        # sigGradientMagImage = sitk.Sigmoid(gradientMagImage, 1.0, 0.0, 255, 0)
        # initialContour = sitk.CannyEdgeDetection(sitk.Cast(bodyMask, sitk.sitkFloat32), 0.0, 0.0, [0.0] * 3, [0.01] * 3)
        # # initialContour = sitk.BinaryFillhole(initialContour)
        # # initialContour = sitk.BinaryThinning(initialContour)
        # finalContour = sitk.GeodesicActiveContourLevelSet(initialContour, sigGradientMagImage, 0.01, -1.0, 1.0, 1.0, 1000)
        #
        # gradientMagImages[slice] = gradientMagImage
        # sigGradientMagImages[slice] = sigGradientMagImage
        # initialContours[slice] = initialContour
        # finalContours[slice] = finalContour

        # # Method doesn't work the best...
        # VATMask = sitk.BinaryMorphologicalClosing(waterImageMask, 6, sitk.sitkBall)
        # VATMask = sitk.BinaryMorphologicalOpening(VATMask, 6, sitk.sitkBall)
        # VATMasks[slice] = VATMask

        toc = time.perf_counter()
        print('Completed slice %i in %f seconds' % (slice, toc - tic))

    if constants.debug:
        sitk.WriteImage(sitk.JoinSeries(fatImageMasks), os.path.join(constants.pathDir, 'debug', 'fatImageMask.img'))
        sitk.WriteImage(sitk.JoinSeries(waterImageMasks), os.path.join(constants.pathDir, 'debug',
                                                                       'waterImageMask.img'))
        sitk.WriteImage(sitk.JoinSeries(bodyMasks), os.path.join(constants.pathDir, 'debug',
                                                                 'bodyMask.img'))
        sitk.WriteImage(sitk.JoinSeries(VATMasks), os.path.join(constants.pathDir, 'debug',
                                                                'VATMask.img'))

        # sitk.WriteImage(sitk.JoinSeries(filledImages), os.path.join(constants.pathDir, 'debug',
        #                                                          'filledImage.img'))

        # sitk.WriteImage(sitk.JoinSeries(gradientMagImages), os.path.join(constants.pathDir, 'debug', 'gradientMagImage.img'))
        # sitk.WriteImage(sitk.JoinSeries(sigGradientMagImages), os.path.join(constants.pathDir, 'debug', 'sigGradientMagImage.img'))
        # sitk.WriteImage(sitk.JoinSeries(initialContours), os.path.join(constants.pathDir, 'debug', 'initialContour.img'))
        # sitk.WriteImage(sitk.JoinSeries(finalContours), os.path.join(constants.pathDir, 'debug', 'finalContour.img'))
