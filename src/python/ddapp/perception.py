import os
import sys
import vtk
import PythonQt
from PythonQt import QtCore, QtGui
import ddapp.objectmodel as om
from ddapp.timercallback import TimerCallback
import vtkDRCFiltersPython as drc
from vtkPointCloudUtils.debugVis import DebugData
import numpy as np


_view = None
def getRenderView():
    return _view


_debugItem = None

def updateDebugItem(polyData):
    global _debugItem
    if not _debugItem:
        _debugItem = om.PolyDataItem('spindle axis', polyData, getRenderView())
        _debugItem.setProperty('Color', QtGui.QColor(0, 255, 0))
        om.addToObjectModel(_debugItem, om.findObjectByName('sensors'))
    else:
        _debugItem.setPolyData(polyData)

    _view.render()


class MultisenseItem(om.ObjectModelItem):

    def __init__(self, model):

        om.ObjectModelItem.__init__(self, 'Multisense', om.Icons.Laser)

        self.model = model
        self.addProperty('Updates Enabled', True)
        self.addProperty('Min Range', model.reader.GetDistanceRange()[0])
        self.addProperty('Max Range', model.reader.GetDistanceRange()[1])
        self.addProperty('Edge Filter Distance', model.reader.GetEdgeDistanceThreshold())
        self.addProperty('Visible', model.visible)
        self.addProperty('Point Size', model.pointSize)
        self.addProperty('Alpha', model.alpha)

        #self.addProperty('Color', QtGui.QColor(255,255,255))
        #self.addProperty('Scanline Color', QtGui.QColor(255,0,0))

    def _onPropertyChanged(self, propertyName):
        om.ObjectModelItem._onPropertyChanged(self, propertyName)

        if propertyName == 'Updates Enabled':
            if self.getProperty('Updates Enabled'):
                self.model.start()
            else:
                self.model.stop()

        elif propertyName == 'Edge Filter Distance':
            self.model.reader.SetEdgeDistanceThreshold(self.getProperty('Edge Filter Distance'))
            self.model.showRevolution(self.model.displayedRevolution)

        elif propertyName == 'Alpha':
            self.model.setAlpha(self.getProperty(propertyName))

        elif propertyName == 'Visible':
            self.model.setVisible(self.getProperty(propertyName))

        elif propertyName == 'Point Size':
            self.model.setPointSize(self.getProperty(propertyName))

        elif propertyName in ('Min Range', 'Max Range'):
            self.model.reader.SetDistanceRange(self.getProperty('Min Range'), self.getProperty('Max Range'))
            self.model.showRevolution(self.model.displayedRevolution)

        _view.render()


    def getPropertyAttributes(self, propertyName):

        if propertyName == 'Point Size':
            return om.PropertyAttributes(decimals=0, minimum=1, maximum=20, singleStep=1, hidden=False)

        elif propertyName in ('Min Range', 'Max Range'):
            return om.PropertyAttributes(decimals=2, minimum=0.0, maximum=100.0, singleStep=0.25, hidden=False)
        elif propertyName == 'Edge Filter Distance':
            return om.PropertyAttributes(decimals=3, minimum=0.0, maximum=10.0, singleStep=0.01, hidden=False)
        else:
            return om.ObjectModelItem.getPropertyAttributes(self, propertyName)


class MultiSenseSource(TimerCallback):

    def __init__(self, view, models):
        TimerCallback.__init__(self)
        self.view = view
        self.models = models
        self.reader = None
        self.displayedRevolution = -1
        self.lastScanLine = -1
        self.numberOfActors = 1
        self.nextActorId = 0
        self.lastRobotStateUtime = 0
        self.pointSize = 1
        self.alpha = 0.5
        self.visible = True
        self._createActors()

        self.revPolyData, self.revMapper, self.revActor = self._newActor()

        self.setPointSize(self.pointSize)
        self.setAlpha(self.alpha)
        self.targetFps = 60


    def _newActor(self):
        polyData = vtk.vtkPolyData()
        mapper = vtk.vtkPolyDataMapper()
        actor = vtk.vtkActor()

        mapper.SetInputData(polyData)
        actor.SetMapper(mapper)
        self.view.renderer().AddActor(actor)
        return polyData, mapper, actor


    def _createActors(self):

        self.polyData = []
        self.mappers = []
        self.actors = []

        for i in xrange(self.numberOfActors):
            polyData, mapper, actor = self._newActor()
            self.polyData.append(polyData)
            self.mappers.append(mapper)
            self.actors.append(actor)
            actor.GetProperty().SetColor(1,0,0)

    def getScanToLocal(self):
        return None

    def showRevolution(self, revId):
        self.reader.GetDataForRevolution(revId, self.revPolyData)
        self.view.render()
        self.displayedRevolution = revId

    def setPointSize(self, pointSize):
        for actor in self.actors:
            actor.GetProperty().SetPointSize(pointSize+2)
        self.revActor.GetProperty().SetPointSize(pointSize)

    def setAlpha(self, alpha):
        self.alpha = alpha
        for actor in self.actors:
            actor.GetProperty().SetOpacity(alpha)
        self.revActor.GetProperty().SetOpacity(alpha)

    def setVisible(self, visible):
        self.visible = visible
        for actor in self.actors:
            actor.SetVisibility(visible)
        self.revActor.SetVisibility(visible)

    def start(self):
        if self.reader is None:
            self.reader = drc.vtkMultisenseSource()
            self.reader.SetDistanceRange(0.25, 4.0)
            self.reader.Start()

        TimerCallback.start(self)

    def updateRobotState(self):

        robotState = vtk.vtkDoubleArray()
        timestamp = self.reader.GetCurrentRobotState(robotState)
        if timestamp == self.lastRobotStateUtime:
            return

        self.lastRobotStateUtime = timestamp
        robotState = [robotState.GetValue(i) for i in xrange(robotState.GetNumberOfTuples())]
        for model in self.models:
            model.setEstRobotState(robotState)

        #self.updateDebugItems()


    def updateScanLines(self):

        currentScanLine = self.reader.GetCurrentScanLine() - 1
        scanLinesToUpdate = currentScanLine - self.lastScanLine

        if not scanLinesToUpdate:
            return


        #print 'current scanline:', currentScanLine
        #print 'scan lines to update:', scanLinesToUpdate
        #print 'updating actors:', self.nextActorId, (self.nextActorId + (scanLinesToUpdate-1)) % self.numberOfActors
        #print 'updating scan lines:', self.lastScanLine + 1, self.lastScanLine + 1 + (scanLinesToUpdate-1)

        for i in xrange(scanLinesToUpdate):
            polyData = self.polyData[(self.nextActorId + i) % self.numberOfActors]
            self.reader.GetDataForScanLine(self.lastScanLine + i + 1, polyData)

        self.lastScanLine = currentScanLine
        self.nextActorId = (self.nextActorId + scanLinesToUpdate) % self.numberOfActors

        self.view.render()


    def updateRevolution(self):

        currentRevolution = self.reader.GetCurrentRevolution() - 1

        if currentRevolution == self.displayedRevolution:
            return

        self.showRevolution(currentRevolution)


    def getSpindleAxis(self):

        t = vtk.vtkTransform()
        self.reader.GetTransform('SCAN', 'local', self.lastRobotStateUtime, t)

        p1 = [0.0, 0.0, 0.0]
        p2 = [2.0, 0.0, 0.0]

        p1 = np.array(t.TransformPoint(p1))
        p2 = np.array(t.TransformPoint(p2))

        axis = p2 - p1
        return axis/np.linalg.norm(axis)


    def updateDebugItems(self):

        t = vtk.vtkTransform()
        self.reader.GetTransform('SCAN', 'local', self.lastRobotStateUtime, t)

        p1 = [0.0, 0.0, 0.0]
        p2 = [2.0, 0.0, 0.0]

        p1 = t.TransformPoint(p1)
        p2 = t.TransformPoint(p2)

        d = DebugData()
        d.addSphere(p1, radius=0.01, color=[0,1,0])
        d.addLine(p1, p2, color=[0,1,0])
        updateDebugItem(d.getPolyData())


    def tick(self):

        self.updateRobotState()
        self.updateRevolution()
        self.updateScanLines()



def init(view, models):
    global _multisenseItem
    global _view

    _view = view

    m = MultiSenseSource(view, models)
    m.start()

    sensorsFolder = om.addContainer('sensors')

    _multisenseItem = MultisenseItem(m)
    om.addToObjectModel(_multisenseItem, sensorsFolder)
    return _multisenseItem

