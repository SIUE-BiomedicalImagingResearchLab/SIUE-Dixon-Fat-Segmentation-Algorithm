import matplotlib
import numpy as np

# Make sure that we are using Qt5
matplotlib.use('Qt5Agg')
from PyQt5 import QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.patches as patches
from PyQt5.Qt import *


class SliceWidget(FigureCanvas):
    def __init__(self, parent=None, dpi=100):
        # Create figure and axes, the axes should cover the entire figure size
        figure = Figure(dpi=dpi, frameon=False)
        self.axes = figure.add_axes((0, 0, 1, 1), facecolor='black')

        # Hide the x and y axis, we just want to see the image
        self.axes.get_xaxis().set_visible(False)
        self.axes.get_yaxis().set_visible(False)

        # Initialize the parent FigureCanvas
        FigureCanvas.__init__(self, figure)
        self.setParent(parent)

        # Set background of the widget to be close to black
        # The color is not made actually black so that the user can distinguish the image bounds from the figure bounds
        self.setStyleSheet('background-color: #222222;')

        # Set widget to have strong focus to receive key press events
        self.setFocusPolicy(Qt.StrongFocus)

        # Create navigation toolbar and hide it
        # We don't want the user to see the toolbar but we are making our own in the user interface that will call
        # functions from the toolbar
        self.toolbar = NavigationToolbar(self, self)
        self.toolbar.hide()

        # Update size policy and geometry
        FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        self.isLPS = False
        self.isLAS = False
        self.image = None
        self.sliceNumber = 0
        self.diaphragmAxial = None
        self.umbilicisInferior = None
        self.umbilicisSuperior = None
        self.umbilicisLeft = None
        self.umbilicisRight = None
        self.umbilicisCoronal = None
        self.CATLine = None
        self.leftArmBounds = None
        self.rightArmBounds = None

    def updateFigure(self):
        # Clear the axes
        self.axes.cla()

        # Draw the image if it is set
        if self.image is not None:
            image = self.image[self.sliceNumber, :, :]

            # For viewing, we use right-anterior-superior (RAS) system. This is the same system that PATS uses.
            # For LPS volumes, we reverse the x/y axes to go from LPS to RAS.
            # Also, TTU data is in LAS which is odd but handle that too
            if self.isLPS:
                image = image[::-1, ::-1]
            elif self.isLAS:
                image = image[:, ::-1]

            self.axes.imshow(image, cmap='gray', origin='lower')

        # Draw rectangle on the diaphragm slice
        if self.sliceNumber == self.diaphragmAxial:
            self.axes.add_patch(patches.Rectangle((0, 0), 20, 20, color='purple'))

        # Draw a line where the umbilicis is set to be
        if self.umbilicisInferior is not None and self.umbilicisSuperior is not None and \
                self.umbilicisCoronal is not None and self.umbilicisLeft is not None and \
                self.umbilicisRight is not None:
            if self.umbilicisInferior <= self.sliceNumber <= self.umbilicisSuperior:
                x = self.umbilicisLeft
                y = self.umbilicisCoronal
                width = self.umbilicisRight - x
                height = 1

                self.axes.add_patch(patches.Rectangle((x, y), width, height, color='orange'))

        # Draw lines for the CAT bounding box configuration
        if self.CATLine is not None and len(self.CATLine) > 1:
            startIndex = next((i for i, x in enumerate(self.CATLine) if min(x) != -1), None)

            CATLine = self.CATLine[startIndex:]
            if len(CATLine) > 1 and CATLine[0][0] <= self.sliceNumber <= CATLine[-1][0]:
                posterior = int(np.round(np.interp(self.sliceNumber, np.array([i[0] for i in CATLine]),
                                                   np.array([i[1] for i in CATLine]))))
                anterior = int(np.round(np.interp(self.sliceNumber, np.array([i[0] for i in CATLine]),
                                                  np.array([i[2] for i in CATLine]))))

                x = self.image.shape[2] // 2.5
                y = posterior
                width = 75
                height = 1
                self.axes.add_patch(patches.Rectangle((x, y), width, height, color='red'))

                y = anterior
                self.axes.add_patch(patches.Rectangle((x, y), width, height, color='red'))

        # Draw a line for the left arm bounds at the current slice
        # Only draw if current slice is between smallest and largest bounds
        if self.leftArmBounds is not None and len(self.leftArmBounds) > 0 and \
                (self.leftArmBounds[0][-1] <= self.sliceNumber <= self.leftArmBounds[-1][-1]):
            # Get a list of slice numbers for the left arm bounds
            xp = np.array([i[4] for i in self.leftArmBounds])

            # Get list of x/y coordinates at the slice numbers
            x1p, y1p = np.array([i[0] for i in self.leftArmBounds]), np.array([i[1] for i in self.leftArmBounds])
            x2p, y2p = np.array([i[2] for i in self.leftArmBounds]), np.array([i[3] for i in self.leftArmBounds])

            # Interpolate for given slice between the bounds, round and convert to an integer
            x1, y1 = int(np.round(np.interp(self.sliceNumber, xp, x1p))), \
                     int(np.round(np.interp(self.sliceNumber, xp, y1p)))
            x2, y2 = int(np.round(np.interp(self.sliceNumber, xp, x2p))), \
                     int(np.round(np.interp(self.sliceNumber, xp, y2p)))

            self.axes.plot([x1, x2], [y1, y2], 'g', lw=2.0)

        # Draw a line for the right arm bounds at the current slice
        # Only draw if current slice is between smallest and largest bounds
        if self.rightArmBounds is not None and len(self.rightArmBounds) > 0 and \
                (self.rightArmBounds[0][-1] <= self.sliceNumber <= self.rightArmBounds[-1][-1]):
            # Get a list of slice numbers for the left arm bounds
            xp = np.array([i[4] for i in self.rightArmBounds])

            # Get list of x/y coordinates at the slice numbers
            x1p, y1p = np.array([i[0] for i in self.rightArmBounds]), np.array([i[1] for i in self.rightArmBounds])
            x2p, y2p = np.array([i[2] for i in self.rightArmBounds]), np.array([i[3] for i in self.rightArmBounds])

            # Interpolate for given slice between the bounds, round and convert to an integer
            x1, y1 = int(np.round(np.interp(self.sliceNumber, xp, x1p))), \
                     int(np.round(np.interp(self.sliceNumber, xp, y1p)))
            x2, y2 = int(np.round(np.interp(self.sliceNumber, xp, x2p))), \
                     int(np.round(np.interp(self.sliceNumber, xp, y2p)))

            self.axes.plot([x1, x2], [y1, y2], 'g', lw=1.5)

        # Draw the figure now
        self.draw()
