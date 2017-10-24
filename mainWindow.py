import os.path
from pathlib import Path

import nibabel as nib
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from lxml import etree

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
                continue

            # TODO Check for forceSegmentation

            # Load unrectified NIFTI files for the current dataPath
            niiFatUpper = nib.load(niiFatUpperFilename)
            niiFatLower = nib.load(niiFatLowerFilename)
            niiWaterUpper = nib.load(niiWaterUpperFilename)
            niiWaterLower = nib.load(niiWaterLowerFilename)

            # Load config XML file
            config = etree.parse(configFilename)

            # Set constant pathDir to be the current data path to allow writing/reading from the current directory
            constants.pathDir = dataPath

            # Run segmentation algorithm
            runSegmentation(niiFatUpper, niiFatLower, niiWaterUpper, niiWaterLower, config)

        print('Segmentation complete!')
