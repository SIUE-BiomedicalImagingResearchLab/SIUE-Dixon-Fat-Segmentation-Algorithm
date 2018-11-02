import os
import traceback

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from core.loadData import loadData, updateCachedData
from core.runSegmentation import runSegmentation
from generated import mainWindow_ui
from gui.configureWindow_TexasTechDixon import ConfigureWindow as ConfigureWindowTexasTechDixon
from util import constants
from util.enums import ScanFormat
from util.fileDialog import FileDialog


class MainWindow(QMainWindow, mainWindow_ui.Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        self.sourceModel = QStandardItemModel(self.sourceListView)
        self.sourceListView.setModel(self.sourceModel)

        # Load the combo box with the data types defined in ScanFormat enumeration
        self.dataTypeComboBox.addItems([str(item) for item in ScanFormat])

        self.loadSettings()

    def loadSettings(self):
        settings = QSettings(constants.applicationName, constants.organizationName)
        settings.beginGroup('mainWindow')

        geometry = settings.value('geometry', QByteArray(), type=QByteArray)
        if not geometry.isEmpty():
            self.restoreGeometry(geometry)

            # Fixes QTBUG-46620 issue
            if settings.value('maximized', False, type=bool):
                self.showMaximized()
                self.setGeometry(QApplication.desktop().availableGeometry(self))

        self.defaultOpenPath = settings.value('defaultOpenPath', QDir.homePath())

        settings.endGroup()

    def saveSettings(self):
        settings = QSettings(constants.applicationName, constants.organizationName)
        settings.beginGroup('mainWindow')

        settings.setValue('geometry', self.saveGeometry())
        settings.setValue('maximized', self.isMaximized())
        settings.setValue('defaultOpenPath', self.defaultOpenPath)

        settings.endGroup()

    @pyqtSlot()
    def on_browseSourceButton_clicked(self):
        directories = FileDialog.getExistingDirectories(self, 'Select source folders of subjects', self.defaultOpenPath)

        # Nothing was selected
        if not directories:
            return

        # Save the last directory used
        self.defaultOpenPath = os.path.dirname(directories[0])

        # Check each of the directories and make sure they are valid
        # Skip adding that row if it isn't valid
        hasError = False
        for directory in directories:
            if not os.path.isdir(directory):
                hasError = True
                continue

            self.sourceModel.appendRow(QStandardItem(directory))

        # If this is the first set of items added to the list, select the first item
        if self.sourceModel.rowCount() > 0 and not self.sourceListView.currentIndex().isValid():
            self.sourceListView.setCurrentIndex(self.sourceModel.index(0, 0))
            self.sourceListView.setFocus()

        # If an error occurred, tell the user that the directory was not added
        if hasError:
            QMessageBox.critical(self, 'Invalid directory',
                                 'One of the directories you chose was invalid. It was not added to the list')

    @pyqtSlot()
    def on_runButton_clicked(self):
        # If there are no source files, then return
        if self.sourceModel.rowCount() is 0:
            QMessageBox.warning(self, 'No source directories', 'There are no source directories in the list currently.'
                                                               'Please add some folders before converting.')
            return

        # Get the scan format
        format = ScanFormat(self.dataTypeComboBox.currentIndex())

        # Loop through each row in the list view
        for i in range(self.sourceModel.rowCount()):
            # Get the data path for the row
            dataPath = self.sourceModel.item(i).text()

            print('Beginning segmentation for %s' % dataPath)

            # Attempt to load the data from the data path
            try:
                data = loadData(dataPath, format)
            except Exception:
                print('Unable to load data from %s. Skipping...' % dataPath)
                print(traceback.format_exc())
                continue

            # Set constant pathDir to be the current data path to allow writing/reading from the current directory
            constants.pathDir = dataPath

            # Run segmentation algorithm
            try:
                runSegmentation(data, format)
                pass
            except Exception:
                print('Unable to run segmentation algorithm on %s. Skipping...' % dataPath)
                print(traceback.format_exc())
                continue

        print('Segmentation complete!')

    @pyqtSlot()
    def on_configureButton_clicked(self):
        selectedIndices = self.sourceListView.selectedIndexes()

        if self.sourceModel.rowCount() is 0:
            QMessageBox.warning(self, 'No source directories', 'There are no source directories in the list currently. '
                                                               'Please add some folders before converting.')
            return
        elif len(selectedIndices) == 0:
            QMessageBox.warning(self, 'No selected source directories', 'There are no source directories selected '
                                                                        'currently. Please select one.')
            return
        elif len(selectedIndices) != 1:
            QMessageBox.warning(self, 'Multiple selected directories', 'There are currently more than one directories '
                                                                       'selected to configure. Please select only one.')
            return

        # Get the scan format
        format = ScanFormat(self.dataTypeComboBox.currentIndex())

        # Get selected index text
        dataPath = selectedIndices[0].data()

        # Attempt to load the data from the data path
        try:
            data = loadData(dataPath, format)
        except Exception:
            print('Unable to load data from %s. Skipping...' % dataPath)
            print(traceback.format_exc())
            return

        if format == ScanFormat.TexasTechDixon:
            configureWindow = ConfigureWindowTexasTechDixon(data, dataPath, parent=self)
            configureWindow.exec()
        elif format == ScanFormat.WashUUnknown:
            raise NotImplementedError()
        elif format == ScanFormat.WashUDixon:
            raise NotImplementedError()
        else:
            raise ValueError('Format must be a valid ScanFormat option')

        # Update the cached data
        updateCachedData(dataPath, configureWindow.getData())

    def loadData(self, dataPath, format):
        try:
            # Load data from cache if available
            data = self.data.get(dataPath)
            if not data:
                data = loadData(dataPath, format)

                # Cache the data for later
                self.data[dataPath] = data

            return data
        except Exception:
            print('Unable to load data from %s. Skipping...' % dataPath)
            print(traceback.format_exc())
            return None

    @pyqtSlot()
    def closeEvent(self, closeEvent):
        # Save settings when the window is closed
        self.saveSettings()
