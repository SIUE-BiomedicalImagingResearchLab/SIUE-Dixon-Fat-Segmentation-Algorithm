import os.path
from pathlib import Path

import nibabel as nib
import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from lxml import etree
from configureWindow import ConfigureWindow
import skimage.exposure
import dicom2
import nrrd
import logging

import constants
import mainWindow_ui
from runSegmentation import runSegmentation


class MainWindow(QMainWindow, mainWindow_ui.Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        self.sourceModel = QStandardItemModel(self.sourceListView)
        self.sourceListView.setModel(self.sourceModel)

        self.t1Series = []


    @pyqtSlot()
    def on_browseSourceButton_clicked(self):

        pass
        # # Read settings file
        # settings = QSettings()
        #
        # # Get the default open path when starting the file dialog, default is the user's home directory
        # defaultOpenPath = settings.value('defaultOpenPath', str(Path.home()))
        #
        # w = QFileDialog(self)
        # w.setFileMode(QFileDialog.DirectoryOnly)
        # w.setWindowTitle('Select source folders of subjects')
        # w.setDirectory(defaultOpenPath)
        # # Must use custom dialog if I want multiple directories to be selected
        # w.setOption(QFileDialog.DontUseNativeDialog, True)
        #
        # # Custom command to allow for multiple directories to be selected
        # for view in self.findChildren((QListView, QTreeView)):
        #     if isinstance(view.model(), QFileSystemModel):
        #         view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        #
        # # Start the dialog box and wait for input, it returns false if cancel was pressed
        # if not w.exec():
        #     return
        #
        # # Get selected directories
        # dirs = w.selectedFiles()
        #
        # # If empty, then cancel was pressed, return
        # if not dirs:
        #     return
        #
        # # Since there were items selected, set the default open path to be the directory the user was last in
        # # Save it to settings
        # defaultOpenPath = w.directory().absolutePath()
        # settings.setValue('defaultOpenPath', defaultOpenPath)
        #
        # # Check to make sure the directories are valid
        # # Note: Don't use dir as variable name because it shadows built-in variable
        # error = False
        # for dir_ in dirs:
        #     if os.path.isdir(dir_):
        #         self.sourceModel.appendRow(QStandardItem(dir_))
        #     else:
        #         error = True
        #
        # # If an error occurred, tell the user that the directory was not added
        # if error:
        #     QMessageBox.critical(self, "Invalid directory",
        #                          "One of the directories you chose was invalid. It was not added to the list")

    @pyqtSlot()
    def on_runButton_clicked(self):
        # If there are no source files, then return
        # if self.sourceModel.rowCount() is 0:
        #     QMessageBox.warning(self, "No source directories",
        #                         "There are no source directories in the list currently. Please add some folders "
        #                         "before converting.")
        #     return

        dataPath = "C:/Users/Clint/PycharmProjects/SIUE-Dixon-Fat-Segmentation-Algorithm/MRI_Data/MF0302-PRE/"


        print('Beginning segmentation for ' + dataPath)

        #fatImage, waterImage, config = self.loadFile(dataPath)
        image, config = self.loadFile(dataPath)
        if image is None:
            print("No image")
            return

        # Set constant pathDir to be the current data path to allow writing/reading from the current directory
        constants.pathDir = dataPath

        # Run segmentation algorithm
        runSegmentation(image, config)

        print('Segmentation complete!')

    @pyqtSlot()
    def on_configureButton_clicked(self):
        #selectedIndices = self.sourceListView.selectedIndexes()

        # if self.sourceModel.rowCount() is 0:
        #     QMessageBox.warning(self, "No source directories",
        #                         "There are no source directories in the list currently. Please add some folders "
        #                         "before converting.")
        #     return
        # elif len(selectedIndices) == 0:
        #     QMessageBox.warning(self, "No selected source directories",
        #                         "There are no source directories selected currently. Please select one.")
        #     return
        # elif len(selectedIndices) != 1:
        #     QMessageBox.warning(self, "Multiple selected directories",
        #                         "There are currently more than one directories selected to configure. "
        #                         "Please select only one.")
        #     return

        # Get selected index text
        #dataPath = selectedIndices[0].data()
        dataPath = "C:/Users/Clint/PycharmProjects/SIUE-Dixon-Fat-Segmentation-Algorithm/MRI_Data/MF0302-PRE/"

        # Load data from path
        image, config = self.loadFile(dataPath)
        if image is None:
            return

        self.configureWindow = ConfigureWindow(image, config, dataPath, parent=self)
        self.configureWindow.show()

    def loadFile(self, dataPath):
        dicomDir = dataPath + "SCANS"
        print(dicomDir)
        # Load DICOM directory and organize by patients, studies, and series
        patients = dicom2.loadDirectory(dicomDir)
        # Should only be one patient so retrieve it
        patient = patients.only()
        # Should only be one study so retrieve the one study
        study = patient.only()
        #
        self.t1Series = []
        for UID, series in study.items():
            if series.Description.startswith('t1_'):
                self.t1Series.append(series)

        # Sort cine images by the series number, looks nicer
        self.t1Series.sort(key=lambda x: x.Number)

        # Loop through each t1 series
        for series in self.t1Series:
            seriesNumber = 21001
            sliceIndex = -1

            sortedSeries, _, _ = dicom2.sortSlices(series, dicom2.MethodType.Unknown)
            if sliceIndex < 0:
                continue
            elif sliceIndex >= len(sortedSeries):
                QMessageBox.critical(self, 'Invalid slice index', 'Invalid slice index given for series number %i'
                                     % seriesNumber)
                return

            print("Slices Sorted")

        (method, type_, space, orientation, spacing, origin, volume) = \
            dicom2.combineSlices(sortedSeries, method=dicom2.MethodType.Unknown)

        nrrdHeaderDict = {'space': space, 'space origin': origin,
                          'space directions': (np.identity(3) * np.array(spacing)).tolist()}
        nrrd.write("C:/Users/Clint/PycharmProjects/SIUE-Dixon-Fat-Segmentation-Algorithm/MRI_Data_Nrrd_Output/newOut.nrrd", volume, nrrdHeaderDict)
        constants.nrrdHeaderDict = {'space': 'right-anterior-superior'}

        configFilename = os.path.join(dataPath, 'config.xml')

        if not os.path.isfile(configFilename):
            print('Missing required files from source path folder. Continuing...')
            return None, None, None
        # Load config XML file
        config = etree.parse(configFilename)

        # Get the root of the config XML file
        configRoot = config.getroot()

        return volume, config