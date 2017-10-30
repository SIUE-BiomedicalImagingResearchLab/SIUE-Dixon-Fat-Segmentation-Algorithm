import os
import time
import sys

import SimpleITK as sitk
import matplotlib.pyplot as plt
import skimage.morphology
import scipy.ndimage.morphology
import skimage.segmentation
import skimage.draw
import skimage.measure

import constants
from biasCorrection import correctBias
from utils import *


# Get resulting path for debug files
def getDebugPath(str):
    return os.path.join(constants.pathDir, 'debug', str)


def segmentAbdomenSlice(fatImageMask, waterImageMask, bodyMask):
    # Fill holes in the fat image mask and invert it to get the background of fat image
    # OR the fat background mask and fat image mask and take NOT of mask to get the fat void mask
    fatBackgroundMask = np.logical_not(scipy.ndimage.morphology.binary_fill_holes(fatImageMask))
    fatVoidMask = np.logical_or(fatBackgroundMask, fatImageMask)
    fatVoidMask = np.logical_not(fatVoidMask)

    # Next, remove small objects based on their area
    # Size is the area threshold of objects to use. This number of pixels must be set in an object
    # for it to stay.
    # remove_small_objects is more desirable than using a simple binary_opening operation in this
    # case because binary_opening with a 5x5 disk SE was removing long, skinny objects that were not
    # wide enough to pass the test. However, their area is larger than smaller objects that I need to
    # remove. So remove_small_objects is better since it utilizes area.
    fatVoidMask = skimage.morphology.remove_small_objects(fatVoidMask, 30)

    # Use active contours to get the abdominal mask
    # Originally, I attempted this using the convex hull but I was not a huge fan of the results
    # since there were instances where the outline was concave and not convex
    # For active contours, we need an initial contour. We will start with an outline of the body mask
    # Find contours of body mask
    image, contours, hierarchy = cv2.findContours(bodyMask.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Sort the contours by area and select the one with largest area, this will be the body mask contour
    sortedContourArea = np.array([cv2.contourArea(contour) for contour in contours])
    index = np.argmax(sortedContourArea)
    initialContour = contours[index]
    initialContour = initialContour.reshape(initialContour.shape[::2])

    # Perform active contour snake algorithm to get outline of the abdominal mask
    snakeContour = skimage.segmentation.active_contour(fatVoidMask.astype(np.uint8) * 255, initialContour, alpha=0.70,
                                                       beta=0.01, gamma=0.1, max_iterations=2500, max_px_move=1.0,
                                                       w_line=0.0, w_edge=5.0, convergence=0.1)

    # Draw snake contour on abdominalMask variable
    # Two options, polygon fills in the area and polygon_perimeter only draws the perimeter
    # Perimeter is good for testing while polygon is the general use one
    abdominalMask = np.zeros(fatVoidMask.shape, np.uint8)
    rr, cc = skimage.draw.polygon(snakeContour[:, 0], snakeContour[:, 1])
    # rr, cc = skimage.draw.polygon_perimeter(snakeContour[:, 0], snakeContour[:, 1])
    abdominalMask[cc, rr] = 1

    # SCAT is all fat outside the abdominal mask
    # VAT is all fat inside the abdominal mask
    SCAT = np.logical_and(np.logical_not(abdominalMask), fatImageMask)
    VAT = np.logical_and(abdominalMask, fatImageMask)

    return fatVoidMask, abdominalMask, SCAT, VAT


def segmentThoracicSlice(fatImageMask, waterImageMask, bodyMask):
    # Lungs are defined as being within body and not containing any fat or water content
    # lungMask = bodyMask & ~fatImageMask & ~waterImageMask
    # Next, remove any small objects from the binary image since the lungs will be large
    # Fill any small holes within the lungs to get the full lungs
    lungMask = np.logical_and(np.logical_and(bodyMask, np.logical_not(fatImageMask)), np.logical_not(waterImageMask))
    lungMask = skimage.morphology.binary_opening(lungMask, skimage.morphology.disk(10))
    lungMask = scipy.ndimage.morphology.binary_fill_holes(lungMask)

    # Use active contours to get the thoracic mask
    # For active contours, we need an initial contour. We will start with an outline of the body mask
    # Find contours of body mask
    image, contours, hierarchy = cv2.findContours(bodyMask.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Sort the contours by area and select the one with largest area, this will be the body mask contour
    sortedContourArea = np.array([cv2.contourArea(contour) for contour in contours])
    index = np.argmax(sortedContourArea)
    initialContour = contours[index]
    initialContour = initialContour.reshape(initialContour.shape[::2])

    # Perform active contour snake algorithm to get outline of the abdominal mask
    snakeContour = skimage.segmentation.active_contour(lungMask.astype(np.uint8) * 255, initialContour, alpha=0.70,
                                                       beta=5.0, gamma=0.1, max_iterations=2500, max_px_move=1.0,
                                                       w_line=0.0, w_edge=1.0, convergence=0.1)

    # Draw snake contour on abdominalMask variable
    # Two options, polygon fills in the area and polygon_perimeter only draws the perimeter
    # Perimeter is good for testing while polygon is the general use one
    thoracicMask = np.zeros(lungMask.shape, np.uint8)
    # rr, cc = skimage.draw.polygon(snakeContour[:, 0], snakeContour[:, 1])
    rr, cc = skimage.draw.polygon_perimeter(snakeContour[:, 0], snakeContour[:, 1])
    thoracicMask[cc, rr] = 1

    # Segmenting based on the lungs doesnt give the best results because part of the epicardial fat is cut off
    # Also I don't know how I would do periaortic fat. I also don't know what is considered epicardial fat

    return lungMask, thoracicMask


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
    diaphragmSuperiorSlice = int(configRoot.find('diaphragm').attrib['superiorSlice'])
    umbilicisTag = configRoot.find('umbilicis')
    umbilicisInferiorSlice = int(umbilicisTag.attrib['inferiorSlice'])
    umbilicisSuperiorSlice = int(umbilicisTag.attrib['superiorSlice'])
    umbilicisLeft = int(umbilicisTag.attrib['left'])
    umbilicisRight = int(umbilicisTag.attrib['right'])
    umbilicisCoronal = int(umbilicisTag.attrib['coronal'])

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
    if os.path.exists(getDebugPath('fatImage.npy')) and os.path.exists(getDebugPath('waterImage.npy')):
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
    SCAT = np.zeros(fatImage.shape, bool)
    VAT = np.zeros(fatImage.shape, bool)

    fatImageMasks = np.zeros(fatImage.shape, bool)
    waterImageMasks = np.zeros(fatImage.shape, bool)
    bodyMasks = np.zeros(fatImage.shape, bool)
    fatVoidMasks = np.zeros(fatImage.shape, bool)
    abdominalMasks = np.zeros(fatImage.shape, bool)

    lungMasks = np.zeros(fatImage.shape, bool)
    thoracicMasks = np.zeros(fatImage.shape, bool)

    for slice in range(0, diaphragmSuperiorSlice):#, fatImage.shape[2]):  # 0, diaphragmSuperiorSlice): # fatImage.shape[2]):
        tic = time.perf_counter()

        fatImageSlice = fatImage[:, :, slice]
        waterImageSlice = waterImage[:, :, slice]

        # Segment fat/water images using K-means
        # labelOrder contains the labels sorted from smallest intensity to greatest
        # Since our k = 2, we want the higher intensity label at index 1
        labelOrder, centroids, fatImageLabels = kmeans(fatImageSlice, constants.kMeanClusters)
        fatImageMask = (fatImageLabels == labelOrder[1])
        labelOrder, centroids, waterImageLabels = kmeans(waterImageSlice, constants.kMeanClusters)
        waterImageMask = (waterImageLabels == labelOrder[1])

        # Algorithm assumes that the skin is a closed contour and fully connects
        # This is a valid assumption but near the umbilicis, there is a discontinuity
        # so this draws a line near there to create a closed contour
        if umbilicisInferiorSlice <= slice <= umbilicisSuperiorSlice:
            fatImageMask[umbilicisLeft:umbilicisRight, umbilicisCoronal] = True

        fatImageMasks[:, :, slice] = fatImageMask
        waterImageMasks[:, :, slice] = waterImageMask

        # Get body mask by combining fat and water masks
        # Apply some closing to the image mask to connect any small gaps (such as at umbilical cord)
        # Fill all holes which will create a solid body mask
        # Remove small objects that are artifacts from segmentation
        bodyMask = np.logical_or(fatImageMask, waterImageMask)
        bodyMask = skimage.morphology.binary_closing(bodyMask, skimage.morphology.disk(3))
        bodyMask = scipy.ndimage.morphology.binary_fill_holes(bodyMask)
        bodyMasks[:, :, slice] = bodyMask

        # Superior of diaphragm is divider between thoracic and abdominal region
        if slice < diaphragmSuperiorSlice:
            fatVoidMask, abdominalMask, SCATSlice, VATSlice = segmentAbdomenSlice(fatImageMask, waterImageMask,
                                                                                  bodyMask)
            fatVoidMasks[:, :, slice] = fatVoidMask
            abdominalMasks[:, :, slice] = abdominalMask
            SCAT[:, :, slice] = SCATSlice
            VAT[:, :, slice] = VATSlice
        else:
            lungMask, thoracicMask = segmentThoracicSlice(fatImageMask, waterImageMask, bodyMask)

            lungMasks[:, :, slice] = lungMask
            thoracicMasks[:, :, slice] = thoracicMask

        toc = time.perf_counter()
        print('Completed slice %i in %f seconds' % (slice, toc - tic))

    if constants.debug:
        np.save(getDebugPath('fatImageMask.npy'), fatImageMasks)
        np.save(getDebugPath('waterImageMask.npy'), waterImageMasks)
        np.save(getDebugPath('bodyMask.npy'), bodyMasks)

        np.save(getDebugPath('fatVoidMask.npy'), fatVoidMasks)
        np.save(getDebugPath('abdominalMask.npy'), abdominalMasks)
        np.save(getDebugPath('SCAT.npy'), SCAT)
        np.save(getDebugPath('VAT.npy'), VAT)

        np.save(getDebugPath('lungMask.npy'), lungMasks)
        np.save(getDebugPath('thoracicMask.npy'), thoracicMasks)
