
import torch

import numpy as np

import sys
from direct.showbase.ShowBase import ShowBase

from direct.showbase.DirectObject import DirectObject
from direct.showbase.InputStateGlobal import inputState

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
import gltf
# from panda3d.core import PandaNode

from panda3d.core import FrameBufferProperties
from panda3d.core import GraphicsBuffer
from panda3d.core import GraphicsPipe

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
import lilly_torch
import time






base=ShowBase()
class Yer(DirectObject):
    def __init__(self):
        gltf.patch_loader(base.loader)
        # create a rendering window
        wp=WindowProperties()
        wp.setSize(1000,1000)
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
        #render.setShaderAuto()


        self.setup() 
        taskMgr.add(self.update, 'updateWorld')
        self.accept('f5', self.doScreenshot)
        self.accept('f3', self.toggleDebug)

        inputState.watchWithModifiers('forward', 'w')
        inputState.watchWithModifiers('left', 'a')
        inputState.watchWithModifiers('reverse', 's')
        inputState.watchWithModifiers('right', 'd')
        inputState.watchWithModifiers('turnLeft', 'q')
        inputState.watchWithModifiers('turnRight', 'e')

        

     
     
    def toggleDebug(self):
        if self.debugNP.isHidden():
            self.debugNP.show()
        else:
            self.debugNP.hide()


    def setup(self):
        
        ## Bullet World #################################################################################
        self.worldNP = render.attachNewNode('World')
        self.debugNP = self.worldNP.attachNewNode(BulletDebugNode('Debug'))
        self.debugNP.show()
        self.debugNP.node().showNormals(True)

        self.world = BulletWorld()        
        self.world.setGravity(Vec3(0, 0, -9.81))        
        self.world.setDebugNode(self.debugNP.node())

        
        # Heightfield (static) ##########################################################################
        height = 6.0
        img = PNMImage()
        # couldn't read the files at fist and asked help from the forum. That's why it looks weird.
        assert img.read(getModelPath().findFile('models/elevation2.png')), "Failed to read!"
        shape = BulletHeightfieldShape(img, height, ZUp)
        shape.setUseDiamondSubdivision(True)
        np = self.worldNP.attachNewNode(BulletRigidBodyNode('Heightfield'))
        np.node().addShape(shape)
        np.setPos(0, 0, 0)        
        np.set_scale(2)
        np.node().setFriction(.5)
        np.setCollideMask(BitMask32.allOn())
        self.world.attachRigidBody(np.node())
        self.hf = np.node() # To enable/disable debug visualisation
        self.terrain = GeoMipTerrain('terrain')
        self.terrain.setHeightfield(img)    
        self.terrain.setBlockSize(32)
        #I don't want any optimization that's why I commented that
        #self.terrain.setNear(50)
        #self.terrain.setFar(100)
        #self.terrain.setFocalPoint(base.camera)    
        rootNP = self.terrain.getRoot()
        rootNP.reparentTo(render)
        rootNP.setSz(height*2)
        rootNP.setSx(2)
        rootNP.setSy(2)
        offset = img.getXSize() / 2.0 - 0.5
        rootNP.setPos(-offset*2, -offset*2, -height )    
        self.terrain.generate()

        
        num_agents=1

        # Box (dynamic) ################################################################################# 
        for r in range(num_agents):

            shape = BulletBoxShape(Vec3(0.5, 0.5, 0.5))
            np = self.worldNP.attachNewNode(BulletRigidBodyNode('Box'))            
            np.node().setMass(5)
            np.node().addShape(shape)
            np.setPos(5, 5, 2)
            np.set_scale(1)
            np.setCollideMask(BitMask32.allOn())
            self.world.attachRigidBody(np.node())
            #Friction for the Box
            np.node().setFriction(0.5)
            self.boxNP = np # For applying force & torque
            
            visualNP = loader.loadModel('models/lilly.gltf')
            visualNP.set_scale(.5)
            mats=visualNP.findAllMaterials()
            mats[0].clearBaseColor()
            
            visualNP.clearModelNodes()
            visualNP.reparentTo(self.boxNP)

            

         
        # Buffers and Cameras ###########################################################################
        fb_prop = FrameBufferProperties()
        # Request 8 RGB bits, no alpha bits, and a depth buffer.
        fb_prop.setRgbColor(True)
        fb_prop.setRgbaBits(8, 8, 8, 0)
        fb_prop.setDepthBits(16)
        # Create a WindowProperties object set to 256x256 size.
        win_prop = WindowProperties.size(240, 240)
        flags = GraphicsPipe.BF_refuse_window
        self.buffs=[]
        self.cams=[]
        for buf in range(0,num_agents):
            self.buffs.append(base.graphicsEngine.make_output(base.pipe,"My Buffer"+str(buf+1), -100, fb_prop, win_prop, flags, base.win.getGsg(), base.win))
            self.cams.append(base.makeCamera(self.buffs[buf],sort=0,displayRegion=(0.0, 1, 0, 1),camName="cam"+str(buf+1)))
            self.cams[buf].reparentTo(self.worldNP.findAllMatches("Box")[buf])





    def doScreenshot(self):
        base.screenshot('Bullet')
        # nice
        t=0
        for buf in self.buffs:
            buf.getActiveDisplayRegion(0).saveScreenshotDefault('MYBUFFER'+str(t))
            t+=1
            #my_output=buf.getActiveDisplayRegion(0).getScreenshot()        
            #numpy_image_data=np.array(my_output.getRamImageAs("RGB"), np.float32)
            #print(numpy_image_data)
            #predict_that=lilly_torch.VGG16_predict("MYBUFFER.jpg")
            #print(predict_that)   
    
    def processInput(self, dt):
        force = Vec3(0, 0, 0)
        torque = Vec3(0, 0, 0)
        
        

        if inputState.isSet('forward'): force.setY( 1.0)
        if inputState.isSet('reverse'): force.setY(-1.0)
        if inputState.isSet('left'):    force.setX(-1.0)
        if inputState.isSet('right'):   force.setX( 1.0)
        if inputState.isSet('turnLeft'):  torque.setZ( 1.0)
        if inputState.isSet('turnRight'): torque.setZ(-1.0)

        force *= 100.0
        
        torque *= 20.0
        for liste in self.worldNP.findAllMatches("Box"):
            force = render.getRelativeVector(liste, force)
            liste.node().setActive(True)
            liste.node().applyCentralForce(force)
            liste.node().applyTorque(torque)
            
        
        



    def update(self, task):
        dt = globalClock.getDt()
        self.processInput(dt)
        self.world.doPhysics(dt) 
        simdi=time.time()


        if len(diriler)==0:
            diri=Diri()
            diriler.append(diri) 
        if len(diriler)<40:            
            if simdi-diriler[-1].start>0.20:
                diri=Diri()
                diriler.append(diri)

        for i in diriler:            
            i.shot()   

        return task.cont

yer = Yer()

class Diri(Yer):
    def __init__(self):

        
        
        # Lilly Brain
        self.lilly_torch=lilly_torch
        self.start=time.time()
        self.yy=0
        self.yy2=0
        fb_prop = FrameBufferProperties()
        # Request 8 RGB bits, no alpha bits, and a depth buffer.
        # fb_prop.setRgbColor(True)
        fb_prop.setSrgbColor(True)
        fb_prop.setRgbaBits(8, 8, 8, 0)
        fb_prop.setDepthBits(16)
        # Create a WindowProperties object set to 256x256 size.
        win_prop = WindowProperties.size(240, 240)
        flags = GraphicsPipe.BF_refuse_window
        
        

        shape = BulletCapsuleShape(.35, 1, ZUp)
        shape2 = BulletCapsuleShape(.35, 1, ZUp)
        head = BulletSphereShape(.3)
        # shape = BulletBoxShape(Vec3(0.5, 0.5, 0.5))
        nopa = yer.worldNP.attachNewNode(BulletRigidBodyNode('Box_'))
        
        self.box_NP = nopa 
        
        self.box_NP.node().setMass(3)
        self.box_NP.node().addShape(shape,TransformState.makePosHpr(Point3(-.35, 0, 0),Point3(90, 0, 90)))
        self.box_NP.node().addShape(shape2,TransformState.makePosHpr(Point3(.35, 0, 0),Point3(90,0, 90)))
        self.box_NP.node().addShape(head,TransformState.makePos(Point3(0, .5, 1)))

        self.box_NP.setPos(np.random.randint(-30,30), np.random.randint(-30,30),np.random.randint(2,7))
        
        self.box_NP.set_scale(1)

        self.box_NP.setCollideMask(BitMask32.allOn())
        yer.world.attachRigidBody(self.box_NP.node())
        #Friction for the Box
        self.box_NP.node().setFriction(0.5)
        

        lens = PerspectiveLens()
        # visualNP = loader.loadModel('models/mox.egg')
        visualNP = loader.loadModel('models/lilly.bam')
        visualNP.set_scale(.5)
        visualNP.setPos(0,0,-.5)
        visualNP.setHpr(180,0,0)

        mats=visualNP.findAllMaterials()
        mats[0].clearBaseColor()

        visualNP.reparentTo(self.box_NP)
        self.buffer=base.graphicsEngine.make_output(base.pipe,"diri Buffer", -100, fb_prop, win_prop, flags, base.win.getGsg(), base.win)
        self.cam=base.makeCamera(self.buffer,sort=6,displayRegion=(0.0, 1, 0, 1),camName="diri_cam")
        self.cam.setHpr(0,0,0)
        self.cam.setPos(0,0,1)
        self.cam.node().setLens(lens)
        lens.setFov(100)
        #self.setFov(100)
        self.cam.reparentTo(self.box_NP)

        


       
       # taskMgr.add(self.engine, 'updateAgent')
        

        
    # def engine(self, task):
    #     dt = globalClock.getDt()
    #     # self.shot()       
             
    #     return task.cont

    def shot(self):
        
        simdi=time.time()        
        self.fark=simdi-self.start
        # for i in diriler:
        #     if i==self:
        #         print(self.shot)
        #         print(time.time())    
            
        
            

        if self.fark>.6:

            self.start=time.time()
            try:
                my_output=self.buffer.getActiveDisplayRegion(0).getScreenshot()        
                numpy_image_data=np.array(my_output.getRamImageAs("RGB"), np.float32)
            except:
                base.graphicsEngine.renderFrame()
                print("except")
                my_output=self.buffer.getActiveDisplayRegion(0).getScreenshot()        
                numpy_image_data=np.array(my_output.getRamImageAs("RGB"), np.float32) 
            prediction=self.lilly_torch.VGG16_predict(numpy_image_data)           
            self.yy=prediction[0][0]
            self.yy2=prediction[0][1]
        
        force_=Vec3(0,self.yy,0)*5
        force=Vec3(0,self.yy2,0)*5
        
        
        if self.box_NP.node().isActive()==False:
            self.box_NP.node().setActive(True)

        #print(self.box_NP.node().isActive())
        #self.box_NP.node().setActive(True)
        self.box_NP.node().applyForce(render.getRelativeVector(self.box_NP, force_),Vec3(-.35, -.5, .3))
        self.box_NP.node().applyForce(render.getRelativeVector(self.box_NP, force),Vec3(0, -.5, .3))
        
        
    

    


 

diriler=[]


    


print(yer.worldNP.getChildren())
print(yer.boxNP.getChildren())
print("render ALL Children")
print(render.getChildren())
print(base.camList)
print(yer.worldNP.findAllMatches("*"))


    
base.run()           