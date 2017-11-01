# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainWindow.ui'
#
# Created by: PyQt5 UI code generator 5.9
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(837, 566)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.configureButton = QtWidgets.QPushButton(self.centralwidget)
        self.configureButton.setObjectName("configureButton")
        self.verticalLayout.addWidget(self.configureButton)
        self.runButton = QtWidgets.QPushButton(self.centralwidget)
        self.runButton.setObjectName("runButton")
        self.verticalLayout.addWidget(self.runButton)
        self.gridLayout.addLayout(self.verticalLayout, 5, 0, 1, 1)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem)
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setObjectName("label")
        self.horizontalLayout_3.addWidget(self.label)
        self.browseSourceButton = QtWidgets.QPushButton(self.centralwidget)
        self.browseSourceButton.setObjectName("browseSourceButton")
        self.horizontalLayout_3.addWidget(self.browseSourceButton)
        self.gridLayout.addLayout(self.horizontalLayout_3, 3, 0, 1, 1)
        self.sourceListView = QtWidgets.QListView(self.centralwidget)
        self.sourceListView.setObjectName("sourceListView")
        self.gridLayout.addWidget(self.sourceListView, 4, 0, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "SIUE Dixon Fat Segmentation Algorithm"))
        self.configureButton.setText(_translate("MainWindow", "Configure"))
        self.runButton.setText(_translate("MainWindow", "Run Segmentation"))
        self.label.setText(_translate("MainWindow", "Source Folders:"))
        self.browseSourceButton.setText(_translate("MainWindow", "Browse"))

