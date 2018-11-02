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

        # Set background of the widget to be black
        self.setStyleSheet('background-color: black;')

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

        self.image = None
        self.sliceNumber = 0
        self.diaphragmAxial = None
        self.umbilicisInferior = None
        self.umbilicisSuperior = None
        self.umbilicisLeft = None
        self.umbilicisRight = None
        self.umbilicisCoronal = None
        self.CATLine = None

    def updateFigure(self):
        # Clear the axes
        self.axes.cla()

        # Draw the image if it is set
        if self.image is not None:
            self.axes.imshow(self.image[:, :, self.sliceNumber].T, cmap='gray', origin='lower')

        # Draw rectangle on the diaphragm slice
        if self.sliceNumber == self.diaphragmAxial:
            self.axes.add_patch(patches.Rectangle((0, 0), 20, 20, color='purple'))

        # Draw a line where the umbilicis is set to be
        if self.umbilicisInferior is not None:
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

                x = self.image.shape[0] // 3
                y = posterior
                width = 75
                height = 1
                self.axes.add_patch(patches.Rectangle((x, y), width, height, color='red'))

                y = anterior
                self.axes.add_patch(patches.Rectangle((x, y), width, height, color='red'))

        # Draw the figure now
        self.draw()
