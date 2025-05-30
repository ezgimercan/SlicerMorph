##BASE PYTHON
import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import glob
import copy
import multiprocessing
import vtk.util.numpy_support as vtk_np
import numpy as np

#
# ALPACA
#

class ALPACA(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "ALPACA" # TODO make this more human readable by adding spaces
    self.parent.categories = ["SlicerMorph.Geometric Morphometrics"]
    self.parent.dependencies = []
    self.parent.contributors = ["Arthur Porto, Sara Rolfe (UW), Murat Maga (UW)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
      This module automatically transfers landmarks on a reference 3D model (mesh) to a target 3D model using dense correspondence and deformable registration. First optimize the parameters in single alignment analysis, then use them in batch mode to apply to all 3D models.
      <p>For more information see the <a href="https://github.com/SlicerMorph/SlicerMorph/tree/master/Docs/ALPACA">online documentation.</a>.</p>
      """
    #self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
      This module was developed by Arthur Porto, Sara Rolfe, and Murat Maga for SlicerMorph. SlicerMorph was originally supported by an NSF/DBI grant, "An Integrated Platform for Retrieval, Visualization and Analysis of 3D Morphology From Digital Biological Collections"
      awarded to Murat Maga (1759883), Adam Summers (1759637), and Douglas Boyer (1759839).
      https://nsf.gov/awardsearch/showAward?AWD_ID=1759883&HistoricalAwards=false
      """ # replace with organization, grant and thanks.

    # Additional initialization step after application startup is complete
    slicer.app.connect("startupCompleted()", registerSampleData)


#
# Register sample data sets in Sample Data module
#

def registerSampleData():
  """
  Add data sets to Sample Data module.
  """
  # It is always recommended to provide sample data for users to make it easy to try the module,
  # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

  import SampleData
  iconsPath = os.path.join(os.path.dirname(__file__), 'Resources/Icons')

  # To ensure that the source code repository remains small (can be downloaded and installed quickly)
  # it is recommended to store data sets that are larger than a few MB in a Github release.

  # TemplateKey1
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='TemplateKey',
    sampleName='TemplateKey1',
    # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
    # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
    thumbnailFileName=os.path.join(iconsPath, 'TemplateKey1.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
    fileNames='TemplateKey1.nrrd',
    # Checksum to ensure file integrity. Can be computed by this command:
    #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
    checksums = 'SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95',
    # This node name will be used when the data set is loaded
    nodeNames='TemplateKey1'
  )

  # TemplateKey2
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='TemplateKey',
    sampleName='TemplateKey2',
    thumbnailFileName=os.path.join(iconsPath, 'TemplateKey2.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
    fileNames='TemplateKey2.nrrd',
    checksums = 'SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97',
    # This node name will be used when the data set is loaded
    nodeNames='TemplateKey2'
  )


#
# ALPACAWidget
#

class ALPACAWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

  def __init__(self, parent=None):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    needRestart = False
    needInstall = False
    if slicer.app.majorVersion*100+slicer.app.minorVersion < 412:
      Open3dVersion = "0.10.0"
    else:
      Open3dVersion = "0.14.1+816263b"
    try:
      import open3d as o3d
      import cpdalp
      from packaging import version
      if version.parse(o3d.__version__) != version.parse(Open3dVersion):
        if not slicer.util.confirmOkCancelDisplay(f"ALPACA requires installation of open3d (version {Open3dVersion}).\nClick OK to upgrade open3d and restart the application."):
          self.showBrowserOnEnter = False
          return
        needRestart = True
        needInstall = True
    except ModuleNotFoundError:
      needInstall = True

    if needInstall:
      progressDialog = slicer.util.createProgressDialog(labelText='Upgrading open3d. This may take a minute...', maximum=0)
      slicer.app.processEvents()
      import SampleData
      sampleDataLogic = SampleData.SampleDataLogic()
      try:
        if slicer.app.os == 'win':
          url = "https://app.box.com/shared/static/friq8fhfi8n4syklt1v47rmuf58zro75.whl"
          wheelName = "open3d-0.14.1+816263b-cp39-cp39-win_amd64.whl"
          wheelPath = sampleDataLogic.downloadFile(url, slicer.app.cachePath, wheelName)
        elif slicer.app.os == 'macosx':
          url = "https://app.box.com/shared/static/ixhac95jrx7xdxtlagwgns7vt9b3mbqu.whl"
          wheelName = "open3d-0.14.1+816263b-cp39-cp39-macosx_10_15_x86_64.whl"
          wheelPath = sampleDataLogic.downloadFile(url, slicer.app.cachePath, wheelName)
        elif slicer.app.os == 'linux':
          url = "https://app.box.com/shared/static/wyzk0f9jhefrbm4uukzym0sow5bf26yi.whl"
          wheelName = "open3d-0.14.1+816263b-cp39-cp39-manylinux_2_27_x86_64.whl"
          wheelPath = sampleDataLogic.downloadFile(url, slicer.app.cachePath, wheelName)
      except:
          slicer.util.infoDisplay('Error: please check the url of the open3d wheel in the script')
          progressDialog.close()
      slicer.util.pip_install(f'cpdalp')
      slicer.util.pip_install(wheelPath)
      import open3d as o3d
      import cpdalp
      progressDialog.close()
    if needRestart:
      slicer.util.restart()

  def onSelect(self):
    self.applyButton.enabled = bool (self.meshDirectory.currentPath and self.landmarkDirectory.currentPath and
      self.sourceModelSelector.currentNode() and self.baseLMSelector.currentNode() and self.baseSLMSelect.currentNode()
      and self.outputDirectory.currentPath)

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Set up tabs to split workflow
    tabsWidget = qt.QTabWidget()
    alignSingleTab = qt.QWidget()
    alignSingleTabLayout = qt.QFormLayout(alignSingleTab)
    alignMultiTab = qt.QWidget()
    alignMultiTabLayout = qt.QFormLayout(alignMultiTab)


    tabsWidget.addTab(alignSingleTab, "Single Alignment")
    tabsWidget.addTab(alignMultiTab, "Batch processing")
    self.layout.addWidget(tabsWidget)

    # Layout within the tab
    alignSingleWidget=ctk.ctkCollapsibleButton()
    alignSingleWidgetLayout = qt.QFormLayout(alignSingleWidget)
    alignSingleWidget.text = "Align and subsample a source and target mesh "
    alignSingleTabLayout.addRow(alignSingleWidget)

    #
    # Select source mesh
    #
    self.sourceModelSelector = ctk.ctkPathLineEdit()
    self.sourceModelSelector.filters  = ctk.ctkPathLineEdit().Files
    self.sourceModelSelector.nameFilters=["*.ply"]
    alignSingleWidgetLayout.addRow("Source mesh: ", self.sourceModelSelector)

    #
    # Select source landmarks
    #
    self.sourceFiducialSelector = ctk.ctkPathLineEdit()
    self.sourceFiducialSelector.filters  = ctk.ctkPathLineEdit().Files
    self.sourceFiducialSelector.nameFilters=["*.fcsv"]
    alignSingleWidgetLayout.addRow("Source landmarks: ", self.sourceFiducialSelector)

    # Select target mesh
    #
    self.targetModelSelector = ctk.ctkPathLineEdit()
    self.targetModelSelector.filters  = ctk.ctkPathLineEdit().Files
    self.targetModelSelector.nameFilters=["*.ply"]
    alignSingleWidgetLayout.addRow("Target mesh: ", self.targetModelSelector)

    self.skipScalingCheckBox = qt.QCheckBox()
    self.skipScalingCheckBox.checked = 0
    self.skipScalingCheckBox.setToolTip("If checked, ALPACA will skip scaling during the alignment (Not recommended).")
    alignSingleWidgetLayout.addRow("Skip scaling", self.skipScalingCheckBox)

    self.skipProjectionCheckBox = qt.QCheckBox()
    self.skipProjectionCheckBox.checked = 0
    self.skipProjectionCheckBox.setToolTip("If checked, ALPACA will skip final refinement step placing landmarks on the target suface.")
    alignSingleWidgetLayout.addRow("Skip projection", self.skipProjectionCheckBox)


    if slicer.app.majorVersion*100+slicer.app.minorVersion < 412:
      [self.projectionFactor,self.pointDensity, self.normalSearchRadius, self.FPFHSearchRadius, self.distanceThreshold, self.maxRANSAC, self.maxRANSACValidation,
      self.ICPDistanceThreshold, self.alpha, self.beta, self.CPDIterations, self.CPDTolerence] = self.addAdvancedMenu(alignSingleWidgetLayout)
    else:
      [self.projectionFactor,self.pointDensity, self.normalSearchRadius, self.FPFHSearchRadius, self.distanceThreshold, self.maxRANSAC, self.RANSACConfidence,
      self.ICPDistanceThreshold, self.alpha, self.beta, self.CPDIterations, self.CPDTolerence] = self.addAdvancedMenu(alignSingleWidgetLayout)

    # Advanced tab connections
    self.projectionFactor.connect('valueChanged(double)', self.onChangeAdvanced)
    self.pointDensity.connect('valueChanged(double)', self.onChangeAdvanced)
    self.normalSearchRadius.connect('valueChanged(double)', self.onChangeAdvanced)
    self.FPFHSearchRadius.connect('valueChanged(double)', self.onChangeAdvanced)
    self.distanceThreshold.connect('valueChanged(double)', self.onChangeAdvanced)
    self.maxRANSAC.connect('valueChanged(double)', self.onChangeAdvanced)
    if slicer.app.majorVersion*100+slicer.app.minorVersion < 412:
      self.maxRANSACValidation.connect('valueChanged(double)', self.onChangeAdvanced)
    else:
      self.RANSACConfidence.connect('valueChanged(double)', self.onChangeAdvanced)
    self.ICPDistanceThreshold.connect('valueChanged(double)', self.onChangeAdvanced)
    self.alpha.connect('valueChanged(double)', self.onChangeAdvanced)
    self.beta.connect('valueChanged(double)', self.onChangeAdvanced)
    self.CPDIterations.connect('valueChanged(double)', self.onChangeAdvanced)
    self.CPDTolerence.connect('valueChanged(double)', self.onChangeAdvanced)

    #
    # Subsample Button
    #
    self.subsampleButton = qt.QPushButton("Run subsampling")
    self.subsampleButton.toolTip = "Run subsampling of the source and target"
    self.subsampleButton.enabled = False
    alignSingleWidgetLayout.addRow(self.subsampleButton)

    #
    # Subsample Information
    #
    self.subsampleInfo = qt.QPlainTextEdit()
    self.subsampleInfo.setPlaceholderText("Subsampling information")
    self.subsampleInfo.setReadOnly(True)
    alignSingleWidgetLayout.addRow(self.subsampleInfo)

    #
    # Align Button
    #
    self.alignButton = qt.QPushButton("Run rigid alignment")
    self.alignButton.toolTip = "Run rigid alignment of the source and target"
    self.alignButton.enabled = False
    alignSingleWidgetLayout.addRow(self.alignButton)

    #
    # Plot Aligned Mesh Button
    #
    self.displayMeshButton = qt.QPushButton("Display rigidly aligned meshes")
    self.displayMeshButton.toolTip = "Display rigid alignment of the source and target meshes"
    self.displayMeshButton.enabled = False
    alignSingleWidgetLayout.addRow(self.displayMeshButton)

    #
    # Coherent point drift registration
    #
    self.CPDRegistrationButton = qt.QPushButton("Run CPD non-rigid registration")
    self.CPDRegistrationButton.toolTip = "Coherent point drift registration between source and target meshes"
    self.CPDRegistrationButton.enabled = False
    alignSingleWidgetLayout.addRow(self.CPDRegistrationButton)

    #
    # DECA registration
    #
    #self.DECAButton = qt.QPushButton("Run DeCA non-rigid registration")
    #self.DECAButton.toolTip = "DeCA registration between source and target meshes"
    #self.DECAButton.enabled = False
    #alignSingleWidgetLayout.addRow(self.DECAButton)

    #
    # Coherent point drift registration
    #
    self.displayWarpedModelButton = qt.QPushButton("Show registered source model")
    self.displayWarpedModelButton.toolTip = "Show CPD warping applied to source model"
    self.displayWarpedModelButton.enabled = False
    alignSingleWidgetLayout.addRow(self.displayWarpedModelButton)

    # connections
    self.sourceModelSelector.connect('validInputChanged(bool)', self.onSelect)
    self.sourceFiducialSelector.connect('validInputChanged(bool)', self.onSelect)
    self.targetModelSelector.connect('validInputChanged(bool)', self.onSelect)
    self.projectionFactor.connect('valueChanged(double)', self.onSelect)
    self.subsampleButton.connect('clicked(bool)', self.onSubsampleButton)
    self.alignButton.connect('clicked(bool)', self.onAlignButton)
    self.displayMeshButton.connect('clicked(bool)', self.onDisplayMeshButton)
    self.CPDRegistrationButton.connect('clicked(bool)', self.onCPDRegistration)
    #self.DECAButton.connect('clicked(bool)', self.onDECARegistration)
    self.displayWarpedModelButton.connect('clicked(bool)', self.onDisplayWarpedModel)

    # Layout within the multiprocessing tab
    alignMultiWidget=ctk.ctkCollapsibleButton()
    alignMultiWidgetLayout = qt.QFormLayout(alignMultiWidget)
    alignMultiWidget.text = "Transfer landmark points from a source mesh to a directory of target meshes "
    alignMultiTabLayout.addRow(alignMultiWidget)

    #
    # Select source mesh
    #
    self.sourceModelMultiSelector = ctk.ctkPathLineEdit()
    self.sourceModelMultiSelector.filters  = ctk.ctkPathLineEdit().Files
    self.sourceModelMultiSelector.nameFilters=["*.ply"]
    self.sourceModelMultiSelector.toolTip = "Select the source mesh"
    alignMultiWidgetLayout.addRow("Source mesh: ", self.sourceModelMultiSelector)

    #
    # Select source landmark file
    #
    self.sourceFiducialMultiSelector = ctk.ctkPathLineEdit()
    self.sourceFiducialMultiSelector.filters  = ctk.ctkPathLineEdit().Files
    self.sourceFiducialMultiSelector.nameFilters=["*.fcsv"]
    self.sourceFiducialMultiSelector.toolTip = "Select the source landmarks"
    alignMultiWidgetLayout.addRow("Source landmarks: ", self.sourceFiducialMultiSelector)

    # Select target mesh directory
    #
    self.targetModelMultiSelector = ctk.ctkPathLineEdit()
    self.targetModelMultiSelector.filters = ctk.ctkPathLineEdit.Dirs
    self.targetModelMultiSelector.toolTip = "Select the directory of meshes to be landmarked"
    alignMultiWidgetLayout.addRow("Target mesh directory: ", self.targetModelMultiSelector)

    # Select output landmark directory
    #
    self.landmarkOutputSelector = ctk.ctkPathLineEdit()
    self.landmarkOutputSelector.filters = ctk.ctkPathLineEdit.Dirs
    self.landmarkOutputSelector.toolTip = "Select the output directory where the landmarks will be saved"
    alignMultiWidgetLayout.addRow("Target output landmark directory: ", self.landmarkOutputSelector)

    self.skipScalingMultiCheckBox = qt.QCheckBox()
    self.skipScalingMultiCheckBox.checked = 0
    self.skipScalingMultiCheckBox.setToolTip("If checked, ALPACA will skip scaling during the alignment.")
    alignMultiWidgetLayout.addRow("Skip scaling", self.skipScalingMultiCheckBox)

    self.skipProjectionCheckBoxMulti = qt.QCheckBox()
    self.skipProjectionCheckBoxMulti.checked = 0
    self.skipProjectionCheckBoxMulti.setToolTip("If checked, ALPACA will skip final refinement step placing landmarks on the target suface.")
    alignMultiWidgetLayout.addRow("Skip projection", self.skipProjectionCheckBoxMulti)

    if slicer.app.majorVersion*100+slicer.app.minorVersion < 412:
      [self.projectionFactorMulti, self.pointDensityMulti, self.normalSearchRadiusMulti, self.FPFHSearchRadiusMulti, self.distanceThresholdMulti, self.maxRANSACMulti, self.maxRANSACValidationMulti,
      self.ICPDistanceThresholdMulti, self.alphaMulti, self.betaMulti, self.CPDIterationsMulti, self.CPDTolerenceMulti] = self.addAdvancedMenu(alignMultiWidgetLayout)
    else:
      [self.projectionFactorMulti, self.pointDensityMulti, self.normalSearchRadiusMulti, self.FPFHSearchRadiusMulti, self.distanceThresholdMulti, self.maxRANSACMulti, self.RANSACConfidenceMulti,
      self.ICPDistanceThresholdMulti, self.alphaMulti, self.betaMulti, self.CPDIterationsMulti, self.CPDTolerenceMulti] = self.addAdvancedMenu(alignMultiWidgetLayout)

    #
    # Run landmarking Button
    #
    self.applyLandmarkMultiButton = qt.QPushButton("Run auto-landmarking")
    self.applyLandmarkMultiButton.toolTip = "Align the taget meshes with the source mesh and transfer landmarks."
    self.applyLandmarkMultiButton.enabled = False
    alignMultiWidgetLayout.addRow(self.applyLandmarkMultiButton)


    # connections
    self.sourceModelMultiSelector.connect('validInputChanged(bool)', self.onSelectMultiProcess)
    self.sourceFiducialMultiSelector.connect('validInputChanged(bool)', self.onSelectMultiProcess)
    self.targetModelMultiSelector.connect('validInputChanged(bool)', self.onSelectMultiProcess)
    self.landmarkOutputSelector.connect('validInputChanged(bool)', self.onSelectMultiProcess)
    self.skipScalingMultiCheckBox.connect('validInputChanged(bool)', self.onSelectMultiProcess)
    self.applyLandmarkMultiButton.connect('clicked(bool)', self.onApplyLandmarkMulti)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Advanced tab connections
    self.projectionFactorMulti.connect('valueChanged(double)', self.updateParameterDictionary)
    self.pointDensityMulti.connect('valueChanged(double)', self.updateParameterDictionary)
    self.normalSearchRadiusMulti.connect('valueChanged(double)', self.updateParameterDictionary)
    self.FPFHSearchRadiusMulti.connect('valueChanged(double)', self.updateParameterDictionary)
    self.distanceThresholdMulti.connect('valueChanged(double)', self.updateParameterDictionary)
    self.maxRANSACMulti.connect('valueChanged(double)', self.updateParameterDictionary)
    if slicer.app.majorVersion*100+slicer.app.minorVersion < 412:
      self.maxRANSACValidationMulti.connect('valueChanged(double)', self.updateParameterDictionary)
    else:
      self.RANSACConfidenceMulti.connect('valueChanged(double)', self.updateParameterDictionary)
    self.ICPDistanceThresholdMulti.connect('valueChanged(double)', self.updateParameterDictionary)
    self.alphaMulti.connect('valueChanged(double)', self.updateParameterDictionary)
    self.betaMulti.connect('valueChanged(double)', self.updateParameterDictionary)
    self.CPDIterationsMulti.connect('valueChanged(double)', self.updateParameterDictionary)
    self.CPDTolerenceMulti.connect('valueChanged(double)', self.updateParameterDictionary)

    # initialize the parameter dictionary from single run parameters
    if slicer.app.majorVersion*100+slicer.app.minorVersion < 412:
      self.parameterDictionary = {
        "projectionFactor": self.projectionFactor.value,
        "pointDensity": self.pointDensity.value,
        "normalSearchRadius" : self.normalSearchRadius.value,
        "FPFHSearchRadius" : self.FPFHSearchRadius.value,
        "distanceThreshold" : self.distanceThreshold.value,
        "maxRANSAC" : int(self.maxRANSAC.value),
        "maxRANSACValidation" : int(self.maxRANSACValidation.value),
        "ICPDistanceThreshold"  : self.ICPDistanceThreshold.value,
        "alpha" : self.alpha.value,
        "beta" : self.beta.value,
        "CPDIterations" : int(self.CPDIterations.value),
        "CPDTolerence" : self.CPDTolerence.value
        }
    else:
      self.parameterDictionary = {
        "projectionFactor": self.projectionFactor.value,
        "pointDensity": self.pointDensity.value,
        "normalSearchRadius" : self.normalSearchRadius.value,
        "FPFHSearchRadius" : self.FPFHSearchRadius.value,
        "distanceThreshold" : self.distanceThreshold.value,
        "maxRANSAC" : int(self.maxRANSAC.value),
        "RANSACConfidence" : int(self.RANSACConfidence.value),
        "ICPDistanceThreshold"  : self.ICPDistanceThreshold.value,
        "alpha" : self.alpha.value,
        "beta" : self.beta.value,
        "CPDIterations" : int(self.CPDIterations.value),
        "CPDTolerence" : self.CPDTolerence.value
        }
    #
    # initialize the parameter dictionary from multi run parameters
    if slicer.app.majorVersion*100+slicer.app.minorVersion < 412:
      self.parameterDictionaryMulti = {
        "projectionFactor": self.projectionFactorMulti.value,
        "pointDensity": self.pointDensityMulti.value,
        "normalSearchRadius" : self.normalSearchRadiusMulti.value,
        "FPFHSearchRadius" : self.FPFHSearchRadiusMulti.value,
        "distanceThreshold" : self.distanceThresholdMulti.value,
        "maxRANSAC" : int(self.maxRANSACMulti.value),
        "maxRANSACValidation" : int(self.maxRANSACValidationMulti.value),
        "ICPDistanceThreshold"  : self.ICPDistanceThresholdMulti.value,
        "alpha" : self.alphaMulti.value,
        "beta" : self.betaMulti.value,
        "CPDIterations" : int(self.CPDIterationsMulti.value),
        "CPDTolerence" : self.CPDTolerenceMulti.value
        }
    else:
      self.parameterDictionaryMulti = {
        "projectionFactor": self.projectionFactorMulti.value,
        "pointDensity": self.pointDensityMulti.value,
        "normalSearchRadius" : self.normalSearchRadiusMulti.value,
        "FPFHSearchRadius" : self.FPFHSearchRadiusMulti.value,
        "distanceThreshold" : self.distanceThresholdMulti.value,
        "maxRANSAC" : int(self.maxRANSACMulti.value),
        "RANSACConfidence" : int(self.RANSACConfidenceMulti.value),
        "ICPDistanceThreshold"  : self.ICPDistanceThresholdMulti.value,
        "alpha" : self.alphaMulti.value,
        "beta" : self.betaMulti.value,
        "CPDIterations" : int(self.CPDIterationsMulti.value),
        "CPDTolerence" : self.CPDTolerenceMulti.value
        }

  def cleanup(self):
    pass

  def onSelect(self):
    self.subsampleButton.enabled = bool ( self.sourceModelSelector.currentPath and self.targetModelSelector.currentPath and self.sourceFiducialSelector.currentPath)
    if bool(self.sourceModelSelector.currentPath):
      self.sourceModelMultiSelector.currentPath = self.sourceModelSelector.currentPath
    if bool(self.sourceFiducialSelector.currentPath):
      self.sourceFiducialMultiSelector.currentPath = self.sourceFiducialSelector.currentPath
    if bool(self.targetModelSelector.currentPath):
      path = os.path.dirname(self.targetModelSelector.currentPath)
      self.targetModelMultiSelector.currentPath = path
    self.skipScalingMultiCheckBox.checked = self.skipScalingCheckBox.checked
    self.skipProjectionCheckBoxMulti.checked = self.skipProjectionCheckBox.checked
    self.projectionFactorMulti.value = self.projectionFactor.value


  def onSelectMultiProcess(self):
    self.applyLandmarkMultiButton.enabled = bool ( self.sourceModelMultiSelector.currentPath and self.sourceFiducialMultiSelector.currentPath
    and self.targetModelMultiSelector.currentPath and self.landmarkOutputSelector.currentPath)

  def onSubsampleButton(self):
    logic = ALPACALogic()
    self.sourceData, self.targetData, self.sourcePoints, self.targetPoints, self.sourceFeatures, \
      self.targetFeatures, self.voxelSize, self.scaling = logic.runSubsample(self.sourceModelSelector.currentPath,
                                                                              self.targetModelSelector.currentPath, self.skipScalingCheckBox.checked, self.parameterDictionary)
    # Convert to VTK points
    self.sourceSLM_vtk = logic.convertPointsToVTK(self.sourcePoints.points)
    self.targetSLM_vtk = logic.convertPointsToVTK(self.targetPoints.points)

    # Display target points
    blue=[0,0,1]
    self.targetCloudNode = logic.displayPointCloud(self.targetSLM_vtk, self.voxelSize/10, 'Target Pointcloud', blue)
    logic.RAS2LPSTransform(self.targetCloudNode)
    self.updateLayout()

    # Enable next step of analysis
    self.alignButton.enabled = True

    # Output information on subsampling
    self.subsampleInfo.clear()
    self.subsampleInfo.insertPlainText(f':: Your subsampled source pointcloud has a total of {len(self.sourcePoints.points)} points. \n')
    self.subsampleInfo.insertPlainText(f':: Your subsampled target pointcloud has a total of {len(self.targetPoints.points)} points. ')

  def onAlignButton(self):
    logic = ALPACALogic()
    self.transformMatrix = logic.estimateTransform(self.sourcePoints, self.targetPoints, self.sourceFeatures, self.targetFeatures, self.voxelSize, self.skipScalingCheckBox.checked, self.parameterDictionary)
    self.ICPTransformNode = logic.convertMatrixToTransformNode(self.transformMatrix, 'Rigid Transformation Matrix')

    # For later analysis, apply transform to VTK arrays directly
    transform_vtk = self.ICPTransformNode.GetMatrixTransformToParent()
    self.alignedSourceSLM_vtk = logic.applyTransform(transform_vtk, self.sourceSLM_vtk)

    # Display aligned source points using transform that can be viewed/edited in the scene
    red=[1,0,0]
    self.sourceCloudNode = logic.displayPointCloud(self.sourceSLM_vtk, self.voxelSize/10, 'Source Pointcloud', red)
    self.sourceCloudNode.SetAndObserveTransformNodeID(self.ICPTransformNode.GetID())
    slicer.vtkSlicerTransformLogic().hardenTransform(self.sourceCloudNode)
    logic.RAS2LPSTransform(self.sourceCloudNode)
    self.updateLayout()

    # Enable next step of analysis
    self.displayMeshButton.enabled = True

  def onDisplayMeshButton(self):
    logic = ALPACALogic()
    # Display target points
    self.targetModelNode = slicer.util.loadModel(self.targetModelSelector.currentPath)
    blue=[0,0,1]

    # Display aligned source points
    self.sourceModelNode = slicer.util.loadModel(self.sourceModelSelector.currentPath)
    points = slicer.util.arrayFromModelPoints(self.sourceModelNode)
    points[:] = np.asarray(self.sourceData.points)
    self.sourceModelNode.GetPolyData().GetPoints().GetData().Modified()
    self.sourceModelNode.SetAndObserveTransformNodeID(self.ICPTransformNode.GetID())
    slicer.vtkSlicerTransformLogic().hardenTransform(self.sourceModelNode)
    logic.RAS2LPSTransform(self.sourceModelNode)
    red=[1,0,0]
    self.sourceModelNode.GetDisplayNode().SetColor(red)

    self.sourceCloudNode.GetDisplayNode().SetVisibility(False)
    self.targetCloudNode.GetDisplayNode().SetVisibility(False)

    # Enable next step of analysis
    self.CPDRegistrationButton.enabled = True

  def onCPDRegistration(self):
    logic = ALPACALogic()
    # Get source landmarks from file
    sourceLM_vtk, sourceLMNode =  logic.loadAndScaleFiducials(self.sourceFiducialSelector.currentPath, self.scaling)
    transform_vtk = self.ICPTransformNode.GetMatrixTransformToParent()
    self.alignedSourceLM_vtk = logic.applyTransform(transform_vtk, sourceLM_vtk)

    # Registration
    self.alignedSourceSLM_np = vtk_np.vtk_to_numpy(self.alignedSourceSLM_vtk.GetPoints().GetData())
    self.alignedSourceLM_np = vtk_np.vtk_to_numpy(self.alignedSourceLM_vtk.GetPoints().GetData())
    self.registeredSourceArray = logic.runCPDRegistration(self.alignedSourceLM_np, self.alignedSourceSLM_np, self.targetPoints.points, self.parameterDictionary)
    outputPoints = logic.exportPointCloud(self.registeredSourceArray, "Initial Predicted Landmarks")
    inputPoints = logic.exportPointCloud(self.alignedSourceLM_np, "Original Landmarks")
    green=[0,1,0]
    outputPoints.GetDisplayNode().SetColor(green)
    logic.RAS2LPSTransform(outputPoints)
    logic.RAS2LPSTransform(inputPoints)
    self.registeredSourceLM_vtk = logic.convertPointsToVTK(self.registeredSourceArray)

    outputPoints_vtk = logic.getFiducialPoints(outputPoints)
    inputPoints_vtk = logic.getFiducialPoints(inputPoints)

    # Get warped source model
    self.warpedSourceNode = logic.applyTPSTransform(inputPoints_vtk, outputPoints_vtk, self.sourceModelNode, 'Warped Source Mesh')
    self.warpedSourceNode.GetDisplayNode().SetVisibility(False)
    outputPoints.GetDisplayNode().SetPointLabelsVisibility(False)
    slicer.mrmlScene.RemoveNode(inputPoints)

    if self.skipProjectionCheckBox.checked:
      logic.propagateLandmarkTypes(sourceLMNode, outputPoints)
    # Projection
    else:
      print(":: Projecting landmarks to external surface")
      projectionFactor = self.projectionFactor.value/100
      projectedLandmarks = logic.runPointProjection(self.warpedSourceNode, self.targetModelNode, outputPoints, projectionFactor)
      logic.propagateLandmarkTypes(sourceLMNode, projectedLandmarks)
      projectedLandmarks.GetDisplayNode().SetPointLabelsVisibility(False)
      outputPoints.GetDisplayNode().SetVisibility(False)


    # Enable next step of analysis
    self.displayWarpedModelButton.enabled = True

    # Update visualization
    slicer.mrmlScene.RemoveNode(sourceLMNode)
    self.sourceModelNode.GetDisplayNode().SetVisibility(False)

  def onDisplayWarpedModel(self):
    logic = ALPACALogic()
    green=[0,1,0]
    self.warpedSourceNode.GetDisplayNode().SetColor(green)
    self.warpedSourceNode.GetDisplayNode().SetVisibility(True)

  def onApplyLandmarkMulti(self):
    logic = ALPACALogic()
    if self.skipProjectionCheckBoxMulti.checked != 0:
      projectionFactor = 0
    else:
      projectionFactor = self.projectionFactor.value/100

    logic.runLandmarkMultiprocess(self.sourceModelMultiSelector.currentPath,self.sourceFiducialMultiSelector.currentPath,
    self.targetModelMultiSelector.currentPath, self.landmarkOutputSelector.currentPath, self.skipScalingMultiCheckBox.checked, projectionFactor,self.parameterDictionaryMulti )


  def updateLayout(self):
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(9)  #set layout to 3D only
    layoutManager.threeDWidget(0).threeDView().resetFocalPoint()
    layoutManager.threeDWidget(0).threeDView().resetCamera()

  def onChangeAdvanced(self):
    self.pointDensityMulti.value = self.pointDensity.value
    self.normalSearchRadiusMulti.value = self.normalSearchRadius.value
    self.FPFHSearchRadiusMulti.value = self.FPFHSearchRadius.value
    self.distanceThresholdMulti.value = self.distanceThreshold.value
    self.maxRANSACMulti.value = self.maxRANSAC.value
    if slicer.app.majorVersion*100+slicer.app.minorVersion < 412:
      self.maxRANSACValidationMulti.value = self.maxRANSACValidation.value
    else:
      self.RANSACConfidenceMulti.value = self.RANSACConfidence.value
    self.ICPDistanceThresholdMulti.value  = self.ICPDistanceThreshold.value
    self.alphaMulti.value = self.alpha.value
    self.betaMulti.value = self.beta.value
    self.CPDTolerenceMulti.value = self.CPDTolerence.value

    self.updateParameterDictionary()


  def updateParameterDictionary(self):
    # update the parameter dictionary from single run parameters
    if hasattr(self, 'parameterDictionary'):
      self.parameterDictionary["projectionFactor"] = self.projectionFactor.value
      self.parameterDictionary["pointDensity"] = self.pointDensity.value
      self.parameterDictionary["normalSearchRadius"] = int(self.normalSearchRadius.value)
      self.parameterDictionary["FPFHSearchRadius"] = int(self.FPFHSearchRadius.value)
      self.parameterDictionary["distanceThreshold"] = self.distanceThreshold.value
      self.parameterDictionary["maxRANSAC"] = int(self.maxRANSAC.value)
      if slicer.app.majorVersion*100+slicer.app.minorVersion < 412:
        self.parameterDictionary["maxRANSACValidation"] = int(self.maxRANSACValidation.value)
      else:
        self.parameterDictionary["RANSACConfidence"] = int(self.RANSACConfidence.value)
      self.parameterDictionary["ICPDistanceThreshold"] = self.ICPDistanceThreshold.value
      self.parameterDictionary["alpha"] = self.alpha.value
      self.parameterDictionary["beta"] = self.beta.value
      self.parameterDictionary["CPDIterations"] = int(self.CPDIterations.value)
      self.parameterDictionary["CPDTolerence"] = self.CPDTolerence.value

    # update the parameter dictionary from multi run parameters
    if hasattr(self, 'parameterDictionaryMulti'):
      self.parameterDictionaryMulti["projectionFactor"] = self.projectionFactorMulti.value
      self.parameterDictionaryMulti["pointDensity"] = self.pointDensityMulti.value
      self.parameterDictionaryMulti["normalSearchRadius"] = int(self.normalSearchRadiusMulti.value)
      self.parameterDictionaryMulti["FPFHSearchRadius"] = int(self.FPFHSearchRadiusMulti.value)
      self.parameterDictionaryMulti["distanceThreshold"] = self.distanceThresholdMulti.value
      self.parameterDictionaryMulti["maxRANSAC"] = int(self.maxRANSACMulti.value)
      if slicer.app.majorVersion*100+slicer.app.minorVersion < 412:
        self.parameterDictionaryMulti["maxRANSACValidation"] = int(self.maxRANSACValidationMulti.value)
      else:
        self.parameterDictionaryMulti["RANSACConfidence"] = int(self.RANSACConfidenceMulti.value)
      self.parameterDictionaryMulti["ICPDistanceThreshold"] = self.ICPDistanceThresholdMulti.value
      self.parameterDictionaryMulti["alpha"] = self.alphaMulti.value
      self.parameterDictionaryMulti["beta"] = self.betaMulti.value
      self.parameterDictionaryMulti["CPDIterations"] = int(self.CPDIterationsMulti.value)
      self.parameterDictionaryMulti["CPDTolerence"] = self.CPDTolerenceMulti.value



  def addAdvancedMenu(self, currentWidgetLayout):
    #
    # Advanced menu for single run
    #
    advancedCollapsibleButton = ctk.ctkCollapsibleButton()
    advancedCollapsibleButton.text = "Advanced parameter settings"
    advancedCollapsibleButton.collapsed = True
    currentWidgetLayout.addRow(advancedCollapsibleButton)
    advancedFormLayout = qt.QFormLayout(advancedCollapsibleButton)

    # Point density label
    pointDensityCollapsibleButton=ctk.ctkCollapsibleButton()
    pointDensityCollapsibleButton.text = "Point density and max projection"
    advancedFormLayout.addRow(pointDensityCollapsibleButton)
    pointDensityFormLayout = qt.QFormLayout(pointDensityCollapsibleButton)

    # Rigid registration label
    rigidRegistrationCollapsibleButton=ctk.ctkCollapsibleButton()
    rigidRegistrationCollapsibleButton.text = "Rigid registration"
    advancedFormLayout.addRow(rigidRegistrationCollapsibleButton)
    rigidRegistrationFormLayout = qt.QFormLayout(rigidRegistrationCollapsibleButton)

    # Deformable registration label
    deformableRegistrationCollapsibleButton=ctk.ctkCollapsibleButton()
    deformableRegistrationCollapsibleButton.text = "Deformable registration"
    advancedFormLayout.addRow(deformableRegistrationCollapsibleButton)
    deformableRegistrationFormLayout = qt.QFormLayout(deformableRegistrationCollapsibleButton)

    # Point Density slider
    pointDensity = ctk.ctkSliderWidget()
    pointDensity.singleStep = 0.1
    pointDensity.minimum = 0.1
    pointDensity.maximum = 3
    pointDensity.value = 1
    pointDensity.setToolTip("Adjust the density of the pointclouds. Larger values increase the number of points, and vice versa.")
    pointDensityFormLayout.addRow("Point Density Adjustment: ", pointDensity)

    # Set max projection factor
    projectionFactor = ctk.ctkSliderWidget()
    projectionFactor.enabled = True
    projectionFactor.singleStep = 1
    projectionFactor.minimum = 0
    projectionFactor.maximum = 10
    projectionFactor.value = 1
    projectionFactor.setToolTip("Set maximum point projection as a percentage of the image diagonal. Point projection is used to make sure predicted landmarks are placed on the target mesh.")
    pointDensityFormLayout.addRow("Maximum projection factor : ", projectionFactor)

    # Normal search radius slider

    normalSearchRadius = ctk.ctkSliderWidget()
    normalSearchRadius.singleStep = 1
    normalSearchRadius.minimum = 2
    normalSearchRadius.maximum = 12
    normalSearchRadius.value = 2
    normalSearchRadius.setToolTip("Set size of the neighborhood used when computing normals")
    rigidRegistrationFormLayout.addRow("Normal search radius: ", normalSearchRadius)

    #FPFH Search Radius slider
    FPFHSearchRadius = ctk.ctkSliderWidget()
    FPFHSearchRadius.singleStep = 1
    FPFHSearchRadius.minimum = 3
    FPFHSearchRadius.maximum = 20
    FPFHSearchRadius.value = 5
    FPFHSearchRadius.setToolTip("Set size of the neighborhood used when computing FPFH features")
    rigidRegistrationFormLayout.addRow("FPFH Search radius: ", FPFHSearchRadius)


    # Maximum distance threshold slider
    distanceThreshold = ctk.ctkSliderWidget()
    distanceThreshold.singleStep = .25
    distanceThreshold.minimum = 0.5
    distanceThreshold.maximum = 4
    distanceThreshold.value = 3
    distanceThreshold.setToolTip("Maximum correspondence points-pair distance threshold")
    rigidRegistrationFormLayout.addRow("Maximum corresponding point distance: ", distanceThreshold)

    # Maximum RANSAC iterations slider
    maxRANSAC = ctk.ctkDoubleSpinBox()
    maxRANSAC.singleStep = 1
    maxRANSAC.setDecimals(0)
    maxRANSAC.minimum = 1
    maxRANSAC.maximum = 500000000
    maxRANSAC.value = 1000000
    maxRANSAC.setToolTip("Maximum number of iterations of the RANSAC algorithm")
    rigidRegistrationFormLayout.addRow("Maximum RANSAC iterations: ", maxRANSAC)

    # Maximum RANSAC validation steps
    if slicer.app.majorVersion*100+slicer.app.minorVersion < 412:
      maxRANSACValidation = ctk.ctkDoubleSpinBox()
      maxRANSACValidation.singleStep = 1
      maxRANSACValidation.setDecimals(0)
      maxRANSACValidation.minimum = 1
      maxRANSACValidation.maximum = 500000000
      maxRANSACValidation.value = 500
      maxRANSACValidation.setToolTip("Maximum number of RANSAC validation steps")
      rigidRegistrationFormLayout.addRow("Maximum RANSAC validation steps: ", maxRANSACValidation)
    else:
      RANSACConfidence = ctk.ctkDoubleSpinBox()
      RANSACConfidence.singleStep = 0.001
      RANSACConfidence.setDecimals(3)
      RANSACConfidence.minimum = 0
      RANSACConfidence.maximum = 1
      RANSACConfidence.value = 0.999
      RANSACConfidence.setToolTip("Set up confidence (convergence criteria) for RANSAC global registration")
      rigidRegistrationFormLayout.addRow("Set up RANSAC confidence: ", RANSACConfidence)

    # ICP distance threshold slider
    ICPDistanceThreshold = ctk.ctkSliderWidget()
    ICPDistanceThreshold.singleStep = .1
    ICPDistanceThreshold.minimum = 0.1
    ICPDistanceThreshold.maximum = 2
    ICPDistanceThreshold.value = 1.5
    ICPDistanceThreshold.setToolTip("Maximum ICP points-pair distance threshold")
    rigidRegistrationFormLayout.addRow("Maximum ICP distance: ", ICPDistanceThreshold)

    # Alpha slider
    alpha = ctk.ctkDoubleSpinBox()
    alpha.singleStep = .1
    alpha.setDecimals(1)
    alpha.minimum = 0.1
    alpha.maximum = 10
    alpha.value = 2
    alpha.setToolTip("Parameter specifying trade-off between fit and smoothness. Low values induce fluidity, while higher values impose rigidity")
    deformableRegistrationFormLayout.addRow("Rigidity (alpha): ", alpha)

    # Beta slider
    beta = ctk.ctkDoubleSpinBox()
    beta.singleStep = 0.1
    beta.setDecimals(1)
    beta.minimum = 0.1
    beta.maximum = 10
    beta.value = 2
    beta.setToolTip("Width of gaussian filter used when applying smoothness constraint")
    deformableRegistrationFormLayout.addRow("Motion coherence (beta): ", beta)

    # # CPD iterations slider
    CPDIterations = ctk.ctkSliderWidget()
    CPDIterations.singleStep = 1
    CPDIterations.minimum = 100
    CPDIterations.maximum = 1000
    CPDIterations.value = 100
    CPDIterations.setToolTip("Maximum number of iterations of the CPD procedure")
    deformableRegistrationFormLayout.addRow("CPD iterations: ", CPDIterations)

    # # CPD tolerance slider
    CPDTolerence = ctk.ctkSliderWidget()
    CPDTolerence.setDecimals(4)
    CPDTolerence.singleStep = .0001
    CPDTolerence.minimum = 0.0001
    CPDTolerence.maximum = 0.01
    CPDTolerence.value = 0.001
    CPDTolerence.setToolTip("Tolerance used to assess CPD convergence")
    deformableRegistrationFormLayout.addRow("CPD tolerance: ", CPDTolerence)

    if slicer.app.majorVersion*100+slicer.app.minorVersion < 412:
      return projectionFactor, pointDensity, normalSearchRadius, FPFHSearchRadius, distanceThreshold, maxRANSAC, maxRANSACValidation, ICPDistanceThreshold, alpha, beta, CPDIterations, CPDTolerence
    else:
      return projectionFactor, pointDensity, normalSearchRadius, FPFHSearchRadius, distanceThreshold, maxRANSAC, RANSACConfidence, ICPDistanceThreshold, alpha, beta, CPDIterations, CPDTolerence

#
# ALPACALogic
#

class ALPACALogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

  def runLandmarkMultiprocess(self, sourceModelPath, sourceLandmarkPath, targetModelDirectory, outputDirectory, skipScaling, projectionFactor, parameters):
    extensionModel = ".ply"
    # Iterate through target models
    for targetFileName in os.listdir(targetModelDirectory):
      if targetFileName.endswith(extensionModel):
        targetFilePath = os.path.join(targetModelDirectory, targetFileName)
        # Subsample source and target models
        sourceData, targetData, sourcePoints, targetPoints, sourceFeatures, targetFeatures, voxelSize, scaling = self.runSubsample(sourceModelPath,
        	targetFilePath, skipScaling, parameters)
        # Rigid registration of source sampled points and landmarks
        sourceLM_vtk, sourceLMNode = self.loadAndScaleFiducials(sourceLandmarkPath, scaling)
        ICPTransform = self.estimateTransform(sourcePoints, targetPoints, sourceFeatures, targetFeatures, voxelSize, skipScaling, parameters)
        ICPTransform_vtk = self.convertMatrixToVTK(ICPTransform)
        sourceSLM_vtk = self.convertPointsToVTK(sourcePoints.points)
        alignedSourceSLM_vtk = self.applyTransform(ICPTransform_vtk, sourceSLM_vtk)
        alignedSourceLM_vtk = self.applyTransform(ICPTransform_vtk, sourceLM_vtk)

        # Non-rigid Registration
        alignedSourceSLM_np = vtk_np.vtk_to_numpy(alignedSourceSLM_vtk.GetPoints().GetData())
        alignedSourceLM_np = vtk_np.vtk_to_numpy(alignedSourceLM_vtk.GetPoints().GetData())
        registeredSourceLM_np = self.runCPDRegistration(alignedSourceLM_np, alignedSourceSLM_np, targetPoints.points, parameters)
        outputFiducialNode = self.exportPointCloud(registeredSourceLM_np, "Initial Predicted Landmarks")
        self.RAS2LPSTransform(outputFiducialNode)
        # Projection
        if projectionFactor == 0:
          self.propagateLandmarkTypes(sourceLMNode, outputFiducialNode)
          # Save output landmarks
          rootName = os.path.splitext(targetFileName)[0]
          outputFilePath = os.path.join(outputDirectory, rootName + ".fcsv")
          slicer.util.saveNode(outputFiducialNode, outputFilePath)
          slicer.mrmlScene.RemoveNode(outputFiducialNode)
        else:
          outputPoints_vtk = self.getFiducialPoints(outputFiducialNode)
          targetModelNode = slicer.util.loadModel(targetFilePath)
          sourceModelNode = slicer.util.loadModel(sourceModelPath)
          sourcePoints = slicer.util.arrayFromModelPoints(sourceModelNode)
          sourcePoints[:] = np.asarray(sourceData.points)
          sourceModelNode.GetPolyData().GetPoints().GetData().Modified()
          sourceModelNode_warped = self.applyTPSTransform(sourceLM_vtk.GetPoints(), outputPoints_vtk, sourceModelNode, 'Warped Source Mesh')

          # project landmarks from template to model
          maxProjection = (targetModelNode.GetPolyData().GetLength()) * projectionFactor
          projectedPoints = self.projectPointsPolydata(sourceModelNode_warped.GetPolyData(), targetModelNode.GetPolyData(), outputPoints_vtk, maxProjection)
          projectedLMNode= slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode',"Refined Predicted Landmarks")
          for i in range(projectedPoints.GetNumberOfPoints()):
            point = projectedPoints.GetPoint(i)
            projectedLMNode.AddFiducialFromArray(point)
          self.propagateLandmarkTypes(sourceLMNode, projectedLMNode)
          # Save output landmarks
          rootName = os.path.splitext(targetFileName)[0]
          outputFilePath = os.path.join(outputDirectory, rootName + ".fcsv")
          slicer.util.saveNode(projectedLMNode, outputFilePath)
          slicer.mrmlScene.RemoveNode(outputFiducialNode)
          slicer.mrmlScene.RemoveNode(projectedLMNode)
          slicer.mrmlScene.RemoveNode(sourceModelNode)
          slicer.mrmlScene.RemoveNode(targetModelNode)
          slicer.mrmlScene.RemoveNode(sourceModelNode_warped)
          slicer.mrmlScene.RemoveNode(sourceLMNode)


  def exportPointCloud(self, pointCloud, nodeName):
    fiducialNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode',nodeName)
    for point in pointCloud:
      fiducialNode.AddFiducialFromArray(point)
    return fiducialNode

    #node.AddFiducialFromArray(point)
  def applyTPSTransform(self, sourcePoints, targetPoints, modelNode, nodeName):
    transform=vtk.vtkThinPlateSplineTransform()
    transform.SetSourceLandmarks( sourcePoints)
    transform.SetTargetLandmarks( targetPoints )
    transform.SetBasisToR() # for 3D transform

    transformFilter = vtk.vtkTransformPolyDataFilter()
    transformFilter.SetInputData(modelNode.GetPolyData())
    transformFilter.SetTransform(transform)
    transformFilter.Update()

    warpedPolyData = transformFilter.GetOutput()
    warpedModelNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode', nodeName)
    warpedModelNode.CreateDefaultDisplayNodes()
    warpedModelNode.SetAndObservePolyData(warpedPolyData)
    #self.RAS2LPSTransform(warpedModelNode)
    return warpedModelNode

  def runCPDRegistration(self, sourceLM, sourceSLM, targetSLM, parameters):
    from open3d import geometry
    from open3d import utility
    sourceArrayCombined = np.append(sourceSLM, sourceLM, axis=0)
    targetArray = np.asarray(targetSLM)
    #Convert to pointcloud for scaling
    sourceCloud = geometry.PointCloud()
    sourceCloud.points = utility.Vector3dVector(sourceArrayCombined)
    targetCloud = geometry.PointCloud()
    targetCloud.points = utility.Vector3dVector(targetArray)
    cloudSize = np.max(targetCloud.get_max_bound() - targetCloud.get_min_bound())
    targetCloud.scale(25 / cloudSize, center = (0,0,0))
    sourceCloud.scale   (25 / cloudSize, center = (0,0,0))
    #Convert back to numpy for cpd
    sourceArrayCombined = np.asarray(sourceCloud.points,dtype=np.float32)
    targetArray = np.asarray(targetCloud.points,dtype=np.float32)
    registrationOutput = self.cpd_registration(targetArray, sourceArrayCombined, parameters["CPDIterations"], parameters["CPDTolerence"], parameters["alpha"], parameters["beta"])
    deformed_array, _ = registrationOutput.register()
    #Capture output landmarks from source pointcloud
    fiducial_prediction = deformed_array[-len(sourceLM):]
    fiducialCloud = geometry.PointCloud()
    fiducialCloud.points = utility.Vector3dVector(fiducial_prediction)
    fiducialCloud.scale(cloudSize/25, center = (0,0,0))
    return np.asarray(fiducialCloud.points)

  def RAS2LPSTransform(self, modelNode):
    matrix=vtk.vtkMatrix4x4()
    matrix.Identity()
    matrix.SetElement(0,0,-1)
    matrix.SetElement(1,1,-1)
    transform=vtk.vtkTransform()
    transform.SetMatrix(matrix)
    transformNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLTransformNode', 'RAS2LPS')
    transformNode.SetAndObserveTransformToParent( transform )
    modelNode.SetAndObserveTransformNodeID(transformNode.GetID())
    slicer.vtkSlicerTransformLogic().hardenTransform(modelNode)
    slicer.mrmlScene.RemoveNode(transformNode)

  def convertMatrixToVTK(self, matrix):
    matrix_vtk = vtk.vtkMatrix4x4()
    for i in range(4):
      for j in range(4):
        matrix_vtk.SetElement(i,j,matrix[i][j])
    return matrix_vtk

  def convertMatrixToTransformNode(self, matrix, transformName):
    matrix_vtk = vtk.vtkMatrix4x4()
    for i in range(4):
      for j in range(4):
        matrix_vtk.SetElement(i,j,matrix[i][j])

    transform = vtk.vtkTransform()
    transform.SetMatrix(matrix_vtk)
    transformNode =  slicer.mrmlScene.AddNewNodeByClass('vtkMRMLTransformNode', transformName)
    transformNode.SetAndObserveTransformToParent( transform )

    return transformNode

  def applyTransform(self, matrix, polydata):
    transform = vtk.vtkTransform()
    transform.SetMatrix(matrix)

    transformFilter = vtk.vtkTransformPolyDataFilter()
    transformFilter.SetTransform(transform)
    transformFilter.SetInputData(polydata)
    transformFilter.Update()
    return transformFilter.GetOutput()

  def convertPointsToVTK(self, points):
    array_vtk = vtk_np.numpy_to_vtk(points, deep=True, array_type=vtk.VTK_FLOAT)
    points_vtk = vtk.vtkPoints()
    points_vtk.SetData(array_vtk)
    polydata_vtk = vtk.vtkPolyData()
    polydata_vtk.SetPoints(points_vtk)
    return polydata_vtk

  def displayPointCloud(self, polydata, pointRadius, nodeName, nodeColor):
    #set up glyph for visualizing point cloud
    sphereSource = vtk.vtkSphereSource()
    sphereSource.SetRadius(pointRadius)
    glyph = vtk.vtkGlyph3D()
    glyph.SetSourceConnection(sphereSource.GetOutputPort())
    glyph.SetInputData(polydata)
    glyph.ScalingOff()
    glyph.Update()

    #display
    modelNode=slicer.mrmlScene.GetFirstNodeByName(nodeName)
    if modelNode is None:  # if there is no node with this name, create with display node
      modelNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode', nodeName)
      modelNode.CreateDefaultDisplayNodes()

    modelNode.SetAndObservePolyData(glyph.GetOutput())
    modelNode.GetDisplayNode().SetColor(nodeColor)
    return modelNode

  def displayMesh(self, polydata, nodeName, nodeColor):
    modelNode=slicer.mrmlScene.GetFirstNodeByName(nodeName)
    if modelNode is None:  # if there is no node with this name, create with display node
      modelNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode', nodeName)
      modelNode.CreateDefaultDisplayNodes()

    modelNode.SetAndObservePolyData(polydata)
    modelNode.GetDisplayNode().SetColor(nodeColor)
    return modelNode

  def estimateTransform(self, sourcePoints, targetPoints, sourceFeatures, targetFeatures, voxelSize, skipScaling, parameters):
    if slicer.app.majorVersion*100+slicer.app.minorVersion < 412:
      ransac = self.execute_global_registration(sourcePoints, targetPoints, sourceFeatures, targetFeatures, voxelSize, 
        parameters["distanceThreshold"], parameters["maxRANSAC"], parameters["maxRANSACValidation"], skipScaling)
    else:
      ransac = self.execute_global_registration_2(sourcePoints, targetPoints, sourceFeatures, targetFeatures, voxelSize, 
        parameters["distanceThreshold"], parameters["maxRANSAC"], parameters["RANSACConfidence"], skipScaling)

    # Refine the initial registration using an Iterative Closest Point (ICP) registration
    icp = self.refine_registration(sourcePoints, targetPoints, sourceFeatures, targetFeatures, voxelSize, ransac, parameters["ICPDistanceThreshold"]) 
    return icp.transformation                                     
  
  def runSubsample(self, sourcePath, targetPath, skipScaling, parameters):
    from open3d import io
    print(":: Loading point clouds and downsampling")
    source = io.read_point_cloud(sourcePath)
    sourceSize = np.linalg.norm(np.asarray(source.get_max_bound()) - np.asarray(source.get_min_bound()))
    target = io.read_point_cloud(targetPath)
    targetSize = np.linalg.norm(np.asarray(target.get_max_bound()) - np.asarray(target.get_min_bound()))
    voxel_size = targetSize/(55*parameters["pointDensity"])
    scaling = (targetSize)/sourceSize
    if skipScaling != 0:
        scaling = 1
    source.scale(scaling, center = (0,0,0))
    source_down, source_fpfh = self.preprocess_point_cloud(source, voxel_size, parameters["normalSearchRadius"], parameters["FPFHSearchRadius"])
    target_down, target_fpfh = self.preprocess_point_cloud(target, voxel_size, parameters["normalSearchRadius"], parameters["FPFHSearchRadius"])
    return source, target, source_down, target_down, source_fpfh, target_fpfh, voxel_size, scaling

  def loadAndScaleFiducials (self, fiducialPath, scaling):
    from open3d import geometry
    from open3d import utility
    sourceLandmarkNode =  slicer.util.loadMarkups(fiducialPath)
    self.RAS2LPSTransform(sourceLandmarkNode)
    point = [0,0,0]
    sourceLandmarks_np=np.zeros(shape=(sourceLandmarkNode.GetNumberOfFiducials(),3))
    for i in range(sourceLandmarkNode.GetNumberOfFiducials()):
      sourceLandmarkNode.GetMarkupPoint(0,i,point)
      sourceLandmarks_np[i,:]=point
    cloud = geometry.PointCloud()
    cloud.points = utility.Vector3dVector(sourceLandmarks_np)
    cloud.scale(scaling, center = (0,0,0))
    fiducialVTK = self.convertPointsToVTK (cloud.points)
    return fiducialVTK, sourceLandmarkNode

  def propagateLandmarkTypes(self,sourceNode, targetNode):
     for i in range(sourceNode.GetNumberOfControlPoints()):
       pointDescription = sourceNode.GetNthControlPointDescription(i)
       targetNode.SetNthControlPointDescription(i,pointDescription)
       pointLabel = sourceNode.GetNthFiducialLabel(i)
       targetNode.SetNthFiducialLabel(i, pointLabel)

  def distanceMatrix(self, a):
    """
    Computes the euclidean distance matrix for n points in a 3D space
    Returns a nXn matrix
     """
    id,jd=a.shape
    fnx = lambda q : q - np.reshape(q, (id, 1))
    dx=fnx(a[:,0])
    dy=fnx(a[:,1])
    dz=fnx(a[:,2])
    return (dx**2.0+dy**2.0+dz**2.0)**0.5

  def preprocess_point_cloud(self, pcd, voxel_size, radius_normal_factor, radius_feature_factor):
    from open3d import geometry
    if slicer.app.majorVersion*100+slicer.app.minorVersion < 412:
      from open3d import registration
    else:
      from open3d import pipelines
      registration = pipelines.registration
    print(":: Downsample with a voxel size %.3f." % voxel_size)
    pcd_down = pcd.voxel_down_sample(voxel_size)
    radius_normal = voxel_size * radius_normal_factor
    print(":: Estimate normal with search radius %.3f." % radius_normal)
    pcd_down.estimate_normals(
        geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=30))
    radius_feature = voxel_size * radius_feature_factor
    print(":: Compute FPFH feature with search radius %.3f." % radius_feature)
    pcd_fpfh = registration.compute_fpfh_feature(
        pcd_down,
        geometry.KDTreeSearchParamHybrid(radius=radius_feature, max_nn=100))
    return pcd_down, pcd_fpfh



  def execute_global_registration(self, source_down, target_down, source_fpfh,
                                target_fpfh, voxel_size, distance_threshold_factor, maxIter, maxValidation, skipScaling):
    from open3d import registration
    distance_threshold = voxel_size * distance_threshold_factor
    print(":: RANSAC registration on downsampled point clouds.")
    print("   Since the downsampling voxel size is %.3f," % voxel_size)
    print("   we use a liberal distance threshold %.3f." % distance_threshold)
    fitness = 0
    count = 0
    maxAttempts = 30
    while fitness < 0.99 and count < maxAttempts:
      result = registration.registration_ransac_based_on_feature_matching(
          source_down, target_down, source_fpfh, target_fpfh, True, distance_threshold,
          registration.TransformationEstimationPointToPoint(skipScaling == 0), 3, [
              registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
              registration.CorrespondenceCheckerBasedOnDistance(
                  distance_threshold)
          ], registration.RANSACConvergenceCriteria(maxIter, maxValidation))
      fitness = result.fitness
      count += 1
    return result

  def execute_global_registration_2(self, source_down, target_down, source_fpfh,
                                target_fpfh, voxel_size, distance_threshold_factor, maxIter, confidence, skipScaling):
    from open3d import pipelines
    registration = pipelines.registration
    distance_threshold = voxel_size * distance_threshold_factor
    print(":: RANSAC registration on downsampled point clouds.")
    print("   Since the downsampling voxel size is %.3f," % voxel_size)
    print("   we use a liberal distance threshold %.3f." % distance_threshold)
    fitness = 0
    count = 0
    maxAttempts = 30
    while fitness < 0.99 and count < maxAttempts:
      result = registration.registration_ransac_based_on_feature_matching(
          source_down, target_down, source_fpfh, target_fpfh, True, distance_threshold,
          registration.TransformationEstimationPointToPoint(skipScaling == 0), 3, [
              registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
              registration.CorrespondenceCheckerBasedOnDistance(
                  distance_threshold)
          ], registration.RANSACConvergenceCriteria(maxIter, confidence))
      fitness = result.fitness
      count += 1 
    return result

  def refine_registration(self, source, target, source_fpfh, target_fpfh, voxel_size, result_ransac, ICPThreshold_factor):
    if slicer.app.majorVersion*100+slicer.app.minorVersion < 412:
      from open3d import registration
    else:
      from open3d import pipelines
      registration = pipelines.registration
    distance_threshold = voxel_size * ICPThreshold_factor
    print(":: Point-to-plane ICP registration is applied on original point")
    print("   clouds to refine the alignment. This time we use a strict")
    print("   distance threshold %.3f." % distance_threshold)
    result = registration.registration_icp(
        source, target, distance_threshold, result_ransac.transformation,
        registration.TransformationEstimationPointToPlane())
    return result



  def cpd_registration(self, targetArray, sourceArray, CPDIterations, CPDTolerence, alpha_parameter, beta_parameter):
    from cpdalp import DeformableRegistration
    output = DeformableRegistration(**{'X': targetArray, 'Y': sourceArray,'max_iterations': CPDIterations, 'tolerance': CPDTolerence, 'low_rank':True}, alpha = alpha_parameter, beta  = beta_parameter)
    return output

  def getFiducialPoints(self,fiducialNode):
    points = vtk.vtkPoints()
    point=[0,0,0]
    for i in range(fiducialNode.GetNumberOfFiducials()):
      fiducialNode.GetNthFiducialPosition(i,point)
      points.InsertNextPoint(point)

    return points

  def runPointProjection(self, template, model, templateLandmarks, maxProjectionFactor):
    maxProjection = (model.GetPolyData().GetLength()) * maxProjectionFactor
    print("Max projection: ", maxProjection)
    templatePoints = self.getFiducialPoints(templateLandmarks)

    # project landmarks from template to model
    projectedPoints = self.projectPointsPolydata(template.GetPolyData(), model.GetPolyData(), templatePoints, maxProjection)
    projectedLMNode= slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode',"Refined Predicted Landmarks")
    for i in range(projectedPoints.GetNumberOfPoints()):
      point = projectedPoints.GetPoint(i)
      projectedLMNode.AddFiducialFromArray(point)
    return projectedLMNode

  def projectPointsPolydata(self, sourcePolydata, targetPolydata, originalPoints, rayLength):
    print("original points: ", originalPoints.GetNumberOfPoints())
    #set up polydata for projected points to return
    projectedPointData = vtk.vtkPolyData()
    projectedPoints = vtk.vtkPoints()
    projectedPointData.SetPoints(projectedPoints)

    #set up locater for intersection with normal vector rays
    obbTree = vtk.vtkOBBTree()
    obbTree.SetDataSet(targetPolydata)
    obbTree.BuildLocator()

    #set up point locator for finding surface normals and closest point
    pointLocator = vtk.vtkPointLocator()
    pointLocator.SetDataSet(sourcePolydata)
    pointLocator.BuildLocator()

    targetPointLocator = vtk.vtkPointLocator()
    targetPointLocator.SetDataSet(targetPolydata)
    targetPointLocator.BuildLocator()

    #get surface normal from each landmark point
    rayDirection=[0,0,0]
    normalArray = sourcePolydata.GetPointData().GetArray("Normals")
    if(not normalArray):
      print("no normal array, calculating....")
      normalFilter=vtk.vtkPolyDataNormals()
      normalFilter.ComputePointNormalsOn()
      normalFilter.SetInputData(sourcePolydata)
      normalFilter.Update()
      normalArray = normalFilter.GetOutput().GetPointData().GetArray("Normals")
      if(not normalArray):
        print("Error: no normal array")
        return projectedPointData
    for index in range(originalPoints.GetNumberOfPoints()):
      originalPoint= originalPoints.GetPoint(index)
      # get ray direction from closest normal
      closestPointId = pointLocator.FindClosestPoint(originalPoint)
      rayDirection = normalArray.GetTuple(closestPointId)
      rayEndPoint=[0,0,0]
      for dim in range(len(rayEndPoint)):
        rayEndPoint[dim] = originalPoint[dim] + rayDirection[dim]* rayLength
      intersectionIds=vtk.vtkIdList()
      intersectionPoints=vtk.vtkPoints()
      obbTree.IntersectWithLine(originalPoint,rayEndPoint,intersectionPoints,intersectionIds)
      #if there are intersections, update the point to most external one.
      if intersectionPoints.GetNumberOfPoints() > 0:
        exteriorPoint = intersectionPoints.GetPoint(intersectionPoints.GetNumberOfPoints()-1)
        projectedPoints.InsertNextPoint(exteriorPoint)
      #if there are no intersections, reverse the normal vector
      else:
        for dim in range(len(rayEndPoint)):
          rayEndPoint[dim] = originalPoint[dim] + rayDirection[dim]* -rayLength
        obbTree.IntersectWithLine(originalPoint,rayEndPoint,intersectionPoints,intersectionIds)
        if intersectionPoints.GetNumberOfPoints()>0:
          exteriorPoint = intersectionPoints.GetPoint(0)
          projectedPoints.InsertNextPoint(exteriorPoint)
        #if none in reverse direction, use closest mesh point
        else:
          closestPointId = targetPointLocator.FindClosestPoint(originalPoint)
          rayOrigin = targetPolydata.GetPoint(closestPointId)
          projectedPoints.InsertNextPoint(rayOrigin)
    return projectedPointData

  def takeScreenshot(self,name,description,type=-1):
    # show the message even if not taking a screen shot
    slicer.util.delayDisplay('Take screenshot: '+description+'.\nResult is available in the Annotations module.', 3000)

    lm = slicer.app.layoutManager()
    # switch on the type to get the requested window
    widget = 0
    if type == slicer.qMRMLScreenShotDialog.FullLayout:
      # full layout
      widget = lm.viewport()
    elif type == slicer.qMRMLScreenShotDialog.ThreeD:
      # just the 3D window
      widget = lm.threeDWidget(0).threeDView()
    elif type == slicer.qMRMLScreenShotDialog.Red:
      # red slice window
      widget = lm.sliceWidget("Red")
    elif type == slicer.qMRMLScreenShotDialog.Yellow:
      # yellow slice window
      widget = lm.sliceWidget("Yellow")
    elif type == slicer.qMRMLScreenShotDialog.Green:
      # green slice window
      widget = lm.sliceWidget("Green")
    else:
      # default to using the full window
      widget = slicer.util.mainWindow()
      # reset the type so that the node is set correctly
      type = slicer.qMRMLScreenShotDialog.FullLayout

    # grab and convert to vtk image data
    qimage = ctk.ctkWidgetsUtils.grabWidget(widget)
    imageData = vtk.vtkImageData()
    slicer.qMRMLUtils().qImageToVtkImageData(qimage,imageData)

    annotationLogic = slicer.modules.annotations.logic()
    annotationLogic.CreateSnapShot(name, description, type, 1, imageData)

  def process(self, inputVolume, outputVolume, imageThreshold, invert=False, showResult=True):
    """
    Run the processing algorithm.
    Can be used without GUI widget.
    :param inputVolume: volume to be thresholded
    :param outputVolume: thresholding result
    :param imageThreshold: values above/below this threshold will be set to 0
    :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
    :param showResult: show output volume in slice viewers
    """

    if not inputVolume or not outputVolume:
      raise ValueError("Input or output volume is invalid")

    import time
    startTime = time.time()
    logging.info('Processing started')

    # Compute the thresholded output volume using the "Threshold Scalar Volume" CLI module
    cliParams = {
      'InputVolume': inputVolume.GetID(),
      'OutputVolume': outputVolume.GetID(),
      'ThresholdValue' : imageThreshold,
      'ThresholdType' : 'Above' if invert else 'Below'
      }
    cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True, update_display=showResult)
    # We don't need the CLI module node anymore, remove it to not clutter the scene with it
    slicer.mrmlScene.RemoveNode(cliNode)

    stopTime = time.time()
    logging.info(f'Processing completed in {stopTime-startTime:.2f} seconds')


class ALPACATest(ScriptedLoadableModuleTest):
  """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
      """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
      """
    self.setUp()
    self.test_ALPACA1()

  def test_ALPACA1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")

    # Get/create input data

    import SampleData
    registerSampleData()
    inputVolume = SampleData.downloadSample('TemplateKey1')
    self.delayDisplay('Loaded test data set')

    inputScalarRange = inputVolume.GetImageData().GetScalarRange()
    self.assertEqual(inputScalarRange[0], 0)
    self.assertEqual(inputScalarRange[1], 695)

    outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    threshold = 100

    # Test the module logic

    logic = ALPACALogic()

    # Test algorithm with non-inverted threshold
    logic.process(inputVolume, outputVolume, threshold, True)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], threshold)

    # Test algorithm with inverted threshold
    logic.process(inputVolume, outputVolume, threshold, False)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], inputScalarRange[1])

    self.delayDisplay('Test passed')
