import os
import time

import scipy.ndimage.morphology
import scipy.io
import skimage.draw
import skimage.measure
import skimage.morphology
import skimage.segmentation
import nrrd
import matplotlib.pyplot as plt

import constants
from biasCorrection import correctBias
from utils import *


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
    # Odd issue where a warning will appear saying that a boolean image should be given. This is a bug in skimage
    # because I traced it down and the label function is returning odd values
    fatVoidMask = skimage.morphology.remove_small_objects(fatVoidMask, constants.thresholdAbdominalFatVoidsArea)

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

    # Remove objects from SCAT where the area is less than given constant
    SCAT = skimage.morphology.remove_small_objects(SCAT, constants.minSCATObjectArea)

    # Remove objects from VAT where the area is less than given constant
    VAT = skimage.morphology.remove_small_objects(VAT, constants.minVATObjectArea)

    return fatVoidMask, abdominalMask, SCAT, VAT


def segmentThoracicSlice(slice, fatImageMask, waterImageMask, bodyMask, CATAxial, CATPosterior, CATAnterior,
                         CATInferior, CATSuperior):
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
    # Odd issue where a warning will appear saying that a boolean image should be given. This is a bug in skimage
    # because I traced it down and the label function is returning odd values
    fatVoidMask = skimage.morphology.remove_small_objects(fatVoidMask, constants.thresholdThoracicFatVoidsArea)

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
    thoracicMask = np.zeros(fatVoidMask.shape, np.uint8)
    rr, cc = skimage.draw.polygon(snakeContour[:, 0], snakeContour[:, 1])
    # rr, cc = skimage.draw.polygon_perimeter(snakeContour[:, 0], snakeContour[:, 1])
    thoracicMask[cc, rr] = 1

    # Lungs are defined as being within body and not containing any fat or water content
    # lungMask = bodyMask & ~fatImageMask & ~waterImageMask
    # Next, remove any small objects from the binary image since the lungs will be large
    # Fill any small holes within the lungs to get the full lungs
    lungMask = np.logical_and(np.logical_and(bodyMask, np.logical_not(fatImageMask)), np.logical_not(waterImageMask))
    lungMask = skimage.morphology.binary_opening(lungMask, skimage.morphology.disk(10))
    lungMask = scipy.ndimage.morphology.binary_fill_holes(lungMask)
    # lungMask = skimage.morphology.binary_opening(lungMask, skimage.morphology.disk(8))

    # SCAT is all fat outside the thoracic mask
    # ITAT is all fat inside the thoracic mask
    SCAT = np.logical_and(np.logical_not(thoracicMask), fatImageMask)
    ITAT = np.logical_and(thoracicMask, fatImageMask)
    CAT = np.zeros_like(ITAT, dtype=bool)

    # Remove objects from SCAT where the area is less than given constant
    SCAT = skimage.morphology.remove_small_objects(SCAT, constants.minSCATObjectArea)

    if CATInferior <= slice <= CATSuperior:
        posterior = int(np.round(np.interp(slice, CATAxial, CATPosterior)))
        anterior = int(np.round(np.interp(slice, CATAxial, CATAnterior)))

        # Label the objects of lung mask. There should only be two objects, the left and right lung
        # Get centroid of each object. Left lung is on left side, so centroid should be below half of total coronal
        # plane size
        lungMaskLabels = skimage.morphology.label(lungMask)
        lungProps = skimage.measure.regionprops(lungMaskLabels, cache=True)

        # Sort lung objects based on area descending, first two largest objects are the left/right lung
        sortedAreaIndices = sorted(range(len(lungProps)), key=lambda x: lungProps[x].area, reverse=True)

        # Next, sort the two lungs based on their sagittal centroid coordinate
        # Smaller sagittal centroid coordinate is the left lung, other is right lung
        # Label ID is the regionprop index + 1
        sortedCentroidIndices = sorted(sortedAreaIndices[0:2], key=lambda x: lungProps[x].centroid[0])
        leftLung = (lungMaskLabels == sortedCentroidIndices[0] + 1)
        rightLung = (lungMaskLabels == sortedCentroidIndices[1] + 1)

        # For the left and right lung, retrieve the outer contour index on a row-by-row basis.
        # Left lung will be lower index and right-lung will be upper index for ROI of CAT
        leftIndices = maxargwhere(leftLung, axis=0)
        rightIndices = minargwhere(rightLung, axis=0)

        # Only extract the relevant indices from posterior to anterior slices
        # Any -1 values indicate there was no lung mask located there, so set it to the minimum index value
        leftIndices = leftIndices[posterior:anterior]
        rightIndices = rightIndices[posterior:anterior]

        leftIndices[leftIndices == -1] = defaultmin(leftIndices[leftIndices != -1], 0)
        rightIndices[rightIndices == -1] = rightIndices.max()

        # Create CATMask which is a mask of where fat can be located around the heart
        # From coronal plane, the upper and lower bounds are determined from user entered points
        # From sagittal plane, this is calculated based on the lungs going around the heart
        CATMask = np.zeros_like(ITAT, dtype=bool)
        for heartSlice, leftIndex, rightIndex in zip(range(posterior, anterior), leftIndices, rightIndices):
            CATMask[leftIndex:rightIndex, heartSlice] = True

        # CAT is defined as ITAT inside the CATMask
        CAT[CATMask] = ITAT[CATMask]

        # Remove objects from CAT where the area is less than given constant
        CAT = skimage.morphology.remove_small_objects(CAT, constants.minCATObjectArea)

    return fatVoidMask, thoracicMask, lungMask, SCAT, ITAT, CAT


# Segment depots of adipose tissue given Dixon MRI images
def runSegmentation(image, config):
    # Create debug directory regardless of whether debug constant is true
    # The bias corrected fat and water images are going to be created in this directory regardless of debug constant
    # The makedirs command is in try/catch because if it already exists, it will throw an exception and we just want
    # to continue in that case
    try:
        os.makedirs(getDebugPath(''))
    except FileExistsError:
        pass

    # # Get the root of the config XML file
    configRoot = config.getroot()
    #
    diaphragmSuperiorSlice = int(configRoot.find('diaphragm').attrib['superiorSlice'])
    umbilicisTag = configRoot.find('umbilicis')
    umbilicisInferiorSlice = int(umbilicisTag.attrib['inferiorSlice'])
    umbilicisSuperiorSlice = int(umbilicisTag.attrib['superiorSlice'])
    umbilicisLeft = int(umbilicisTag.attrib['left'])
    umbilicisRight = int(umbilicisTag.attrib['right'])
    umbilicisCoronal = int(umbilicisTag.attrib['coronal'])

    print(diaphragmSuperiorSlice)
    print(umbilicisInferiorSlice)
    print(umbilicisSuperiorSlice)
    print(umbilicisLeft)
    print(umbilicisRight)
    print(umbilicisCoronal)

    #
    # # Load cardiac adipose tissue (CAT) tag and corresponding lines in axial plane
    # CATTag = configRoot.find('CAT')
    # CATAxial = []
    # CATPosterior = []
    # CATAnterior = []
    # # Foreach line in the CAT tag, append to the three arrays
    # for line in CATTag:
    #     if line.tag != 'line':
    #         print('Invalid tag for CAT, must be line')
    #         continue
    #
    #     CATAxial.append(int(line.attrib['axial']))
    #     CATPosterior.append(int(line.attrib['posterior']))
    #     CATAnterior.append(int(line.attrib['anterior']))
    #
    #
    # # # Convert three arrays to NumPy and get minimum/maximum axial slice
    # # # The min/max axial slice is used to determine the start and stopping point
    # # # of calculating CAT
    # CATAxial = np.array(CATAxial)
    # CATPosterior = np.array(CATPosterior)
    # CATAnterior = np.array(CATAnterior)
    # CATInferior = CATAxial.min()
    # CATSuperior = CATAxial.max()
    # #
    # # # Sort the three arrays based on CAT axial, ascending
    # CATAxialSortedInds = CATAxial.argsort()
    # CATAxial = CATAxial[CATAxialSortedInds]
    # CATPosterior = CATPosterior[CATAxialSortedInds]
    # CATAnterior = CATAnterior[CATAxialSortedInds]
    #
    # Perform bias correction on MRI images to remove inhomogeneity
    # tic = time.perf_counter()
    # if os.path.exists(getDebugPath('MRI_Data_Nrrd_Output/t1_fl2d_tra_p3_256_BC.nrrd')):
    #     fatAndWaterImage, header = nrrd.read(getDebugPath('MRI_Data_Nrrd_Output/t1_fl2d_tra_p3_256.nrrd'))
    # else:
    #     fatAndWaterImage = correctBias(fatAndWaterImage, shrinkFactor=constants.shrinkFactor,
    #                            prefix='fatImageBiasCorrection')
    #
    #     # If bias correction is performed, saved images to speed up algorithm in future runs
    #     nrrd.write(getDebugPath('MRI_Data_Nrrd_Output/t1_fl2d_tra_p3_256_BC.nrrd'), fatAndWaterImage, constants.nrrdHeaderDict)
    #
    # toc = time.perf_counter()
    # print('N4ITK bias field correction took %f seconds' % (toc - tic))
    #
    # Create empty arrays that will contain slice-by-slice intermediate images when processing the images
    # These are used to print the entire 3D volume out for debugging afterwards
    fatImage, header = nrrd.read(getDebugPath("C:/Users/Clint/PycharmProjects/SIUE-Dixon-Fat-Segmentation-Algorithm/MRI_Data_Nrrd_Output/newOut.nrrd"))
    fatImageMasks = np.zeros(fatImage.shape, bool)

    # Final 3D volume results
    SCAT = np.zeros(fatImage.shape, bool)
    VAT = np.zeros(fatImage.shape, bool)
    ITAT = np.zeros(fatImage.shape, bool)
    CAT = np.zeros(fatImage.shape, bool)
    #
    for slice in range(0, image.shape[2]):  # 0, diaphragmSuperiorSlice): # fatImage.shape[2]):
        tic = time.perf_counter()

        imageSlice = image[:, :, slice]
        # waterImageSlice = waterImage[:, :, slice]

        # Segment fat/water images using K-means
        # labelOrder contains the labels sorted from smallest intensity to greatest
        # Since our k = 2, we want the higher intensity label at index 1
        labelOrder, centroids, imageLabels = kmeans(imageSlice, 2)
        fatImageMask = (imageLabels == labelOrder[1])
        #plt.figure()
        #plt.imshow(imageLabels*127, cmap="gray")
        #plt.show()



        # # Algorithm assumes that the skin is a closed contour and fully connects
        # # This is a valid assumption but near the umbilicis, there is a discontinuity
        # # so this draws a line near there to create a closed contour
        if umbilicisInferiorSlice <= slice <= umbilicisSuperiorSlice:
            fatImageMask[umbilicisLeft:umbilicisRight, umbilicisCoronal] = True
        #
        fatImageMasks[:, :, slice] = fatImageMask
        # waterImageMasks[:, :, slice] = waterImageMask
        #
        # # Get body mask by combining fat and water masks
        # # Apply some closing to the image mask to connect any small gaps (such as at umbilical cord)
        # # Fill all holes which will create a solid body mask
        # # Remove small objects that are artifacts from segmentation
        # bodyMask = np.logical_or(fatImageMask, waterImageMask)
        # bodyMask = skimage.morphology.binary_closing(bodyMask, skimage.morphology.disk(3))
        # bodyMask = scipy.ndimage.morphology.binary_fill_holes(bodyMask)
        # bodyMasks[:, :, slice] = bodyMask
    #
    #     # Superior of diaphragm is divider between thoracic and abdominal region
    #     if slice < diaphragmSuperiorSlice:
    #         fatVoidMask, abdominalMask, SCATSlice, VATSlice = \
    #             segmentAbdomenSlice(slice, fatImageMask, waterImageMask, bodyMask)
    #
    #         fatVoidMasks[:, :, slice] = fatVoidMask
    #         abdominalMasks[:, :, slice] = abdominalMask
    #         SCAT[:, :, slice] = SCATSlice
    #         VAT[:, :, slice] = VATSlice
    #     else:
    #         fatVoidMask, thoracicMask, lungMask, SCATSlice, ITATSlice, CATSlice = \
    #             segmentThoracicSlice(slice, fatImageMask, waterImageMask, bodyMask, CATAxial, CATPosterior,
    #                                  CATAnterior, CATInferior, CATSuperior)
    #
    #         fatVoidMasks[:, :, slice] = fatVoidMask
    #         thoracicMasks[:, :, slice] = thoracicMask
    #         lungMasks[:, :, slice] = lungMask
    #         SCAT[:, :, slice] = SCATSlice
    #         ITAT[:, :, slice] = ITATSlice
    #         CAT[:, :, slice] = CATSlice
    #
    #     toc = time.perf_counter()
    #     print('Completed slice %i in %f seconds' % (slice, toc - tic))
    #
    if constants.debug:
        nrrd.write(getDebugPath("C:/Users/Clint/PycharmProjects/SIUE-Dixon-Fat-Segmentation-Algorithm/MRI_Data_Nrrd_Output/fatImageMask.nrrd"), skimage.img_as_ubyte(fatImageMasks), constants.nrrdHeaderDict)
        # nrrd.write(getDebugPath('waterImageMask.nrrd'), skimage.img_as_ubyte(waterImageMasks), constants.nrrdHeaderDict)
        # nrrd.write(getDebugPath('bodyMask.nrrd'), skimage.img_as_ubyte(bodyMasks), constants.nrrdHeaderDict)
        #
        # nrrd.write(getDebugPath('fatVoidMask.nrrd'), skimage.img_as_ubyte(fatVoidMasks), constants.nrrdHeaderDict)
        # nrrd.write(getDebugPath('abdominalMask.nrrd'), skimage.img_as_ubyte(abdominalMasks), constants.nrrdHeaderDict)
        #
        # nrrd.write(getDebugPath('lungMask.nrrd'), skimage.img_as_ubyte(lungMasks), constants.nrrdHeaderDict)
        # nrrd.write(getDebugPath('thoracicMask.nrrd'), skimage.img_as_ubyte(thoracicMasks), constants.nrrdHeaderDict)
    #
    # nrrd.write(getPath('SCAT.nrrd'), skimage.img_as_ubyte(SCAT), constants.nrrdHeaderDict)
    # nrrd.write(getPath('VAT.nrrd'), skimage.img_as_ubyte(VAT), constants.nrrdHeaderDict)
    # nrrd.write(getPath('ITAT.nrrd'), skimage.img_as_ubyte(ITAT), constants.nrrdHeaderDict)
    # nrrd.write(getPath('CAT.nrrd'), skimage.img_as_ubyte(CAT), constants.nrrdHeaderDict)
    #
    # if constants.saveMat:
    #     scipy.io.savemat(getPath('results.mat'), mdict={'SCAT': SCAT, 'VAT': VAT, 'ITAT': ITAT, 'CAT': CAT})
