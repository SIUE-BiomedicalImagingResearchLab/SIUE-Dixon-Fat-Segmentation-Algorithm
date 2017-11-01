import random

import matplotlib
import numpy as np

# Make sure that we are using Qt5
matplotlib.use('Qt5Agg')
from PyQt5 import QtCore, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.patches as patches

class SliceWidget(FigureCanvas):
    def __init__(self, parent=None, dpi=100):
        fig = Figure(dpi=dpi)
        self.axes = fig.add_subplot(111)

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        fig.tight_layout()

        self.toolbar = NavigationToolbar(self, self)
        self.toolbar.hide()

        self.mpl_connect('motion_notify_event', self.mouseMoved)

        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        self.locationLabel = None
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
        self.axes.cla()

        if self.image is not None:
            self.axes.imshow(self.image[:, :, self.sliceNumber], cmap="gray")

        if self.sliceNumber == self.diaphragmAxial:
            self.axes.add_patch(patches.Rectangle((0, 0), 20, 20, color='purple'))

        if self.umbilicisInferior is not None:
            if self.umbilicisInferior <= self.sliceNumber <= self.umbilicisSuperior:
                x = self.umbilicisLeft
                y = self.umbilicisCoronal
                width = 1
                height = self.umbilicisRight - x

                self.axes.add_patch(patches.Rectangle((y, x), width, height, color='orange'))

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
                width = 1
                height = 75
                self.axes.add_patch(patches.Rectangle((y, x), width, height, color='red'))

                y = anterior
                self.axes.add_patch(patches.Rectangle((y, x), width, height, color='red'))

        self.draw()

    def mouseMoved(self, event):
        if self.locationLabel is not None and event.inaxes:
            x, y, z = event.xdata, event.ydata, self.sliceNumber
        else:
            x, y, z = 0, 0, self.sliceNumber

        self.locationLabel.setText("(%i, %i, %i)" % (x, y, z))