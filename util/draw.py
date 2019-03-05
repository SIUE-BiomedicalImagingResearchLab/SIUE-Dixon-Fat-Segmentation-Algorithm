import cv2
import numpy as np


def binaryLine(startPoint, endPoint, shape, thickness=1, lineType=cv2.LINE_4):
    """Create an image of a given shape with a binary line drawn from one point to another
    
    Parameters
    ----------
    startPoint : (2,) tuple or list or :class:`numpy.ndarray`
        Starting point to begin drawing line from in Cartesian coordinates (x, y)
    endPoint : (2,) tuple or list or :class:`numpy.ndarray`
        Ending point to end drawing line from in Cartesian coordinates (x, y)
    shape : (N,) tuple or list
        Shape of image to be created in C-order, meaning (height, width) format
    thickness : int, optional
        Thickness of the line to draw, see OpenCV :meth:`cv2.line` function for more info (default is 1)
    lineType : int, optional
        Type of the line to draw, see OpenCV :meth:`cv2.line` function for more info (default is cv2.LINE_4 which is a
        4-connected line)

        Valid options are: cv2.LINE_4, cv2.LINE_8, cv2.LINE_AA

    Returns
    -------
    (M,N) :class:`numpy.ndarray`
        Numpy array of image with binary line drawn on it. Shape of image is given by :obj:`shape` argument
    """

    # Create image of all zeros of size shape
    # Note that the image shape is in C-order meaning it is reversed from typical Cartesian coordinates
    image = np.zeros(shape, np.uint8)

    # Draw line on image from point1 to point2 with given thickness and line type
    # Note that point1 and point2 are in Cartesian coordinates while the shape is reversed
    cv2.line(image, startPoint, endPoint, 1, thickness, lineType)

    # Convert the image to a binary image
    binaryImage = (image == 1)

    return binaryImage


def binaryRectangle(startPoint, endPoint, shape, thickness=cv2.FILLED, lineType=cv2.LINE_4):
    """Create an image of a given shape with a binary rectangle drawn between two given corners

    Parameters
    ----------
    startPoint : (2,) tuple or list or :class:`numpy.ndarray`
        Vertex of one corner of the rectangle in Cartesian coordinates (x, y)
    endPoint : (2,) tuple or list or :class:`numpy.ndarray`
        Vertex of opposite corner to the startPoint of the rectangle in Cartesian coordinates (x, y)
    shape : (N,) tuple or list
        Shape of image to be created in C-order, meaning (height, width) format
    thickness : int, optional
        Thickness of the line to draw, see OpenCV :meth:`cv2.rectangle` function for more info. Setting to cv2.FILLED
        will fill the rectangle (default is cv2.FILLED)
    lineType : int, optional
        Type of the line to draw for the rectangle, see OpenCV :meth:`cv2.line` function for more info (default is
        cv2.LINE_4 which is a 4-connected line)

        Valid options are: cv2.LINE_4, cv2.LINE_8, cv2.LINE_AA

    Returns
    -------
    (M,N) :class:`numpy.ndarray`
        Numpy array of image with binary rectangle
    """

    # Create image of all zeros of size shape
    # Note that the image shape is in C-order meaning it is reversed from typical Cartesian coordinates
    image = np.zeros(shape, np.uint8)

    # Draw rectangle from one corner to another with given thickness and line type
    # Note that point1 and point2 are in Cartesian coordinates while the shape is reversed
    cv2.rectangle(image, startPoint, endPoint, 1, thickness, lineType)

    # Convert the image to a binary image
    binaryImage = (image == 1)

    return binaryImage


def binaryFilledPolygon(points, shape, lineType=cv2.LINE_4):
    """Create an image of a given shape with a binary line drawn from one point to another

    Parameters
    ----------
    points : (N, 2) tuple or list or :class:`numpy.ndarray`
        List of coordinates for the filled polygon to be drawn. Coordinates are in Cartesian format (x, y)
    shape : (N,) tuple or list
        Shape of image to be created in C-order, meaning (height, width) format
    lineType : int, optional
        Type of the line to draw, see OpenCV :meth:`cv2.line` function for more info (default is cv2.LINE_4 which is a
        4-connected line)

        Valid options are: cv2.LINE_4, cv2.LINE_8, cv2.LINE_AA

    Returns
    -------
    (M,N) :class:`numpy.ndarray`
        Numpy array of image with binary filled polygon drawn on it. Shape of image is given by :obj:`shape` argument
    """

    # Create image of all zeros of size shape
    # Note that the image shape is in C-order meaning it is reversed from typical Cartesian coordinates
    image = np.zeros(shape, np.uint8)

    # Convert the list of points for the polygon to a Numpy array of ints
    # OpenCV requires that the datatype be a 32-bit signed integer
    points = np.array(points, dtype=np.int32)

    # Expand
    # cv2.fillPoly requires a list of polygons to draw that are a list of coordinates
    # Thus, the data should be 3D with the dimensions being (polygon #, coordinate #, x/y)
    # If only 2D data is given, assume that only one polygon is to be drawn and expand the dimensions at the 0th axis
    # Shape will go from (w, z) to (1, w, z)
    if points.ndim == 2:
        points = np.expand_dims(points, axis=0)

    # Draw line on image from point1 to point2 with given thickness and line type
    # Note that point1 and point2 are in Cartesian coordinates while the shape is reversed
    cv2.fillPoly(image, points, 1, lineType)

    # Convert the image to a binary image
    binaryImage = (image == 1)

    return binaryImage


def lineCoords(*args, **kwargs):
    binaryImage = binaryLine(*args, **kwargs)

    return np.argwhere(binaryImage)
