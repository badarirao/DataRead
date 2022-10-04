"""

Each loops in an IV file must be separated.
Then add each item into the listwidget, that will be easier and also neat.

"""

import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from showFile import Ui_Plotter
import pandas as pd
import os
import numpy as np
from datetime import datetime
from sklearn.cluster import KMeans
from pathlib import Path

import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use('Qt5Agg')

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import PdfPages


#TODO: option to plot as subplots when plots of different types are selected for plotting
#TODO: when plotting multiple switch data, maybe change scatter plot shape for each. Also, legend shoud be shown appropriately
#TODO: Option to use the touch-pen to write something on the plot, and then it should be saved.
#TODO: Option to save each plot in buffer, and it can be retrieved later for saving or further processing.
#TODO: Option to send the data and plot directly to originlab!
#TODO: When plotting multiple selected plots, remove the title bar.
#TODO: Editmetadata button activates even when a different item is single clicked, which does not load that item. The previous item is still active.
#TODO: Add converter program into GUI
#TODO: in multiple loops, loop number 10 comes after 1, instead of coming after 9.
#TODO: When multiple plots are selected, the comment section should show the comments of the first item in the plot.
#TODO: In comment section of switch experiment, add information about pulse width, limiting current, etc.
#TODO: The horizontal scrollbar for listwidget does not show the full text of the item. Needs some adjustment.
#TODO: Maybe it is better to display plot just by single click?

class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        fig.set_tight_layout(True)
        self.ax = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)

def h5load(store, keyName):
    data = store[keyName]
    metadata = store.get_storer(keyName).attrs.metadata
    return data, metadata

def h5store(filename, df, keyName, mode, **kwargs):
    store = pd.HDFStore(filename, mode=mode)
    store.put(keyName, df)
    store.get_storer(keyName).attrs.metadata = kwargs
    store.close()

class itemDetail:
    def __init__(self, store, file):
        self.data, self.metadata = h5load(store, file)
        self.name = file
        self.initialize_plot()
        self.logy = True

    def initialize_plot(self):
        if '_IV' in self.name:
            self.xAxis = 0
            self.yAxis = 2
            self.yAxis2 = 3
            self.data["Abs Current (A)"] = abs(self.data.iloc[:,2].values)
        elif '_RV' in self.name:
            self.xAxis = 0
            self.yAxis = 4
        elif '_Switch' in self.name:
            n = self.data.loc[:,["Pulse Voltage (V)", "Read Voltage (V)", "Pulse Width (ms)", "Compliance current (A)"]].copy() # copy relevant cluster identification columns
            c = np.ones(len(n))
            n['c']=c
            inertia = 1000
            i = 2
            #TODO: Option to manually change number of clusters
            while inertia > 2: # Set by trial and error method. You can change it to improve the plotting
                kmeans = KMeans(n_clusters=i).fit(n)
                inertia = kmeans.inertia_
                #print(f"{i} cluster inertia = {inertia}")
                i+=1
            i -= 1
            self.xAx = np.linspace(1,len(n),len(n))
            centroids = [x[0] for x in kmeans.cluster_centers_]
            self.pointLabels = []
            for l in kmeans.labels_:
                self.pointLabels.append(float(centroids[int(l)]))
        elif '_Forming' in self.name:
            self.xAxis = 0
            self.yAxis = 1
        elif '_Retention' in self.name:
            self.xAxis = 0
            self.yAxis = 1
            self.yAxis2 = 2
        elif '_Fatigue' in self.name:
            self.xAxis = 0
            self.yAxis = 3
            self.yAxis2 = 4

    def plot(self, canvas, vlegend=True, multiPlot = False):
        if self.data.empty:
            print("Empty dataset")
            return
        if multiPlot == False:
            title = self.name
        else:
            title = ""
        if '_IV' in self.name:
            if self.logy == False: #Normal IV
                self.data.plot(x=self.xAxis,y=self.yAxis, ax=canvas.ax,
                               ylabel = 'Current (A)', legend = False, title = title)
            else: # Absolute IV in log plot
                self.data.plot(x=self.xAxis,y=self.yAxis2, logy = True, ax=canvas.ax,
                               ylabel = "Abs. Current (A)", legend = False, title = title)
        elif '_Retention' in self.name:
            self.data.plot(x=self.xAxis,y=self.yAxis, ax=canvas.ax,
                           ylabel = 'Read Resistance (Ω)', legend = False, title = title)
            if self.data.shape[1] >= 2:
                self.data.plot(x=self.xAxis,y=self.yAxis2, legend = False, ax=canvas.ax, title = title)
        elif '_Fatigue' in self.name:
            self.data.plot(x=self.xAxis,y=self.yAxis,ax=canvas.ax,
                           ylabel = 'Read Resistance (Ω)', legend = False, title = title)
            self.data.plot(x=self.xAxis,y=self.yAxis2,ax=canvas.ax)
        elif not '_Switch' in self.name:
            self.data.plot(x=self.xAxis,y=self.yAxis, ax=canvas.ax,
                           ylabel = self.data.columns[self.yAxis], legend = False, title = title)
        else:
            scatter = canvas.ax.scatter(self.xAx, self.data.iloc[:,5], c = self.pointLabels, s = 3**2)
            canvas.ax.set_title(title)
            if vlegend:
                canvas.ax.set_xlabel("Pulse Number")
                canvas.ax.set_ylabel(self.data.columns[5])
                legend1 = canvas.ax.legend(*scatter.legend_elements(fmt="{x:.2f} V"),
                        loc="upper right", title="Applied Voltages")
                legend1.set_draggable(state=True)
                canvas.ax.add_artist(legend1)

class app_Plotter(QtWidgets.QMainWindow,Ui_Plotter):
    """The plotter app module."""

    def __init__(self):
        super(app_Plotter, self).__init__()
        self.setupUi(self)
        self.modifyGUI()
        self.connectSignals()
        self.show()
        self.items = []
        self.maxlen = 0
        self.activeItems = []
        self.root = self.plotTree.invisibleRootItem()

    def connectSignals(self):
        self.addPlotButton.clicked.connect(self.openFile)
        self.plotTree.installEventFilter(self)
        self.plotTree.itemChanged.connect(self.itemSelected)
        self.plotTree.itemDoubleClicked.connect(self.showItem)
        self.plotSelectedButton.clicked.connect(self.plotSelected)
        self.clearPlotButton.clicked.connect(self.clearPlot)
        self.clearExperimentButton.clicked.connect(self.clearExperiment)
        self.editMetadataButton.clicked.connect(self.editMetadata)
        self.metaDataComments.textChanged.connect(self.modifyComments)
        self.plotTree.itemClicked.connect(self.disableMetadata)
        self.clearSelectionsButton.clicked.connect(self.clearSelection)
        self.actionLoad_data.triggered.connect(self.loadNewData)
        self.actionLoad_data.setShortcut(QtGui.QKeySequence('Ctrl+o'))
        self.actionAdd_data.triggered.connect(self.openFile)
        self.actionAdd_data.setShortcut(QtGui.QKeySequence('Ctrl+a'))
        self.actionSave_File.triggered.connect(self.saveData)
        self.actionSave_File.setShortcut(QtGui.QKeySequence('Ctrl+s'))
        self.actionAs_txt.triggered.connect(self.save_active_as_txt)
        self.actionAs_txt.setShortcut(QtGui.QKeySequence('Ctrl+Shift+t'))
        self.actionAs_PNG.triggered.connect(self.save_active_as_PNG)
        self.actionAs_PNG.setShortcut(QtGui.QKeySequence('Ctrl+Shift+p'))
        self.actionAs_JPG.triggered.connect(self.save_active_as_jpg)
        self.actionAs_JPG.setShortcut(QtGui.QKeySequence('Ctrl+Shift+j'))
        self.actionAs_TIFF.triggered.connect(self.save_active_as_tiff)
        self.actionAs_TIFF.setShortcut(QtGui.QKeySequence('Ctrl+Shift+f'))
        self.actionAs_PDF.triggered.connect(self.save_active_as_pdf)
        self.actionAs_PDF.setShortcut(QtGui.QKeySequence('Ctrl+Shift+d'))
        self.actionAs_txt_2.triggered.connect(self.save_all_as_txt)
        self.actionAs_txt_2.setShortcut(QtGui.QKeySequence('Ctrl+Alt+t'))
        self.actionAs_PNG_2.triggered.connect(self.save_all_as_PNG)
        self.actionAs_PNG_2.setShortcut(QtGui.QKeySequence('Ctrl+Alt+p'))
        self.actionAs_JPG_2.triggered.connect(self.save_all_as_jpg)
        self.actionAs_JPG_2.setShortcut(QtGui.QKeySequence('Ctrl+Alt+j'))
        self.actionAs_TIFF_2.triggered.connect(self.save_all_as_tiff)
        self.actionAs_TIFF_2.setShortcut(QtGui.QKeySequence('Ctrl+Alt+f'))
        self.actionAs_PDF_2.triggered.connect(self.save_all_as_pdf)
        self.actionAs_PDF_2.setShortcut(QtGui.QKeySequence('Ctrl+Alt+d'))
        self.linxTool.clicked.connect(self.setlinearX)
        self.logxTool.clicked.connect(self.setlogX)
        self.linyTool.clicked.connect(self.setlinearY)
        self.logyTool.clicked.connect(self.setlogY)
        self.invxTool.clicked.connect(self.setinvX)
        self.invyTool.clicked.connect(self.setinvY)
        self.gridTool.clicked.connect(self.setgrid)
        self.generateReportButton.clicked.connect(self.testPlot)

    def testPlot(self):
        self.sc.ax.cla()
        self.root.child(0).item.ax.imshow()
        self.sc.draw()

    def setlinearX(self):
        if self.linxTool.isChecked():
            self.logxTool.setChecked(False)
            self.sc.ax.set_xscale('linear')
            self.sc.draw()

    def setlogX(self):
        if self.logxTool.isChecked():
            self.linxTool.setChecked(False)
            self.sc.ax.set_xscale('log')
            self.sc.draw()

    def setlinearY(self):
        if self.linyTool.isChecked():
            if '_IV' in self.activeItems[0].item.name:
                self.sc.ax.cla()
                legend_names = []
                for item in self.activeItems:
                    item.item.logy = False
                    item.item.plot(self.sc)
                    legend_names.append(item.item.name)
                if len(legend_names) > 1:
                    leg = self.sc.ax.legend(legend_names, loc='upper left')
                    leg.set_draggable(state=True)
            self.logyTool.setChecked(False)
            self.sc.ax.set_yscale('linear')
            self.sc.draw()

    def setlogY(self):
        if self.logyTool.isChecked():
            if '_IV' in self.activeItems[0].item.name:
                self.sc.ax.cla()
                legend_names = []
                for item in self.activeItems:
                    item.item.logy = True
                    item.item.plot(self.sc)
                    legend_names.append(item.item.name)
                if len(legend_names) > 1:
                    leg = self.sc.ax.legend(legend_names, loc='lower left')
                    leg.set_draggable(state=True)
            self.linyTool.setChecked(False)
            self.sc.ax.set_yscale('log')
            self.sc.draw()

    def setinvX(self):
        self.sc.ax.invert_xaxis()
        self.sc.draw()

    def setinvY(self):
        self.sc.ax.invert_yaxis()
        self.sc.draw()

    def setgrid(self):
        if self.gridTool.isChecked():
            self.sc.ax.grid()
        else:
            self.sc.ax.grid(False)
        self.sc.draw()

    def modifyGUI(self):
        self.metaDataComments.setEnabled(False)
        self.metaDataFixed.setEnabled(False)
        width = 300
        self.plotTree.setMinimumWidth(width)
        self.plotTree.header().setDefaultSectionSize(width)
        self.plotTree.header().setMinimumSectionSize(int(width/2))
        self.plotTree.header().setStretchLastSection(True)
        # plot window
        self.sc = MplCanvas(self.frame, width=5, height=4, dpi=200)
        self.toolbar = NavigationToolbar(self.sc, self)
        self.gridLayout_2.replaceWidget(self.frame,self.sc)
        self.gridLayout_2.replaceWidget(self.frame_2,self.toolbar)
        self.toolBarWidget.setMaximumWidth(90)  # hide the toolbar for now
        self.verticalLayout_3.setContentsMargins(0,0,0,0)

    def eventFilter(self, obj, event):
        if obj == self.plotTree:
            if event.type() == QtCore.QEvent.KeyPress:
                if event.key() == QtCore.Qt.Key_Return:
                    self.showItem(self.plotTree.currentItem(),0)
                elif event.key() == QtCore.Qt.Key_Delete:
                    self.deleteItem(self.plotTree.currentItem())
                elif event.key() == QtCore.Qt.Key_Up or event.key() == QtCore.Qt.Key_Down:
                    self.disableMetadata()
        return super(app_Plotter, self).eventFilter(obj, event)

    def deleteItem(self, item):
        if item.childCount() > 0:
            for i in range(item.childCount()):
                self.items.remove(item.child(i).item)
        else:
            self.items.remove(item.item)
        if item.parent():
            item.parent().removeChild(item)
        else:
            index = self.plotTree.indexOfTopLevelItem(item)
            self.plotTree.takeTopLevelItem(index)

    def showItem(self, item, column):
        if item.childCount() != 0:
            return
        # Display the metadata
        metadata = self.plotTree.currentItem().item.metadata.copy()
        comments = "Comments: " + metadata.pop("Comments") + '\n'
        self.metaDataComments.setText(comments)
        text = ""
        i = 0
        for key,value in metadata.items():
            if isinstance(value, datetime):
                value = value.strftime("%m/%d/%Y, %H:%M:%S")
            elif not isinstance(value, str):
                value = str(value)
            if i%2:
                sep = '; \n'
            else:
                sep = '; \t'
            text += (key + ': ' + value + sep)
            i += 1
        self.metaDataFixed.setText(text)
        self.sc.ax.cla()
        # Plot the selected item
        item.item.plot(self.sc)
        self.activeItems = [item]
        self.sc.draw()

        self.linxTool.setChecked(False)
        self.logxTool.setChecked(False)
        self.linyTool.setChecked(False)
        self.logyTool.setChecked(False)
        self.invxTool.setChecked(False)
        self.invyTool.setChecked(False)
        self.gridTool.setChecked(False)
        self.recipyTool.setChecked(False)

    def itemSelected(self, item, column):
        """
        Identify the selected data, and plot it accordingly.
        :param item: the selected item
        :param column: the corresponding column in the tree (always 0 in this case)
        :return: None
        """
        self.plotTree.blockSignals(True)
        itemName = ""
        if item.parent(): # check if it has a parent item
            itemName = item.parent().text(0) + '/'
            allChecked = True
            allUnChecked = True
            for i in range(item.parent().childCount()):
                if item.parent().child(i).checkState(0) != 2:
                    allChecked = False
                    break
            for i in range(item.parent().childCount()):
                if item.parent().child(i).checkState(0) != 0:
                    allUnChecked = False
                    break
            if allChecked:
                item.parent().setCheckState(0, 2)
            elif allUnChecked:
                item.parent().setCheckState(0, 0)
            else:
                item.parent().setCheckState(0, 1)
        itemName += item.text(column)
        if item.checkState(column) == 2:  # Checked
            if item.childCount() > 0:
                for i in range(item.childCount()):
                    item.child(i).setCheckState(0, 2)
            else:
                pass
        elif item.checkState(column) == 0 or item.checkState(column) == 1:  # Unchecked
            if item.checkState(column) == 1:
                item.setCheckState(0, 0)
            if item.childCount() > 0:
                for i in range(item.childCount()):
                    if item.child(i).checkState(column) == 2:
                        item.child(i).setCheckState(0, False)
        self.plotTree.blockSignals(False)

    def plotSelected(self):
        """
        Plot all selected data of same type
        Currently only one type of data can be plotted at a time.
        :return: None
        """
        childCount = self.root.childCount()
        plotItems = []
        graphType = ''
        start = True
        for i in range(childCount):
            item = self.root.child(i)
            if item.childCount() > 0:
                for j in range(item.childCount()):
                    childItem = item.child(j)
                    if childItem.checkState(0) == 2:
                        plotItems.append(childItem)
            else:
                if item.checkState(0) == 2:
                    plotItems.append(item)
        if plotItems:
            self.activeItems = plotItems
            firstItem = plotItems[0].item
            if '_IV' in firstItem.name:
                graphType = '_IV'
            elif '_RV' in firstItem.name:
                graphType = '_RV'
            elif '_Switch' in firstItem.name:
                graphType = '_Switch'
            elif '_Forming' in firstItem.name:
                graphType = '_Forming'
            elif '_Retention' in firstItem.name:
                graphType = '_Retention'
            elif '_Fatigue' in firstItem.name:
                graphType = '_Fatigue'
            self.sc.ax.cla()
            # Plot the selected items
            # Only data matching the type of first item are plotted.
            legend_names = []
            for item in plotItems:
                if graphType in item.item.name:
                    if graphType == '_Switch':
                        item.item.plot(self.sc, vlegend = False, multiPlot = True)
                    else:
                        item.item.plot(self.sc, multiPlot = True)
                    legend_names.append(item.item.name)
            legend_location = 'upper left'
            if graphType == '_IV':
                legend_location = 'lower left'
            leg = self.sc.ax.legend(legend_names, loc=legend_location)
            leg.set_draggable(state=True)
            self.sc.draw()

            self.linxTool.setChecked(False)
            self.logxTool.setChecked(False)
            self.linyTool.setChecked(False)
            self.logyTool.setChecked(False)
            self.invxTool.setChecked(False)
            self.invyTool.setChecked(False)
            self.gridTool.setChecked(False)
            self.recipyTool.setChecked(False)

    def clearPlot(self):
        self.sc.ax.cla()
        self.sc.draw()
        self.activeItems = []

    def clearExperiment(self):
        self.items.clear()
        self.plotTree.clear()

    def clearSelection(self):
        self.plotTree.selectionModel().clearSelection()
        childCount = self.root.childCount()
        for i in range(childCount):
            item = self.root.child(i)
            if item.checkState(0) == 2 or item.checkState(0) == 1:
                item.setCheckState(0,0)
            if item.childCount() > 0:
                for j in range(item.childCount()):
                    childItem = item.child(j)
                    if childItem.checkState(0) == 2 or childItem.checkState(0) == 1:
                        childItem.setCheckState(0,0)

    def disableMetadata(self):
        if self.editMetadataButton.text() == "Finish Editing Metadata":
            self.editMetadataButton.setText("Edit Metadata")
            self.metaDataComments.setEnabled(False)

    def editMetadata(self):
        if len(self.plotTree.selectedItems()) > 0:
            if self.editMetadataButton.text() == "Edit Metadata":
                self.editMetadataButton.setText("Finish Editing Metadata")
                self.metaDataComments.setEnabled(True)
            else:
                self.editMetadataButton.setText("Edit Metadata")
                self.metaDataComments.setEnabled(False)

    def modifyComments(self):
        comments = self.metaDataComments.toPlainText()
        currentItem = self.plotTree.currentItem()
        currentItem.item.metadata["Comments"] = comments

    def loadNewData(self):
        self.clearExperiment()
        self.clearPlot()
        self.openFile()

    def saveData(self):
        childItems = self.root.childCount()
        items = []
        for i in range(childItems):
            item = self.root.child(i)
            if item.childCount() > 0:
                for j in range(item.childCount()):
                    childItem = item.child(j)
                    items.append(childItem.item)
            else:
                items.append(item.item)
        filename = QtWidgets.QFileDialog.getSaveFileName(self, 'Choose file name & location')
        if '.' in filename[0]:
            index = filename[0].rindex('.')
        else:
            index = len(filename[0])
        filename = filename[0][:index] + '.h5'
        store = pd.HDFStore(filename, mode='w')
        for item in items:
            store.put(item.name, item.data)
            store.get_storer(item.name).attrs.metadata = item.metadata
        store.close()

    def openFile(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "QFileDialog.getOpenFileNames()", "", "Experiment Files (*.h5);;All Files (*)", options=options)
        if files:
            n = len(files)
            if n > 1:
                files.sort(key=os.path.getmtime)
            for i in range(n):
                file = files[i]
                self.addData(file)

    def saveAction(self, ext, elements):
        # a general save action function that processes all types of save commands
        # Just seeing if it is feasible
        path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Save Directory')
        for i in range(len(elements)):
            plotitem = elements[i]
            item = plotitem.item
            name = item.name.split('/')[0]
            folderName = "".join(name.split('_')[:-2])
            filename = path + '\\' + folderName + '\\' + item.name + ext
            pathName = Path(filename)
            print(pathName.parent)
            if not pathName.parent.exists():
                pathName.parent.mkdir(parents=True)
            if ext == '.txt':
                data = item.data
                data.to_csv(filename, sep='\t', index=False)
            elif ext == '.png':
                pass

    def save_active_as_txt(self):
        if self.activeItems:
            path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Save Directory')
            for i in range(len(self.activeItems)):
                plotitem = self.activeItems[i]
                item = plotitem.item
                data = item.data
                name = item.name.split('/')[0]
                folderName = "".join(name.split('_')[:-2])
                filename = path + '\\' + folderName + '\\' + item.name + '.txt'
                pathName = Path(filename)
                print(pathName.parent)
                if not pathName.parent.exists():
                    pathName.parent.mkdir(parents=True)
                data.to_csv(filename, sep='\t', index=False)
        else:
            self.statusBar().showMessage("No active plot exists for saving", 3000)

    def save_all_as_txt(self):
        childCount = self.root.childCount()
        plotItems = []
        for i in range(childCount):
            item = self.root.child(i)
            if item.childCount() > 0:
                for j in range(item.childCount()):
                    plotItems.append(item.child(j))
            else:
                plotItems.append(item)
        if plotItems:
            path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Save Directory')
            for i in range(len(plotItems)):
                plotitem = plotItems[i]
                item = plotitem.item
                data = item.data
                name = item.name.split('/')[0]
                folderName = "".join(name.split('_')[:-2])
                filename = path + '\\' + folderName + '\\' + item.name + '.txt'
                pathName = Path(filename)
                print(pathName.parent)
                if not pathName.parent.exists():
                    pathName.parent.mkdir(parents=True)
                data.to_csv(filename, sep='\t', index=False)
        else:
            self.statusBar().showMessage("No data in list for saving", 3000)

    def save_active_as_PNG(self):
        self.save_active_as_image('.png')

    def save_active_as_jpg(self):
        self.save_active_as_image('.jpg')

    def save_active_as_tiff(self):
        self.save_active_as_image('.tiff')

    def save_active_as_pdf(self):
        self.save_active_as_image('.pdf')

    def save_active_as_image(self, ext):
        if self.activeItems:
            fileName = QtWidgets.QFileDialog.getSaveFileName(self, 'Choose file name & location')
            if '.' in fileName[0]:
                index = fileName[0].rindex('.')
            else:
                index = len(fileName[0])
            fileName = fileName[0][:index] + ext
            self.sc.figure.savefig(fileName)
        else:
            self.statusBar().showMessage("No active plot exists for saving", 3000)

    def save_all_as_PNG(self):
        self.save_all_as_image('.png')

    def save_all_as_jpg(self):
        self.save_all_as_image('.jpg')

    def save_all_as_tiff(self):
        self.save_all_as_image('.tiff')

    def save_all_as_pdf(self):
        self.save_all_as_image('.pdf')

    def save_all_as_image(self, ext):
        childCount = self.root.childCount()
        plotItems = []
        for i in range(childCount):
            item = self.root.child(i)
            if item.childCount() > 0:
                for j in range(item.childCount()):
                    plotItems.append(item.child(j))
            else:
                plotItems.append(item)
        if plotItems:
            path = ""
            if ext == '.pdf':
                name = QtWidgets.QFileDialog.getSaveFileName(self, 'Choose file name & location')
                if '.' in name[0]:
                    index = name[0].rindex('.')
                else:
                    index = len(name[0])
                name = name[0][:index] + '.pdf'
                pdf = PdfPages(name)
            else:
                path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Save Directory')
            for i in range(len(plotItems)):
                plotitem = plotItems[i]
                item = plotitem.item
                data = item.data
                name = item.name.split('/')[0]
                folderName = "".join(name.split('_')[:-2])
                filename = path + '\\' + folderName + '\\' + item.name + ext
                pathName = Path(filename)
                self.sc.ax.cla()
                item.plot(self.sc)
                if ext == '.pdf':
                    pdf.savefig(self.sc.figure)
                else:
                    if not pathName.parent.exists():
                        pathName.parent.mkdir(parents=True)
                    self.sc.figure.savefig(filename)
            self.sc.ax.cla()
            if ext == '.pdf':
                pdf.close()
        else:
            self.statusBar().showMessage("No data in list for saving", 3000)

    def addData(self, file):
        # if the file is an hdf5 file, then it will have many plots within, so take care of it accordingly
        # if it is a single plot file, the do further analysis of the file
        # if IV file has multiple cycles, should each cycle be displayed as separate item?
        # todo:  Handle duplicate entries (currently both copies are kept as it is, but it may create problem when saving files)
        print("adding {}".format(file))
        currentItems = []
        if file.endswith('h5'):
            store = pd.HDFStore(file)
            fnames = store.keys()
            fnames = [f[1:] for f in fnames]
            if fnames:
                for expt in fnames:
                    item = itemDetail(store, expt)
                    currentItems.append(item)
                currentItems.sort(key=lambda x: x.metadata['timestamp'])
                self.items.extend(currentItems)
                for item in currentItems:
                    self.add_to_list(item)
            store.close()
        else:
            self.statusBar().showMessage("Only h5 files can be read", 3000)
        #elif '_IV_' in file and file.endswith('.dat'):
        #    pass

    def add_to_list(self, item):
        if '/' in item.name:
            parentItem, childItem = item.name.split('/')
            items = self.plotTree.findItems(parentItem, QtCore.Qt.MatchRecursive, 0)
            if not items:
                treeItem = QtWidgets.QTreeWidgetItem([parentItem])
            else:
                treeItem = items[0]
            childItem = QtWidgets.QTreeWidgetItem([childItem])
            childItem.item = item
            childItem.setCheckState(0,False)
            treeItem.addChild(childItem)
        else:
            treeItem = QtWidgets.QTreeWidgetItem([item.name])
            treeItem.item = item
        treeItem.setCheckState(0,False)
        #listItem.setData(item.data)
        #treeItem.setCheckState(False)
        self.plotTree.addTopLevelItem(treeItem)
        if len(item.name) > self.maxlen:
            self.plotTree.resizeColumnToContents(len(self.items)-1)
            self.maxlen = len(item.name)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    Plotter = app_Plotter()
    sys.exit(app.exec_())