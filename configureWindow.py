import os
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from lxml import etree

import configureWindow_ui


class ConfigureWindow(QMainWindow, configureWindow_ui.Ui_ConfigureWindow):
    def __init__(self, fatImage, waterImage, config, dataPath, parent=None):
        super(ConfigureWindow, self).__init__(parent)
        self.setupUi(self)

        self.fatImage = fatImage
        self.waterImage = waterImage
        self.config = config
        self.dataPath = dataPath

        self.locationLabel = QLabel("(0, 0, 0)")
        self.statusbar.addWidget(self.locationLabel)
        self.sliceWidget.locationLabel = self.locationLabel

        self.setupDefaults()

        self.sliceWidget.updateFigure()

    def setupDefaults(self):
        # Get the root of the config XML file
        configRoot = self.config.getroot()

        self.sliceSlider.setValue(self.sliceWidget.sliceNumber)
        self.sliceSlider.setMaximum(self.fatImage.shape[2] - 1)

        self.viewFatRadioButton.setChecked(True)
        self.sliceWidget.image = self.fatImage
        self.noneRadioButton.setChecked(True)

        diaphragmTag = configRoot.find('diaphragm')
        self.diaphragmAxialSpinBox.setMaximum(self.fatImage.shape[2] - 1)
        if diaphragmTag is not None and diaphragmTag.attrib['superiorSlice'] is not None:
            self.diaphragmAxialSpinBox.setValue(int(configRoot.find('diaphragm').attrib['superiorSlice']))
        self.sliceWidget.diaphragmAxial = self.diaphragmAxialSpinBox.value()

        umbilicisTag = configRoot.find('umbilicis')
        if umbilicisTag is not None:
            self.umbilicisInferiorSpinBox.setValue(int(umbilicisTag.attrib['inferiorSlice']))
            self.umbilicisSuperiorSpinBox.setValue(int(umbilicisTag.attrib['superiorSlice']))
            self.umbilicisLeftSpinBox.setValue(int(umbilicisTag.attrib['left']))
            self.umbilicisRightSpinBox.setValue(int(umbilicisTag.attrib['right']))
            self.umbilicisCoronalSpinBox.setValue(int(umbilicisTag.attrib['coronal']))

        self.umbilicisInferiorSpinBox.setMaximum(self.fatImage.shape[2] - 1)
        self.umbilicisSuperiorSpinBox.setMaximum(self.fatImage.shape[2] - 1)
        self.umbilicisLeftSpinBox.setMaximum(self.fatImage.shape[0] - 1)
        self.umbilicisRightSpinBox.setMaximum(self.fatImage.shape[0] - 1)
        self.umbilicisCoronalSpinBox.setMaximum(self.fatImage.shape[1] - 1)
        self.sliceWidget.umbilicisInferior = self.umbilicisInferiorSpinBox.value()
        self.sliceWidget.umbilicisSuperior = self.umbilicisSuperiorSpinBox.value()
        self.sliceWidget.umbilicisLeft = self.umbilicisLeftSpinBox.value()
        self.sliceWidget.umbilicisRight = self.umbilicisRightSpinBox.value()
        self.sliceWidget.umbilicisCoronal = self.umbilicisCoronalSpinBox.value()

        CATTag = configRoot.find('CAT')
        self.CATLine = []
        if CATTag is not None:
            for line in CATTag:
                if line.tag != 'line':
                    print('Invalid tag for CAT, must be line')
                    continue

                self.CATLine.append([int(line.attrib['axial']), int(line.attrib['posterior']),
                                     int(line.attrib['anterior'])])

            # Sort the three arrays based on CAT axial, ascending
            self.CATLine.sort()
            self.updateCATPointsTable()
            self.sliceWidget.CATLine = self.CATLine

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

    @pyqtSlot(int)
    def on_sliceSlider_valueChanged(self, value):
        self.sliceWidget.sliceNumber = value
        self.locationLabel.setText("(%i, %i, %i)" % (0, 0, value))
        self.sliceWidget.updateFigure()

    @pyqtSlot(int)
    def on_diaphragmAxialSpinBox_valueChanged(self, value):
        self.sliceWidget.diaphragmAxial = value
        self.sliceWidget.updateFigure()

    @pyqtSlot(int)
    def on_umbilicisInferiorSpinBox_valueChanged(self, value):
        self.sliceWidget.umbilicisInferior = value
        self.sliceWidget.updateFigure()

    @pyqtSlot(int)
    def on_umbilicisSuperiorSpinBox_valueChanged(self, value):
        self.sliceWidget.umbilicisSuperior = value
        self.sliceWidget.updateFigure()

    @pyqtSlot(int)
    def on_umbilicisLeftSpinBox_valueChanged(self, value):
        self.sliceWidget.umbilicisLeft = value
        self.sliceWidget.updateFigure()

    @pyqtSlot(int)
    def on_umbilicisRightSpinBox_valueChanged(self, value):
        self.sliceWidget.umbilicisRight = value
        self.sliceWidget.updateFigure()

    @pyqtSlot(int)
    def on_umbilicisCoronalSpinBox_valueChanged(self, value):
        self.sliceWidget.umbilicisCoronal = value
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

        self.updateCATPointsTable()
        self.sliceWidget.CATLine = self.CATLine
        self.sliceWidget.updateFigure()

    @pyqtSlot()
    def on_CATBoundsAddButton_clicked(self):
        self.CATLine.append([-1, -1, -1])
        self.CATLine.sort()
        self.updateCATPointsTable()

        self.sliceWidget.CATLine = self.CATLine
        self.sliceWidget.updateFigure()

    @pyqtSlot(QTableWidgetItem)
    def on_CATBoundsTableWidget_itemChanged(self, item):
        self.CATLine[item.row()][item.column()] = int(item.text())
        self.CATLine.sort()
        self.updateCATPointsTable()

        self.sliceWidget.CATLine = self.CATLine
        self.sliceWidget.updateFigure()

    @pyqtSlot()
    def on_saveButton_clicked(self):
        configRoot = self.config.getroot()

        diaphragmTag = configRoot.find('diaphragm')
        if diaphragmTag is not None:
            diaphragmTag.attrib['superiorSlice'] = str(self.diaphragmAxialSpinBox.value())
        else:
            etree.SubElement(configRoot, 'diaphragm', superiorSlice=str(self.diaphragmAxialSpinBox.value()))

        umbilicisTag = configRoot.find('umbilicis')
        if umbilicisTag is not None:
            umbilicisTag.attrib['inferiorSlice'] = str(self.umbilicisInferiorSpinBox.value())
            umbilicisTag.attrib['superiorSlice'] = str(self.umbilicisSuperiorSpinBox.value())
            umbilicisTag.attrib['left'] = str(self.umbilicisLeftSpinBox.value())
            umbilicisTag.attrib['right'] = str(self.umbilicisRightSpinBox.value())
            umbilicisTag.attrib['coronal'] = str(self.umbilicisCoronalSpinBox.value())
        else:
            etree.SubElement(configRoot, 'umbilicis', inferiorSlice=str(self.umbilicisInferiorSpinBox.value()),
                             superiorSlice=str(self.umbilicisSuperiorSpinBox.value()),
                             left=str(self.umbilicisLeftSpinBox.value()),
                             right=str(self.umbilicisRightSpinBox.value()),
                             coronal=str(self.umbilicisCoronalSpinBox.value()))

        CATTag = configRoot.find('CAT')
        if CATTag is not None:
            for line in CATTag:
                CATTag.remove(line)

            i = 4
        else:
            CATTag = etree.SubElement(configRoot, 'CAT')

        for line in self.CATLine:
            etree.SubElement(CATTag, 'line', axial=str(line[0]), posterior=str(line[1]), anterior=str(line[2]))

        configFilename = os.path.join(self.dataPath, 'config.xml')
        # self.config.write('D:\\Users\\addis\\Desktop\\test.xml')
        self.config.write(configFilename, pretty_print=True)
        self.statusbar.showMessage('Saved to config file')
