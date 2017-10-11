import os

import SimpleITK as sitk
import numpy as np

import constants


# Given an image and a shrink factor, the image is corrected via N4 bias correction method
def correctBias(image, shrinkFactor, prefix):
    # If debug bias correction is turned on, then create the directory where the debug files will be saved
    # The makedirs command is in try/catch because if it already exists, it will throw an exception and we just want
    # to continue in that case
    if constants.debugBiasCorrection:
        try:
            os.makedirs(os.path.join(constants.pathDir, 'debug', prefix))
        except:
            pass

    if constants.debugBiasCorrection:
        sitk.WriteImage(image, os.path.join(constants.pathDir, 'debug', prefix, 'image.img'))

    # Shrink image by shrinkFactor to make the bias correction quicker
    # Use resample to linearly interpolate between pixel values
    # TODO Issue using numpy.array() parameter for size but not the spacing or origin
    shrinkedImage = sitk.Resample(image, [round(x / shrinkFactor) for x in image.GetSize()], sitk.Transform(),
                                  sitk.sitkLinear, image.GetOrigin(), [x * shrinkFactor for x in image.GetSpacing()],
                                  image.GetDirection())

    if constants.debugBiasCorrection:
        sitk.WriteImage(shrinkedImage, os.path.join(constants.pathDir, 'debug', prefix, 'imageShrinked.img'))

    # Perform Otsu's thresholding method on images to get a mask for N4 correction bias
    # According to Sled's paper (author of N3 bias correction), the mask is to remove infinity values
    # from log-space (log(0) = infinity)
    imageMask = sitk.OtsuThreshold(shrinkedImage, 0, 1, 200)

    if constants.debugBiasCorrection:
        sitk.WriteImage(imageMask, os.path.join(constants.pathDir, 'debug', prefix, 'imageMask.img'))

    # Apply N4 bias field correction to the shrinked image
    correctedImage = sitk.N4BiasFieldCorrection(shrinkedImage, imageMask)

    if constants.debugBiasCorrection:
        sitk.WriteImage(correctedImage, os.path.join(constants.pathDir, 'debug', prefix, 'correctedImageShrinked.img'))

    # Replace all 0s in shrinked image with very small number
    # Prevents infinity values when calculating shrinked bias field, prevents divide by zero issues
    zeroShrinkedImageMask = sitk.Cast(shrinkedImage == 0.0, shrinkedImage.GetPixelIDValue())
    notZeroShrinkedImageMask = sitk.InvertIntensity(zeroShrinkedImageMask, 1.0)
    shrinkedImage = (shrinkedImage * notZeroShrinkedImageMask) + (0.001 * zeroShrinkedImageMask)

    # Get the bias field by dividing measured image by corrected image
    # v(x) / u(x) = f(x)
    # TODO Division causes __truediv__ which uses DivideReal. Only returns double type, not float
    biasFieldShrinked = sitk.Cast(shrinkedImage / correctedImage, sitk.sitkFloat32)

    if constants.debugBiasCorrection:
        sitk.WriteImage(biasFieldShrinked, os.path.join(constants.pathDir, 'debug', prefix, 'biasFieldShrinked.img'))

    # TODO This causes the first and last slice of the biasField to be all 0s
    # Since the image was shrinked when performing bias correction to speed up the process, the bias field is
    # now expanded to the original image size
    newSpacing = np.array(biasFieldShrinked.GetSize()) / np.array(image.GetSize()) * \
                 np.array(biasFieldShrinked.GetSpacing())
    print(newSpacing)
    biasField = sitk.Resample(biasFieldShrinked, image.GetSize(), sitk.Transform(), sitk.sitkLinear,
                              image.GetOrigin(), newSpacing,  # np.array(biasFieldShrinked.GetSpacing()) / shrinkFactor,
                              image.GetDirection())
    biasField.SetSpacing(image.GetSpacing())

    # Replace all 0s in shrinked image with 1s
    # Prevents infinity values when calculating corrected image, by setting the bias field to 1 at
    # that index, it will set the corrected image pixel equal to the original image pixel value
    zeroBiasFieldMask = sitk.Cast(biasField == 0.0, biasField.GetPixelIDValue())
    notZeroBiasFieldMask = sitk.InvertIntensity(zeroBiasFieldMask, 1.0)
    biasField = (biasField * notZeroBiasFieldMask) + (1.0 * zeroBiasFieldMask)

    if constants.debugBiasCorrection:
        sitk.WriteImage(biasField, os.path.join(constants.pathDir, 'debug', prefix, 'biasField.img'))

    # Get the actual image by dividing original image by the bias field
    # u(x) = v(x) / f(x)
    correctedImage = image / biasField

    if constants.debugBiasCorrection:
        sitk.WriteImage(correctedImage, os.path.join(constants.pathDir, 'debug', prefix, 'correctedImage.img'))

    return correctedImage
