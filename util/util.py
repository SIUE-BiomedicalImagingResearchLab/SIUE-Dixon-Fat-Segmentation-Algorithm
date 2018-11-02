import numpy as np
import sklearn.cluster


def kmeans(image, k, isVector=False):
    # Flatten the image so that all of the values are in an array
    # If the image is a vector, then do not combine the last dimension
    flattenedImage = image.reshape(-1, image.shape[-1] if isVector else 1)

    centroids, labels, inertia = sklearn.cluster.k_means(flattenedImage, k)
    labelOrder = np.argsort(centroids.sum(axis=1))

    return labelOrder, centroids, labels.reshape(image.shape[:-1] if isVector else image.shape)


def fuseImageFalseColor(image1, image2):
    result = np.dstack((image2, image1, image2))

    return result


def nearestNonzeroIdx(array, x, y, includeCurrent=False):
    if includeCurrent:
        prevValue = array[x, y]
        array[x, y] = 0

    r, c = np.nonzero(array)
    ((r - x) ** 2 + (c - y) ** 2).argmin()

    a[x, y] = tmp
    min_idx = ((r - x) ** 2 + (c - y) ** 2).argmin()

    if includeCurrent:
        array[x, y] = prevValue

    return r[min_idx], c[min_idx]


def maxargwhere(array, axis=0):
    def func(a):
        x = np.argwhere(a)
        return -1 if len(x) == 0 else x.max()

    return np.apply_along_axis(func, axis, array)


def minargwhere(array, axis=0):
    def func(a):
        x = np.argwhere(a)
        return -1 if len(x) == 0 else x.min()

    return np.apply_along_axis(func, axis, array)


def nearestargwhere(array, index=0, axis=0):
    def func(a):
        x = np.argwhere(a)
        if len(x) == 0:
            return -1

        minIndex = np.abs(x - index).argmin()

        return x[minIndex]

    return np.apply_along_axis(func, axis, array)


def defaultmin(x, default):
    return default if x.size == 0 else x.min()
