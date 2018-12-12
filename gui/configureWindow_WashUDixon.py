import os

import yaml
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from generated import configureWindow_WashUDixon_ui
from util import constants


class ConfigureWindow(QDialog, configureWindow_WashUDixon_ui.Ui_ConfigureWindow):
    def __init__(self, data, dataPath, parent=None):
        super(ConfigureWindow, self).__init__(parent)
        self.setupUi(self)

        self.fatImage, self.waterImage, self.config = data
        self.dataPath = dataPath
        self.clickState = 0
        self.clickData = []

        self.sliceWidget.mpl_connect('motion_notify_event', self.on_sliceWidget_mouseMoved)
        self.sliceWidget.mpl_connect('key_press_event', self.on_sliceWidget_keyPressed)
        self.sliceWidget.mpl_connect('button_press_event', self.on_sliceWidget_clicked)

        self.setupDefaults()

        self.loadSettings()

        # DICOM data uses LPS, we tell the slice widget this to standardize it to RAS coordinate system
        self.sliceWidget.isLPS = True
        self.sliceWidget.updateFigure()

    def loadSettings(self):
        settings = QSettings(constants.applicationName, constants.organizationName)
        settings.beginGroup('configureWindow_WashUDixon')

        geometry = settings.value('geometry', QByteArray(), type=QByteArray)
        if not geometry.isEmpty():
            self.restoreGeometry(geometry)

            # Fixes QTBUG-46620 issue
            if settings.value('maximized', False, type=bool):
                self.showMaximized()
                self.setGeometry(QApplication.desktop().availableGeometry(self))

        settings.endGroup()

    def saveSettings(self):
        settings = QSettings(constants.applicationName, constants.organizationName)
        settings.beginGroup('configureWindow_WashUDixon')

        settings.setValue('geometry', self.saveGeometry())
        settings.setValue('maximized', self.isMaximized())

        settings.endGroup()

    def setupDefaults(self):
        self.sliceSlider.setValue(self.sliceWidget.sliceNumber)
        self.sliceSlider.setMinimum(0)
        self.sliceSlider.setMaximum(self.fatImage.shape[0] - 1)

        self.viewFatRadioButton.setChecked(True)
        self.sliceWidget.image = self.fatImage
        self.noneRadioButton.setChecked(True)

        diaphragmAxialSlice = self.config.get('diaphragmAxial')
        if diaphragmAxialSlice:
            self.diaphragmAxialSpinBox.setValue(diaphragmAxialSlice)

        umbilicis = self.config.get('umbilicis')
        if umbilicis:
            self.umbilicisInferiorSpinBox.setValue(umbilicis['inferior'])
            self.umbilicisSuperiorSpinBox.setValue(umbilicis['superior'])
            self.umbilicisLeftSpinBox.setValue(umbilicis['left'])
            self.umbilicisRightSpinBox.setValue(umbilicis['right'])
            self.umbilicisCoronalSpinBox.setValue(umbilicis['coronal'])

            # Update the slice widget values, must transform X/Y coordinates appropriately
            self.sliceWidget.umbilicisInferior = umbilicis['inferior']
            self.sliceWidget.umbilicisSuperior = umbilicis['superior']
            self.sliceWidget.umbilicisLeft = self.transformX(umbilicis['left'])
            self.sliceWidget.umbilicisRight = self.transformX(umbilicis['right'])
            self.sliceWidget.umbilicisCoronal = self.transformY(umbilicis['coronal'])

        armBounds = self.config.get('armBounds')
        if armBounds:
            leftArm = armBounds.get('leftArm')
            rightArm = armBounds.get('rightArm')

            self.leftArmBounds = [(x['firstPoint'][0], x['firstPoint'][1], x['secondPoint'][0],
                                   x['secondPoint'][1], x['axialPosition'])
                                  for x in leftArm]
            self.rightArmBounds = [(x['firstPoint'][0], x['firstPoint'][1], x['secondPoint'][0],
                                   x['secondPoint'][1], x['axialPosition'])
                                  for x in rightArm]

            self.updateArmBounds()
        else:
            self.leftArmBounds = []
            self.rightArmBounds = []

        self.umbilicisInferiorSpinBox.setMaximum(self.fatImage.shape[0] - 1)
        self.umbilicisSuperiorSpinBox.setMaximum(self.fatImage.shape[0] - 1)
        self.umbilicisLeftSpinBox.setMaximum(self.fatImage.shape[2] - 1)
        self.umbilicisRightSpinBox.setMaximum(self.fatImage.shape[2] - 1)
        self.umbilicisCoronalSpinBox.setMaximum(self.fatImage.shape[1] - 1)

    def getData(self):
        return self.fatImage, self.waterImage, self.config

    @pyqtSlot(bool)
    def on_viewFatRadioButton_toggled(self, checked):
        if not checked:
            return

        self.sliceWidget.image = self.fatImage
        self.sliceWidget.updateFigure()

    @pyqtSlot(bool)
    def on_viewWaterRadioButton_toggled(self, checked):
        if not checked:
            return

        self.sliceWidget.image = self.waterImage
        self.sliceWidget.updateFigure()

    @pyqtSlot(bool)
    def on_noneRadioButton_toggled(self, checked):
        if not checked:
            return

        self.infoLabel.setText('')
        self.clickState = 0
        self.clickData = []

    @pyqtSlot(bool)
    def on_diaphragmRadioButton_toggled(self, checked):
        if not checked:
            return

        self.infoLabel.setText('Click on a slice to make it the axial slice of the diaphragm')
        self.clickState = 0
        self.clickData = []

    @pyqtSlot(bool)
    def on_umbilicisRadioButton_toggled(self, checked):
        if not checked:
            return

        self.infoLabel.setText('Click first point of umbilicis line')
        self.clickState = 0
        self.clickData = []

    @pyqtSlot(bool)
    def on_armBoundsRadioButton_toggled(self, checked):
        if not checked:
            return

        self.infoLabel.setText('Click on first point of line for left arm')
        self.clickState = 0
        self.clickData = []

    @pyqtSlot(int)
    def on_sliceSlider_valueChanged(self, value):
        self.sliceWidget.sliceNumber = value
        self.locationLabel.setText('(%i, %i, %i)' % (0, 0, value))
        self.sliceWidget.updateFigure()

    @pyqtSlot(int)
    def on_diaphragmAxialSpinBox_valueChanged(self, value):
        self.sliceWidget.diaphragmAxial = value if value >= 0 else None
        self.sliceWidget.updateFigure()

    @pyqtSlot(int)
    def on_umbilicisInferiorSpinBox_valueChanged(self, value):
        self.sliceWidget.umbilicisInferior = value if value >= 0 else None
        self.sliceWidget.updateFigure()

    @pyqtSlot(int)
    def on_umbilicisSuperiorSpinBox_valueChanged(self, value):
        self.sliceWidget.umbilicisSuperior = value if value >= 0 else None
        self.sliceWidget.updateFigure()

    @pyqtSlot(int)
    def on_umbilicisLeftSpinBox_valueChanged(self, value):
        self.sliceWidget.umbilicisLeft = self.transformX(value) if value >= 0 else None
        self.sliceWidget.updateFigure()

    @pyqtSlot(int)
    def on_umbilicisRightSpinBox_valueChanged(self, value):
        self.sliceWidget.umbilicisRight = self.transformX(value) if value >= 0 else None
        self.sliceWidget.updateFigure()

    @pyqtSlot(int)
    def on_umbilicisCoronalSpinBox_valueChanged(self, value):
        self.sliceWidget.umbilicisCoronal = self.transformY(value) if value >= 0 else None
        self.sliceWidget.updateFigure()

    @pyqtSlot()
    def on_homeButton_clicked(self):
        self.sliceWidget.toolbar.home()

    @pyqtSlot()
    def on_panButton_clicked(self):
        self.sliceWidget.toolbar.pan()

    @pyqtSlot()
    def on_zoomButton_clicked(self):
        self.sliceWidget.toolbar.zoom()

    @pyqtSlot()
    def on_saveButton_clicked(self):
        self.config['diaphragmAxial'] = self.diaphragmAxialSpinBox.value()

        self.config['umbilicis'] = {
            'inferior': self.umbilicisInferiorSpinBox.value(),
            'superior': self.umbilicisSuperiorSpinBox.value(),
            'left': self.umbilicisLeftSpinBox.value(),
            'right': self.umbilicisRightSpinBox.value(),
            'coronal': self.umbilicisCoronalSpinBox.value()
        }

        leftArmBoundsDict = [{
            'firstPoint': (x[0], x[1]),
            'secondPoint': (x[2], x[3]),
            'axialPosition': x[4]
        } for x in self.leftArmBounds]

        rightArmBoundsDict = [{
            'firstPoint': (x[0], x[1]),
            'secondPoint': (x[2], x[3]),
            'axialPosition': x[4]
        } for x in self.rightArmBounds]

        self.config['armBounds'] = {
            'leftArm': leftArmBoundsDict,
            'rightArm': rightArmBoundsDict
        }

        configFilename = os.path.join(self.dataPath, 'config.yml')
        with open(configFilename, 'w') as fh:
            yaml.dump(self.config, fh, default_flow_style=False)

        self.accept()

    def transformEvent(self, event):
        # DICOM uses LPS coordinate system which is converted to RAS in sliceWidget
        # We need to convert the X/Y coordinates back to LPS
        if event.inaxes:
            event.xdata = self.fatImage.shape[2] - event.xdata
            event.ydata = self.fatImage.shape[1] - event.ydata

    def transformX(self, x):
        return self.fatImage.shape[2] - x

    def transformY(self, y):
        return self.fatImage.shape[1] - y

    def on_sliceWidget_mouseMoved(self, event):
        self.transformEvent(event)

        # When the mouse is moved, update the location label
        if self.locationLabel is not None and event.inaxes:
            x, y, z = event.xdata, event.ydata, self.sliceWidget.sliceNumber
        else:
            x, y, z = 0, 0, self.sliceWidget.sliceNumber

        self.locationLabel.setText('(%i, %i, %i)' % (x, y, z))

    def on_sliceWidget_keyPressed(self, event):
        self.transformEvent(event)

        if event.key == 'left':
            value = self.sliceSlider.value() - 1

            if value < 0:
                value = self.fatImage.shape[0] - 1

            self.sliceSlider.setValue(value)
        elif event.key == 'right':
            value = self.sliceSlider.value() + 1

            if value >= self.fatImage.shape[0]:
                value = 0

            self.sliceSlider.setValue(value)
        elif event.key == 'f':
            self.viewFatRadioButton.setChecked(True)
        elif event.key == 'w':
            self.viewWaterRadioButton.setChecked(True)

    def on_sliceWidget_clicked(self, event):
        self.transformEvent(event)

        if self.diaphragmRadioButton.isChecked():
            self.diaphragmAxialSpinBox.setValue(self.sliceWidget.sliceNumber)

            # Set the none editing radio button so that clicking does nothing now
            self.noneRadioButton.setChecked(True)
        elif self.umbilicisRadioButton.isChecked():
            # If not clicking inside the image, then do nothing
            if not event.inaxes:
                return

            # State machine, click first/second point of umbilicus line and then select start/stop axial slices
            if self.clickState == 0:
                # Append the x/y data. Saves this information when all the points are selected
                self.clickData.append((event.xdata, event.ydata))

                # Update click state and the text
                self.infoLabel.setText('Click second point of umbilicis line')
                self.clickState += 1
            elif self.clickState == 1:
                # Append the x/y data. Saves this information when all the points are selected
                self.clickData.append((event.xdata, event.ydata))

                # Update click state and the text
                self.infoLabel.setText('Click inferior (bottom-most) slice you want umbilicis line to start at')
                self.clickState += 1
            elif self.clickState == 2:
                # Append the x/y data. Saves this information when all the points are selected
                self.clickData.append(self.sliceWidget.sliceNumber)

                # Update click state and the text
                self.infoLabel.setText('Click superior (top-most) slice you want umbilicis line to stop at')
                self.clickState += 1
            elif self.clickState == 3:
                # Append the x/y data. Saves this information when all the points are selected
                self.clickData.append(self.sliceWidget.sliceNumber)

                # All the data is retrieved, now set the values
                # Get the x/y coordinates of first two points clicked
                x1, y1 = self.clickData[0]
                x2, y2 = self.clickData[1]

                # Left point is the smaller of the two points and right is the other one
                # Coronal Y is the average of the two points (two Y's should be about the same)
                leftX, rightX = (x1, x2) if x1 < x2 else (x2, x1)
                coronalY = int((y1 + y2) / 2)

                # Set the spinbox values
                self.umbilicisLeftSpinBox.setValue(int(leftX))
                self.umbilicisRightSpinBox.setValue(int(rightX))
                self.umbilicisCoronalSpinBox.setValue(coronalY)
                self.umbilicisInferiorSpinBox.setValue(self.clickData[2])
                self.umbilicisSuperiorSpinBox.setValue(self.clickData[3])

                # Set the none editing radio button so that clicking does nothing now
                self.noneRadioButton.setChecked(True)
        elif self.armBoundsRadioButton.isChecked():
            # If not clicking inside the image, then do nothing
            if not event.inaxes:
                return

            # State machine:
            # First click first/second point of line for left arm, then first/second point of right arm
            if self.clickState == 0:
                # Append the x/y data. Saves this information when all the points are selected
                self.clickData.extend([int(event.xdata), int(event.ydata)])

                # Update click state and the text
                self.infoLabel.setText('Click on second point of line for left arm')
                self.clickState += 1
            elif self.clickState == 1:
                # Append the x/y data. Saves this information when all the points are selected
                self.clickData.extend([int(event.xdata), int(event.ydata)])

                # Update click state and the text
                self.infoLabel.setText('Click on first point of line for right arm')
                self.clickState += 1
            elif self.clickState == 2:
                # Append the x/y data. Saves this information when all the points are selected
                self.clickData.extend([int(event.xdata), int(event.ydata)])

                # Update click state and the text
                self.infoLabel.setText('Click on second point of line for right arm')
                self.clickState += 1
            elif self.clickState == 3:
                # Append the x/y data. Saves this information when all the points are selected
                self.clickData.extend([int(event.xdata), int(event.ydata)])

                # Remove any arm bound entries on the same slice as this one
                self.leftArmBounds = list(filter(lambda x: x[4] != self.sliceWidget.sliceNumber, self.leftArmBounds))
                self.rightArmBounds = list(filter(lambda x: x[4] != self.sliceWidget.sliceNumber, self.rightArmBounds))

                # Append new left/right arm bounds
                self.leftArmBounds.append((self.clickData[0], self.clickData[1], self.clickData[2], self.clickData[3],
                                           self.sliceWidget.sliceNumber))
                self.rightArmBounds.append((self.clickData[4], self.clickData[5], self.clickData[6], self.clickData[7],
                                            self.sliceWidget.sliceNumber))

                # Update arm bounds and the slice widget
                self.updateArmBounds()

                # Update click state and the text
                self.infoLabel.setText('Click on first point of line for left arm')
                self.clickState = 0
                self.clickData = []

    def updateArmBounds(self):
        # Sort the left/right arm bounds by the slice number (last entry in tuple)
        self.leftArmBounds.sort(key=lambda x: x[4])
        self.rightArmBounds.sort(key=lambda x: x[4])

        # Set the slice widget bounds to the new ones but transformed from LPS coordinate system to RAS system
        self.sliceWidget.leftArmBounds = [(self.transformX(b[0]), self.transformY(b[1]),
                                           self.transformX(b[2]), self.transformY(b[3]), b[4])
                                          for b in self.leftArmBounds]
        self.sliceWidget.rightArmBounds = [(self.transformX(b[0]), self.transformY(b[1]),
                                            self.transformX(b[2]), self.transformY(b[3]), b[4])
                                           for b in self.rightArmBounds]

        # Update the figure
        self.sliceWidget.updateFigure()

    @pyqtSlot()
    def reject(self):
        self.saveSettings()
        self.done(QDialog.Rejected)

    @pyqtSlot()
    def accept(self):
        self.saveSettings()
        self.done(QDialog.Accepted)
