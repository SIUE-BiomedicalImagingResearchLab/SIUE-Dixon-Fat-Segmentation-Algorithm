import os.path
from pathlib import Path

import nibabel as nib
import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from lxml import etree
from configureWindow import ConfigureWindow

import constants
import mainWindow_ui
from runSegmentation import runSegmentation


class MainWindow(QMainWindow, mainWindow_ui.Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        self.sourceModel = QStandardItemModel(self.sourceListView)
        self.sourceListView.setModel(self.sourceModel)

    @pyqtSlot()
    def on_browseSourceButton_clicked(self):
        # Read settings file
        settings = QSettings()

        # Get the default open path when starting the file dialog, default is the user's home directory
        defaultOpenPath = settings.value('defaultOpenPath', str(Path.home()))

        w = QFileDialog(self)
        w.setFileMode(QFileDialog.DirectoryOnly)
        w.setWindowTitle('Select source folders of subjects')
        w.setDirectory(defaultOpenPath)
        # Must use custom dialog if I want multiple directories to be selected
        w.setOption(QFileDialog.DontUseNativeDialog, True)

        # Custom command to allow for multiple directories to be selected
        for view in self.findChildren((QListView, QTreeView)):
            if isinstance(view.model(), QFileSystemModel):
                view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Start the dialog box and wait for input, it returns false if cancel was pressed
        if not w.exec():
            return

        # Get selected directories
        dirs = w.selectedFiles()

        # If empty, then cancel was pressed, return
        if not dirs:
            return

        # Since there were items selected, set the default open path to be the directory the user was last in
        # Save it to settings
        defaultOpenPath = w.directory().absolutePath()
        settings.setValue('defaultOpenPath', defaultOpenPath)

        # Check to make sure the directories are valid
        # Note: Don't use dir as variable name because it shadows built-in variable
        error = False
        for dir_ in dirs:
            if os.path.isdir(dir_):
                self.sourceModel.appendRow(QStandardItem(dir_))
            else:
                error = True

        # If an error occurred, tell the user that the directory was not added
        if error:
            QMessageBox.critical(self, "Invalid directory",
                                 "One of the directories you chose was invalid. It was not added to the list")

    @pyqtSlot()
    def on_runButton_clicked(self):
        # If there are no source files, then return
        if self.sourceModel.rowCount() is 0:
            QMessageBox.warning(self, "No source directories",
                                "There are no source directories in the list currently. Please add some folders "
                                "before converting.")
            return

        for i in range(self.sourceModel.rowCount()):
            dataPath = self.sourceModel.item(i).text()

            print('Beginning segmentation for ' + dataPath)

            fatImage, waterImage, config = self.loadFile(dataPath)
            if fatImage is None:
                continue

            # Set constant pathDir to be the current data path to allow writing/reading from the current directory
            constants.pathDir = dataPath

            # Run segmentation algorithm
            runSegmentation(fatImage, waterImage, config)

        print('Segmentation complete!')

    @pyqtSlot()
    def on_configureButton_clicked(self):
        selectedIndices = self.sourceListView.selectedIndexes()

        if self.sourceModel.rowCount() is 0:
            QMessageBox.warning(self, "No source directories",
                                "There are no source directories in the list currently. Please add some folders "
                                "before converting.")
            return
        elif len(selectedIndices) == 0:
            QMessageBox.warning(self, "No selected source directories",
                                "There are no source directories selected currently. Please select one.")
            return
        elif len(selectedIndices) != 1:
            QMessageBox.warning(self, "Multiple selected directories",
                                "There are currently more than one directories selected to configure. "
                                "Please select only one.")
            return

        # Get selected index text
        dataPath = self.sourceModel.itemFromIndex(selectedIndices[0]).text()

        dataPath = selectedIndices[0].data()

        # Load data from path
        fatImage, waterImage, config = self.loadFile(dataPath)
        if fatImage is None:
            return

        self.configureWindow = ConfigureWindow(fatImage, waterImage, config, dataPath, parent=self)
        self.configureWindow.show()

    def loadFile(self, dataPath):
        # Get the filenames for the rectified NIFTI files for current dataPath
        niiFatUpperFilename = os.path.join(dataPath, 'fatUpper.nii')
        niiFatLowerFilename = os.path.join(dataPath, 'fatLower.nii')
        niiWaterUpperFilename = os.path.join(dataPath, 'waterUpper.nii')
        niiWaterLowerFilename = os.path.join(dataPath, 'waterLower.nii')
        configFilename = os.path.join(dataPath, 'config.xml')

        if not (os.path.isfile(niiFatUpperFilename) and os.path.isfile(niiFatLowerFilename) and os.path.isfile(
                niiWaterUpperFilename) and os.path.isfile(niiWaterLowerFilename) and os.path.isfile(
            configFilename)):
            print('Missing required files from source path folder. Continuing...')
            return None, None, None

        # TODO Check for forceSegmentation

        # Load unrectified NIFTI files for the current dataPath
        niiFatUpper = nib.load(niiFatUpperFilename)
        niiFatLower = nib.load(niiFatLowerFilename)
        niiWaterUpper = nib.load(niiWaterUpperFilename)
        niiWaterLower = nib.load(niiWaterLowerFilename)

        # Load config XML file
        config = etree.parse(configFilename)

        # Get the root of the config XML file
        configRoot = config.getroot()

        # Piece together upper and lower images for fat and water
        # Retrieve the inferior and superior axial slice from config file for upper and lower images
        imageUpperTag = configRoot.find('imageUpper')
        imageLowerTag = configRoot.find('imageLower')
        imageUpperInferiorSlice = int(imageUpperTag.attrib['inferiorSlice'])
        imageUpperSuperiorSlice = int(imageUpperTag.attrib['superiorSlice'])
        imageLowerInferiorSlice = int(imageLowerTag.attrib['inferiorSlice'])
        imageLowerSuperiorSlice = int(imageLowerTag.attrib['superiorSlice'])

        # Use inferior and superior axial slice to obtain the valid portion of the upper and lower fat and water images
        fatUpperImage = niiFatUpper.get_data()[:, :, imageUpperInferiorSlice:imageUpperSuperiorSlice]
        fatLowerImage = niiFatLower.get_data()[:, :, imageLowerInferiorSlice:imageLowerSuperiorSlice]
        waterUpperImage = niiWaterUpper.get_data()[:, :, imageUpperInferiorSlice:imageUpperSuperiorSlice]
        waterLowerImage = niiWaterLower.get_data()[:, :, imageLowerInferiorSlice:imageLowerSuperiorSlice]

        # Concatenate the lower and upper image into one along the Z dimension
        # TODO Consider removing this and performing segmentation on upper/lower pieces separately
        fatImage = np.concatenate((fatLowerImage, fatUpperImage), axis=2)
        waterImage = np.concatenate((waterLowerImage, waterUpperImage), axis=2)

        # Normalize the fat/water images so that the intensities are between (0.0, 1.0)
        fatImage = (fatImage - fatImage.min()) / (fatImage.max() - fatImage.min())
        waterImage = (waterImage - waterImage.min()) / (waterImage.max() - waterImage.min())

        return fatImage, waterImage, config
