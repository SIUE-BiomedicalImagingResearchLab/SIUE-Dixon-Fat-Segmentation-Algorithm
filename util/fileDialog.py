from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *


class FileDialogProxyModel(QIdentityProxyModel):
    def headerData(self, section, orientation, role=None):
        # Center the text in the header
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        return super().headerData(section, orientation, role)


# TODO Add recommended sidebar URLs to the non-native dialog by default
# TODO Save geometry of the native dialog by default
class FileDialog(QFileDialog):
    Directories = QFileDialog.FileMode(5)

    def __init__(self, parent=None, caption='', directory='', filter=''):
        super(FileDialog, self).__init__(parent, caption, directory, filter)

        # Search for a tree view in the dialog, indicating it a is a non-native dialog
        # Then we set the proxy model to center the text and set window icon
        if len(self.findChildren(QTreeView)) != 0:
            self.setProxyModel(FileDialogProxyModel())

            # Set the window icon for non-native file dialogs
            self.setWindowIcon(QIcon(':/images/heart-48.png'))

            # Make the tool button icons larger
            hboxLayout = self.findChild(QHBoxLayout, 'hboxLayout')

            for button in self.findChildren(QToolButton):
                button.setIconSize(QSize(25, 25))
                button.setMinimumSize(QSize(25, 25))
                hboxLayout.setAlignment(button, Qt.AlignVCenter)

        self._selectMultipleDirectories = False

    def setOptions(self, options):
        super().setOptions(options)

        if options & QFileDialog.DontUseNativeDialog:
            # Set proxy model to center the text in header sections
            self.setProxyModel(FileDialogProxyModel())

            # Set the window icon for non-native file dialogs
            self.setWindowIcon(QIcon(':/images/heart-48.png'))

    def setFileMode(self, mode):
        if mode == FileDialog.Directories and not self.isNative():
            # Error will be thrown for unknown mode, so set it to directory and set an internal flag in this class
            mode = FileDialog.DirectoryOnly
            self._selectMultipleDirectories = True

            # Set the file mode
            super().setFileMode(mode)

            # Overwrite the selection mode used by tree view and list view to extended selection
            # Search for the tree view and list view and set to extended selection
            for view in self.findChildren((QListView, QTreeView)):
                view.setSelectionMode(QAbstractItemView.ExtendedSelection)

            return

        # Otherwise, just set the file mode like normal
        super().setFileMode(mode)

    def fileMode(self):
        # Retrieve the actual file mode and set it to Directories if the internal flag is set to allow multiple
        # directories to be selected
        mode = super().fileMode()
        if mode == FileDialog.Directory and self._selectMultipleDirectories:
            mode = FileDialog.Directories

        return mode

    def isNative(self):
        return not (self.options() & FileDialog.DontUseNativeDialog or len(self.findChildren(QTreeView)) != 0)

    def _splitDirectory(url: QUrl):
        if not url or url.isEmpty():
            # If empty, then it will already have the directory set based on d->init!
            return QUrl(), ''

        if url.isLocalFile():
            info = QFileInfo(QDir.current(), url.toLocalFile())

            if info.exists() and info.isDir():
                return QUrl.fromLocalFile(info.absoluteFilePath()), ''
            else:
                return QUrl.fromLocalFile(info.absolutePath()), info.fileName()
        else:
            return url, url.fileName()

    # region Static helper methods for file dialog

    @staticmethod
    def getExistingDirectory(parent=None, caption='', directory='', options=QFileDialog.ShowDirsOnly):
        schemes = ['file']
        selectedUrl = FileDialog.getExistingDirectoryUrl(parent, caption, QUrl.fromLocalFile(directory), options,
                                                         schemes)
        return selectedUrl.toLocalFile()

    @staticmethod
    def getExistingDirectoryUrl(parent=None, caption='', directory=QUrl(), options=QFileDialog.ShowDirsOnly,
                                supportedSchemes=[]):
        dialog = FileDialog(parent, caption)
        dialog.setOptions(options)
        dialog.setFileMode(QFileDialog.DirectoryOnly)
        dialog.setSupportedSchemes(supportedSchemes)

        directory, _ = FileDialog._splitDirectory(directory)
        dialog.setDirectoryUrl(directory)

        if dialog.exec() == QDialog.Accepted:
            return dialog.selectedUrls()[0]

        return QUrl()

    @staticmethod
    def getExistingDirectories(parent=None, caption='', directory='',
                               options=QFileDialog.DontUseNativeDialog | QFileDialog.ShowDirsOnly):
        schemes = ['file']
        selectedUrls = FileDialog.getExistingDirectoriesUrl(parent, caption, QUrl.fromLocalFile(directory), options,
                                                            schemes)
        return [url.toLocalFile() for url in selectedUrls]

    @staticmethod
    def getExistingDirectoriesUrl(parent=None, caption='', directory=QUrl(),
                                  options=QFileDialog.DontUseNativeDialog | QFileDialog.ShowDirsOnly,
                                  supportedSchemes=[]):
        dialog = FileDialog(parent, caption)
        dialog.setOptions(options)
        dialog.setFileMode(FileDialog.Directories)
        dialog.setSupportedSchemes(supportedSchemes)

        directory, _ = FileDialog._splitDirectory(directory)
        dialog.setDirectoryUrl(directory)

        if dialog.exec() == QDialog.Accepted:
            return dialog.selectedUrls()

        return []

    @staticmethod
    def getOpenFileName(parent=None, caption='', directory='', filter='', selectedFilter='',
                        options=QFileDialog.Options()):
        schemes = ['file']
        selectedUrl, selectedFilter = FileDialog.getOpenFileUrl(parent, caption, QUrl.fromLocalFile(directory), filter,
                                                                selectedFilter,
                                                                options, schemes)
        return selectedUrl.toLocalFile(), selectedFilter

    @staticmethod
    def getOpenFileUrl(parent=None, caption='', directory=QUrl(), filter='', initialFilter='',
                       options=QFileDialog.Options(), supportedSchemes=[]):
        dialog = FileDialog(parent, caption, filter=filter)
        dialog.setOptions(options)
        dialog.setFileMode(FileDialog.ExistingFile)
        dialog.setSupportedSchemes(supportedSchemes)

        directory, filename = FileDialog._splitDirectory(directory)
        dialog.setDirectoryUrl(directory)
        dialog.selectFile(filename)

        if initialFilter:
            dialog.selectedNameFilter(initialFilter)

        if dialog.exec() == QDialog.Accepted:
            return dialog.selectedUrls()[0], dialog.selectedNameFilter()

        return QUrl(), ''

    @staticmethod
    def getOpenFileNames(parent=None, caption='', directory='', filter='', initialFilter='',
                         options=QFileDialog.Options()):
        schemes = ['file']
        selectedUrls, selectedFilter = FileDialog.getOpenFileUrls(parent, caption, QUrl.fromLocalFile(directory),
                                                                  filter, initialFilter, options, schemes)

        return [url.toLocalFile() for url in selectedUrls] if selectedUrls else [], selectedFilter

    @staticmethod
    def getOpenFileUrls(parent=None, caption='', directory=QUrl(), filter='', initialFilter='',
                        options=QFileDialog.Options(), supportedSchemes=[]):
        dialog = FileDialog(parent, caption, filter=filter)
        dialog.setOptions(options)
        dialog.setFileMode(FileDialog.ExistingFiles)
        dialog.setSupportedSchemes(supportedSchemes)

        directory, filename = FileDialog._splitDirectory(directory)
        dialog.setDirectoryUrl(directory)
        dialog.selectFile(filename)

        if initialFilter:
            dialog.selectedNameFilter(initialFilter)

        if dialog.exec() == QDialog.Accepted:
            return dialog.selectedUrls(), dialog.selectedNameFilter()

        return None, ''

    @staticmethod
    def getSaveFileName(parent=None, caption='', directory='', filter='', initialFilter='',
                        options=QFileDialog.Options()):
        schemes = ['file']
        selectedUrl, selectedFilter = FileDialog.getSaveFileUrl(parent, caption, QUrl.fromLocalFile(directory),
                                                                filter, initialFilter, options, schemes)
        return selectedUrl.toLocalFile(), selectedFilter

    @staticmethod
    def getSaveFileUrl(parent=None, caption='', directory=QUrl(), filter='', initialFilter='',
                       options=QFileDialog.Options(), supportedSchemes=[]):
        dialog = FileDialog(parent, caption, filter=filter)
        dialog.setFileMode(FileDialog.AnyFile)
        dialog.setOptions(options)
        dialog.setSupportedSchemes(supportedSchemes)
        dialog.setAcceptMode(FileDialog.AcceptSave)

        directory, filename = FileDialog._splitDirectory(directory)
        dialog.setDirectoryUrl(directory)
        dialog.selectFile(filename)

        if initialFilter:
            dialog.selectedNameFilter(initialFilter)

        if dialog.exec() == QDialog.Accepted:
            return dialog.selectedUrls()[0], dialog.selectedNameFilter()

        return QUrl(), ''

    # endregion
