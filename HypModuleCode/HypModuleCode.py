import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import numpy as np
import pip
from pip._internal import main
import math
import SimpleITK as sitk
import re

# Install necessary libraries
try:
    import matplotlib
except ModuleNotFoundError:
    import pip

    slicer.util.pip_install("matplotlib")
    import matplotlib

try:
    import PIL
except ModuleNotFoundError:
    import pip

    slicer.util.pip_install("PIL")
    import PIL

try:
    import skimage
except ModuleNotFoundError:
    import pip

    slicer.util.pip_install("scikit-image")
    import skimage

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pylab import savefig


# Define global variables
import time

nodeName = '\\result_{}.png'.format(int(time.time()))
globalCellMask = {}
roiNames = []
channelNames = []
selectedRoi = None
roiDict = None
selectedChannel = None
scatterPlotRoi = None
tsnePcaData = None
gatingList = []
selectedGates = None


#
# TITAN Module
#

class HypModuleCode(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "TITAN"  # TODO make this more human readable by adding spaces
        self.parent.categories = ["Analysis"]
        self.parent.dependencies = []
        self.parent.contributors = [
            "Sindhura Thirumal (Med-i Lab Queen's University)"]  # replace with "Firstname Lastname (Organization)"
        self.parent.helpText = """
This is an analysis pipeline catered towards Hyperion imaging mass cytometry data.
It allows for visualization, mask creation, and statistical analyses.
"""
        self.parent.helpText += self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = """
This file was originally developed by Sindhura Thirumal, Med-i Lab at Queen's University.
"""  # replace with organization, grant and thanks.

        # Set module icon from Resources/Icons/<ModuleName>.png
        moduleDir = os.path.dirname(self.parent.path)
        iconPath = os.path.join(moduleDir, 'Resources/Icons', 'logo v2.PNG')
        if os.path.isfile(iconPath):
            parent.icon = qt.QIcon(iconPath)

        # Add this test to the SelfTest module's list for discovery when the module
        # is created.  Since this module may be discovered before SelfTests itself,
        # create the list if it doesn't already exist.
        try:
            slicer.selfTests
        except AttributeError:
            slicer.selfTests = {}
        slicer.selfTests[self.moduleName] = self.runTest

#
# TITAN Module Widget
#

class HypModuleCodeWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer)
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/HypModuleCode.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set inputs to be a MRML node in a scene
        self.ui.gatingMasks.clear()

        # Data
        self.ui.subjectHierarchy.setMRMLScene(slicer.mrmlScene)

        # Connections

        # Data
        self.ui.textFileLoad.connect("clicked(bool)", self.onTextFileLoad)

        self.ui.roiList.connect("itemSelectionChanged()", self.onRoiList)
        self.ui.channelList.connect("itemSelectionChanged()", self.onChannelList)
        self.ui.refreshLists.connect("clicked(bool)", self.onRefreshLists)

        # Visualization
        self.ui.resetViewButton.connect("clicked(bool)", self.onReset)

        self.ui.crtThumbnails.connect("clicked(bool)", self.onThumbnails)

        self.ui.roiVisualization.connect("activated(int)", self.onVisualization)

        self.ui.redSelect.connect("activated(int)", self.onVisualization)
        self.ui.greenSelect.connect("activated(int)", self.onVisualization)
        self.ui.blueSelect.connect("activated(int)", self.onVisualization)
        self.ui.yellowSelect.connect("activated(int)", self.onVisualization)
        self.ui.cyanSelect.connect("activated(int)", self.onVisualization)
        self.ui.magentaSelect.connect("activated(int)", self.onVisualization)
        self.ui.whiteSelect.connect("activated(int)", self.onVisualization)

        self.ui.threshMinSlider.connect('valueChanged(int)', self.onVisualization)
        self.ui.threshMaxSlider.connect('valueChanged(int)', self.onVisualization)

        self.ui.getWLButton.connect("clicked(bool)", self.onGetWL)
        self.ui.setWLButton.connect("clicked(bool)", self.onSetWL)

        self.ui.saveImgButton.connect('clicked(bool)', self.onSaveButton)

        # Add vertical spacer
        self.layout.addStretch(1)

        # Mask Creation
        self.ui.crtMaskButton.connect('clicked(bool)', self.onCreateMasks)

        # Analysis
        self.ui.crtPlotButton.connect('clicked(bool)', self.onCreatePlot)

        self.ui.analysisResetButton.connect("clicked(bool)", self.onReset)

        self.ui.saveHistoTable.connect('clicked(bool)', self.onHistoSave)

        self.ui.crtHeatmapChannel.connect('clicked(bool)', self.onHeatmapChannelPlot)
        self.ui.saveHeatmapTable.connect('clicked(bool)', self.onHeatmapSaveTable)

        self.ui.crtScatterButton.connect('clicked(bool)', self.onScatterPlot)
        self.ui.saveScatPlotTable.connect('clicked(bool)', self.onScatPlotSaveTable)

        self.ui.crtHeatmapButton.connect('clicked(bool)', self.onHeatmapPlot)

        self.ui.updPlotFromSel.connect("clicked(bool)", self.onUpdatePlotFromSelection)
        self.ui.clearSelection.connect("clicked(bool)", self.onClearSelection)

        self.ui.gatingMasks.connect("itemSelectionChanged()", self.onGatingList)

        # Advanced
        self.ui.crtTsne.connect('clicked(bool)', self.onCreateTsne)
        self.ui.crtPCA.connect('clicked(bool)', self.onCreatePCA)
        self.ui.crtKMeans.connect('clicked(bool)', self.onCreateKMeans)
        self.ui.crtHierarch.connect('clicked(bool)', self.onHierarchicalCluster)
        self.ui.crtRawData.connect('clicked(bool)', self.onCreateRawData)
        # self.ui.crtPhenograph.connect('clicked(bool)', self.onPhenograph)

    def onReset(self):
        slicer.util.resetSliceViews()

    def onSubjectHierarchy(self):
        print(self.ui.subjectHierarchy.currentItems)

    def onTextFileLoad(self):
        logic = HypModuleLogic()
        logic.textFileLoad()

    def onThumbnails(self):
        if selectedChannel is None or len(selectedChannel) <= 1:
            self.ui.thumbErrorMessage.text = "ERROR: Minimum 1 channel should be selected."
            return
        elif selectedRoi is None or len(selectedRoi) != 1:
            self.ui.thumbErrorMessage.text = "ERROR: 1 ROI should be selected."
            return
        else:
            self.ui.thumbErrorMessage.text = ""
        logic = HypModuleLogic()
        logic.thumbnails()

    # Whenever something is updated in Visualization tab, this function runs
    def onVisualization(self):
        logic = HypModuleLogic()

        logic.visualizationRun(self.ui.roiVisualization.currentText, self.ui.redSelect.currentText,
                               self.ui.greenSelect.currentText, self.ui.blueSelect.currentText,
                               self.ui.yellowSelect.currentText, self.ui.cyanSelect.currentText,
                               self.ui.magentaSelect.currentText, self.ui.whiteSelect.currentText, self.ui.threshMinSlider.value,
                               self.ui.threshMaxSlider.value)

        self.ui.fileNameLabel.text = nodeName + ".png"

        self.ui.saveImgButton.enabled = self.ui.roiVisualization.currentText or self.ui.redSelect.currentText or \
                                        self.ui.greenSelect.currentText or self.ui.blueSelect.currentText or \
                                        self.ui.yellowSelect.currentText or self.ui.cyanSelect.currentText or \
                                        self.ui.magentaSelect.currentText or self.ui.whiteSelect.currentText

        self.ui.threshMinSlider.enabled = self.ui.roiVisualization.currentText or self.ui.redSelect.currentText or \
                                        self.ui.greenSelect.currentText or self.ui.blueSelect.currentText or \
                                        self.ui.yellowSelect.currentText or self.ui.cyanSelect.currentText or \
                                        self.ui.magentaSelect.currentText or self.ui.whiteSelect.currentText

        self.ui.threshMaxSlider.enabled = self.ui.roiVisualization.currentText or self.ui.redSelect.currentText or \
                                        self.ui.greenSelect.currentText or self.ui.blueSelect.currentText or \
                                        self.ui.yellowSelect.currentText or self.ui.cyanSelect.currentText or \
                                        self.ui.magentaSelect.currentText or self.ui.whiteSelect.currentText

        self.ui.threshMin.enabled = self.ui.roiVisualization.currentText or self.ui.redSelect.currentText or \
                                        self.ui.greenSelect.currentText or self.ui.blueSelect.currentText or \
                                        self.ui.yellowSelect.currentText or self.ui.cyanSelect.currentText or \
                                        self.ui.magentaSelect.currentText or self.ui.whiteSelect.currentText

        self.ui.threshMax.enabled = self.ui.roiVisualization.currentText or self.ui.redSelect.currentText or \
                                        self.ui.greenSelect.currentText or self.ui.blueSelect.currentText or \
                                        self.ui.yellowSelect.currentText or self.ui.cyanSelect.currentText or \
                                        self.ui.magentaSelect.currentText or self.ui.whiteSelect.currentText

    def onGetWL(self):
        currentId = slicer.app.layoutManager().sliceWidget("Red").sliceLogic().GetSliceCompositeNode().GetBackgroundVolumeID()
        currentNode = slicer.util.getNode(currentId)
        displayNode = currentNode.GetDisplayNode()
        window = displayNode.GetWindow()
        level = displayNode.GetLevel()
        self.ui.getWindow.text = str(window)
        self.ui.getLevel.text = str(level)
        self.ui.setWindow.value = window
        self.ui.setLevel.value = level

    def onSetWL(self):
        currentId = slicer.app.layoutManager().sliceWidget("Red").sliceLogic().GetSliceCompositeNode().GetBackgroundVolumeID()
        currentNode = slicer.util.getNode(currentId)
        displayNode = currentNode.GetDisplayNode()
        window = self.ui.setWindow.value
        level = self.ui.setLevel.value
        displayNode.SetWindow(window)
        displayNode.SetLevel(level)

    def onSelect(self):
        self.ui.crtPlotButton.enabled = self.ui.imageHistogramSelect.currentNode() \
                                        and self.ui.imageHistogramSelectTwo.currentNode() \
                                        and self.ui.imageHistogramSelectThree.currentNode()
        # self.ui.crtHeatmapChannel.enabled = self.ui.heatmapChannelSelect.currentNode()
        self.ui.crtScatterButton.enabled = self.ui.channelTwoScatter.currentNode() and self.ui.channelOneScatter.currentNode()

    def onRoiList(self):
        global selectedRoi
        selectedRoi = []
        for item in self.ui.roiList.selectedItems():
            selectedRoi.append(item.text())

    def onChannelList(self):
        global selectedChannel
        selectedChannel = []
        for item in self.ui.channelList.selectedItems():
            selectedChannel.append(item.text())

    def onGatingList(self):
        global selectedGates
        selectedGates = []
        for item in self.ui.gatingMasks.selectedItems():
            selectedGates.append(item.text())

    def onRefreshLists(self):
        # Get list of ROI's

        global channelNames
        channelNames = []
        global roiNames
        roiNames = []
        global roiDict
        roiDict = {}

        # Get list of all channels
        allChannels = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")

        # Create dictionary of each channel with its respective ROI
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
        for channel in allChannels:
            # if shNode.GetItemName(shNode.GetItemParent(shNode.GetItemByDataNode(channel))) != "Scene":
            itemId = shNode.GetItemByDataNode(channel)  # Channel
            parent = shNode.GetItemParent(itemId)  # ROI
            roiName = shNode.GetItemName(parent)
            channelName = shNode.GetItemName(itemId)
            print(channelName)
            if re.findall(r"_[0-9][0-9]?\b", channelName) != []:
                channelName = channelName.split("_")[0]
            if channelName not in channelNames:
                # if channelName.endswith(".ome"):
                if any(substring in channelName for substring in ["Mask", "Density", "Clustering"]):
                    pass
                else:
                    channelNames.append(channelName)
            if roiName not in roiNames:
                roiNames.append(roiName)
        if roiNames == ["Scene"]:
            roiNames = ["ROI"]


        # Display ROI's and Channels in list widget

        self.ui.roiList.clear()
        self.ui.channelList.clear()
        self.ui.roiVisualization.clear()
        self.ui.redSelect.clear()
        self.ui.blueSelect.clear()
        self.ui.greenSelect.clear()
        self.ui.yellowSelect.clear()
        self.ui.cyanSelect.clear()
        self.ui.magentaSelect.clear()
        self.ui.whiteSelect.clear()

        self.ui.redSelect.addItem("None")
        self.ui.greenSelect.addItem("None")
        self.ui.blueSelect.addItem("None")
        self.ui.yellowSelect.addItem("None")
        self.ui.cyanSelect.addItem("None")
        self.ui.magentaSelect.addItem("None")
        self.ui.whiteSelect.addItem("None")

        roiPosCount = 0
        for roi in roiNames:
            if roi != "Scene":
                self.ui.roiList.addItem(roi)
                self.ui.roiVisualization.addItem(roi)
                roiDict[roi] = roiPosCount
                roiPosCount += 1
        for channel in channelNames:
            self.ui.channelList.addItem(channel)
            self.ui.redSelect.addItem(channel)
            self.ui.greenSelect.addItem(channel)
            self.ui.blueSelect.addItem(channel)
            self.ui.yellowSelect.addItem(channel)
            self.ui.cyanSelect.addItem(channel)
            self.ui.magentaSelect.addItem(channel)
            self.ui.whiteSelect.addItem(channel)

    # When "Save Image" is clicked, run saveVisualization function
    def onSaveButton(self):
        logic = HypModuleLogic()
        logic.saveVisualization(self.ui.fileNameLabel.text)

    # When Create Nucleus Mask is clicked, run nucleusMaskRun function
    def onCreateMasks(self):
        if selectedChannel is None or len(selectedChannel) != 1:
            self.ui.segmentationErrorMessage.text = "ERROR: 1 channel should be selected."
            return
        elif selectedRoi is None or len(selectedRoi) == 0:
            self.ui.segmentationErrorMessage.text = "ERROR: Minimum 1 ROI should be selected."
            return
        else:
            self.ui.segmentationErrorMessage.text = ""
        logic = HypModuleLogic()
        nucleiMin = self.ui.nucleiMin.value
        nucleiMax = self.ui.nucleiMax.value
        cellDim = self.ui.cellDimInput.value
        nCells = logic.crtMasksRun(nucleiMin, nucleiMax, cellDim)
        nCellsText = []
        for roi in nCells:
            nCellsText.append(roi + ": " + str(nCells[roi]))
        self.ui.nCellsLabel.text = "\n".join(nCellsText)

    def onCreatePlot(self):
        if selectedChannel is None or len(selectedChannel) < 1:
            self.ui.analysisErrorMessage.text = "ERROR: Minimum 1 channel should be selected."
            return
        elif selectedRoi is None or len(selectedRoi) == 0:
            self.ui.analysisErrorMessage.text = "ERROR: Minimum 1 ROI should be selected."
            return
        else:
            self.ui.analysisErrorMessage.text = ""
        logic = HypModuleLogic()
        logic.analysisRun()

    def onHistoSave(self):
        logic = HypModuleLogic()
        logic.saveTableData()

    def onHeatmapChannelPlot(self):
        if selectedChannel is None or len(selectedChannel) != 1:
            self.ui.analysisErrorMessage.text = "ERROR: 1 channel should be selected."
            return
        elif selectedRoi is None or len(selectedRoi) != 1:
            self.ui.analysisErrorMessage.text = "ERROR: 1 ROI should be selected."
            return
        elif len(globalCellMask) == 0:
            self.ui.analysisErrorMessage.text = "ERROR: Masks have not been created."
            return
        else:
            self.ui.analysisErrorMessage.text = ""
        logic = HypModuleLogic()
        logic.heatmapChannelRun()

    def onHeatmapSaveTable(self):
        logic = HypModuleLogic()
        logic.saveTableData()

    def onScatterPlot(self):
        if selectedChannel is None or len(selectedChannel) != 2:
            self.ui.analysisErrorMessage.text = "ERROR: 2 channels should be selected."
            return
        elif selectedRoi is None or len(selectedRoi) != 1:
            self.ui.analysisErrorMessage.text = "ERROR: 1 ROI should be selected."
            return
        elif len(globalCellMask) == 0:
            self.ui.analysisErrorMessage.text = "ERROR: Masks have not been created."
            return
        elif self.ui.arcsinTrans.checkState() != 0 and self.ui.logTrans.checkState() != 0:
            self.ui.analysisErrorMessage.text = "ERROR: Maximum 1 transform can be selected."
            return
        else:
            self.ui.analysisErrorMessage.text = ""

        self.ui.selectedCellsCount.text = ""

        logic = HypModuleLogic()

        if self.ui.arcsinTrans.checkState()==0:
            arcsinState = False
        else:
            arcsinState = True

        if self.ui.logTrans.checkState() == 0:
            logState = False
        else:
            logState = True

        if selectedGates is None or len(selectedGates) == 0:
            logic.scatterPlotRun(False, arcsinState, logState)
        elif len(selectedGates) > 1:
            self.ui.analysisErrorMessage.text = "ERROR: One mask should be selected."
        else:
            logic.scatterPlotRun(True, arcsinState, logState)

        # Scatter plot gating signal
        layoutManager = slicer.app.layoutManager()
        plotWidget = layoutManager.plotWidget(0)
        plotView = plotWidget.plotView()
        plotView.connect("dataSelected(vtkStringArray*, vtkCollection*)", self.onDataSelected)

    def onDataSelected(self, mrmlPlotDataIDs, selectionCol):
        """
        Runs when user selects point on scatter plot
        """

        # Delete any existing selected cell masks
        existingMasks = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")


        for selectionIndex in range(mrmlPlotDataIDs.GetNumberOfValues()):
            pointIdList = []
            pointIds = selectionCol.GetItemAsObject(selectionIndex)
            for pointIndex in range(pointIds.GetNumberOfValues()):
                pointIdList.append(pointIds.GetValue(pointIndex))

        # Get cell number
        tables = slicer.util.getNodesByClass("vtkMRMLTableNode")
        tableNode = tables[0]
        cellLabels = []
        for cell in pointIdList:
            label = tableNode.GetCellText(cell, 2)
            cellLabels.append(label)
        cellCount = len(cellLabels)
        self.ui.selectedCellsCount.text = cellCount
        self.ui.tsneSelectedCellsCount.text = cellCount

        cellMaskNode = globalCellMask[scatterPlotRoi]
        cellMaskArray = slicer.util.arrayFromVolume(cellMaskNode)

        selectedCellsMask = np.copy(cellMaskArray)

        # Remove cells in the array that aren't part of the selected cells
        for cell in np.unique(selectedCellsMask):
            if cell != 0:
                if str(cell) not in cellLabels:
                    selectedCellsMask[selectedCellsMask == cell] = 0

        # Create new cell mask image
        name = self.ui.selectedCellsName.text + " - " + str(cellCount) + " Cells"

        volumeNode = slicer.modules.volumes.logic().CloneVolume(cellMaskNode, name)
        slicer.util.updateVolumeFromArray(volumeNode, selectedCellsMask)

        # Add to global list of cell masks
        globalCellMask[name] = volumeNode

        # Change colormap of volume
        red_logic = slicer.app.layoutManager().sliceWidget("Red").sliceLogic()
        red_logic.GetSliceCompositeNode().SetBackgroundVolumeID(volumeNode.GetID())

        for img in existingMasks:
            if name in img.GetName():
                slicer.mrmlScene.RemoveNode(img)

        # Add mask name to list of possible gating masks
        global gatingList
        if name not in gatingList:
            gatingList.append(name)
        self.ui.gatingMasks.clear()
        for i in gatingList:
            self.ui.gatingMasks.addItem(i)

    def onUpdatePlotFromSelection(self):
        """
        After user makes a selection on the cell mask or other image, update the cell mask to reflect this
        """
        # Delete any existing selected cell masks
        existingMasks = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")

        # Export segmentation into a labelmap
        cellMask = globalCellMask[scatterPlotRoi]

        segs = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        seg = segs[-1]
        labelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "Selection on image")
        # slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(seg, labelmap)
        visibleIds = vtk.vtkStringArray()
        slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(seg, visibleIds, labelmap, cellMask)

        selectedCellLabels = []

        # Get values of cell labels
        cellMaskArray = slicer.util.arrayFromVolume(cellMask)
        labelmapArray = slicer.util.arrayFromVolume(labelmap)
        for selection in np.unique(labelmapArray):
            if selection != 0:
                points = np.where(labelmapArray == selection)
                values = cellMaskArray[points]
                cellLabels = list(np.unique(values))
                for i in cellLabels:
                    if i != 0:
                        # if np.any(i not in selectedCellLabels):
                        if i not in selectedCellLabels:
                            selectedCellLabels.append(i)

        selectedCellsMask = np.copy(cellMaskArray)

        # Remove cells in the array that aren't part of the selected cells
        for cell in np.unique(selectedCellsMask):
            if cell != 0:
                if cell not in selectedCellLabels:
                # if np.any(cell not in selectedCellLabels):
                    selectedCellsMask[selectedCellsMask == cell] = 0

        # Create new cell mask image
        name = self.ui.selectedCellsName.text

        volumeNode = slicer.modules.volumes.logic().CloneVolume(cellMask, name)
        slicer.util.updateVolumeFromArray(volumeNode, selectedCellsMask)

        # Add to global list of cell masks
        globalCellMask[name] = volumeNode

        self.ui.selectedCellsCount.text = len(cellLabels)

        if self.ui.arcsinTrans.checkState()==0:
            arcsinState = False
        else:
            arcsinState = True

        if self.ui.logTrans.checkState() == 0:
            logState = False
        else:
            logState = True

        logic = HypModuleLogic()

        if selectedGates is None or len(selectedGates) == 0:
            logic.scatterPlotRun(False, arcsinState, logState)
        elif len(selectedGates) > 1:
            self.ui.analysisErrorMessage.text = "ERROR: One mask should be selected."
        else:
            logic.scatterPlotRun(True, arcsinState, logState)

        red_logic = slicer.app.layoutManager().sliceWidget("Red").sliceLogic()
        red_logic.GetSliceCompositeNode().SetBackgroundVolumeID(volumeNode.GetID())

        for img in existingMasks:
            if name in img.GetName():
                slicer.mrmlScene.RemoveNode(img)

        # Add mask name to list of possible gating masks
        global gatingList
        if name not in gatingList:
            gatingList.append(name)
        self.ui.gatingMasks.clear()
        for i in gatingList:
            self.ui.gatingMasks.addItem(i)

    def onClearSelection(self):
        existingSegs = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")

        for seg in existingSegs:
            slicer.mrmlScene.RemoveNode(seg)

    def onScatPlotSaveTable(self):
        logic = HypModuleLogic()
        logic.saveTableData()

    def onHeatmapPlot(self):
        if selectedChannel is None or len(selectedChannel) < 1:
            self.ui.analysisErrorMessage.text = "ERROR: Minimum 1 channel should be selected."
            return
        elif selectedRoi is None or len(selectedRoi) < 1:
            self.ui.analysisErrorMessage.text = "ERROR: Minimum 1 ROI should be selected."
            return
        elif self.ui.hmapNormalizeRoi.checkState() !=0 and self.ui.hmapNormalizeChannel.checkState() != 0:
            self.ui.analysisErrorMessage.text = "ERROR: Only one normalization should be selected."
            return
        else:
            self.ui.analysisErrorMessage.text = ""

        logic = HypModuleLogic()

        if self.ui.hmapNormalizeRoi.checkState()==0:
            normalizeRoi = False
        else:
            normalizeRoi = True

        if self.ui.hmapNormalizeChannel.checkState()==0:
            normalizeChannel = False
        else:
            normalizeChannel = True

        logic.heatmapRun(normalizeRoi, normalizeChannel)

    def onCreateTsne(self):
        if selectedChannel is None or len(selectedChannel) < 1:
            self.ui.advancedErrorMessage.text = "ERROR: Minimum 1 channel should be selected."
            return
        elif selectedRoi is None or len(selectedRoi) < 1:
            self.ui.advancedErrorMessage.text = "ERROR: Minimum 1 ROI should be selected."
            return
        else:
            self.ui.advancedErrorMessage.text = ""

        self.ui.tsneSelectedCellsCount.text = ""

        logic = HypModuleLogic()

        if selectedGates is None or len(selectedGates) == 0:
            logic.tsnePCARun("tsne", False)
        elif len(selectedGates) > 1:
            self.ui.advancedErrorMessage.text = "ERROR: One mask should be selected."
        else:
            logic.tsnePCARun("tsne", True)

        # Scatter plot gating signal
        layoutManager = slicer.app.layoutManager()
        plotWidget = layoutManager.plotWidget(0)
        plotView = plotWidget.plotView()
        plotView.connect("dataSelected(vtkStringArray*, vtkCollection*)", self.onDataSelected)

    def onCreatePCA(self):
        if selectedChannel is None or len(selectedChannel) < 2:
            self.ui.advancedErrorMessage.text = "ERROR: Minimum 2 channels should be selected."
            return
        elif selectedRoi is None or len(selectedRoi) < 1:
            self.ui.advancedErrorMessage.text = "ERROR: Minimum 1 ROI should be selected."
            return
        else:
            self.ui.advancedErrorMessage.text = ""

        self.ui.tsneSelectedCellsCount.text = ""

        logic = HypModuleLogic()

        if selectedGates is None or len(selectedGates) == 0:
            logic.tsnePCARun("pca", False)
        elif len(selectedGates) > 1:
            self.ui.advancedErrorMessage.text = "ERROR: One mask should be selected."
        else:
            logic.tsnePCARun("pca", True)

        # Scatter plot gating signal
        layoutManager = slicer.app.layoutManager()
        plotWidget = layoutManager.plotWidget(0)
        plotView = plotWidget.plotView()
        plotView.connect("dataSelected(vtkStringArray*, vtkCollection*)", self.onDataSelected)

    def onCreateKMeans(self):
        logic = HypModuleLogic()
        logic.clusterRun(nClusters=self.ui.nClusters.value, clusterType="kmeans")

    def onHierarchicalCluster(self):
        logic = HypModuleLogic()
        logic.clusterRun(nClusters=self.ui.nClusters.value, clusterType="hierarchical")

    # def onPhenograph(self):
    #     if selectedChannel is None or len(selectedChannel) < 1:
    #         self.ui.advancedErrorMessage.text = "ERROR: Minimum 1 channel should be selected."
    #         return
    #     elif selectedRoi is None or len(selectedRoi) != 1:
    #         self.ui.advancedErrorMessage.text = "ERROR: Only 1 ROI should be selected."
    #         return
    #     else:
    #         self.ui.advancedErrorMessage.text = ""
    #
    #     logic = HypModuleLogic()
    #     logic.phenographRun()

    def onCreateRawData(self):
        logic = HypModuleLogic()
        logic.rawDataRun()


#
# TITAN Module Logic
#


class HypModuleLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """


    def textFileLoad(self):
        # Open file explorer for user to select files
        fileExplorer = qt.QFileDialog()
        filePaths = fileExplorer.getOpenFileNames()

        roiCount = 0

        # For each file, generate arrays for each image
        for data_path in filePaths:
            roiName = data_path.split('/')[-1]
            data = []
            # Parse through each row and get the pixel values
            with open(data_path, 'r') as read_obj:
                for i, line in enumerate(read_obj):
                    x = line.split("\t")
                    if i == 0:
                        headers = x
                    else:
                        y = [float(num) for num in x]
                        data.append(np.expand_dims(y, axis=0))


            data = np.concatenate(data, axis=0)

            # Get image size
            dim_x = int(np.max(data[:, 3])) + 1
            dim_y = int(np.max(data[:, 4])) + 1
            dim_ch = len(headers) - 6
            ch_name = headers[6:]
            # Generate list of arrays for each image
            ROI = np.zeros([dim_y, dim_x, dim_ch])
            for i in range(len(data)):
                ch_val = data[i, 6:]
                ROI[int(data[i, 4]), int(data[i, 3]), :] = ch_val

            # index = 0
            folderId = None

            # For each image, create a new volume node
            for index in range(len(ch_name)):
                channelName = ch_name[index]
                if roiCount != 0:
                    channelName = channelName + "_" + str(roiCount)
                channelArray = ROI[:,:,index]
                arraySize = channelArray.shape
                # print(arraySize)

                # Create new volume "Image Overlay"
                # Set name of overlaid image to be the names of all the channels being overlaid
                imageSize = [arraySize[1], arraySize[0], 1]
                voxelType = vtk.VTK_UNSIGNED_CHAR
                imageOrigin = [0.0, 0.0, 0.0]
                imageSpacing = [1.0, 1.0, 1.0]
                imageDirections = [[-1, 0, 0], [0, -1, 0], [0, 0, 1]]
                fillVoxelValue = 0

                # Create an empty image volume, filled with fillVoxelValue
                imageData = vtk.vtkImageData()
                imageData.SetDimensions(imageSize)
                imageData.AllocateScalars(voxelType, 1)
                imageData.GetPointData().GetScalars().Fill(fillVoxelValue)

                # Create volume node
                # Needs to be a vector volume in order to show in colour

                volumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", channelName)
                volumeNode.SetOrigin(imageOrigin)
                volumeNode.SetSpacing(imageSpacing)
                volumeNode.SetIJKToRASDirections(imageDirections)
                volumeNode.SetAndObserveImageData(imageData)
                volumeNode.CreateDefaultDisplayNodes()
                volumeNode.CreateDefaultStorageNode()

                voxels = slicer.util.arrayFromVolume(volumeNode)
                voxels[:] = channelArray

                volumeNode.Modified()

                # After creating volume node, need to manipulate subject hierarchy
                shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
                # Get channel node id
                volumeId = shNode.GetItemByDataNode(volumeNode)
                # Get scene id
                sceneId = shNode.GetItemParent(volumeId)

                if index == 0:
                    # Create ROI folder
                    # shNode.CreateFolderItem(volumeId, nameOfFolder)
                    folderId = shNode.CreateFolderItem(sceneId, roiName)
                    # shNode.SetItemParent(folderId, sceneId)
                # Set image to be a child of ROI folder
                shNode.SetItemParent(volumeId, folderId)

            roiCount += 1


    def visualizationRun(self, roiSelect, redSelect, greenSelect, blueSelect, yellowSelect, cyanSelect, magentaSelect, whiteSelect, threshMin, threshMax):
        """
        Runs the algorithm to display the volumes selected in "Visualization" in their respective colours
        """
        # Delete any existing image overlays
        existingOverlays = slicer.util.getNodesByClass("vtkMRMLVectorVolumeNode")

        # Make dictionary of the selected channels
        selectChannels = {} # key = colour, value = node
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
        allChannels = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
        for channel in allChannels:
            name = channel.GetName()
            if redSelect in name:
                # Check if channel is the correct ROI
                id = shNode.GetItemByDataNode(channel)
                parent = shNode.GetItemParent(id)
                if roiSelect == "ROI":
                    selectChannels["red"] = channel
                else:
                    roiName = shNode.GetItemName(parent)
                    if roiName == roiSelect:
                        selectChannels["red"] = channel
            elif greenSelect in name:
                # Check if channel is the correct ROI
                id = shNode.GetItemByDataNode(channel)
                parent = shNode.GetItemParent(id)
                if roiSelect == "ROI":
                    selectChannels["green"] = channel
                else:
                    roiName = shNode.GetItemName(parent)
                    if roiName == roiSelect:
                        selectChannels["green"] = channel
            elif blueSelect in name:
                # Check if channel is the correct ROI
                id = shNode.GetItemByDataNode(channel)
                parent = shNode.GetItemParent(id)
                if roiSelect == "ROI":
                    selectChannels["blue"] = channel
                else:
                    roiName = shNode.GetItemName(parent)
                    if roiName == roiSelect:
                        selectChannels["blue"] = channel
            elif yellowSelect in name:
                # Check if channel is the correct ROI
                id = shNode.GetItemByDataNode(channel)
                parent = shNode.GetItemParent(id)
                if roiSelect == "ROI":
                    selectChannels["yellow"] = channel
                else:
                    roiName = shNode.GetItemName(parent)
                    if roiName == roiSelect:
                        selectChannels["yellow"] = channel
            elif cyanSelect in name:
                # Check if channel is the correct ROI
                id = shNode.GetItemByDataNode(channel)
                parent = shNode.GetItemParent(id)
                if roiSelect == "ROI":
                    selectChannels["cyan"] = channel
                else:
                    roiName = shNode.GetItemName(parent)
                    if roiName == roiSelect:
                        selectChannels["cyan"] = channel
            elif magentaSelect in name:
                # Check if channel is the correct ROI
                id = shNode.GetItemByDataNode(channel)
                parent = shNode.GetItemParent(id)
                if roiSelect == "ROI":
                    selectChannels["magenta"] = channel
                else:
                    roiName = shNode.GetItemName(parent)
                    if roiName == roiSelect:
                        selectChannels["magenta"] = channel
            elif whiteSelect in name:
                # Check if channel is the correct ROI
                id = shNode.GetItemByDataNode(channel)
                parent = shNode.GetItemParent(id)
                if roiSelect == "ROI":
                    selectChannels["white"] = channel
                else:
                    roiName = shNode.GetItemName(parent)
                    if roiName == roiSelect:
                        selectChannels["white"] = channel
        saveImageName = ""
        arrayList = []
        arraySize = None
        for colour in selectChannels:
            if colour == "red":
                name = redSelect[:-4]
                saveImageName += name
                # Set redscale array
                array = slicer.util.arrayFromVolume(selectChannels[colour])
                if array.shape[0] != 1:
                    array = array[49]
                    array = np.expand_dims(array, axis=0)
                # Scale the array
                scaled = np.interp(array, (array.min(), array.max()), (0, 255))
                if arraySize == None:
                    arraySize = scaled.shape
                stacked = np.stack((scaled,) * 3, axis=-1)
                stacked[:, :, :, 1] = 0
                stacked[:, :, :, 2] = 0
                arrayList.append(stacked)
            elif colour == "green":
                name = greenSelect[:-4]
                saveImageName += name
                # Set greenscale array
                array = slicer.util.arrayFromVolume(selectChannels[colour])
                # Scale the array
                scaled = np.interp(array, (array.min(), array.max()), (0, 255))
                if arraySize == None:
                    arraySize = scaled.shape
                stacked = np.stack((scaled,) * 3, axis=-1)
                stacked[:, :, :, 0] = 0
                stacked[:, :, :, 2] = 0
                arrayList.append(stacked)
            elif colour == "blue":
                name = blueSelect[:-4]
                saveImageName += name
                # Set bluescale array
                array = slicer.util.arrayFromVolume(selectChannels[colour])
                # Scale the array
                scaled = np.interp(array, (array.min(), array.max()), (0, 255))
                if arraySize == None:
                    arraySize = scaled.shape
                stacked = np.stack((scaled,) * 3, axis=-1)
                stacked[:, :, :, 0] = 0
                stacked[:, :, :, 1] = 0
                arrayList.append(stacked)
            elif colour == "yellow":
                name = yellowSelect[:-4]
                saveImageName += name
                # Set bluescale array
                array = slicer.util.arrayFromVolume(selectChannels[colour])
                # Scale the array
                scaled = np.interp(array, (array.min(), array.max()), (0, 255))
                if arraySize == None:
                    arraySize = scaled.shape
                stacked = np.stack((scaled,) * 3, axis=-1)
                stacked[:, :, :, 2] = 0
                arrayList.append(stacked)
            elif colour == "cyan":
                name = cyanSelect[:-4]
                saveImageName += name
                # Set bluescale array
                array = slicer.util.arrayFromVolume(selectChannels[colour])
                # Scale the array
                scaled = np.interp(array, (array.min(), array.max()), (0, 255))
                if arraySize == None:
                    arraySize = scaled.shape
                stacked = np.stack((scaled,) * 3, axis=-1)
                stacked[:, :, :, 0] = 0
                arrayList.append(stacked)
            elif colour == "magenta":
                name = magentaSelect[:-4]
                saveImageName += name
                # Set bluescale array
                array = slicer.util.arrayFromVolume(selectChannels[colour])
                # Scale the array
                scaled = np.interp(array, (array.min(), array.max()), (0, 255))
                if arraySize == None:
                    arraySize = scaled.shape
                stacked = np.stack((scaled,) * 3, axis=-1)
                stacked[:, :, :, 1] = 0
                arrayList.append(stacked)
            elif colour == "white":
                name = whiteSelect[:-4]
                saveImageName += name
                # Set bluescale array
                array = slicer.util.arrayFromVolume(selectChannels[colour])
                # Scale the array
                scaled = np.interp(array, (array.min(), array.max()), (0, 255))
                if arraySize == None:
                    arraySize = scaled.shape
                stacked = np.stack((scaled,) * 3, axis=-1)
                arrayList.append(stacked)

        overlay = sum(arrayList)

        # Run helper function
        HypModuleLogic().visualizationRunHelper(overlay, threshMin, threshMax, saveImageName, arraySize,
                                                existingOverlays)
        return True


    def visualizationRunHelper(self, overlay, threshMin, threshMax, saveImageName, arraySize, existingOverlays):

        # Set array with thresholded values
        overlay[overlay < threshMin] = 0
        threshMaxVal = 255 - threshMax
        overlay[overlay > threshMaxVal] = 255

        # Create new volume "Image Overlay"
        # Set name of overlaid image to be the names of all the channels being overlaid
        imageSize = [arraySize[2], arraySize[1], 1]
        voxelType = vtk.VTK_UNSIGNED_CHAR
        imageOrigin = [0.0, 0.0, 0.0]
        imageSpacing = [1.0, 1.0, 1.0]
        imageDirections = [[-1, 0, 0], [0, -1, 0], [0, 0, 1]]
        fillVoxelValue = 0

        # Create an empty image volume, filled with fillVoxelValue
        imageData = vtk.vtkImageData()
        imageData.SetDimensions(imageSize)
        imageData.AllocateScalars(voxelType, 3)
        imageData.GetPointData().GetScalars().Fill(fillVoxelValue)

        # Create volume node
        # Needs to be a vector volume in order to show in colour
        volumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLVectorVolumeNode", saveImageName)
        volumeNode.SetOrigin(imageOrigin)
        volumeNode.SetSpacing(imageSpacing)
        volumeNode.SetIJKToRASDirections(imageDirections)
        volumeNode.SetAndObserveImageData(imageData)
        volumeNode.CreateDefaultDisplayNodes()
        volumeNode.CreateDefaultStorageNode()

        voxels = slicer.util.arrayFromVolume(volumeNode)
        voxels[:] = overlay

        volumeNode.Modified()

        slicer.util.setSliceViewerLayers(background=volumeNode, foreground=None)

        for overlay in existingOverlays:
            slicer.mrmlScene.RemoveNode(overlay)

        global nodeName
        nodeName = saveImageName
        # Set slice view to display Red window only
        lm = slicer.app.layoutManager()
        lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)

        # Reset field of view to show entire image
        slicer.util.resetSliceViews()

        # Fix window/level values
        widget = slicer.vtkMRMLWindowLevelWidget()
        widget.SetSliceNode(slicer.util.getNode('vtkMRMLSliceNodeRed'))
        widget.SetMRMLApplicationLogic(slicer.app.applicationLogic())
        p1 = voxels.shape[1] // 2
        p2 = voxels.shape[2] // 2
        widget.UpdateWindowLevelFromRectangle(0, [p1, p1], [p2, p2])
        # widget.UpdateWindowLevelFromRectangle(0, [60, 60], [45, 45])

    def thumbnails(self):
        """
        Generate thumbnails for all loaded images
        """
        from PIL import Image, ImageOps

        existingOverviews = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")

        for node in existingOverviews:
            if "Thumbnail Overview" in node.GetName():
                slicer.mrmlScene.RemoveNode(node)

        positions = []
        channelNodes = []
        # shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)

        for roi in selectedRoi:
            positions.append(roiDict[roi])

        for channel in selectedChannel:
            for pos in positions:
                if pos == 0:
                    node = slicer.util.getNode(channel)
                    # itemId = shNode.GetItemByDataNode(node)
                    channelNodes.append(node)
                else:
                    suffix = "_" + str(pos)
                    name = channel + suffix
                    node = slicer.util.getNode(name)
                    # itemId = shNode.GetItemByDataNode(node)
                    channelNodes.append(node)

        size = 400,400
        thumbnailArrays = []
        for node in channelNodes:
            array = slicer.util.arrayFromVolume(node)
            img = Image.fromarray(array[0])
            img = img.convert("L")
            img.thumbnail(size)
            img = ImageOps.autocontrast(img)
            # img = ImageOps.equalize(img)
            thumbArr = np.array(img)
            thumbnailArrays.append(thumbArr)

        from skimage.util import montage
        arrIn = np.stack(thumbnailArrays, axis=0)
        mont = montage(arrIn)
        img = Image.fromarray(mont)
        # img = img.convert("L")
        # img = ImageOps.equalize(img)
        grid = np.array(img)
        arraySize = grid.shape

        # Create image node out of array
        imageSize = [arraySize[1], arraySize[0], 1]
        voxelType = vtk.VTK_UNSIGNED_CHAR
        imageOrigin = [0.0, 0.0, 0.0]
        imageSpacing = [1.0, 1.0, 1.0]
        imageDirections = [[-1, 0, 0], [0, -1, 0], [0, 0, 1]]
        fillVoxelValue = 0

        # Create an empty image volume, filled with fillVoxelValue
        imageData = vtk.vtkImageData()
        imageData.SetDimensions(imageSize)
        imageData.AllocateScalars(voxelType, 1)
        imageData.GetPointData().GetScalars().Fill(fillVoxelValue)

        # Create volume node
        # Needs to be a vector volume in order to show in colour
        volumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "Thumbnail Overview")
        volumeNode.SetOrigin(imageOrigin)
        volumeNode.SetSpacing(imageSpacing)
        volumeNode.SetIJKToRASDirections(imageDirections)
        volumeNode.SetAndObserveImageData(imageData)
        volumeNode.CreateDefaultDisplayNodes()
        volumeNode.CreateDefaultStorageNode()

        voxels = slicer.util.arrayFromVolume(volumeNode)
        voxels[:] = grid

        volumeNode.Modified()



        slicer.util.setSliceViewerLayers(background=volumeNode, foreground=None)

        # Set slice view to display Red window only
        lm = slicer.app.layoutManager()
        lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)

        slicer.util.resetSliceViews()

        # Fix window/level values
        widget = slicer.vtkMRMLWindowLevelWidget()
        widget.SetSliceNode(slicer.util.getNode('vtkMRMLSliceNodeRed'))
        widget.SetMRMLApplicationLogic(slicer.app.applicationLogic())
        p1 = voxels.shape[1]//2
        # p1Range = (voxels.shape[1]//4)//2
        p2 = voxels.shape[2]//2
        # p2Range = (voxels.shape[2] // 8) // 2
        # widget.UpdateWindowLevelFromRectangle(0, [p1-p1Range, p2-p2Range], [p1+p1Range,p2+p2Range])
        widget.UpdateWindowLevelFromRectangle(0, [p1 - 50, p2 - 50], [p1 + 50, p2 + 50])
        # widget.UpdateWindowLevelFromRectangle(0, [800, 800], [500,500])


    def saveVisualization(self, fileName):
        viewNodeID = 'vtkMRMLSliceNodeRed'
        import ScreenCapture
        cap = ScreenCapture.ScreenCaptureLogic()
        view = cap.viewFromNode(slicer.mrmlScene.GetNodeByID(viewNodeID))
        defaultPath = slicer.app.defaultScenePath
        pathName = defaultPath + '/' + fileName
        cap.captureImageFromView(view, pathName)
        import subprocess
        try:
            subprocess.Popen('explorer defaultPath')
        except:
            subprocess.Popen(["open", defaultPath])

    def crtMasksRun(self, nucleiMin, nucleiMax, cellDimInput):
        """
        Perform threshold segmentation on the nucleiImageInput
        """

        positions = []
        channelItems = []
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)

        for roi in selectedRoi:
            positions.append(roiDict[roi])

        for channel in selectedChannel:
            for pos in positions:
                if pos == 0:
                    node = slicer.util.getNode(channel)
                    itemId = shNode.GetItemByDataNode(node)
                    channelItems.append(itemId)
                else:
                    suffix = "_" + str(pos)
                    name = channel + suffix
                    node = slicer.util.getNode(name)
                    itemId = shNode.GetItemByDataNode(node)
                    channelItems.append(itemId)

        # Set dictionary for number of cells of each mask
        nCells = {}

        # Set "global" variables for nucleus, cell, and cytoplasm volumes, in order to display later
        nucleusMaskVolume = None
        cellMaskVolume = None
        cytoplasmMaskVolume = None
        dnaNode = None

        # For each nucleus mask, run this loop; parentDict length should be number of ROI's
        for itemId in channelItems:
            # Get array of channel
            parent = shNode.GetItemParent(itemId)  # ROI
            roiName = shNode.GetItemName(parent)
            dnaName = shNode.GetItemName(itemId)
            dnaNode = slicer.util.getNode(dnaName)
            dnaArray = slicer.util.arrayFromVolume(dnaNode)#[47]
            # dnaArray = np.expand_dims(dnaArray, axis=0)
            dnaImg = sitk.GetImageFromArray(dnaArray)

            # Delete any existing masks
            existingVolumes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")

            for img in existingVolumes:
                if roiName + " Nucleus Mask" in img.GetName():
                    slicer.mrmlScene.RemoveNode(img)
                elif roiName + " Cell Mask" in img.GetName():
                    slicer.mrmlScene.RemoveNode(img)
                elif roiName + " Cytoplasm Mask" in img.GetName():
                    slicer.mrmlScene.RemoveNode(img)

            # Rescale image
            filter = sitk.RescaleIntensityImageFilter()
            filter.SetOutputMinimum(0)
            filter.SetOutputMaximum(255)
            rescaled = filter.Execute(dnaImg)
            # Adjust contrast
            filter = sitk.AdaptiveHistogramEqualizationImageFilter()
            contrasted = filter.Execute(rescaled)
            # Otsu thresholding
            filter = sitk.OtsuThresholdImageFilter()
            t_otsu = filter.Execute(contrasted)
            # Closing
            filter = sitk.BinaryMorphologicalClosingImageFilter()
            binImg = filter.Execute(t_otsu)

            # Connected-component labeling
            min_img = sitk.RegionalMinima(binImg, backgroundValue=0, foregroundValue=1.0, fullyConnected=False,
                                          flatIsMinima=True)
            labeled = sitk.ConnectedComponent(min_img)
            # Fill holes in image
            filter = sitk.BinaryFillholeImageFilter()
            filled = filter.Execute(binImg)
            # Distance Transform
            dist = sitk.SignedMaurerDistanceMap(filled != 0, insideIsPositive=False, squaredDistance=False,
                                                useImageSpacing=False)
            # Get seeds
            # if dnaImg.GetSpacing()[0] <= 0.001:
            #     sigma = dnaImg.GetSpacing()[0]
            # else:
            #     sigma = 0.001
            sigma = 0.0001
            seeds = sitk.ConnectedComponent(dist < -sigma)
            seeds = sitk.RelabelComponent(seeds)

            # Invert distance transform to use with watershed
            distInvert = -1*dist
            # Watershed using distance transform
            ws = sitk.MorphologicalWatershedFromMarkers(distInvert, seeds)
            ws = sitk.Mask(ws, sitk.Cast(labeled, ws.GetPixelID()))
            ws = sitk.ConnectedComponent(ws)

            # Generate nucleus mask array
            nucleusMaskArray = sitk.GetArrayFromImage(ws)

            # Remove nuclei too small or large
            stats = sitk.LabelShapeStatisticsImageFilter()
            stats.Execute(ws)

            labelSizes = {}

            for label in stats.GetLabels():
                labelSizes[label] = stats.GetNumberOfPixels(label)

            for i in labelSizes:
                if i != 0:
                    if labelSizes[i] > nucleiMax:
                        nucleusMaskArray[nucleusMaskArray == i] = 0
                    elif labelSizes[i] < nucleiMin:
                        nucleusMaskArray[nucleusMaskArray == i] = 0

            # Manually remove border cells
            nucMaskShape = nucleusMaskArray.shape
            for i in range(nucMaskShape[2]):
                label = nucleusMaskArray[0][0][i]
                if label != 0:
                    nucleusMaskArray[nucleusMaskArray == label] = 0
                label = nucleusMaskArray[0][nucMaskShape[1]-1][i]
                if label != 0:
                    nucleusMaskArray[nucleusMaskArray == label] = 0
            for i in range(nucMaskShape[1]):
                label = nucleusMaskArray[0][i][0]
                if label != 0:
                    nucleusMaskArray[nucleusMaskArray == label] = 0
                label = nucleusMaskArray[0][i][nucMaskShape[2] - 1]
                if label != 0:
                    nucleusMaskArray[nucleusMaskArray == label] = 0

            # Create simpleitk object of nucleus mask
            nucleusMaskObject = sitk.GetImageFromArray(nucleusMaskArray)

            # Create new volume using the nucleus mask array
            name = roiName + " Nucleus Mask"
            nucleusMaskVolume = slicer.modules.volumes.logic().CloneVolume(dnaNode, name)
            slicer.util.updateVolumeFromArray(nucleusMaskVolume, nucleusMaskArray)

            # Change colormap of volume
            labels = slicer.util.getFirstNodeByName("Labels")
            nucleusDisplayNode = nucleusMaskVolume.GetScalarVolumeDisplayNode()
            nucleusDisplayNode.SetAndObserveColorNodeID(labels.GetID())

            # Create cell mask
            # cellDilate = sitk.BinaryDilate(nucleusMaskObject!=0, cellDimInput)
            filter = sitk.BinaryDilateImageFilter()
            filter.SetKernelRadius(cellDimInput)
            cellDilate = filter.Execute(nucleusMaskObject!=0)
            distCell = sitk.SignedMaurerDistanceMap(nucleusMaskObject != 0, insideIsPositive=False, squaredDistance=False,
                                                    useImageSpacing=False)
            wsdCell = sitk.MorphologicalWatershedFromMarkers(distCell, nucleusMaskObject, markWatershedLine=False)
            cellMask = sitk.Mask(wsdCell, cellDilate)
            cellMaskArray = sitk.GetArrayFromImage(cellMask)

            # Manually remove border cells
            cellMaskShape = cellMaskArray.shape
            for i in range(cellMaskShape[2]):
                label = cellMaskArray[0][0][i]
                if label != 0:
                    cellMaskArray[cellMaskArray == label] = 0
                label = cellMaskArray[0][cellMaskShape[1] - 1][i]
                if label != 0:
                    cellMaskArray[cellMaskArray == label] = 0
            for i in range(cellMaskShape[1]):
                label = cellMaskArray[0][i][0]
                if label != 0:
                    cellMaskArray[cellMaskArray == label] = 0
                label = cellMaskArray[0][i][cellMaskShape[2] - 1]
                if label != 0:
                    cellMaskArray[cellMaskArray == label] = 0

            nCells[roiName] = len(np.unique(cellMaskArray)) - 1 # subtracting 1 for the "0" labels

            # Create new volume using cell mask array
            name = roiName + " Cell Mask"
            cellMaskVolume = slicer.modules.volumes.logic().CloneVolume(dnaNode, name)
            slicer.util.updateVolumeFromArray(cellMaskVolume, cellMaskArray)
            global globalCellMask
            globalCellMask[roiName] = cellMaskVolume

            # Change colormap of volume
            labels = slicer.util.getFirstNodeByName("Labels")
            cellDisplayNode = cellMaskVolume.GetScalarVolumeDisplayNode()
            cellDisplayNode.SetAndObserveColorNodeID(labels.GetID())

            # Create cytoplasm mask
            cytoplasmMaskArray = cellMaskArray[:]
            cytoplasmMaskArray[cytoplasmMaskArray == nucleusMaskArray] = 0

            # Create new volume using cytoplasm mask array
            name = roiName + " Cytoplasm Mask"
            cytoplasmMaskVolume = slicer.modules.volumes.logic().CloneVolume(dnaNode, name)
            slicer.util.updateVolumeFromArray(cytoplasmMaskVolume, cytoplasmMaskArray)

            # Change colormap of volume
            labels = slicer.util.getFirstNodeByName("Labels")
            cytoplasmDisplayNode = cytoplasmMaskVolume.GetScalarVolumeDisplayNode()
            cytoplasmDisplayNode.SetAndObserveColorNodeID(labels.GetID())

        # View nucleus image in window
        slicer.util.setSliceViewerLayers(background=nucleusMaskVolume, foreground=None)
        lm = slicer.app.layoutManager()
        lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutTwoOverTwoView)

        # Set red slice to show the heatmap
        red_logic = slicer.app.layoutManager().sliceWidget("Red").sliceLogic()
        red_logic.GetSliceCompositeNode().SetBackgroundVolumeID(nucleusMaskVolume.GetID())

        # Set yellow slice to show cloned, thresholded channel
        yellow_widget = slicer.app.layoutManager().sliceWidget("Yellow")
        yellow_widget.setSliceOrientation("Axial")
        # yellowDisplayNode = channelOne.GetScalarVolumeDisplayNode()
        # yellowDisplayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeRed")
        yellow_logic = yellow_widget.sliceLogic()
        yellow_logic.GetSliceCompositeNode().SetBackgroundVolumeID(cellMaskVolume.GetID())

        # Set green slice to show cell mask
        green_widget = slicer.app.layoutManager().sliceWidget("Green")
        green_widget.setSliceOrientation("Axial")
        # greenDisplayNode = channelTwo.GetScalarVolumeDisplayNode()
        # greenDisplayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeRed")
        green_logic = green_widget.sliceLogic()
        green_logic.GetSliceCompositeNode().SetBackgroundVolumeID(cytoplasmMaskVolume.GetID())

        # Set black slice to show original nucleus channel
        blackDisplayNode = dnaNode.GetScalarVolumeDisplayNode()
        blackDisplayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeRed")
        black_logic = slicer.app.layoutManager().sliceWidget("Slice4").sliceLogic()
        black_logic.GetSliceCompositeNode().SetBackgroundVolumeID(dnaNode.GetID())

        slicer.util.resetSliceViews()

        # Fix window/level values
        widget = slicer.vtkMRMLWindowLevelWidget()
        widget.SetSliceNode(slicer.util.getNode('Slice4'))
        widget.SetMRMLApplicationLogic(slicer.app.applicationLogic())
        p1 = dnaArray.shape[1] // 2
        p2 = dnaArray.shape[2] // 2
        widget.UpdateWindowLevelFromRectangle(0, [p1, p1], [p2, p2])

        # Fix window/level values
        widget = slicer.vtkMRMLWindowLevelWidget()
        widget.SetSliceNode(slicer.util.getNode('vtkMRMLSliceNodeRed'))
        widget.SetMRMLApplicationLogic(slicer.app.applicationLogic())
        p2 = dnaArray.shape[1]
        widget.UpdateWindowLevelFromRectangle(0, [0, 0], [p2, p2])

        # Fix window/level values
        widget = slicer.vtkMRMLWindowLevelWidget()
        widget.SetSliceNode(slicer.util.getNode('vtkMRMLSliceNodeGreen'))
        widget.SetMRMLApplicationLogic(slicer.app.applicationLogic())
        widget.UpdateWindowLevelFromRectangle(0, [0, 0], [p2, p2])

        # Fix window/level values
        widget = slicer.vtkMRMLWindowLevelWidget()
        widget.SetSliceNode(slicer.util.getNode('vtkMRMLSliceNodeYellow'))
        widget.SetMRMLApplicationLogic(slicer.app.applicationLogic())
        widget.UpdateWindowLevelFromRectangle(0, [0, 0], [p2, p2])

        return nCells


    def analysisRun(self):
        """
        Create histogram of intensity values of the selected image
        """

        # Delete any existing plots
        existingPlots = slicer.util.getNodesByClass("vtkMRMLPlotChartNode")
        existingSeriesNodes = slicer.util.getNodesByClass("vtkMRMLPlotSeriesNode")
        existingTables = slicer.util.getNodesByClass("vtkMRMLTableNode")

        for plot in existingPlots:
            slicer.mrmlScene.RemoveNode(plot)
        for seriesNode in existingSeriesNodes:
            slicer.mrmlScene.RemoveNode(seriesNode)
        for table in existingTables:
            slicer.mrmlScene.RemoveNode(table)

        positions = []
        channelItems = []
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)

        for roi in selectedRoi:
            positions.append(roiDict[roi])

        for channel in selectedChannel:
            for pos in positions:
                if pos == 0:
                    node = slicer.util.getNode(channel)
                    itemId = shNode.GetItemByDataNode(node)
                    channelItems.append(itemId)
                else:
                    suffix = "_" + str(pos)
                    name = channel + suffix
                    node = slicer.util.getNode(name)
                    itemId = shNode.GetItemByDataNode(node)
                    channelItems.append(itemId)

        # Set "global" variables in order to display later
        tableNode = None
        plotChartNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotChartNode",
                                                           "Histogram of Channel Mean Intensities")
        plotChartNode.SetTitle("Histogram of Channel Mean Intensities")
        plotChartNode.SetXAxisTitle("Mean Intensity of Channel in Cell (Bins)")
        plotChartNode.SetYAxisTitle("Count")
        displayList = []

        # Set a count to determine what colour the plot series will be
        count = 0

        # For each channel, run this loop to create histogram; parentDict length should be number of channels to be plotted

        # for itemId in parentDict:
        for itemId in channelItems:

            count +=1
            # Get array of channel
            parent = shNode.GetItemParent(itemId)
            roiName = shNode.GetItemName(parent)
            channelName = shNode.GetItemName(itemId)
            channelNode = slicer.util.getNode(channelName)
            channelArray = slicer.util.arrayFromVolume(channelNode)

            if count <= 3:
                displayList.append(channelNode)

            # Get array for cell mask
            cellMask = globalCellMask[roiName]
            cellMaskArray = slicer.util.arrayFromVolume(cellMask)

            # Get counts of pixels in each cell
            cell, counts = np.unique(cellMaskArray, return_counts=True)
            cellPixelCounts = dict(zip(cell, counts))

            channelMeanIntens = []

            for cell in cellPixelCounts.keys():
                if cell != 0:
                    blank, i, j = np.nonzero(cellMaskArray == cell)
                    # if blank.shape[0] != 0 and i.shape[0] == 0 and j.shape[0] == 0:
                    cellPixels = channelArray[:, i, j]
                    sumIntens = np.sum(cellPixels)
                    nonZeroes = np.where(cellPixels != 0)
                    numNonZeroes = nonZeroes[1].shape[0]
                    if numNonZeroes == 0:
                        # avg = 0
                        continue
                    else:
                        avg = float(sumIntens) / float(numNonZeroes)
                    channelMeanIntens.append(avg)

            histogram = np.histogram(channelMeanIntens, bins=20)

            # Save results to a new table node
            tableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", channelName + "_" + roiName + 'data')
            slicer.util.updateTableFromArray(tableNode, histogram)
            tableNode.GetTable().GetColumn(0).SetName("Count")
            tableNode.GetTable().GetColumn(1).SetName("Intensity")

            # Create plot
            plotSeriesNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotSeriesNode",
                                                                channelName + "_" + roiName + " series")
            plotSeriesNode.SetAndObserveTableNodeID(tableNode.GetID())
            plotSeriesNode.SetXColumnName("Intensity")
            plotSeriesNode.SetYColumnName("Count")
            plotSeriesNode.SetPlotType(plotSeriesNode.PlotTypeBar)
            plotSeriesNode.SetColor(tuple(np.random.choice(range(256), size=3)))

            # Create chart and add plot
            plotChartNode = slicer.util.getNode("Histogram of Channel Mean Intensities")
            plotChartNode.AddAndObservePlotSeriesNodeID(plotSeriesNode.GetID())

        # Show plot in layout
        slicer.modules.plots.logic().ShowChartInLayout(plotChartNode)
        slicer.app.layoutManager().setLayout(
            slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpPlotView)  # or SlicerLayoutThreeOverThreePlotView
        slicer.app.applicationLogic().GetSelectionNode().SetReferenceActiveTableID(tableNode.GetID())
        slicer.app.applicationLogic().PropagateTableSelection()

        # Set red slice to show the heatmap
        redDisplayNode = displayList[0].GetScalarVolumeDisplayNode()
        redArray = slicer.util.arrayFromVolume(displayList[0])
        redDisplayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeRed")
        red_logic = slicer.app.layoutManager().sliceWidget("Red").sliceLogic()
        red_logic.GetSliceCompositeNode().SetBackgroundVolumeID(displayList[0].GetID())

        # Set green slice to show cell mask
        green_widget = slicer.app.layoutManager().sliceWidget("Green")
        green_widget.setSliceOrientation("Axial")
        if len(displayList) > 1:
            greenDisplayNode = displayList[1].GetScalarVolumeDisplayNode()
            greenArray = slicer.util.arrayFromVolume(displayList[1])
            greenDisplayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeGreen")
            green_logic = green_widget.sliceLogic()
            green_logic.GetSliceCompositeNode().SetBackgroundVolumeID(displayList[1].GetID())
        else:
            green_logic = green_widget.sliceLogic()
            green_logic.GetSliceCompositeNode().SetBackgroundVolumeID(displayList[0].GetID())
            greenArray = slicer.util.arrayFromVolume(displayList[0])

        # Set yellow slice to show cloned, thresholded channel
        yellow_widget = slicer.app.layoutManager().sliceWidget("Yellow")
        yellow_widget.setSliceOrientation("Axial")
        if len(displayList) > 2:
            yellowDisplayNode = displayList[2].GetScalarVolumeDisplayNode()
            yellowArray = slicer.util.arrayFromVolume(displayList[2])
            yellowDisplayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeBlue")
            yellow_logic = yellow_widget.sliceLogic()
            yellow_logic.GetSliceCompositeNode().SetBackgroundVolumeID(displayList[2].GetID())
        else:
            yellow_logic = yellow_widget.sliceLogic()
            yellow_logic.GetSliceCompositeNode().SetBackgroundVolumeID(displayList[0].GetID())
            yellowArray = slicer.util.arrayFromVolume(displayList[0])

        # Fix window/level values
        widget = slicer.vtkMRMLWindowLevelWidget()
        widget.SetSliceNode(slicer.util.getNode('vtkMRMLSliceNodeRed'))
        widget.SetMRMLApplicationLogic(slicer.app.applicationLogic())
        p1 = redArray.shape[1] // 2
        p2 = redArray.shape[2] // 2
        widget.UpdateWindowLevelFromRectangle(0, [p1, p1], [p2, p2])

        # Fix window/level values
        widget = slicer.vtkMRMLWindowLevelWidget()
        widget.SetSliceNode(slicer.util.getNode('vtkMRMLSliceNodeGreen'))
        widget.SetMRMLApplicationLogic(slicer.app.applicationLogic())
        p1 = greenArray.shape[1] // 2
        p2 = greenArray.shape[2] // 2
        widget.UpdateWindowLevelFromRectangle(0, [p1, p1], [p2, p2])

        # Fix window/level values
        widget = slicer.vtkMRMLWindowLevelWidget()
        widget.SetSliceNode(slicer.util.getNode('vtkMRMLSliceNodeYellow'))
        widget.SetMRMLApplicationLogic(slicer.app.applicationLogic())
        p1 = yellowArray.shape[1] // 2
        p2 = yellowArray.shape[2] // 2
        widget.UpdateWindowLevelFromRectangle(0, [p1, p1], [p2, p2])

        slicer.util.resetSliceViews()

    def scatterPlotRun(self, checkboxState, arcsinState, logState):

        """
        Create scatter plot of channelOne x channelTwo, where data points are the cells, values are the mean intensity
        of each channel within that cell
        """

        # Delete any existing plots
        existingPlots = slicer.util.getNodesByClass("vtkMRMLPlotChartNode")
        existingSeriesNodes = slicer.util.getNodesByClass("vtkMRMLPlotSeriesNode")
        existingTables = slicer.util.getNodesByClass("vtkMRMLTableNode")
        existingNodes = slicer.util.getNodesByClass("vtkMRMLVectorVolumeNode")

        for table in existingTables:
            slicer.mrmlScene.RemoveNode(table)

        positions = []
        channelItems = []
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)

        for roi in selectedRoi:
            positions.append(roiDict[roi])

        for channel in selectedChannel:
            for pos in positions:
                if pos == 0:
                    node = slicer.util.getNode(channel)
                    itemId = shNode.GetItemByDataNode(node)
                    channelItems.append(itemId)
                else:
                    suffix = "_" + str(pos)
                    name = channel + suffix
                    node = slicer.util.getNode(name)
                    itemId = shNode.GetItemByDataNode(node)
                    channelItems.append(itemId)

        # channels = list(parentDict.keys())
        # Get ROI name or Selected Cells mask
        if checkboxState == False:
            parent = shNode.GetItemParent(channelItems[0])  # ROI
            roiName = shNode.GetItemName(parent)
        else:
            roiName = selectedGates[0]

        # Get array of channel

        channelOneName = shNode.GetItemName(channelItems[0])
        channelOneNode = slicer.util.getNode(channelOneName)
        channelOneArray = slicer.util.arrayFromVolume(channelOneNode)
        channelTwoName = shNode.GetItemName(channelItems[1])
        channelTwoNode = slicer.util.getNode(channelTwoName)
        channelTwoArray = slicer.util.arrayFromVolume(channelTwoNode)

        if arcsinState == True:
            channelOneTransform = np.interp(channelOneArray, (channelOneArray.min(), channelOneArray.max()), (0, 1))
            channelTwoTransform = np.interp(channelTwoArray, (channelTwoArray.min(), channelTwoArray.max()), (0, 1))
            channelOneTransform = np.sqrt(channelOneTransform)
            channelTwoTransform = np.sqrt(channelTwoTransform)
            channelOneArray = np.arcsin(channelOneTransform)
            channelTwoArray = np.arcsin(channelTwoTransform)

        if logState == True:
            channelOneArray = np.log(channelOneArray+1)
            channelTwoArray = np.log(channelTwoArray+1)

        # Get arrays for cell mask and channels
        cellMask = globalCellMask[roiName]
        cellMaskArray = slicer.util.arrayFromVolume(cellMask)

        # Get counts of pixels in each cell
        cell, counts = np.unique(cellMaskArray, return_counts=True)
        cellPixelCounts = dict(zip(cell, counts))

        # Create list of mean intensities for all cells for each channel
        channelOneMeanIntens = []
        channelTwoMeanIntens = []
        cellLabels = []

        for cell in range(cellMaskArray.max() + 1):
            if cell != 0:
                if cell in cellPixelCounts.keys():
                    # Channel one
                    blank, i, j = np.nonzero(cellMaskArray == cell)
                    cellPixels = channelOneArray[:, i, j]
                    sumIntens = np.sum(cellPixels)
                    totalPixels = cellPixels.shape[1]
                    nonZeroes = np.where(cellPixels != 0)
                    numNonZeroes = nonZeroes[1].shape[0]
                    if numNonZeroes == 0:
                        avg = 0
                    else:
                        avg = float(sumIntens) / float(totalPixels)
                    # print("Sum Intensity: " + str(sumIntens) + " total pixels: " + str(totalPixels) + " avg: " + str(avg))
                    channelOneMeanIntens.append(avg)
                    # Channel two
                    cellPixelsTwo = channelTwoArray[:, i, j]
                    sumIntensTwo = np.sum(cellPixelsTwo)
                    totalPixelsTwo = cellPixelsTwo.shape[1]
                    nonZeroesTwo = np.where(cellPixelsTwo != 0)
                    numNonZeroesTwo = nonZeroesTwo[1].shape[0]
                    if numNonZeroesTwo == 0:
                        avgTwo = 0
                    else:
                        avgTwo = float(sumIntensTwo) / float(totalPixelsTwo)
                    channelTwoMeanIntens.append(avgTwo)
                    # Cell label
                    cellLabels.append(cell)

        # Set x and y values
        x = channelOneMeanIntens
        y = channelTwoMeanIntens
        z = cellLabels
        nPoints = len(x)

        # Create table with x and y columns
        tableName = roiName + ": " + channelOneName + " x " + channelTwoName + " data"
        tableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", tableName)

        # Delete existing tables with same data
        for table in existingTables:
            if tableName in table.GetName():
                slicer.mrmlScene.RemoveNode(table)

        table = tableNode.GetTable()

        arrX = vtk.vtkFloatArray()
        arrX.SetName(channelOneName)
        table.AddColumn(arrX)

        arrY = vtk.vtkFloatArray()
        arrY.SetName(channelTwoName)
        table.AddColumn(arrY)

        arrZ = vtk.vtkIntArray()
        arrZ.SetName("Cell Label")
        table.AddColumn(arrZ)

        # Fill in table with values
        table.SetNumberOfRows(nPoints)
        for i in range(nPoints):
            table.SetValue(i, 0, x[i])
            table.SetValue(i, 1, y[i])
            table.SetValue(i, 2, z[i])

        # Create plot series nodes
        plotSeriesNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotSeriesNode", roiName)

        # Delete existing tables with same data
        for plotSeries in existingSeriesNodes:
            if roiName in plotSeries.GetName():
                slicer.mrmlScene.RemoveNode(plotSeries)

        plotSeriesNode.SetAndObserveTableNodeID(tableNode.GetID())
        plotSeriesNode.SetXColumnName(channelOneName)
        plotSeriesNode.SetYColumnName(channelTwoName)
        plotSeriesNode.SetPlotType(slicer.vtkMRMLPlotSeriesNode.PlotTypeScatter)
        plotSeriesNode.SetLineStyle(slicer.vtkMRMLPlotSeriesNode.LineStyleNone)
        plotSeriesNode.SetMarkerStyle(slicer.vtkMRMLPlotSeriesNode.MarkerStyleCircle)
        plotSeriesNode.SetColor(0.46, 0.67, 0.96)

        # Create plot chart node
        plotChartName = roiName + ": " + channelOneName + " x " + channelTwoName
        plotChartNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotChartNode", plotChartName)

        # Delete existing tables with same data
        for chart in existingPlots:
            if roiName in chart.GetName():
                slicer.mrmlScene.RemoveNode(chart)

        plotChartNode.AddAndObservePlotSeriesNodeID(plotSeriesNode.GetID())
        plotChartNode.SetTitle(roiName + ": " + channelOneName + " x " + channelTwoName)
        plotChartNode.SetXAxisTitle(channelOneName)
        plotChartNode.SetYAxisTitle(channelTwoName)

        # Show plot in layout
        slicer.modules.plots.logic().ShowChartInLayout(plotChartNode)
        slicer.app.layoutManager().setLayout(
            slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpPlotView)

        # Set red slice to show the cell mask
        red_logic = slicer.app.layoutManager().sliceWidget("Red").sliceLogic()
        red_logic.GetSliceCompositeNode().SetBackgroundVolumeID(cellMask.GetID())

        # Create density plot with matplotlib
        # Install necessary libraries
        try:
            import matplotlib
        except ModuleNotFoundError:
            import pip
            slicer.util.pip_install("matplotlib")
            import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from pylab import savefig

        from scipy.stats import gaussian_kde

        # Calculate point density
        xy = np.vstack([x,y])
        densColour = gaussian_kde(xy)(xy)

        # Sort points by density
        idx = densColour.argsort()
        xArr = np.array(x)
        yArr = np.array(y)
        xArr, yArr, densColour = xArr[idx], yArr[idx], densColour[idx]

        fig, ax = plt.subplots()
        ax.scatter(xArr, yArr, c=densColour, s=10)

        ax.set_xlabel(channelOneName)
        ax.set_ylabel(channelTwoName)
        ax.set_title(roiName + ": " + channelOneName + " x " + channelTwoName, wrap=True)

        # Display heatmap
        defaultPath = slicer.app.defaultScenePath
        pathName = defaultPath + '/' + "densityScatter.jpg"
        savefig(pathName)
        densScatterImg = sitk.ReadImage(pathName)
        densScatterArray = sitk.GetArrayFromImage(densScatterImg)
        arraySize = densScatterArray.shape
        plt.close()

        # Create new volume "Density Scatter Plot"
        imageSize = [arraySize[1], arraySize[0], 1]
        voxelType = vtk.VTK_UNSIGNED_CHAR
        imageOrigin = [0.0, 0.0, 0.0]
        imageSpacing = [1.0, 1.0, 1.0]
        imageDirections = [[-1, 0, 0], [0, -1, 0], [0, 0, 1]]
        fillVoxelValue = 0

        # Create an empty image volume, filled with fillVoxelValue
        imageData = vtk.vtkImageData()
        imageData.SetDimensions(imageSize)
        imageData.AllocateScalars(voxelType, 3)
        imageData.GetPointData().GetScalars().Fill(fillVoxelValue)

        # Create volume node
        # Needs to be a vector volume in order to show in colour
        volumeNodeName = roiName + ": " + channelOneName + " x " + channelTwoName + " Density Scatter"
        volumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLVectorVolumeNode", volumeNodeName)
        for img in existingNodes:
            if volumeNodeName in img.GetName():
                slicer.mrmlScene.RemoveNode(img)
        volumeNode.SetOrigin(imageOrigin)
        volumeNode.SetSpacing(imageSpacing)
        volumeNode.SetIJKToRASDirections(imageDirections)
        volumeNode.SetAndObserveImageData(imageData)
        volumeNode.CreateDefaultDisplayNodes()
        volumeNode.CreateDefaultStorageNode()

        voxels = slicer.util.arrayFromVolume(volumeNode)
        voxels[:] = densScatterArray

        volumeNode.Modified()
        volumeNode.GetDisplayNode().AutoWindowLevelOff()
        volumeNode.GetDisplayNode().SetWindowLevel((arraySize[1] // 8), 127)

        # Set yellow slice to display density scatter plot
        yellow_widget = slicer.app.layoutManager().sliceWidget("Yellow")
        yellow_widget.setSliceOrientation("Axial")
        yellow_logic = yellow_widget.sliceLogic()
        yellow_logic.GetSliceCompositeNode().SetBackgroundVolumeID(volumeNode.GetID())

        # Set green slice to show cell mask
        green_widget = slicer.app.layoutManager().sliceWidget("Green")
        green_widget.setSliceOrientation("Axial")
        greenDisplayNode = channelTwoNode.GetScalarVolumeDisplayNode()
        greenDisplayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeRed")
        green_logic = green_widget.sliceLogic()
        green_logic.GetSliceCompositeNode().SetBackgroundVolumeID(channelTwoNode.GetID())

        # Fix window/level values
        widget = slicer.vtkMRMLWindowLevelWidget()
        widget.SetSliceNode(slicer.util.getNode('vtkMRMLSliceNodeRed'))
        widget.SetMRMLApplicationLogic(slicer.app.applicationLogic())
        p2 = cellMaskArray.shape[1]
        widget.UpdateWindowLevelFromRectangle(0, [0, 0], [p2, p2])

        # Fix window/level values
        widget = slicer.vtkMRMLWindowLevelWidget()
        widget.SetSliceNode(slicer.util.getNode('vtkMRMLSliceNodeGreen'))
        widget.SetMRMLApplicationLogic(slicer.app.applicationLogic())
        p1 = cellMaskArray.shape[1] // 2
        p2 = cellMaskArray.shape[2] // 2
        widget.UpdateWindowLevelFromRectangle(0, [p1, p1], [p2, p2])



        slicer.util.resetSliceViews()

        global scatterPlotRoi
        scatterPlotRoi = roiName


    def saveTableData(self):
        # Get table node
        print("working")
        tables = slicer.util.getNodesByClass("vtkMRMLTableNode")
        savedPaths = []
        # Save table to .csv file
        for table in tables:
            fileName = table.GetName() + ".csv"
            defaultPath = slicer.app.defaultScenePath
            pathName = defaultPath + '/' + fileName
            slicer.util.saveNode(table, pathName)
            savedPaths.append(pathName)
        import subprocess
        try:
            subprocess.Popen('explorer savedPaths[0]')
        except:
            subprocess.Popen(["open", savedPaths[0]])
        print("done")

    def heatmapChannelRun(self):

        """
        Create heatmap of the selected channel overlaid onto the cell mask
        """

        # Delete any existing heatmap images
        existingHeatmaps = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")

        for img in existingHeatmaps:
            if "Heatmap" in img.GetName():
                slicer.mrmlScene.RemoveNode(img)

        positions = []
        channelItems = []
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)

        for roi in selectedRoi:
            positions.append(roiDict[roi])

        for channel in selectedChannel:
            for pos in positions:
                if pos == 0:
                    node = slicer.util.getNode(channel)
                    itemId = shNode.GetItemByDataNode(node)
                    channelItems.append(itemId)
                else:
                    suffix = "_" + str(pos)
                    name = channel + suffix
                    node = slicer.util.getNode(name)
                    itemId = shNode.GetItemByDataNode(node)
                    channelItems.append(itemId)

        # Get array of channel
        parent = shNode.GetItemParent(channelItems[0])  # ROI
        roiName = shNode.GetItemName(parent)
        channelName = shNode.GetItemName(channelItems[0])
        channelNode = slicer.util.getNode(channelName)
        channelArray = slicer.util.arrayFromVolume(channelNode)

        # Get arrays for cell mask and channels
        cellMask = globalCellMask[roiName]
        cellMaskArray = slicer.util.arrayFromVolume(cellMask)

        # Get counts of pixels in each cell
        cell, counts = np.unique(cellMaskArray, return_counts=True)
        cellPixelCounts = dict(zip(cell, counts))

        # Create dictionary of heatmap percentages for all cells
        hmapPercentages = {0: 0}

        for cell in range(cellMaskArray.max() + 1):
            if cell != 0:
                if cell in cellPixelCounts.keys():
                    blank, i, j = np.nonzero(cellMaskArray == cell)
                    cellPixels = channelArray[:, i, j]
                    nActivePixels = np.count_nonzero(cellPixels)
                    perc = float(nActivePixels) / float(cellPixelCounts[cell])
                    hmapPercentages[cell] = perc

        # Map percentages to the cell mask array
        cellMaskHeatmap = np.copy(cellMaskArray)
        for cell in range(cellMaskHeatmap.max() + 1):
            if cell != 0:
                if cell in cellPixelCounts.keys():
                    cellMaskHeatmap = np.where(cellMaskHeatmap == cell, hmapPercentages[cell], cellMaskHeatmap)

        # Display image of cellMaskHeatmap
        # Create new volume "Heatmap on Channel"
        name = channelName
        if ".ome" in name:
            name = name.replace(".ome", "")

        volumeNode = slicer.modules.volumes.logic().CloneVolume(cellMask, "Heatmap on Channel " + name)
        slicer.util.updateVolumeFromArray(volumeNode, cellMaskHeatmap)

        # Change colormap of volume
        inferno = slicer.util.getFirstNodeByName("Inferno")
        displayNode = volumeNode.GetScalarVolumeDisplayNode()
        displayNode.SetAndObserveColorNodeID(inferno.GetID())

        slicer.util.setSliceViewerLayers(background=volumeNode, foreground=None)

        # Create histogram plot of the intensity values

        # Delete any existing plots
        existingPlots = slicer.util.getNodesByClass("vtkMRMLPlotChartNode")
        existingSeriesNodes = slicer.util.getNodesByClass("vtkMRMLPlotSeriesNode")
        existingTables = slicer.util.getNodesByClass("vtkMRMLTableNode")

        for plot in existingPlots:
            slicer.mrmlScene.RemoveNode(plot)
        for seriesNode in existingSeriesNodes:
            slicer.mrmlScene.RemoveNode(seriesNode)
        for table in existingTables:
            slicer.mrmlScene.RemoveNode(table)

        # Compute histogram values
        histValues = np.array(list(hmapPercentages.values()))
        histogram = np.histogram(histValues[histValues!=0], bins=20)

        # Save results to a new table node
        tableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", volumeNode.GetName() + ' data')
        slicer.util.updateTableFromArray(tableNode, histogram)
        tableNode.GetTable().GetColumn(0).SetName("Count")
        tableNode.GetTable().GetColumn(1).SetName("Marker:Cell Ratio")

        # Create plot
        plotSeriesNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotSeriesNode",
                                                            volumeNode.GetName() + " plot")
        plotSeriesNode.SetAndObserveTableNodeID(tableNode.GetID())
        plotSeriesNode.SetXColumnName("Marker:Cell Ratio")
        plotSeriesNode.SetYColumnName("Count")
        plotSeriesNode.SetPlotType(plotSeriesNode.PlotTypeScatterBar)
        plotSeriesNode.SetColor(0.46, 0.67, 0.96)

        # Create chart and add plot
        plotChartNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotChartNode",
                                                           volumeNode.GetName() + 'histogram')
        plotChartNode.AddAndObservePlotSeriesNodeID(plotSeriesNode.GetID())
        plotChartNode.SetTitle("Histogram of Marker:Cell Ratio")
        plotChartNode.SetXAxisTitle("Marker:Cell Ratio")
        plotChartNode.SetYAxisTitle("Count")

        # Show plot in layout
        slicer.modules.plots.logic().ShowChartInLayout(plotChartNode)
        slicer.app.layoutManager().setLayout(
            slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpPlotView)

        # Set red slice to show the heatmap
        red_logic = slicer.app.layoutManager().sliceWidget("Red").sliceLogic()
        red_logic.GetSliceCompositeNode().SetBackgroundVolumeID(volumeNode.GetID())

        # Set yellow slice to show cloned, thresholded channel
        yellow_widget = slicer.app.layoutManager().sliceWidget("Yellow")
        yellow_widget.setSliceOrientation("Axial")
        yellowDisplayNode = channelNode.GetScalarVolumeDisplayNode()
        yellowDisplayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeRed")
        yellow_logic = yellow_widget.sliceLogic()
        yellow_logic.GetSliceCompositeNode().SetBackgroundVolumeID(cellMask.GetID())

        # Set green slice to show cell mask
        green_widget = slicer.app.layoutManager().sliceWidget("Green")
        green_widget.setSliceOrientation("Axial")
        green_logic = green_widget.sliceLogic()
        green_logic.GetSliceCompositeNode().SetBackgroundVolumeID(channelNode.GetID())

        # Fix window/level values
        widget = slicer.vtkMRMLWindowLevelWidget()
        widget.SetSliceNode(slicer.util.getNode('vtkMRMLSliceNodeRed'))
        widget.SetMRMLApplicationLogic(slicer.app.applicationLogic())
        p1 = channelArray.shape[1] // 2
        p2 = channelArray.shape[2] // 2
        widget.UpdateWindowLevelFromRectangle(0, [p1, p1], [p2, p2])

        # Fix window/level values
        widget = slicer.vtkMRMLWindowLevelWidget()
        widget.SetSliceNode(slicer.util.getNode('vtkMRMLSliceNodeGreen'))
        widget.SetMRMLApplicationLogic(slicer.app.applicationLogic())
        widget.UpdateWindowLevelFromRectangle(0, [p1, p1], [p2, p2])

        # Fix window/level values
        widget = slicer.vtkMRMLWindowLevelWidget()
        widget.SetSliceNode(slicer.util.getNode('vtkMRMLSliceNodeYellow'))
        widget.SetMRMLApplicationLogic(slicer.app.applicationLogic())
        p2 = channelArray.shape[1]
        widget.UpdateWindowLevelFromRectangle(0, [0, 0], [p2, p2])

        slicer.util.resetSliceViews()

    def heatmapRun(self, normalizeRoiState, normalizeChannelState):

        """
        Create heatmap showing mean intensities of channels across all ROI's
        """

        # Delete any existing heatmap images
        existingHeatmaps = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")

        for img in existingHeatmaps:
            if "Heatmap" in img.GetName():
                slicer.mrmlScene.RemoveNode(img)

        channelRows = []
        roiColumns = []

        # Get list of all channels
        allChannels = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")

        # Create dictionary of each channel with its respective ROI
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
        parentDict = {}
        for channel in allChannels:
            itemId = shNode.GetItemByDataNode(channel)   # Channel
            parent = shNode.GetItemParent(itemId)    # ROI
            roiName = shNode.GetItemName(parent)
            channelName = shNode.GetItemName(itemId)
            if re.findall(r"_[0-9]\b", channelName) != []:
                channelName = channelName[:-2]
            if roiName == "Scene":
                roiName = "ROI"
            # Check if the specific channel was selected
            if roiName in selectedRoi and channelName in selectedChannel:
                parentDict[itemId] = roiName
                if channelName not in channelRows:
                    channelRows.append(channelName)
                if roiName not in roiColumns:
                    roiColumns.append(roiName)

        # Create empty matrix of mean intensities
        meanIntensities = np.full((len(roiColumns), len(channelRows)), 0.00)

        # Fill meanIntensities matrix with proper values
        for i in parentDict:
            # Get array of channel
            channelName = shNode.GetItemName(i)
            channelNode = slicer.util.getNode(channelName)
            channelArray = slicer.util.arrayFromVolume(channelNode)
            # Get mean intensity of channel
            sumIntens = np.sum(channelArray)
            nonZeroes = np.where(channelArray != 0)
            numNonZeroes = nonZeroes[1].shape[0]
            meanIntens = float(sumIntens) / float(numNonZeroes)
            # Update meanIntensities matrix with this value
            if re.findall(r"_[0-9]\b", channelName) != []:
                channelName = channelName[:-2]
            rowPos = channelRows.index(channelName)
            columnPos = roiColumns.index(parentDict[i])
            meanIntensities[columnPos, rowPos] = round(meanIntens, 2)
        # Normalize by row if option is selected
        if normalizeRoiState is True:
            count = 0
            for i in meanIntensities:
                norm = np.interp(i, (i.min(), i.max()), (0, 1))
                meanIntensities[count] = np.round(norm, 2)
                count += 1
        if normalizeChannelState is True:
            count = 0
            transArr = np.transpose(meanIntensities)
            for i in transArr:
                norm = np.interp(i, (i.min(), i.max()), (0, 1))
                transArr[count] = np.round(norm, 2)
                count += 1
            meanIntensities = np.transpose(transArr)
        # Run helper function
        HypModuleLogic().heatmapRunHelper(channelRows, roiColumns, meanIntensities)
        return True

    def heatmapRunHelper(self, channelRows, roiColumns, meanIntensities):

        # Install necessary libraries
        try:
            import matplotlib
        except ModuleNotFoundError:
            import pip
            slicer.util.pip_install("matplotlib")
            import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from pylab import savefig

        # Create heatmap
        # plt.rcParams.update({'font.size': 6})
        fig, ax = plt.subplots(figsize=(20,10))

        ax.set_xticks(np.arange(len(channelRows)))
        ax.set_yticks(np.arange(len(roiColumns)))

        ax.set_xticklabels(channelRows)
        ax.set_yticklabels(roiColumns)

        plt.setp(ax.get_xticklabels(), rotation = 45, ha = "right",
                 rotation_mode = "anchor")

        # Loop through data and create text annotations
        if len(channelRows) < 30:
            for i in range(len(roiColumns)):
                for j in range(len(channelRows)):
                    text = ax.text(j, i, meanIntensities[i,j],
                                   ha = "center", va = "center", color = "w")

        ax.set_title("Heatmap of Mean Intensities")

        # Add colour bar to heatmap
        im = ax.imshow(meanIntensities)
        cbar = ax.figure.colorbar(im)
        cbar.ax.set_ylabel("Mean Intensity", rotation = -90, va = "bottom")

        # Display heatmap
        defaultPath = slicer.app.defaultScenePath
        pathName = defaultPath + '/' + "heatmap.jpg"
        savefig(pathName)
        heatmapImg = sitk.ReadImage(pathName)
        heatmapArray = sitk.GetArrayFromImage(heatmapImg)
        arraySize = heatmapArray.shape
        plt.close()
        # Create new volume "Heatmap"
        imageSize = [arraySize[1], arraySize[0], 1]
        voxelType = vtk.VTK_UNSIGNED_CHAR
        imageOrigin = [0.0, 0.0, 0.0]
        imageSpacing = [1.0, 1.0, 1.0]
        imageDirections = [[-1, 0, 0], [0, -1, 0], [0, 0, 1]]
        fillVoxelValue = 0

        # Create an empty image volume, filled with fillVoxelValue
        imageData = vtk.vtkImageData()
        imageData.SetDimensions(imageSize)
        imageData.AllocateScalars(voxelType, 3)
        imageData.GetPointData().GetScalars().Fill(fillVoxelValue)

        # Create volume node
        # Needs to be a vector volume in order to show in colour
        volumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLVectorVolumeNode", "Heatmap")
        volumeNode.SetOrigin(imageOrigin)
        volumeNode.SetSpacing(imageSpacing)
        volumeNode.SetIJKToRASDirections(imageDirections)
        volumeNode.SetAndObserveImageData(imageData)
        volumeNode.CreateDefaultDisplayNodes()
        volumeNode.CreateDefaultStorageNode()

        voxels = slicer.util.arrayFromVolume(volumeNode)
        voxels[:] = heatmapArray

        volumeNode.Modified()
        volumeNode.GetDisplayNode().AutoWindowLevelOff()
        volumeNode.GetDisplayNode().SetWindowLevel((arraySize[1]//8), 127)

        slicer.util.setSliceViewerLayers(background=volumeNode, foreground=None)

        # Set slice view to display Red window only
        lm = slicer.app.layoutManager()
        lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)

        # Reset field of view to show entire image
        slicer.util.resetSliceViews()

        # pm = qt.QPixmap("heatmap.png")
        # imgWidget = qt.QLabel()
        # imgWidget.setPixmap(pm)
        # imgWidget.setScaledContents(True)
        # imgWidget.show()
        # return True

    def rawDataRun(self):
        """
        Generate raw data tables for all ROI and channels
        """
        existingTables = slicer.util.getNodesByClass("vtkMRMLTableNode")

        for table in existingTables:
            slicer.mrmlScene.RemoveNode(table)

        # Get list of all channels
        allChannels = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)


        #
        # df = pd.DataFrame(columns=["ROI", "Cell Label"])
        #
        # for channel in channelNames:
        #     df[channel] = ""

        # Create list of mean intensities for all cells for each channel
        # Create empty matrix of mean intensities
        roiIntensitiesDict = {}
        roiCellMaskArrays = {}
        roiPixelCounts = {}
        for roi in roiNames:
            if roi == "Scene":
                continue
            # Get cell mask array
            cellMask = globalCellMask[roi]
            cellMaskArray = slicer.util.arrayFromVolume(cellMask)
            roiCellMaskArrays[roi] = cellMaskArray
            # Get counts of pixels in each cell
            cell, counts = np.unique(cellMaskArray, return_counts=True)
            cellPixelCounts = dict(zip(cell, counts))
            roiPixelCounts[roi] = cellPixelCounts
            roiIntensitiesDict[roi] = np.full((len(cell) - 1, len(channelNames) + 1), 0.00)



        for channelNode in allChannels:
            itemId = shNode.GetItemByDataNode(channelNode)  # Channel
            parent = shNode.GetItemParent(itemId)  # ROI
            roiName = shNode.GetItemName(parent)
            channelName = shNode.GetItemName(itemId)
            if ".ome" not in channelName:
                continue
            if re.findall(r"_[0-9]\b", channelName) != []:
                channelName = channelName[:-2]
            if roiName == "Scene":
                roiName = "ROI"
            # Get column index for mean intensities array
            columnPos = channelNames.index(channelName) + 1
            # Get arrays for cell mask and channels
            cellMaskArray = roiCellMaskArrays[roiName]
            # Get counts of pixels in each cell
            cellPixelCounts = roiPixelCounts[roiName]
            # Get intensities for each cell
            for cell in range(cellMaskArray.max() + 1):
                if cell != 0:
                    if cell in cellPixelCounts.keys():
                        # Channel one
                        blank, i, j = np.nonzero(cellMaskArray == cell)
                        # Get array of channel
                        channelArray = slicer.util.arrayFromVolume(channelNode)
                        # Get mean intensity of channel
                        cellPixels = channelArray[:, i, j]
                        sumIntens = np.sum(cellPixels)
                        totalPixels = cellPixels.shape[1]
                        nonZeroes = np.where(cellPixels != 0)
                        numNonZeroes = nonZeroes[1].shape[0]
                        if numNonZeroes == 0:
                            avg = 0
                        else:
                            avg = float(sumIntens) / float(totalPixels)
                        # Update meanIntensities matrix with this value
                        rowPos = list(cellPixelCounts.keys()).index(cell) - 1
                        roiIntensitiesDict[roiName][rowPos, columnPos] = avg
                        roiIntensitiesDict[roiName][rowPos, 0] = cell

        # Create dataframe of all arrays
        try:
            import pandas as pd
        except ModuleNotFoundError:
            import pip
            slicer.util.pip_install("pandas")
            import pandas as pd

        pathName = ""

        for roi in roiIntensitiesDict:
            arr = roiIntensitiesDict[roi]
            # Convert array to dataframe
            df = pd.DataFrame(data=arr)
            df.insert(0, "ROI", roi)
            # Rename the columns
            df = df.rename(columns = {0: "Cell Label"})
            for i in range(len(channelNames)):
                df = df.rename(columns = {i + 1: channelNames[i]})
            # # Delete any columns with all zeros (these are DNA channels that we don't calculate for)
            # df = df.loc[:, (df != 0).any(axis=0)]
            # Save dataframe to .csv file
            filename = "rawData_" + roi + ".csv"
            defaultPath = slicer.app.defaultScenePath
            pathName = defaultPath + '/' + filename
            df.to_csv(pathName, index=False)

        # Open file location in explorer
        import subprocess
        try:
            subprocess.Popen('explorer defaultPath')

        except:
            subprocess.Popen(["open", defaultPath])



    def tsnePCARun(self, plotType, checkState):
        """
        Create t-sne plot of selected channels
        """

        # Delete any existing plots
        existingPlots = slicer.util.getNodesByClass("vtkMRMLPlotChartNode")
        existingSeriesNodes = slicer.util.getNodesByClass("vtkMRMLPlotSeriesNode")
        existingTables = slicer.util.getNodesByClass("vtkMRMLTableNode")

        for table in existingTables:
            slicer.mrmlScene.RemoveNode(table)

        for plot in existingPlots:
            slicer.mrmlScene.RemoveNode(plot)

        for series in existingSeriesNodes:
            slicer.mrmlScene.RemoveNode(series)

        # Get list of all channels
        allChannels = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")

        # Create dictionary of each channel with its respective ROI
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)

        # Create list of mean intensities for all cells for each channel
        # Create empty matrix of mean intensities
        roiIntensitiesDict = {}
        roiCellMaskArrays = {}
        roiPixelCounts = {}
        if checkState == True:
            roi = selectedGates[0]
            # Get cell mask array
            cellMask = globalCellMask[roi]
            cellMaskArray = slicer.util.arrayFromVolume(cellMask)
            roiCellMaskArrays[roi] = cellMaskArray
            # Get counts of pixels in each cell
            cell, counts = np.unique(cellMaskArray, return_counts=True)
            cellPixelCounts = dict(zip(cell, counts))
            roiPixelCounts[roi] = cellPixelCounts
            roiIntensitiesDict[roi] = np.full((len(cell) - 1, len(selectedChannel) + 1), 0.00)
        else:
            for roi in selectedRoi:
                # if roi == "Scene":
                #     continue
                # Get cell mask array
                cellMask = globalCellMask[roi]
                cellMaskArray = slicer.util.arrayFromVolume(cellMask)
                roiCellMaskArrays[roi] = cellMaskArray
                # Get counts of pixels in each cell
                cell, counts = np.unique(cellMaskArray, return_counts=True)
                cellPixelCounts = dict(zip(cell, counts))
                roiPixelCounts[roi] = cellPixelCounts
                roiIntensitiesDict[roi] = np.full((len(cell) - 1, len(selectedChannel)+1), 0.00)

        # cellLabels = []
        displayList = []
        channelItems = []
        positions = []

        for roi in selectedRoi:
            positions.append(roiDict[roi])

        for channel in selectedChannel:
            for pos in positions:
                if pos == 0:
                    node = slicer.util.getNode(channel)
                    itemId = shNode.GetItemByDataNode(node)
                    channelItems.append(itemId)
                    if len(displayList) <= 2:
                        displayList.append(node)
                else:
                    suffix = "_" + str(pos)
                    name = channel + suffix
                    node = slicer.util.getNode(name)
                    itemId = shNode.GetItemByDataNode(node)
                    channelItems.append(itemId)
                    if len(displayList) <= 2:
                        displayList.append(node)

        for channel in channelItems:
            channelName = shNode.GetItemName(channel)
            if checkState == True:
                roiName = selectedGates[0]
            else:
                roiName = shNode.GetItemName(shNode.GetItemParent(channel))
            # Get column index for mean intensities array
            if re.findall(r"_[0-9]\b", channelName) != []:
                channelName = channelName[:-2]
            columnPos = channelNames.index(channelName)
            # Get arrays for cell mask and channels
            cellMaskArray = roiCellMaskArrays[roiName]
            # Get counts of pixels in each cell
            cellPixelCounts = roiPixelCounts[roiName]
            # Get intensities for each cell
            for cell in range(cellMaskArray.max() + 1):
                if cell != 0:
                    if cell in cellPixelCounts.keys():
                        # Channel one
                        blank, i, j = np.nonzero(cellMaskArray == cell)
                        # Get array of channel
                        channelNode = shNode.GetItemDataNode(channel)
                        channelArray = slicer.util.arrayFromVolume(channelNode)
                        # Get mean intensity of channel
                        cellPixels = channelArray[:, i, j]
                        sumIntens = np.sum(cellPixels)
                        totalPixels = cellPixels.shape[1]
                        nonZeroes = np.where(cellPixels != 0)
                        numNonZeroes = nonZeroes[1].shape[0]
                        if numNonZeroes == 0:
                            avg = 0
                        else:
                            avg = float(sumIntens) / float(totalPixels)
                        # Update meanIntensities matrix with this value
                        rowPos = list(cellPixelCounts.keys()).index(cell) - 1
                        roiIntensitiesDict[roiName][rowPos, columnPos] = avg
                        roiIntensitiesDict[roiName][rowPos, 0] = cell

        # Perform 99th-percentile normalization on each ROI array
        for roiName, array in roiIntensitiesDict.items():
            cellLabels = array[:,0]
            newArray = array[:,1:]
            percentile = np.percentile(newArray, 99)
            normArray = array/percentile
            finalArray = np.insert(normArray, 0, values=cellLabels, axis=1)
            roiIntensitiesDict[roiName] = finalArray


        # Append the arrays for each ROI together
        concatArray = list(roiIntensitiesDict.values())[0]
        count = 0

        for roi in roiIntensitiesDict:
            if count == 0:
                count += 1
            else:
                array = roiIntensitiesDict[roi]
                concatArray = np.append(concatArray, array, axis=0)

        # Create tsne array
        try:
            import sklearn
        except ModuleNotFoundError:
            import pip
            slicer.util.pip_install("sklearn")

        if plotType == "tsne":
            from sklearn.manifold import TSNE

            plotValues = TSNE().fit_transform(concatArray[:,1:])
            name = "t-SNE"

        else:
            from sklearn.decomposition import PCA

            plotValues = PCA(n_components=2).fit_transform(concatArray[:,1:])
            name = "PCA"

        # If only one ROI in t-sne, create plot that allows gating
        if len(roiCellMaskArrays) == 1:
            if checkState == True:
                roiName = selectedGates[0] #list(roiCellMaskArrays.keys())[0]
            else:
                roiName = selectedRoi[0]
            x = []
            y = []
            z = concatArray[:,0]

            for i in plotValues:
                x.append(i[0])
                y.append(i[1])

            # Create table with x and y columns
            tableName = roiName + ": "  + name + " data"
            tableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", tableName)

            # Delete existing tables with same data
            for table in existingTables:
                if tableName in table.GetName():
                    slicer.mrmlScene.RemoveNode(table)

            table = tableNode.GetTable()

            arrX = vtk.vtkFloatArray()
            arrX.SetName(name + " 1")
            table.AddColumn(arrX)

            arrY = vtk.vtkFloatArray()
            arrY.SetName(name + " 2")
            table.AddColumn(arrY)

            arrZ = vtk.vtkFloatArray()
            arrZ.SetName("Cell Label")
            table.AddColumn(arrZ)

            # Fill in table with values
            table.SetNumberOfRows(len(plotValues))
            for i in range(len(plotValues)):
                arrX.InsertNextValue(x[i])
                arrY.InsertNextValue(y[i])
                arrZ.InsertNextValue(z[i])

            for i in range(len(plotValues)):
                table.RemoveRow(0)

            # Create plot series nodes
            seriesName = roiName + ": " + name + " Points"
            plotSeriesNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotSeriesNode", seriesName)

            # Delete existing plot series with same data
            for series in existingSeriesNodes:
                if seriesName in series.GetName():
                    slicer.mrmlScene.RemoveNode(series)

            plotSeriesNode.SetAndObserveTableNodeID(tableNode.GetID())
            plotSeriesNode.SetXColumnName(name + " 1")
            plotSeriesNode.SetYColumnName(name + " 2")
            plotSeriesNode.SetPlotType(slicer.vtkMRMLPlotSeriesNode.PlotTypeScatter)
            plotSeriesNode.SetLineStyle(slicer.vtkMRMLPlotSeriesNode.LineStyleNone)
            plotSeriesNode.SetMarkerStyle(slicer.vtkMRMLPlotSeriesNode.MarkerStyleCircle)
            plotSeriesNode.SetColor(0.46, 0.67, 0.96)

            # Create plot chart node
            chartName = roiName + name
            plotChartNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotChartNode", chartName)

            # Delete existing plot series with same data
            for chart in existingPlots:
                if chartName in chart.GetName():
                    slicer.mrmlScene.RemoveNode(chart)

            plotChartNode.AddAndObservePlotSeriesNodeID(plotSeriesNode.GetID())
            plotChartNode.SetTitle(roiName + " " + name)
            plotChartNode.SetXAxisTitle(name + " 1")
            plotChartNode.SetYAxisTitle(name + " 2")

            # Show plot in layout
            slicer.modules.plots.logic().ShowChartInLayout(plotChartNode)
            slicer.app.layoutManager().setLayout(
                slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpPlotView)

            # Set red slice to show the cell mask
            red_logic = slicer.app.layoutManager().sliceWidget("Red").sliceLogic()
            red_logic.GetSliceCompositeNode().SetBackgroundVolumeID(cellMask.GetID())

            # Set green slice to show cell mask
            green_widget = slicer.app.layoutManager().sliceWidget("Green")
            green_widget.setSliceOrientation("Axial")
            greenDisplayNode = displayList[0].GetScalarVolumeDisplayNode()
            greenDisplayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeGreen")
            green_logic = green_widget.sliceLogic()
            green_logic.GetSliceCompositeNode().SetBackgroundVolumeID(displayList[0].GetID())

            # Set yellow slice to show cloned, thresholded channel
            yellow_widget = slicer.app.layoutManager().sliceWidget("Yellow")
            yellow_widget.setSliceOrientation("Axial")
            if len(displayList) >= 2:
                yellowDisplayNode = displayList[1].GetScalarVolumeDisplayNode()
                yellowDisplayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeBlue")
                yellow_logic = yellow_widget.sliceLogic()
                yellow_logic.GetSliceCompositeNode().SetBackgroundVolumeID(displayList[1].GetID())
            else:
                yellowDisplayNode = displayList[0].GetScalarVolumeDisplayNode()
                yellowDisplayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeBlue")
                yellow_logic = yellow_widget.sliceLogic()
                yellow_logic.GetSliceCompositeNode().SetBackgroundVolumeID(displayList[0].GetID())

            slicer.util.resetSliceViews()

            global scatterPlotRoi
            scatterPlotRoi = roiName
        # If multiple ROI, create matplotlib plot and pandas excel table
        else:
            # Create dataframe of all arrays
            try:
                import pandas as pd
            except ModuleNotFoundError:
                import pip
                slicer.util.pip_install("pandas")
                import pandas as pd

            roiNamesList = []
            roiColourLabels = {}
            count = 0

            for roi in roiIntensitiesDict:
                # Map a colour to each ROI
                roiColourLabels[roi] = count
                count += 1
                array = roiIntensitiesDict[roi]
                for i in range(len(array)):
                    roiNamesList.append(roi)

            df = pd.DataFrame(data = plotValues, columns = ["Dim 1", "Dim 2"])
            df.insert(0, "Cell Label", concatArray[:, 0])
            df.insert(0, "ROI", roiNamesList)

            # Create matplot scatter plot
            try:
                import matplotlib
            except ModuleNotFoundError:
                import pip
                slicer.util.pip_install("matplotlib")
                import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from pylab import savefig

            fig, ax = plt.subplots(figsize = (15,10))
            axis_font = {'fontname': 'Arial', 'size': '18'}

            scatter = ax.scatter(df["Dim 1"], df["Dim 2"], c=df["ROI"].apply(lambda x: roiColourLabels[x]), s=10)

            ax.set_xlabel("Dimension 1", **axis_font)
            ax.set_ylabel("Dimension 2", **axis_font)
            ax.set_title(name, **axis_font)

            legend1 = ax.legend(handles = scatter.legend_elements()[0], loc = "best", title = "ROI", labels = selectedRoi, fontsize = 14)

            # Display cluster plot
            defaultPath = slicer.app.defaultScenePath
            pathName = defaultPath + '/' + "dimReduction.jpg"
            savefig(pathName)
            dimRedImg = sitk.ReadImage(pathName)
            dimRedArray = sitk.GetArrayFromImage(dimRedImg)
            arraySize = dimRedArray.shape
            plt.close()

            # Create new volume "K-Means Clustering"
            imageSize = [arraySize[1], arraySize[0], 1]
            voxelType = vtk.VTK_UNSIGNED_CHAR
            imageOrigin = [0.0, 0.0, 0.0]
            imageSpacing = [1.0, 1.0, 1.0]
            imageDirections = [[-1, 0, 0], [0, -1, 0], [0, 0, 1]]
            fillVoxelValue = 0

            # Create an empty image volume, filled with fillVoxelValue
            imageData = vtk.vtkImageData()
            imageData.SetDimensions(imageSize)
            imageData.AllocateScalars(voxelType, 3)
            imageData.GetPointData().GetScalars().Fill(fillVoxelValue)

            # Create volume node
            # Needs to be a vector volume in order to show in colour
            volumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLVectorVolumeNode", "Dimension Reduction Plot")
            volumeNode.SetOrigin(imageOrigin)
            volumeNode.SetSpacing(imageSpacing)
            volumeNode.SetIJKToRASDirections(imageDirections)
            volumeNode.SetAndObserveImageData(imageData)
            volumeNode.CreateDefaultDisplayNodes()
            volumeNode.CreateDefaultStorageNode()

            voxels = slicer.util.arrayFromVolume(volumeNode)
            voxels[:] = dimRedArray

            volumeNode.Modified()
            volumeNode.GetDisplayNode().AutoWindowLevelOff()
            volumeNode.GetDisplayNode().SetWindowLevel((arraySize[1] // 6), 127)

            # Show plot in layout
            slicer.app.layoutManager().setLayout(
                slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)

            # Set red slice to show the cell mask
            red_logic = slicer.app.layoutManager().sliceWidget("Red").sliceLogic()
            red_logic.GetSliceCompositeNode().SetBackgroundVolumeID(volumeNode.GetID())

            # Save dataframe to .csv file
            filename = name + " plot.csv"
            defaultPath = slicer.app.defaultScenePath
            pathName = defaultPath + '/' + filename
            df.to_csv(pathName, index=False)
            # Open file location in explorer
            import subprocess
            try:
                subprocess.Popen('explorer defaultPath')
            except:
                subprocess.Popen(["open", defaultPath])

            global tsnePcaData
            tsnePcaData = df

        slicer.util.resetSliceViews()



    def clusterRun(self, nClusters, clusterType):
        """
        Create k-means clustering based on an already created t-sne or pca plot.
        """

        # Get columns from t-sne/pca table
        if slicer.util.getNodesByClass("vtkMRMLTableNode") != []:
            tableNode = slicer.util.getNodesByClass("vtkMRMLTableNode")[-1]
            nRows = tableNode.GetNumberOfRows()
            kmeansArray = np.full((nRows, 2), 0.00)
            dim1 = []
            dim2 = []
            cellLabels = []
            for row in range(nRows):
                dim1Val = float(tableNode.GetCellText(row, 0))
                dim2Val = float(tableNode.GetCellText(row, 1))
                kmeansArray[row,0] = dim1Val
                kmeansArray[row, 1] = dim2Val
                dim1.append(dim1Val)
                dim2.append(dim2Val)
                cellLabels.append(int(tableNode.GetCellText(row, 2)))

        else:
            kmeansArray = tsnePcaData.iloc[:,2:]
            dim1 = tsnePcaData["Dim 1"]
            dim2 = tsnePcaData["Dim 2"]
            cellLabels = tsnePcaData["Cell Label"]

        # Compute k-means
        try:
            import sklearn
        except ModuleNotFoundError:
            import pip
            slicer.util.pip_install("sklearn")

        from sklearn.cluster import KMeans
        from sklearn.cluster import AgglomerativeClustering

        if clusterType == "kmeans":
            clusLabels = KMeans(n_clusters = nClusters, random_state = 0).fit_predict(kmeansArray)
            name = "K-Means Clustering"
        else:
            clusLabels = AgglomerativeClustering(n_clusters=nClusters).fit_predict(kmeansArray)
            name = "Hierarchical Clustering"


        # Create table with x and y columns
        kMeansTableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", name + " Data")
        table = kMeansTableNode.GetTable()

        arrX = vtk.vtkFloatArray()
        arrX.SetName("Dim 1")
        table.AddColumn(arrX)

        arrY = vtk.vtkFloatArray()
        arrY.SetName("Dim 2")
        table.AddColumn(arrY)

        arrZ = vtk.vtkFloatArray()
        arrZ.SetName("Cell Label")
        table.AddColumn(arrZ)

        arrK = vtk.vtkFloatArray()
        arrK.SetName("Cluster Label")
        table.AddColumn(arrK)


        # Fill in table with values
        table.SetNumberOfRows(len(dim1))
        for i in range(len(dim1)):
            arrX.InsertNextValue(dim1[i])
            arrY.InsertNextValue(dim2[i])
            arrZ.InsertNextValue(cellLabels[i])
            arrK.InsertNextValue(clusLabels[i])

        for i in range(len(dim1)):
            table.RemoveRow(0)

        # Create cluster plot with matplotlib
        # Install necessary libraries
        try:
            import matplotlib
        except ModuleNotFoundError:
            import pip
            slicer.util.pip_install("matplotlib")
            import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from pylab import savefig

        fig, ax = plt.subplots(figsize=(15,10))
        ax.scatter(dim1, dim2, c=clusLabels, s=10)
        ax.set_xlabel("Dimension 1")
        ax.set_ylabel("Dimension 2")
        ax.set_title(name)

        # Display cluster plot
        defaultPath = slicer.app.defaultScenePath
        pathName = defaultPath + '/' + "kMeans.jpg"
        savefig(pathName)
        kMeansImg = sitk.ReadImage(pathName)
        kMeansArray = sitk.GetArrayFromImage(kMeansImg)
        arraySize = kMeansArray.shape
        plt.close()

        # Create new volume "K-Means Clustering"
        imageSize = [arraySize[1], arraySize[0], 1]
        voxelType = vtk.VTK_UNSIGNED_CHAR
        imageOrigin = [0.0, 0.0, 0.0]
        imageSpacing = [1.0, 1.0, 1.0]
        imageDirections = [[-1, 0, 0], [0, -1, 0], [0, 0, 1]]
        fillVoxelValue = 0

        # Create an empty image volume, filled with fillVoxelValue
        imageData = vtk.vtkImageData()
        imageData.SetDimensions(imageSize)
        imageData.AllocateScalars(voxelType, 3)
        imageData.GetPointData().GetScalars().Fill(fillVoxelValue)

        # Create volume node
        # Needs to be a vector volume in order to show in colour
        volumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLVectorVolumeNode", name)
        volumeNode.SetOrigin(imageOrigin)
        volumeNode.SetSpacing(imageSpacing)
        volumeNode.SetIJKToRASDirections(imageDirections)
        volumeNode.SetAndObserveImageData(imageData)
        volumeNode.CreateDefaultDisplayNodes()
        volumeNode.CreateDefaultStorageNode()

        voxels = slicer.util.arrayFromVolume(volumeNode)
        voxels[:] = kMeansArray

        volumeNode.Modified()
        volumeNode.GetDisplayNode().AutoWindowLevelOff()
        volumeNode.GetDisplayNode().SetWindowLevel((arraySize[1] // 8), 127)

        # Set yellow slice to display density scatter plot
        red_widget = slicer.app.layoutManager().sliceWidget("Red")
        red_widget.setSliceOrientation("Axial")
        red_logic = red_widget.sliceLogic()
        red_logic.GetSliceCompositeNode().SetBackgroundVolumeID(volumeNode.GetID())

        slicer.app.layoutManager().setLayout(
            slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)
        slicer.util.resetSliceViews()

    def saveHeatmapChannelImg(self):

        fileName = "heatmap on channel.png"
        viewNodeID = 'vtkMRMLSliceNodeRed'
        import ScreenCapture
        cap = ScreenCapture.ScreenCaptureLogic()
        view = cap.viewFromNode(slicer.mrmlScene.GetNodeByID(viewNodeID))
        defaultPath = slicer.app.defaultScenePath
        pathName = defaultPath + '/' + fileName
        cap.captureImageFromView(view, pathName)
        import subprocess
        try:
            subprocess.Popen('explorer defaultPath')
        except:
            subprocess.Popen(["open", defaultPath])
