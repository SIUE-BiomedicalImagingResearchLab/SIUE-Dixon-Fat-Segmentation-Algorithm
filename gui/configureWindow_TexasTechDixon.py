import os

import yaml
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from generated import configureWindow_TexasTechDixon_ui
from util import constants


class ConfigureWindow(QDialog, configureWindow_TexasTechDixon_ui.Ui_ConfigureWindow):
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

        self.sliceWidget.isLAS = True
        self.sliceWidget.updateFigure()

    def loadSettings(self):
        settings = QSettings(constants.applicationName, constants.organizationName)
        settings.beginGroup('configureWindow_TexasTechDixon')

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
        settings.beginGroup('configureWindow_TexasTechDixon')

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

        self.umbilicisInferiorSpinBox.setMaximum(self.fatImage.shape[0] - 1)
        self.umbilicisSuperiorSpinBox.setMaximum(self.fatImage.shape[0] - 1)
        self.umbilicisLeftSpinBox.setMaximum(self.fatImage.shape[2] - 1)
        self.umbilicisRightSpinBox.setMaximum(self.fatImage.shape[2] - 1)
        self.umbilicisCoronalSpinBox.setMaximum(self.fatImage.shape[1] - 1)
        self.diaphragmAxialSpinBox.setMaximum(self.fatImage.shape[0] - 1)

        CATBounds = self.config.get('CATBounds')
        if CATBounds:
            self.CATLine = [(x['axial'], x['posterior'], x['anterior']) for x in CATBounds]
            self.CATLine.sort()
            self.updateCATPointsTable()
            self.sliceWidget.CATLine = self.CATLine
        else:
            self.CATLine = []

    def getData(self):
        return self.fatImage, self.waterImage, self.config

    def updateCATBounds(self):
        # Sort bounds by axial position
        self.CATLine.sort()

        self.updateCATPointsTable()

        # Set appropriate slice widget CATLine (transform coordinates) and update figure
        self.sliceWidget.CATLine = [(x[0], self.transformY(x[1]), self.transformY(x[2])) for x in self.CATLine]
        self.sliceWidget.updateFigure()

    def updateCATPointsTable(self):
        self.CATBoundsTableWidget.blockSignals(True)

        self.CATBoundsTableWidget.setRowCount(len(self.CATLine))
        for i, line in zip(range(0, len(self.CATLine)), self.CATLine):
            self.CATBoundsTableWidget.setItem(i, 0, QTableWidgetItem(str(line[0])))
            self.CATBoundsTableWidget.setItem(i, 1, QTableWidgetItem(str(line[1])))
            self.CATBoundsTableWidget.setItem(i, 2, QTableWidgetItem(str(line[2])))

        self.CATBoundsTableWidget.blockSignals(False)

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
    def on_CATBoundsRadioButton_toggled(self, checked):
        if not checked:
            return

        self.infoLabel.setText('Click first point of CAT bounds')
        self.clickState = 0
        self.clickData = []

    @pyqtSlot(int)
    def on_sliceSlider_valueChanged(self, value):
        self.sliceWidget.sliceNumber = value
        self.locationLabel.setText('(%i, %i, %i)' % (0, 0, value))
        self.sliceWidget.updateFigure()

    @pyqtSlot(int)
    def on_diaphragmAxialSpinBox_valueChanged(self, value):
        self.sliceWidget.diaphragmAxial = value
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
    def on_CATBoundsRemoveButton_clicked(self):
        selectedIndices = self.CATBoundsTableWidget.selectedIndexes()
        if len(selectedIndices) < 1:
            print('Please select one row')
            return

        index = selectedIndices[0].row()
        del self.CATLine[index]

        self.updateCATBounds()

    @pyqtSlot()
    def on_CATBoundsAddButton_clicked(self):
        self.CATLine.append((-1, -1, -1))
        self.updateCATBounds()

    @pyqtSlot(QTableWidgetItem)
    def on_CATBoundsTableWidget_itemChanged(self, item):
        self.CATLine[item.row()][item.column()] = int(item.text())
        self.updateCATBounds()

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

        self.config['CATBounds'] = [{
            'axial': x[0],
            'posterior': x[1],
            'anterior': x[2]
        } for x in self.CATLine]

        configFilename = os.path.join(self.dataPath, 'config.yml')
        with open(configFilename, 'w') as fh:
            yaml.dump(self.config, fh, default_flow_style=False)

        self.accept()

    def transformEvent(self, event):
        # TTU data is in LAS coordinate system but data is in RAS
        # We need to convert the X/Y coordinates back to LAS
        if event.inaxes:
            event.xdata = self.fatImage.shape[2] - event.xdata

    def transformX(self, x):
        return self.fatImage.shape[2] - x

    def transformY(self, y):
        return y

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
        elif self.CATBoundsRadioButton.isChecked():
            # If not clicking inside the image, then do nothing
            if not event.inaxes:
                return

            # State machine, click first/second point of where CAT bounds should be
            if self.clickState == 0:
                # Append the x/y and slice data. Saves this information when all the points are selected
                self.clickData.append(event.ydata)

                # Update click state and the text
                self.infoLabel.setText('Click second point of CAT bounds')
                self.clickState += 1
            elif self.clickState == 1:
                # Append the x/y data. Saves this information when all the points are selected
                self.clickData.append(event.ydata)

                # Get the clickdata
                y1 = int(self.clickData[0])
                y2 = int(self.clickData[1])
                posteriorY, anteriorY = (y1, y2) if y1 < y2 else (y2, y1)

                # Append the new line to the list, sort the list and update the table
                self.CATLine.append((self.sliceWidget.sliceNumber, posteriorY, anteriorY))
                self.CATLine.sort()
                self.updateCATPointsTable()

                # Update the slice widget's reference to the line list and update the figure
                self.sliceWidget.CATLine = self.CATLine
                self.sliceWidget.updateFigure()

                # Update click state and the text
                self.infoLabel.setText('Click first point of CAT bounds')
                self.clickState = 0
                self.clickData = []

    @pyqtSlot()
    def reject(self):
        self.saveSettings()
        self.done(QDialog.Rejected)

    @pyqtSlot()
    def accept(self):
        self.saveSettings()
        self.done(QDialog.Accepted)
