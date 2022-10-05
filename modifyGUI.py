from PyQt5 import QtCore

def change_dimensions(dataViewGUI):
    # to modify the GUI display of a different PC, just change these sizes appropriately.
    dataViewGUI.resize(1063, 896) # size of whole GUI (but also depends on minimum sizes of other objects)
    dataViewGUI.commentsBox.setMaximumSize(QtCore.QSize(16777215, 300))
    dataViewGUI.metaDataFixed.setMaximumSize(QtCore.QSize(16777215, 100))
    dataViewGUI.metaDataComments.setMaximumSize(QtCore.QSize(16777215, 100))
    dataViewGUI.plotTree.setMinimumSize(QtCore.QSize(200, 500))
    dataViewGUI.frame_2.setMaximumSize(QtCore.QSize(16777215, 50))
    dataViewGUI.frame.setMinimumSize(QtCore.QSize(550, 500))
    dataViewGUI.toolBarWidget.setMaximumSize(QtCore.QSize(100, 16777215))
    dataViewGUI.menubar.setGeometry(QtCore.QRect(0, 0, 1063, 21))
