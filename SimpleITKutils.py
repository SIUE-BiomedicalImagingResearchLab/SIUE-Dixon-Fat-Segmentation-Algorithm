import numpy as np
import SimpleITK as sitk

def concatenate(images, axis=0):
    # Numpy arrays are stored in C-order indexing while the axis specified above is
    # Forton indexing. This is converted by taking # Dimension - axis
    numpyArrays = [sitk.GetArrayViewFromImage(image) for image in images]
    resultImage = np.concatenate(numpyArrays, images[0].GetDimension() - axis - 1)

    result = sitk.GetImageFromArray(resultImage)
    result.SetSpacing(images[0].GetSpacing())
    result.SetOrigin(images[0].GetOrigin())
    result.SetDirection(images[0].GetDirection())

    return result