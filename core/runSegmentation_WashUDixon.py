import os
import time

import cv2
import nrrd
import scipy.io
import scipy.ndimage.morphology
import skimage.draw
import skimage.measure
import skimage.morphology
import skimage.segmentation

from core.biasCorrection import correctBias
from util import constants
from util import draw
from util.util import *


# Get resulting path for debug files
def getDebugPath(path):
    return os.path.join(constants.pathDir, 'debug', path)


# Get resulting path for files
def getPath(path):
    return os.path.join(constants.pathDir, path)


# noinspection PyUnusedLocal
def segmentAbdomenSlice(slice, fatImageMask, waterImageMask, bodyMask):
    # Fill holes in the fat image mask and invert it to get the background of fat image
    # OR the fat background mask and fat image mask and take NOT of mask to get the fat void mask
    fatBackgroundMask = ~scipy.ndimage.morphology.binary_fill_holes(fatImageMask)
    fatVoidMask = ~(fatBackgroundMask | fatImageMask)

    # This hack is to prevent the large voids in the mammary glands from causing the abdominal mask being wrong
    # TODO This hack should be implemented into the YAML file and should be configurable via PATS
    # ------------------------------------------------ BEGIN HACK ------------------------------------------------------
    # List of polygons to draw on the fat void mask in order to correct issues
    fatVoidCorrections = []

    if constants.subjectName == 'MF0322-PRE':
        fatVoidCorrections = [
            # ([Inferior Slice, Superior Slice], List of polygons)
            ([66, 77], [
                [[228, 74], [171, 44], [174, 59], [219, 89]],
                [[105, 40], [50, 67], [58, 82], [106, 55]]
            ])
        ]
    elif constants.subjectName == 'MF0323-PRE':
        fatVoidCorrections = [
            # ([Inferior Slice, Superior Slice], List of polygons)
            ([67, 79], [
                [[244, 70], [160, 20], [153, 49], [208, 99]],
                [[95, 26], [12, 75], [49, 112], [106, 46]]
            ]),
            ([46, 66], [
                [[242, 79], [160, 14], [143, 34], [220, 110]],
                [[86, 18], [7, 90], [42, 113], [114, 38]]
            ])
        ]
    elif constants.subjectName == 'MF0324-PRE':
        fatVoidCorrections = [
            # ([Inferior Slice, Superior Slice], List of polygons)
            ([60, 79], [
                [[253, 49], [169, 19], [154, 40], [236, 96]],
                [[90, 10], [7, 62], [32, 95], [111, 41]]
            ])
        ]
    elif constants.subjectName == 'MF0325-PRE':
        fatVoidCorrections = [
            # ([Inferior Slice, Superior Slice], List of polygons)
            ([63, 79], [
                [[248, 65], [189, 29], [172, 52], [229, 100]],
                [[75, 41], [19, 76], [47, 100], [96, 55]]
            ])
        ]

    for correction in fatVoidCorrections:
        if slice >= correction[0][0] and slice <= correction[0][1]:
            # Draw the polygons and turn into a binary image where True is within the polygons and False is outside of
            binaryImageMask = draw.binaryFilledPolygon(correction[1], fatVoidMask.shape)
            fatVoidMask = fatVoidMask & ~binaryImageMask
            break
    # ---------------------------------------------- END HACK HERE -----------------------------------------------------

    # Next, remove small objects based on their area
    # Size is the area threshold of objects to use. This number of pixels must be set in an object for it to stay.
    # remove_small_objects is more desirable than using a simple binary_opening operation in this case because
    # binary_opening with a 5x5 disk SE was removing long, skinny objects that were not wide enough to pass the test.
    # However, their area is larger than smaller objects that I need to remove. So remove_small_objects is better since
    # it utilizes area. Odd issue where a warning will appear saying that a boolean image should be given. This is a
    # bug in skimage because I traced it down and the label function is returning odd values
    fatVoidMask = skimage.morphology.remove_small_objects(fatVoidMask, constants.thresholdAbdominalFatVoidsArea)

    # Use active contours to get the abdominal mask
    # Originally, I attempted this using the convex hull but I was not a huge fan of the results since there were
    # instances where the outline was concave and not convex
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
                                                       w_line=0.0, w_edge=1.0, convergence=0.1)

    # Draw snake contour on abdominalMask variable
    # Two options, polygon fills in the area and polygon_perimeter only draws the perimeter
    # Perimeter is good for testing while polygon is the general use one
    abdominalMask = np.zeros(fatVoidMask.shape, np.uint8)
    rr, cc = skimage.draw.polygon(snakeContour[:, 0], snakeContour[:, 1])
    # rr, cc = skimage.draw.polygon_perimeter(snakeContour[:, 0], snakeContour[:, 1])
    abdominalMask[cc, rr] = 1
    abdominalMask = abdominalMask.astype(bool)

    # SCAT is all fat outside the abdominal mask
    # VAT is all fat inside the abdominal mask
    SCAT = ~abdominalMask & fatImageMask & bodyMask
    VAT = abdominalMask & fatImageMask

    # Remove objects from SCAT where the area is less than given constant
    SCAT = skimage.morphology.remove_small_objects(SCAT, constants.minSCATObjectArea)

    # Remove objects from VAT where the area is less than given constant
    VAT = skimage.morphology.remove_small_objects(VAT, constants.minVATObjectArea)

    return fatVoidMask, abdominalMask, SCAT, VAT


def runSegmentation(data):
    # Get the data from the data tuple
    fatImage, waterImage, config = data

    # Start time of the run segmentation
    timeStarted = time.perf_counter()

    # Create debug directory regardless of whether debug constant is true
    # The bias corrected fat and water images are going to be created in this directory regardless of debug constant
    os.makedirs(getDebugPath(''), exist_ok=True)

    # Load values from config dictionary
    diaphragmAxialSlice = config['diaphragmAxial']
    umbilicis = config['umbilicis']
    umbilicisInferior = umbilicis['inferior']
    umbilicisSuperior = umbilicis['superior']
    umbilicisLeft = umbilicis['left']
    umbilicisRight = umbilicis['right']
    umbilicisCoronal = umbilicis['coronal']

    # Retrieve arm bounds from configuration file
    leftArm = config['armBounds']['leftArm']
    rightArm = config['armBounds']['rightArm']

    leftArmBounds = [(x['firstPoint'][0], x['firstPoint'][1], x['secondPoint'][0], x['secondPoint'][1],
                      x['axialPosition']) for x in leftArm]
    rightArmBounds = [(x['firstPoint'][0], x['firstPoint'][1], x['secondPoint'][0], x['secondPoint'][1],
                       x['axialPosition']) for x in rightArm]

    # Perform bias correction on MRI images to remove inhomogeneity
    # If bias correction has been performed already, then load the saved data
    tic = time.perf_counter()
    if not constants.forceBiasCorrection and os.path.exists(getDebugPath('fatImageBC.nrrd')) and os.path.exists(
            getDebugPath('waterImageBC.nrrd')):
        fatImage, header = nrrd.read(getDebugPath('fatImageBC.nrrd'))
        waterImage, header = nrrd.read(getDebugPath('waterImageBC.nrrd'))

        # Transpose image to get back into C-order indexing
        fatImage, waterImage = fatImage.T, waterImage.T
    else:
        fatImage = correctBias(fatImage, shrinkFactor=constants.shrinkFactor, prefix='fatImageBiasCorrection')
        waterImage = correctBias(waterImage, shrinkFactor=constants.shrinkFactor, prefix='waterImageBiasCorrection')

        # If bias correction is performed, saved images to speed up algorithm in future runs
        nrrd.write(getDebugPath('fatImageBC.nrrd'), fatImage.T, constants.nrrdHeaderDict, compression_level=1)
        nrrd.write(getDebugPath('waterImageBC.nrrd'), waterImage.T, constants.nrrdHeaderDict, compression_level=1)

    toc = time.perf_counter()
    print('N4ITK bias field correction took %f seconds' % (toc - tic))

    # Create empty arrays that will contain slice-by-slice intermediate images when processing the images
    # These are used to print the entire 3D volume out for debugging afterwards
    fatImageMasks = np.zeros(fatImage.shape, bool)
    waterImageMasks = np.zeros(fatImage.shape, bool)
    bodyMasks = np.zeros(fatImage.shape, bool)
    fatVoidMasks = np.zeros(fatImage.shape, bool)
    abdominalMasks = np.zeros(fatImage.shape, bool)

    # Final 3D volume results
    SCAT = np.zeros(fatImage.shape, bool)
    VAT = np.zeros(fatImage.shape, bool)

    # Loop from starting slice to the diaphragm slice
    # The diaphragm is what differentiates abdominal region from thoracic region and we just want the abdominal
    # statistics for WashU data because we have cardiac MRI scans for cardiac adipose tissue
    for slice in range(diaphragmAxialSlice):
        tic = time.perf_counter()

        fatImageSlice = fatImage[slice, :, :]
        waterImageSlice = waterImage[slice, :, :]

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
        if umbilicisInferior <= slice <= umbilicisSuperior:
            fatImageMask[umbilicisCoronal, umbilicisLeft:umbilicisRight] = True

        # Save fat and water masks for debugging
        fatImageMasks[slice, :, :] = fatImageMask
        waterImageMasks[slice, :, :] = waterImageMask

        # Get body mask by combining fat and water masks
        # Apply some closing to the image mask to connect any small gaps (such as at umbilical cord)
        # Fill all holes which will create a solid body mask
        # Remove small objects that are artifacts from segmentation
        bodyMask = fatImageMask | waterImageMask
        bodyMask = skimage.morphology.binary_closing(bodyMask, skimage.morphology.disk(3))
        bodyMask = scipy.ndimage.morphology.binary_fill_holes(bodyMask)

        # Apply left and right arm bounds by drawing a line through the body mask where the arm bounds are
        # This will cut the arms away from the body mask and then the largest object will be selected
        # Only draw line on body mask if the slice is between the first and last arm bound axial slices specified
        if len(leftArmBounds) > 0 and (leftArmBounds[0][-1] <= slice <= leftArmBounds[-1][-1]):
            # Get a list of slice numbers for the left arm bounds
            xp = np.array([i[4] for i in leftArmBounds])

            # Get list of x/y coordinates at the slice numbers
            x1p, y1p = np.array([i[0] for i in leftArmBounds]), np.array([i[1] for i in leftArmBounds])
            x2p, y2p = np.array([i[2] for i in leftArmBounds]), np.array([i[3] for i in leftArmBounds])

            # Interpolate for given slice between the bounds, round and convert to an integer
            x1, y1 = int(np.round(np.interp(slice, xp, x1p))), int(np.round(np.interp(slice, xp, y1p)))
            x2, y2 = int(np.round(np.interp(slice, xp, x2p))), int(np.round(np.interp(slice, xp, y2p)))

            # Get a binary image where True values are a line from first to second point of arm bounds with a thickness
            # of 2
            # Draw that line on the body mask by setting body mask False where the line is
            binaryLineImage = draw.binaryLine((x1, y1), (x2, y2), bodyMask.shape, thickness=2)
            bodyMask = bodyMask & ~binaryLineImage

        if len(rightArmBounds) > 0 and (rightArmBounds[0][-1] <= slice <= rightArmBounds[-1][-1]):
            # Get a list of slice numbers for the left arm bounds
            xp = np.array([i[4] for i in rightArmBounds])

            # Get list of x/y coordinates at the slice numbers
            x1p, y1p = np.array([i[0] for i in rightArmBounds]), np.array([i[1] for i in rightArmBounds])
            x2p, y2p = np.array([i[2] for i in rightArmBounds]), np.array([i[3] for i in rightArmBounds])

            # Interpolate for given slice between the bounds, round and convert to an integer
            x1, y1 = int(np.round(np.interp(slice, xp, x1p))), int(np.round(np.interp(slice, xp, y1p)))
            x2, y2 = int(np.round(np.interp(slice, xp, x2p))), int(np.round(np.interp(slice, xp, y2p)))

            # Get a binary image where True values are a line from first to second point of arm bounds with a thickness
            # of 2
            # Draw that line on the body mask by setting body mask False where the line is
            binaryLineImage = draw.binaryLine((x1, y1), (x2, y2), bodyMask.shape, thickness=2)
            bodyMask = bodyMask & ~binaryLineImage

        # Label the objects of the body mask. There should only be one body object and other other objects are either
        # the arms or some unwanted object
        # Calculate the region properties of each object
        bodyMaskLabels = skimage.morphology.label(bodyMask)
        bodyMaskProps = skimage.measure.regionprops(bodyMaskLabels, cache=True)

        # Sort by area from largest to smallest. Assumption is that body object will have largest amount of area
        sortedBodyMaskProps = sorted(bodyMaskProps, key=lambda prop: prop.area, reverse=True)

        # Remove any smaller objects and only keep the largest area object
        bodyMask = (bodyMaskLabels == sortedBodyMaskProps[0].label)
        bodyMasks[slice, :, :] = bodyMask

        fatVoidMask, abdominalMask, SCATSlice, VATSlice = segmentAbdomenSlice(slice, fatImageMask, waterImageMask,
                                                                              bodyMask)

        # Save some data for debugging
        fatVoidMasks[slice, :, :] = fatVoidMask
        abdominalMasks[slice, :, :] = abdominalMask
        SCAT[slice, :, :] = SCATSlice
        VAT[slice, :, :] = VATSlice

        toc = time.perf_counter()
        print('Completed slice %i in %f seconds' % (slice, toc - tic))

    # Write out debug variables
    # Note: All Numpy arrays are transposed before being written to NRRD file because the Numpy arrays are in C-order
    # whereas the NRRD specification says that the arrays should be in Fortran-order.
    # C-order means that you index the array as (z, y, x) where the first index is the slowest varying and the last
    # index is fastest varying. Fortran-order, on the other hand is the direct opposite, where you index it as
    # (x, y, z) with the first axis being the fastest varying and the last axis being the slowest varying.
    # There are different benefits to each method and it's primarily a standard that programming languages pick. MATLAB
    # & Fortran use Fortarn-ordered, while C and Python and other languages use C-order. C-order is used now because it
    # is what is primarily used by many Python libraries, including Numpy.
    if constants.debug:
        nrrd.write(getDebugPath('fatImageMask.nrrd'), skimage.img_as_ubyte(fatImageMasks).T, constants.nrrdHeaderDict,
                   compression_level=1)
        nrrd.write(getDebugPath('waterImageMask.nrrd'), skimage.img_as_ubyte(waterImageMasks).T,
                   constants.nrrdHeaderDict,
                   compression_level=1)
        nrrd.write(getDebugPath('bodyMask.nrrd'), skimage.img_as_ubyte(bodyMasks).T, constants.nrrdHeaderDict,
                   compression_level=1)

        nrrd.write(getDebugPath('fatVoidMask.nrrd'), skimage.img_as_ubyte(fatVoidMasks).T, constants.nrrdHeaderDict,
                   compression_level=1)
        nrrd.write(getDebugPath('abdominalMask.nrrd'), skimage.img_as_ubyte(abdominalMasks).T, constants.nrrdHeaderDict,
                   compression_level=1)

    # Save the results of adipose tissue segmentation and the original fat/water images
    nrrd.write(getPath('fatImage.nrrd'), skimage.img_as_ubyte(fatImage).T, constants.nrrdHeaderDict,
               compression_level=1)
    nrrd.write(getPath('waterImage.nrrd'), skimage.img_as_ubyte(waterImage).T, constants.nrrdHeaderDict,
               compression_level=1)
    nrrd.write(getPath('SCAT.nrrd'), skimage.img_as_ubyte(SCAT).T, constants.nrrdHeaderDict, compression_level=1)
    nrrd.write(getPath('VAT.nrrd'), skimage.img_as_ubyte(VAT).T, constants.nrrdHeaderDict, compression_level=1)

    # If desired, save the results in MATLAB
    if constants.saveMat:
        scipy.io.savemat(getPath('results.mat'), mdict={'SCAT': SCAT.T, 'VAT': VAT.T})

    # Finish time of the segmentation algorithm
    timeEnded = time.perf_counter()
    print('Total time taken for segmentation: %f seconds' % (timeEnded - timeStarted))
