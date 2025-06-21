import torch
import numpy as np
from numpy import interp as interp
import itertools  
import random
import sys
import copy
from direct.showbase.ShowBase import ShowBase

from direct.showbase.DirectObject import DirectObject
from direct.showbase.InputStateGlobal import inputState
from panda3d.core import LVecBase3
from panda3d.core import AmbientLight
from panda3d.core import DirectionalLight
from panda3d.core import Vec3
from panda3d.core import Vec4
from panda3d.core import Point3
from panda3d.core import TransformState
from panda3d.core import BitMask32
from panda3d.core import Filename
from panda3d.core import PNMImage
from panda3d.core import GeoMipTerrain
from panda3d.core import getModelPath
from panda3d.core import WindowProperties
from panda3d.core import GraphicsOutput
from panda3d.core import Texture
from panda3d.core import Camera
from panda3d.core import PerspectiveLens
from panda3d.core import Material
from direct.gui.DirectGui import *
#import gltf
# from panda3d.core import PandaNode

from panda3d.core import FrameBufferProperties
from panda3d.core import GraphicsBuffer
from panda3d.core import GraphicsPipe
from panda3d.bullet import BulletGhostNode
from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletPlaneShape
from panda3d.bullet import BulletBoxShape
from panda3d.bullet import BulletCapsuleShape
from panda3d.bullet import BulletSphereShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletDebugNode
from panda3d.bullet import BulletHeightfieldShape
from panda3d.bullet import ZUp
from panda3d.bullet import BulletCharacterControllerNode
from panda3d.core import GraphicsEngine


import lab_vanilla

import time
from time import perf_counter



base = ShowBase()



class Yer(DirectObject):

    def __init__(self):

        #gltf loader instead of native loader (must be installed first)
        #gltf.patch_loader(base.loader)
        # create a rendering window
        
        wp = WindowProperties()
        wp.setSize(1500, 1500)
        # somehow this is IMPORTANT (requestProperties)
        base.win.requestProperties(wp)
        base.setBackgroundColor(0.1, 0.1, 0.8, 1)
        base.setFrameRateMeter(True)
        base.cam.setPos(0, -80, 50)
        base.cam.lookAt(0, 0, 0)
        base.disableMouse()
        base.useTrackball()

        # Light      ####################################################################################

        alight = AmbientLight('ambientLight')
        alight.setColor(Vec4(0.5, 0.5, 0.5, 1))
        alightNP = render.attachNewNode(alight)
        dlight = DirectionalLight('directionalLight')
        dlight.setDirection(Vec3(1, 1, -1))
        dlight.setColor(Vec4(0.8, 0.8, 0.8, 1))
        dlightNP = render.attachNewNode(dlight)

        render.clearLight()
        render.setLight(alightNP)
        render.setLight(dlightNP)
        render.setShaderAuto()

        self.landscape()
        taskMgr.add(self.update, 'updateWorld')
        self.accept('f3', self.toggleDebug)

    def update(self, task):        
        """ updates every frame """
        dt = globalClock.getDt()
        self.world.doPhysics(dt)
        agent.heart()
        return task.cont

    def toggleDebug(self):
        if self.debugNP.isHidden():
            self.debugNP.show()
        else:
            self.debugNP.hide()


    def landscape(self):
        ## Bullet World #################################################################################
        self.worldNP = render.attachNewNode('World')

        self.debugNP = self.worldNP.attachNewNode(BulletDebugNode('Debug'))
        self.debugNP.show()
        self.debugNP.node().showNormals(True)

        self.world = BulletWorld()
        self.world.setDebugNode(self.debugNP.node())
        self.world.setGravity(Vec3(0, 0, -9.81))

        # Heightfield Surface ##########################################################################
        height = 6.0
        img = PNMImage()
        # couldn't read the files at fist and asked help from the forum. That's why it looks weird.
        assert img.read(getModelPath().findFile(
            'models/elevation3.png')), "Failed to read!"
        shape = BulletHeightfieldShape(img, height, ZUp)
        shape.setUseDiamondSubdivision(True)
        np = self.worldNP.attachNewNode(BulletRigidBodyNode('Heightfield'))
        np.node().addShape(shape)
        np.setPos(0, 0, 0)
        np.set_scale(2)
        np.node().setFriction(.5)
        np.setCollideMask(BitMask32.bit(2))
        self.world.attach(np.node())
        self.hf = np.node()  # To enable/disable debug visualisation
        self.terrain = GeoMipTerrain('terrain')
        self.terrain.setHeightfield(img)
        self.terrain.setBlockSize(32)

        rootNP = self.terrain.getRoot()
        rootNP.reparentTo(render)
        rootNP.setSz(height * 2)
        rootNP.setSx(2)
        rootNP.setSy(2)
        offset = img.getXSize() / 2.0 - 0.5
        rootNP.setPos(-offset * 2, -offset * 2, -height)
        self.terrain.generate()

# bu degisiklik yapilacak

class Lillies(Yer):

    def __init__(self, agent_name,brain):
        # not used can be deleted
        self.name=agent_name
        self.hearttime = 0
        # bullet notePath 'z' value
        self.my_z = 0
        # self.lilly_11=lilly_11
        # self.brain = small_net
        self.brain = brain
        #print(self.brain.model)
        # print(self.lilly_11[0].values)
        self.x_Force = 0
        self.y_Force = 0
        self.z_Force = 0
        self.z_Torque = 0

        fb_prop = FrameBufferProperties()
        # Request 8 RGB bits, no alpha bits, and a depth buffer.
        fb_prop.setRgbColor(True)
        # fb_prop.setSrgbColor(True)**** Dosn't work with this in this file???? ************
        fb_prop.setRgbaBits(8, 8, 8, 0)
        fb_prop.setDepthBits(16)
        # Create a WindowProperties object set to 256x256 size.
        win_prop = WindowProperties.size(20, 20)
        flags = GraphicsPipe.BF_refuse_window
        # flags = GraphicsPipe.BF_require_window

        lens = PerspectiveLens()
        self.my_buff = base.graphicsEngine.make_output(
            base.pipe,agent_name +"_buffer", -100, fb_prop, win_prop, flags, base.win.getGsg(), base.win)
        my_cam = base.makeCamera(self.my_buff, sort=6, displayRegion=(
            0.0, 1, 0, 1), camName= agent_name +"_cam")
        my_cam.setHpr(0, 0, 0)
        my_cam.setPos(0, 0, 1)
        my_cam.node().setLens(lens)
        lens.setFov(100)

        # make body of the agent

        agent_name, body_node_path, body_node = Lillies.make_body(agent_name)
        self.my_path = body_node_path
        self.body_node = body_node
        my_cam.reparentTo(body_node_path)
        body_node_path.setPos(np.random.randint(-60, 60),
                              np.random.randint(-60, 60), np.random.randint(2, 5))      
        yer.world.attach(body_node)

        # removing except statement from  heart() and adding "renderFrame" may lead better performance TRY IT
        base.graphicsEngine.renderFrame()

    def heart(self):

        # now = perf_counter()
        self.my_z = self.my_path.getZ()
        my_output = self.my_buff.getActiveDisplayRegion(0).getScreenshot()
            # for feeding neural net
        numpy_image_data = np.array(my_output.getRamImageAs("RGB"), np.float32)
        
        # print('heartbeat')
        # I removed this try/except part because it slows down all process (pyhon try/except is very slow)
        # instead I add renderFrame to _init_ to solve the error (if you try to get screenShot before creating cam)
        
        # try:
        #     my_output = self.my_buff.getActiveDisplayRegion(
        #         0).getScreenshot()
        #     # for feeding neural net
        #     numpy_image_data = np.array(
        #         my_output.getRamImageAs("RGB"), np.float32)
        # except:
        #     base.graphicsEngine.renderFrame()
        #     print("except")
        #     my_output = self.my_buff.getActiveDisplayRegion(
        #         0).getScreenshot()
        #     numpy_image_data = np.array(
        #         my_output.getRamImageAs("RGB"), np.float32)
        # # output neural net

        prediction = lab_vanilla.predict(numpy_image_data,self.brain)

        x_Force = prediction[0][0][0][0]
        y_Force = prediction[0][0][0][1]
        z_Force = 0 #prediction[0][2]
        z_Torque = prediction[0][0][0][2]

        force = Vec3(x_Force, y_Force, z_Force)*6*8
        torque = Vec3(0, 0, z_Torque)*2

        force = yer.worldNP.getRelativeVector(self.my_path, force)
        torque = yer.worldNP.getRelativeVector(self.my_path, torque)
        self.body_node.setActive(True)
        self.body_node.applyCentralForce(force)
        self.body_node.applyTorque(torque)

    def make_body(agent_name):
        """creates agents for the world"""
        shape = BulletCapsuleShape(.35, 1, ZUp)
        shape2 = BulletCapsuleShape(.35, 1, ZUp)
        head = BulletSphereShape(.3)
        # nodepath---------------------------
        body_node_path = yer.worldNP.attachNewNode(
            BulletRigidBodyNode(agent_name))
        # print(body_node_path)
        body_node_path.setPos(0, 0, 5)
        # body_node_path.set_scale(3)
        body_node_path.setCollideMask(BitMask32.allOn())
        # node-------------------------------
        body_node = body_node_path.node()
        body_node.setMass(5)
        body_node.addShape(shape, TransformState.makePosHpr(
            Point3(-.35, 0, 0), Point3(90, 0, 90)))
        body_node.addShape(shape2, TransformState.makePosHpr(
            Point3(.35, 0, 0), Point3(90, 0, 90)))
        body_node.addShape(head, TransformState.makePos(Point3(0, .5, 1)))
        body_node.setFriction(0.5)
        # visual representation--------------
        visualNP = loader.loadModel('models/lilly.gltf')
        
        #visualNP = gltf.load_model('models/lilly.gltf')
        visualNP.set_scale(.5)
        visualNP.setPos(0, 0, 0)
        visualNP.setHpr(180, 270, 0)
        materials = visualNP.findAllMaterials()
        materials[0].clearBaseColor()

        # BU NE?
        visualNP.clearModelNodes()
        # BU NE?
        visualNP.reparentTo(body_node_path)
        return agent_name, body_node_path, body_node








    

yer = Yer()
agent = Lillies("me",lab_vanilla.model)           
base.run()
