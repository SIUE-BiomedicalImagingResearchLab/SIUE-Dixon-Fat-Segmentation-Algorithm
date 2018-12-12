import numpy as np
import sklearn.cluster


def kmeans(image, k, isVector=False):
    # Flatten the image so that all of the values are in an array
    # If the image is a vector, then do not combine the last dimension
    flattenedImage = image.reshape(-1, image.shape[-1] if isVector else 1)

    centroids, labels, inertia = sklearn.cluster.k_means(flattenedImage, k)
    labelOrder = np.argsort(centroids.sum(axis=1))

    return labelOrder, centroids, labels.reshape(image.shape[:-1] if isVector else image.shape)


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

