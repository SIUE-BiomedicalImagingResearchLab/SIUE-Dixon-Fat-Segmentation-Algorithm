from .sortSlices import *

pydicom.config.datetime_conversion = True


def combineSlices(datasets, method=MethodType.Unknown, reverse=False):
    """
    Combines the given dataset for Volume into a 3D volume. In addition, some parameters for the volume are
    calculated, such as:
        Origin, spacing, coordinate system, and orientation.
    """

    type_ = VolumeType.Unknown

    if method is MethodType.Unknown:
        method, type_ = getBestMethod(datasets)
    elif not isMethodAvailable(datasets, method):
        raise TypeError('Invalid method specified')

    sortedDataset, zSpacing, sliceCosines = sortSlices(datasets, method, reverse)

    # Get 3D volume from list of datasets
    volume = np.dstack((x.pixel_array for x in sortedDataset))

    space = 'left-posterior-superior'
    # Append the Z cosines to image orientation and then resize into 3x3 matrix
    orientation = np.reshape(list(datasets[0].ImageOrientationPatient) + sliceCosines, (3, 3)).T
    # Concatenate (x,y) spacing list and zSpacing list
    spacing = list(datasets[0].PixelSpacing) + list([zSpacing])
    origin = datasets[0].ImagePositionPatient

    return method, type_, space, orientation, spacing, origin, volume
