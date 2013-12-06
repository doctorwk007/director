from ddapp.segmentation import *

from ddapp import mapsregistrar
from ddapp import drilltaskpanel
import PythonQt
from PythonQt import QtCore, QtGui



def getLumberDimensions(lumberId):

    dimensions = [
                  [0.089, 0.038], # 2x4
                  [0.140, 0.038], # 2x6
                  [0.089, 0.089], # 4x4
                 ]

    return dimensions[lumberId]


def _makeButton(text, func):

    b = QtGui.QPushButton(text)
    b.connect('clicked()', func)
    return b


class SegmentationPanel(object):

    def __init__(self):
        self.panel = QtGui.QWidget()
        self.panel.setWindowTitle('Segmentation Tools')

        self.taskSelection = PythonQt.dd.ddTaskSelection()
        self.taskSelection.connect('taskSelected(int)', self.onTaskSelected)

        l = QtGui.QVBoxLayout(self.panel)
        self.backButton = self._makeBackButton()
        l.addWidget(self.backButton)
        l.addWidget(self.taskSelection)
        self.backButton.hide()

        wizards = {
                    'driving' : self._makeDrivingWizard,
                    'terrain' : self._makeTerrainWizard,
                    'ladder' : self._makeLadderWizard,
                    'debris' : self._makeDebrisWizard,
                    'door' : self._makeDoorWizard,
                    'drill' : self._makeDrillWizard,
                    'valve' : self._makeValveWizard,
                    'firehose' : self._makeFirehoseWizard,
                  }

        self.wizards = {}
        for name, func in wizards.iteritems():
          widget = func()
          self.wizards[name] = widget
          l.addWidget(widget)
          widget.hide()

    def _makeDebrisWizard(self):
        debrisWizard = QtGui.QWidget()
        lumberSelection = PythonQt.dd.ddLumberSelection()
        lumberSelection.connect('lumberSelected(int)', self.onDebrisLumberSelected)
        l = QtGui.QVBoxLayout(debrisWizard)
        l.addWidget(lumberSelection)
        l.addWidget(_makeButton('segment cinderblock wall', startSegmentDebrisWall))
        l.addWidget(_makeButton('segment cinderblock wall manual', startSegmentDebrisWallManual))
        l.addStretch()
        return debrisWizard

    def _makeFirehoseWizard(self):
        firehoseWizard = QtGui.QWidget()
        segmentButton = QtGui.QToolButton()
        segmentButton.setIcon(QtGui.QIcon(':/images/wye.png'))
        segmentButton.setIconSize(QtCore.QSize(60,60))
        segmentButton.connect('clicked()', self.onSegmentWye)
        l = QtGui.QVBoxLayout(firehoseWizard)
        l.addWidget(segmentButton)
        l.addWidget(_makeButton('segment hose nozzle', startHoseNozzleSegmentation))
        l.addStretch()
        return firehoseWizard

    def _makeDoorWizard(self):
        wizard = QtGui.QWidget()
        l = QtGui.QVBoxLayout(wizard)
        l.addWidget(_makeButton('segment door handle - left', functools.partial(startDoorHandleSegmentation, 'left')))
        l.addWidget(_makeButton('segment door handle - right', functools.partial(startDoorHandleSegmentation, 'right')))
        l.addStretch()
        return wizard

    def _makeDrivingWizard(self):
        wizard = QtGui.QWidget()
        l = QtGui.QVBoxLayout(wizard)
        l.addStretch()
        return wizard

    def _makeLadderWizard(self):
        wizard = QtGui.QWidget()
        l = QtGui.QVBoxLayout(wizard)
        l.addStretch()
        return wizard

    def _makeValveWizard(self):
        wizard = QtGui.QWidget()
        l = QtGui.QVBoxLayout(wizard)
        l.addWidget(_makeButton('segment valve', functools.partial(startValveSegmentationByWallPlane, 0.195)))
        l.addWidget(_makeButton('segment small valve', functools.partial(startValveSegmentationByWallPlane, 0.10)))
        l.addWidget(_makeButton('segment bar', functools.partial(startInteractiveLineDraw, [0.015, 0.015])))
        l.addWidget(QtGui.QLabel(''))
        l.addWidget(_makeButton('refit wall', startRefitWall))

        hw = QtGui.QFrame()
        hl = QtGui.QHBoxLayout(hw)
        hl.addWidget(_makeButton('request valve circle plan', self.requestValveCirclePlan))
        self.circlePlanAngle = QtGui.QSpinBox()
        self.circlePlanAngle.setMinimum(-360)
        self.circlePlanAngle.setMaximum(360)
        self.circlePlanAngle.setSingleStep(5)
        hl.addWidget(self.circlePlanAngle)
        hl.addWidget(QtGui.QLabel('degrees'))
        l.addWidget(hw)

        l.addStretch()
        return wizard


    def _makeDrillWizard(self):
        drillWizard = QtGui.QGroupBox('Drill Segmentation')
        l = QtGui.QVBoxLayout(drillWizard)
        l.addWidget(_makeButton('segment drill on table', startDrillAutoSegmentation))
        l.addWidget(_makeButton('segment drill in hand', startDrillInHandSegmentation))
        l.addWidget(_makeButton('segment wall', startDrillWallSegmentation))
        l.addWidget(_makeButton('segment wall constrained', startDrillWallSegmentationConstrained))

        hw = QtGui.QWidget()
        hl = QtGui.QHBoxLayout(hw)
        hl.addWidget(_makeButton('move drill to hand', self.moveDrillToHand))
        self.handCombo = QtGui.QComboBox()
        self.handCombo.addItem('left')
        self.handCombo.addItem('right')
        hl.addWidget(self.handCombo)
        hl.addWidget(_makeButton('flip z', self.flipDrill))
        self.drillFlip = False
        l.addWidget(hw)
        self.drillRotationSlider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.drillRotationSlider.setMinimum(0)
        self.drillRotationSlider.setMaximum(100)
        self.drillRotationSlider.setValue(0)
        l.addWidget(self.drillRotationSlider)
        hw.connect(self.drillRotationSlider, 'valueChanged(int)', self.moveDrillToHand)
        l.addWidget(QtGui.QLabel(''))


        self.drillTaskPanel = drilltaskpanel.DrillTaskPanel()
        l.addWidget(self.drillTaskPanel.widget)

        l.addStretch()
        return drillWizard


    def _makeTerrainWizard(self):
        terrainWizard = QtGui.QWidget()

        self.cinderBlockButton = QtGui.QToolButton()
        self.cinderBlock2Button = QtGui.QToolButton()
        self.cinderBlockButton.setIcon(QtGui.QIcon(':/images/cinderblock.png'))
        self.cinderBlock2Button.setIcon(QtGui.QIcon(':/images/cinderblock_double.png'))
        self.cinderBlockButton.setIconSize(QtCore.QSize(60,60))
        self.cinderBlock2Button.setIconSize(QtCore.QSize(60,60))

        self.cinderBlockButton.connect('clicked()', functools.partial(self.onTerrainCinderblockSelected, self.cinderBlockButton))
        self.cinderBlock2Button.connect('clicked()', functools.partial(self.onTerrainCinderblockSelected, self.cinderBlock2Button))

        buttons = QtGui.QWidget()
        l = QtGui.QHBoxLayout(buttons)
        l.addStretch()
        l.addWidget(self.cinderBlockButton)
        l.addWidget(self.cinderBlock2Button)
        l.addStretch()

        l = QtGui.QVBoxLayout(terrainWizard)
        l.addWidget(buttons)
        l.addWidget(_makeButton('double wide', functools.partial(startInteractiveLineDraw, [0.1905*2, 0.149225])))


        l.addStretch()
        return terrainWizard

    def _makeBackButton(self):
        w = QtGui.QPushButton()
        w.setIcon(QtGui.QApplication.style().standardIcon(QtGui.QStyle.SP_ArrowBack))
        w.connect('clicked()', self.onBackButton)

        frame = QtGui.QWidget()
        l = QtGui.QHBoxLayout(frame)
        l.addWidget(w)
        l.addStretch()
        return frame


    def onBackButton(self):
        self.cancelCurrentTask()

    def onSegmentWye(self):
        startWyeSegmentation()

    def onDebrisLumberSelected(self, lumberId):
        blockDimensions = getLumberDimensions(lumberId)
        startInteractiveLineDraw(blockDimensions)

    def onTerrainCinderblockSelected(self, button):
        if button == self.cinderBlockButton:
            blockDimensions = [0.1905, 0.149225]
        elif button == self.cinderBlock2Button:
            blockDimensions = [0.1905, 0.29845]
        startInteractiveLineDraw(blockDimensions)

    def _showTaskWidgets(self, w):
        self.taskSelection.hide()
        self.backButton.show()
        w.show()

    def startTask(self, taskName):
        self._showTaskWidgets(self.wizards[taskName])

    def requestValveCirclePlan(self):
        self.drillTaskPanel.valveCirclePlan(self.circlePlanAngle.value)

    def moveDrillToHand(self):
        hand = self.handCombo.currentText
        rotation = (self.drillRotationSlider.value / 100.0) * 360
        self.drillOffset = getDrillInHandOffset(zRotation=rotation, flip=self.drillFlip)
        moveDrillToHand(self.drillOffset, hand)

    def flipDrill(self):
        self.drillFlip = not self.drillFlip

        self.moveDrillToHand()

    def cancelCurrentTask(self):
        for w in self.wizards.values():
            w.hide()
        self.backButton.hide()
        self.taskSelection.show()

    def onTaskSelected(self, taskId):

        tasks = {
                   1: 'driving',
                   2: 'terrain',
                   3: 'ladder',
                   4: 'debris',
                   5: 'door',
                   6: 'drill',
                   7: 'valve',
                   8: 'firehose',
                  }

        taskName = tasks[taskId+1]
        self.startTask(taskName)


def createDockWidget():
    global _segmentationPanel, _dock
    try: _segmentationPanel
    except NameError:
        _segmentationPanel = SegmentationPanel()
        _dock = app.addWidgetToDock(_segmentationPanel.panel)
        _dock.hide()



def getOrCreateSegmentationView():

    viewManager = app.getViewManager()
    segmentationView = viewManager.findView('Segmentation View')
    if not segmentationView:
        segmentationView = viewManager.createView('Segmentation View', 'VTK View')
        installEventFilter(segmentationView, segmentationViewEventFilter)

    return segmentationView


def onSegmentationViewDoubleClicked(displayPoint):


    action = 'zoom_to'


    if om.findObjectByName('major planes'):
        action = 'select_actor'


    if action == 'zoom_to':

        zoomToDisplayPoint(displayPoint)

    elif action == 'select_with_ray':

        extractPointsAlongClickRay(displayPoint)

    elif action == 'select_actor':
        selectActor(displayPoint)


eventFilters = {}

def segmentationViewEventFilter(obj, event):

    eventFilter = eventFilters[obj]

    if event.type() == QtCore.QEvent.MouseButtonDblClick:
        eventFilter.setEventHandlerResult(True)
        onSegmentationViewDoubleClicked(mapMousePosition(obj, event))

    else:

        for picker in viewPickers:
            if not picker.enabled:
                continue

            if event.type() == QtCore.QEvent.MouseMove:
                picker.onMouseMove(mapMousePosition(obj, event), event.modifiers())
                eventFilter.setEventHandlerResult(True)
            elif event.type() == QtCore.QEvent.MouseButtonPress:
                picker.onMousePress(mapMousePosition(obj, event), event.modifiers())
                eventFilter.setEventHandlerResult(True)


def drcViewEventFilter(obj, event):

    eventFilter = eventFilters[obj]
    if event.type() == QtCore.QEvent.MouseButtonDblClick:
        eventFilter.setEventHandlerResult(True)
        activateSegmentationMode()


def installEventFilter(view, func):

    global eventFilters
    eventFilter = PythonQt.dd.ddPythonEventFilter()

    qvtkwidget = view.vtkWidget()
    qvtkwidget.installEventFilter(eventFilter)
    eventFilters[qvtkwidget] = eventFilter

    eventFilter.addFilteredEventType(QtCore.QEvent.MouseButtonDblClick)
    eventFilter.addFilteredEventType(QtCore.QEvent.MouseMove)
    eventFilter.addFilteredEventType(QtCore.QEvent.MouseButtonPress)
    eventFilter.addFilteredEventType(QtCore.QEvent.MouseButtonRelease)
    eventFilter.connect('handleEvent(QObject*, QEvent*)', func)



def activateSegmentationMode(debug=False):

    if debug:
        polyData = getDebugRevolutionData()
    else:
        polyData = getCurrentMapServerData() or getCurrentRevolutionData()

    if not polyData:
        return

    segmentationView = getOrCreateSegmentationView()
    app.getViewManager().switchToView('Segmentation View')

    perspective()

    mapsregistrar.storeInitialTransform()

    thresholdWorkspace = False
    doRemoveGround = False

    if thresholdWorkspace:
        polyData = thresholdPoints(polyData, 'distance_along_robot_x', [0.3, 2.0])
        polyData = thresholdPoints(polyData, 'distance_along_robot_y', [-3.0, 3.0])
        polyData = thresholdPoints(polyData, 'distance_along_robot_z', [-10.0, 1.5])

    if doRemoveGround:
        groundPoints, polyData = removeGround(polyData)
        segmentationObj = updatePolyData(groundPoints, 'ground', alpha=0.3, visible=False)

    segmentationObj = updatePolyData(polyData, 'pointcloud snapshot', alpha=0.3)
    segmentationObj.headAxis = perception._multisenseItem.model.getAxis('head', [1,0,0])

    segmentationView.camera().DeepCopy(app.getDRCView().camera())
    segmentationView.render()

    _dock.show()


def init():

    installEventFilter(app.getViewManager().findView('DRC View'), drcViewEventFilter)

    getOrCreateSegmentationView()
    createDockWidget()
    #mapsregistrar.initICPCallback()

    #activateSegmentationMode(debug=True)
