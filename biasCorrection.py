import os

import SimpleITK as sitk
import numpy as np
import scipy.ndimage.interpolation
import skimage.filters
import skimage.transform

import constants


# Get resulting path for debug files
def getDebugPath(prefix, filename):
    return os.path.join(constants.pathDir, 'debug', prefix, filename)


# Given an image and a shrink factor, the image is corrected via N4 bias correction method
def correctBias(image, shrinkFactor, prefix):
    # If debug bias correction is turned on, then create the directory where the debug files will be saved
    # The makedirs command is in try/catch because if it already exists, it will throw an exception and we just want
    # to continue in that case
    if constants.debugBiasCorrection:
        try:
            os.makedirs(getDebugPath(prefix, ''))
        except os.error:
            pass

    if constants.debugBiasCorrection:
        np.save(getDebugPath(prefix, 'image.npy'), image)

    # Shrink image by shrinkFactor to make the bias correction quicker
    # Use resample to linearly interpolate between pixel values
    shrinkedImage = scipy.ndimage.interpolation.zoom(image, 1 / shrinkFactor)

    if constants.debugBiasCorrection:
        np.save(getDebugPath(prefix, 'imageShrinked.npy'), shrinkedImage)

    # Perform Otsu's thresholding method on images to get a mask for N4 correction bias
    # According to Sled's paper (author of N3 bias correction), the mask is to remove infinity values
    # from log-space (log(0) = infinity)
    imageMaskThresh = skimage.filters.threshold_otsu(shrinkedImage)
    imageMask = (shrinkedImage >= imageMaskThresh).astype(np.uint8)

    if constants.debugBiasCorrection:
        np.save(getDebugPath(prefix, 'imageMask.npy'), imageMask)

    # Apply N4 bias field correction to the shrinked image
    shrinkedImageITK = sitk.GetImageFromArray(shrinkedImage)
    imageMaskITK = sitk.GetImageFromArray(imageMask)
    correctedImageITK = sitk.N4BiasFieldCorrection(shrinkedImageITK, imageMaskITK)
    correctedImage = sitk.GetArrayFromImage(correctedImageITK)

    if constants.debugBiasCorrection:
        np.save(getDebugPath(prefix, 'correctedImageShrinked.npy'), correctedImage)

    # Replace all 0s in shrinked image with very small number
    # Prevents infinity values when calculating shrinked bias field, prevents divide by zero issues
    correctedImage[correctedImage == 0] = 0.001

    # Get the bias field by dividing measured image by corrected image
    # v(x) / u(x) = f(x)
    biasFieldShrinked = shrinkedImage / correctedImage

    if constants.debugBiasCorrection:
        np.save(getDebugPath(prefix, 'biasFieldShrinked.npy'), biasFieldShrinked)

    # TODO This causes the first and last slice of the biasField to be all 0s
    # Since the image was shrinked when performing bias correction to speed up the process, the bias field is
    # now expanded to the original image size
    biasField = scipy.ndimage.interpolation.zoom(biasFieldShrinked, np.array(image.shape) / biasFieldShrinked.shape)

    # Replace all 0s in shrinked image with 1s
    # Prevents infinity values when calculating corrected image, by setting the bias field to 1 at
    # that index, it will set the corrected image pixel equal to the original image pixel value
    biasField[biasField == 0] = 1

    if constants.debugBiasCorrection:
        np.save(getDebugPath(prefix, 'biasField.npy'), biasField)

    # Get the actual image by dividing original image by the bias field
    # u(x) = v(x) / f(x)
    correctedImage = image / biasField

    if constants.debugBiasCorrection:
        np.save(getDebugPath(prefix, 'correctedImage.npy'), biasField)

    return correctedImage
