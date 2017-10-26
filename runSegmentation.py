import os
import time
import sys

import SimpleITK as sitk
import matplotlib.pyplot as plt
import skimage.morphology
import scipy.ndimage.morphology
import skimage.segmentation
import skimage.draw

import constants
from biasCorrection import correctBias
from utils import *


# Get resulting path for debug files
def getDebugPath(str):
    return os.path.join(constants.pathDir, 'debug', str)

sliceNumber = 0
showDiff = True
image1 = None
image2 = None

def segmentAbdomenSlice(fatImageMask, waterImageMask, bodyMask):
    # fatImageMask2 is a closed version of fatImageMask. This is necessary around the
    # umbilical cord since the fat image mask will not be connected all the way around
    # Fill holes in the fat image mask and invert it to get the background of fat image
    # OR the fat background mask and fat image mask and take NOT of mask to get the fat void mask
    # Next, remove small objects by morphologically opening
    fatImageMask2 = skimage.morphology.binary_closing(fatImageMask, skimage.morphology.disk(3))
    fatBackgroundMask = np.logical_not(scipy.ndimage.morphology.binary_fill_holes(fatImageMask2))
    fatVoidMask = np.logical_or(fatBackgroundMask, fatImageMask)
    fatVoidMask = np.logical_not(fatVoidMask)
    fatVoidMask = skimage.morphology.binary_closing(fatVoidMask, skimage.morphology.disk(6))
    fatVoidMask = skimage.morphology.binary_opening(fatVoidMask, skimage.morphology.disk(6))

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
    i = 4

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
    fatImageMasks = np.zeros(fatImage.shape, bool)
    waterImageMasks = np.zeros(fatImage.shape, bool)
    bodyMasks = np.zeros(fatImage.shape, bool)
    fatVoidMasks = np.zeros(fatImage.shape, bool)
    abdominalMasks = np.zeros(fatImage.shape, bool)
    SCAT = np.zeros(fatImage.shape, bool)
    VAT = np.zeros(fatImage.shape, bool)
    # blankImage = sitk.Image(fatImage.GetWidth(), fatImage.GetHeight(), sitk.sitkUInt8)
    # blankImage.CopyInformation(fatImage[:, :, 0])
    # fatImageMasks = [blankImage] * fatImage.GetDepth()
    # waterImageMasks = [blankImage] * fatImage.GetDepth()
    # bodyMasks = [blankImage] * fatImage.GetDepth()
    # VATMasks = [blankImage] * fatImage.GetDepth()
    #
    # filledImages = [blankImage] * fatImage.GetDepth()

    # gradientMagImages = [sitk.Cast(blankImage, sitk.sitkFloat32)] * fatImage.GetDepth()
    # sigGradientMagImages = [sitk.Cast(blankImage, sitk.sitkFloat32)] * fatImage.GetDepth()
    # initialContours = [sitk.Cast(blankImage, sitk.sitkFloat32)] * fatImage.GetDepth()
    # finalContours = [sitk.Cast(blankImage, sitk.sitkFloat32)] * fatImage.GetDepth()

    for slice in range(80, 88): #diaphragmSuperiorSlice): # fatImage.shape[2]):
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
            i = 4

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

    # Figure stuff
    def press(event):
        global image1
        global image2
        global sliceNumber
        global showDiff

        print('Press: ', event.key)
        sys.stdout.flush()

        if event.key == '1':
            image1 = fatImage
            image2 = fatImageMasks
        elif event.key == '2':
            image1 = waterImage
            image2 = waterImageMasks
        elif event.key == '3':
            image1 = fatImage
            image2 = bodyMasks
        elif event.key == '4':
            image1 = fatImage
            image2 = fatVoidMasks
        elif event.key == '5':
            image1 = fatImage
            image2 = abdominalMasks
        elif event.key == 'x':
            showDiff = not showDiff
        elif event.key == 'a':
            sliceNumber = sliceNumber - 1
        elif event.key == 'd':
            sliceNumber = sliceNumber + 1
        else:
            return

        if sliceNumber < 0:
            sliceNumber = 0

        plt.clf()

        if showDiff:
            plt.imshow(fuseImageFalseColor(image1[:, :, sliceNumber], image2[:, :, sliceNumber]))
        else:
            plt.imshow(image1[:, :, sliceNumber])

        plt.title('Slice %i' % (sliceNumber))

        event.canvas.draw()

    fig = plt.figure(1)
    fig.canvas.mpl_connect('key_press_event', press)

    if showDiff:
        plt.imshow(fuseImageFalseColor(fatImage[:, :, sliceNumber], fatImageMasks[:, :, sliceNumber]))
    else:
        plt.imshow(fatImage[:, :, sliceNumber])

    global image1
    global image2
    image1 = fatImage
    image2 = fatImageMasks
    plt.title('Slice %i' % (sliceNumber))

    plt.show()

