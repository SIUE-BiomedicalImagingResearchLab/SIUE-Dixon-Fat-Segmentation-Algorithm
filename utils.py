import cv2
import numpy as np
import sklearn.cluster
import cv2

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