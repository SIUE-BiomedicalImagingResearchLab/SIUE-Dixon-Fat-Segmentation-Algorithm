import cv2
import numpy as np


def binaryLine(point1, point2, shape, thickness=1, lineType=cv2.LINE_4):
    # Create image of all zeros of size shape
    image = np.zeros(shape, np.uint8)

    # Draw line on image from point1 to point2 with given thickness and line type
    # Reverse point1 and point2 because OpenCV uses (row, column) coordinates (which is (y, x))
    cv2.line(image, point1[::-1], point2[::-1], 1, thickness, lineType)

    # Convert the image to a binary image
    binaryImage = (image == 1)

    return binaryImage


def lineCoords(*args, **kwargs):
    binaryImage = binaryLine(*args, **kwargs)

    return np.argwhere(binaryImage)
