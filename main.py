import sys

import constants
from mainWindow import *

# Back up the reference to the exceptionhook
sys._excepthook = sys.excepthook


# Exception hook is used to print out the exception
# This is necessary for Qt 5 applications because Qt uses an event loop which will not trigger a traceback
def my_exception_hook(exctype, value, traceback):
    # Print the error and traceback
    print(exctype, value, traceback)

    # Call the normal Exception hook after
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


def main():
    # Set application, organization name and version
    # This is used for the QSettings (when an empty constructor is given)
    QCoreApplication.setApplicationName(constants.applicationName)
    QCoreApplication.setOrganizationName(constants.organizationName)
    QCoreApplication.setApplicationVersion(constants.version)

    app = QApplication(sys.argv)

    form = MainWindow()
    form.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
