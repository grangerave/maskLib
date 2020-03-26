# -*- coding: utf-8 -*-
"""
Created on Fri Aug 31 16:45:06 2018

@author: slab
"""

import maskLib.MaskLib as m
from maskLib.microwaveLib import *
from maskLib.Entities import SolidPline, SkewRect, CurveRect, InsideCurve
import numpy as np
from dxfwrite import DXFEngine as dxf
from dxfwrite import const
from dxfwrite.entities import *
from dxfwrite.vector2d import vadd

# ===============================================================================
# wafer setup
# ===============================================================================

w = m.Wafer('StructureTest01','DXF/')
#set wafer properties

w.waferDiameter = 50800 #2 inches
w.padding = 2500
w.sawWidth = 203.2 #8 mils
w.chipY = 7000 + w.sawWidth
w.chipX = 7000 + w.sawWidth
w.frame = 1   #draw frame layer?
w.solid = 1   #draw things solid?
w.multiLayer = 1  #draw in multiple layers?
if w.multiLayer:
    w.addLayer('BASEMETAL',4)
    #w.addLayer('EBEAM',3)
    w.defaultLayer = 'BASEMETAL'

#initialize the wafer
w.init()

w.thin=5      #thin section of crosshair
w.thick=20    #thick section of crosshair AND dash thickness
w.short=40    #short section of crosshair
w.long=100    #long section of crosshair
w.dash=400    #spacing between dashes
curve_pts = 30  #point resolution of all curves

#do dicing border
w.DicingBorder()

print('solid? ',w.solid)



#=============================
class FancyChip(m.Chip7mm):
    def __init__(self,wafer,chipID,layer):
        m.Chip7mm.__init__(self,wafer,chipID,layer,defaults={'w':10, 's':5, 'radius':50,'r_out':5,'r_ins':5})
        
        for s in self.structures:
            self.add(dxf.rectangle(s.start,80,20,rotation=s.direction,layer='FRAME',halign = const.RIGHT,valign = const.MIDDLE))
            
        self.add(dxf.rectangle(self.getStart(3),200,40,rotation = self.getDir(3),valign = const.MIDDLE),structure=3,length=200,angle=-90)
        self.add(dxf.rectangle(self.getStart(3),200,40,rotation = self.getDir(3),valign = const.MIDDLE),structure=3,length=200)
        
        #launcher subcomponents
        CPW_stub_open(self,1,r_out=100,r_ins=50,w=300,s=160,flipped=True)
        CPW_straight(self,1,300,w=300,s=160)
        CPW_taper(self,1,w0=300,s0=160)
        #
        CPW_straight(self,1,600)
        
        
        
        JellyfishResonator(self,self.structures[1].cloneAlongLast((300,40),newDirection=90),520,480,5565,w_cap=40,s_cap=20,maxWidth=100)
        
        
        CPW_bend(self,1,angle=45)
        CPW_straight(self,1,600)
        
        DoubleJellyfishResonator(self,self.structures[1].cloneAlongLast((100,40),newDirection=90),520,480,2565,w_cap=40,s_cap=20,maxWidth=70,ialign=const.MIDDLE)
        DoubleJellyfishResonator(self,self.structures[1].cloneAlongLast((-200,640),newDirection=90),480,200,2565,w_ind=2,w_cap=40,s_cap=20,maxWidth=60,ialign=const.MIDDLE)
        
        #clone position for new structure
        s0 = m.Structure(self,start=self.structures[1].getLastPos((300,-40)),defaults={'w':20, 's':10, 'radius':100,'r_out':5,'r_ins':5})
        
        CPW_stub_short(self,1,s=10,r_out=2.5,curve_out=False)
        self.structure(1).shiftPos(40)
        CPW_stub_short(self,1,s=10,r_out=2.5,curve_ins=False,flipped=True)
        CPW_straight(self,1,200)
        
        DoubleJellyfishResonator(self,self.structures[1].cloneAlongLast((100,40),newDirection=90),520,80,2565,w_cap=40,s_cap=20,maxWidth=70,ialign=const.MIDDLE)
        
        CPW_bend(self,1,angle=20,radius=200)
        CPW_straight(self,1,200,10,5)
        CPW_wiggles(self,1,length=3750,maxWidth=200,CCW=False)
        CPW_straight(self,1,200)
        CPW_bend(self,1,angle=55,CCW=False,radius=200)
        CPW_wiggles(self,1,length=2350,maxWidth=300,CCW=False,stop_bend=False)
        CPW_wiggles(self,1,length=1205,maxWidth=100,CCW=False,stop_bend=False,start_bend=False)
        CPW_wiggles(self,1,length=2350,maxWidth=300,CCW=False,start_bend=False,stop_bend=False)
        CPW_straight(self,1,600)
        
        #s1 = m.Structure(self,start=self.structures[1].getLastPos((300,-50)),direction=self.structures[1].direction,defaults=self.defaults)
        s1 = self.structures[1].cloneAlongLast((300,-50))
        s2 = m.Structure(self,start=self.structures[1].getLastPos((300,-100)),direction=self.structures[1].direction,defaults=self.defaults)
        s3 = m.Structure(self,start=self.structures[1].getLastPos((300,-150)),direction=self.structures[1].direction,defaults=self.defaults)
        
        CPW_wiggles(self,1,length=1200,maxWidth=200,start_bend=False,stop_bend=False)
        CPW_wiggles(self,1,length=1200,maxWidth=200,radius=10,start_bend=False,stop_bend=True)
        CPW_straight(self,1,20,s=195)
        #CPW_straight(self,1,200)
        Inductor_wiggles(self,1,length=200,Width=200,nTurns=10,radius=20,start_bend=True,stop_bend=False,pad_to_width=True)
        #CPW_stub_open(self,1,r_out=0)
        
        CPW_launcher(self,2)
        
        
        #continue independent structure
        CPW_stub_open(self,s0,flipped=True)
        CPW_straight(self,s0,200)
        CPW_taper(self,s0,50,w1=self.structures[2].defaults['w'],s1=self.structures[2].defaults['s'])
        s0.defaults['w']=self.structures[2].defaults['w']
        s0.defaults['s']=self.structures[2].defaults['s']
        CPW_directTo(self,s0,self.structures[2],radius=200)
        
        #continue independent structure 2
        
        CPW_stub_open(self,s1,flipped=True,w=20,s=10)
        CPW_straight(self,s1,100,w=20,s=10)
        CPW_taper(self,s1,w0=20,s0=10)
        CPW_straight(self,s1,400)
        
        CPW_stub_open(self,s2,flipped=True,w=20,s=10)
        CPW_straight(self,s2,100,w=20,s=10)
        CPW_taper(self,s2,w0=20,s0=10)
        
        CPW_stub_open(self,s3,flipped=True,w=20,s=10)
        CPW_straight(self,s3,100,w=20,s=10)
        CPW_taper(self,s3,w0=20,s0=10)
        #CPW_bend(self,s3,30,radius=200)
        
        CPW_launcher(self,8)
        CPW_launcher(self,5)
        CPW_launcher(self,4)
        
        CPW_directTo(self,s1,self.structures[8],radius=200)
        CPW_directTo(self,s2,self.structures[5],radius=200)
        CPW_directTo(self,s3,self.structures[4],radius=200)
        
        pline = SolidPline(self.centered((300,0)),points = [(3000,0)],color=2,bgcolor=w.bg(),rotation=30,flags=0)#1
        pline.add_vertices([(3000,600),(2800,800),(2600,1000),(0,1000),(0,0)])
        #don't need to close
        self.add(pline)
        
        pline = SolidPline(self.centered((300,-600)),points = [(300,-600)],bgcolor=w.bg(),rotation=-30,flags=0)#1
        pline.add_vertices([(300,0),(100,400),(0,-600)])
        #don't need to close
        self.add(pline)
        
        #demonstrate skewrect
        self.add(SkewRect(self.centered((-1600,-650)),100,80,(20,-30),10,bgcolor=w.bg(),valign=const.MIDDLE))
        self.add(dxf.rectangle(self.centered((-1600,-650)),100,80,color=1,valign=const.MIDDLE))
        self.add(dxf.line(self.centered((-1600 + 100,-650)),self.centered(( -1600 + 100 +20,-680)),color=2))
        
        #test alignment
        self.add(dxf.line(self.centered((-1600,-500)),self.centered((0,-500)),color=1))
        self.add(dxf.line(self.centered((-1200,-540)),self.centered((0,-540)),color=1))
        
        self.add(SkewRect(self.centered((-1200,-500)),100,80,(0,-40),20,valign=const.BOTTOM,edgeAlign=const.BOTTOM,bgcolor=w.bg()))
        self.add(SkewRect(self.centered((-1000,-500)),100,80,(0,-40),20,valign=const.TOP,edgeAlign=const.TOP,bgcolor=w.bg()))
        self.add(SkewRect(self.centered((-800,-500)),100,80,(0,-40),20,valign=const.MIDDLE,edgeAlign=const.MIDDLE,bgcolor=w.bg()))
        
        #test alignment and rotation
        self.add(dxf.line(self.centered((-1400,-800)),self.centered((0,-800)),color=1))
        self.add(dxf.line(self.centered((-1200,-840)),self.centered((0,-840)),color=1))
        
        self.add(SkewRect(self.centered((-1200,-800)),100,80,(0,-40),20,rotation=30,valign=const.BOTTOM,edgeAlign=const.BOTTOM,bgcolor=w.bg()))
        self.add(SkewRect(self.centered((-1000,-800)),100,80,(0,-40),20,rotation=30,valign=const.TOP,edgeAlign=const.TOP,bgcolor=w.bg()))
        self.add(SkewRect(self.centered((-800,-800)),100,80,(0,-40),20,rotation=30,valign=const.MIDDLE,edgeAlign=const.MIDDLE,bgcolor=w.bg()))
        
        #curverect testing
        self.add(dxf.line(self.centered((-2000,650)),self.centered((-100,650)),color=1))
        
        self.add(CurveRect(self.centered((-2400,650)),80,200,angle=140,rotation=30,bgcolor=2,valign=const.BOTTOM,hflip=True))
        
        self.add(CurveRect(self.centered((-1800,650)),30,60,angle=140,rotation=30,bgcolor=2,valign=const.BOTTOM))
        self.add(CurveRect(self.centered((-1800,650)),30,60,angle=140,rotation=30,bgcolor=3,hflip=True,valign=const.TOP))
        
        self.add(CurveRect(self.centered((-1600,650)),30,60,angle=140,rotation=30,valign=const.TOP,vflip=True))
        
        self.add(CurveRect(self.centered((-1400,650)),60,30,ralign=const.TOP,bgcolor=3))
        self.add(CurveRect(self.centered((-1400,650)),60,30,ralign=const.TOP,hflip=True,bgcolor=2))
        
        self.add(CurveRect(self.centered((-1200,650)),60,30,angle=200,valign=const.TOP,bgcolor=2))
        
        #cpw bend test
        self.add(CurveRect(self.centered((-1000,650)),30,90,angle=140,roffset=15,ralign=const.BOTTOM,rotation=30,vflip=True))
        self.add(CurveRect(self.centered((-1000,650)),30,90,angle=140,roffset=15,ralign=const.BOTTOM,rotation=30))
        self.add(CurveRect(self.centered((-1000,650)),30,90,angle=140,roffset=-15,ralign=const.TOP,valign=const.TOP,rotation=30,vflip=True))
        
        
        #inside corner test
        self.add(dxf.rectangle(self.centered((-500,0)),1000,100,valign=const.MIDDLE,halign=const.CENTER,bgcolor=w.bg()))
        self.add(dxf.rectangle(self.centered((-300,0)),800,100,valign=const.MIDDLE,halign=const.CENTER,rotation=50,bgcolor=w.bg()))
        self.add(dxf.rectangle(self.centered((-700,0)),800,100,valign=const.MIDDLE,halign=const.CENTER,rotation=90,bgcolor=w.bg()))
        
        self.add(InsideCurve(self.centered((-750,-50)),50,bgcolor=2))
        self.add(InsideCurve(self.centered((-650,-50)),50,bgcolor=2,hflip=True))
        self.add(InsideCurve(self.centered((-750,50)),50,bgcolor=2,vflip=True))
        self.add(InsideCurve(self.centered((-650,50)),50,bgcolor=2,hflip=True,vflip=True))
        
        x1 = 50/np.tan(np.radians(50))
        x2 = 50/np.sin(np.radians(50))
        self.add(InsideCurve(self.centered((-300 - x1 - x2,-50)),50,angle=50,bgcolor=2))
        self.add(InsideCurve(self.centered((-300 - x1 + x2,-50)),50,angle=130,bgcolor=2,hflip=True))
        self.add(InsideCurve(self.centered((-300 + x1 - x2,50)),50,angle=130,bgcolor=2,vflip=True))
        self.add(InsideCurve(self.centered((-300 + x1 + x2,50)),50,angle=50,bgcolor=2,hflip=True,vflip=True))
        
        
        #----------------------- test CPW launcher
        
   
        
myFancyChip = FancyChip(w,'FANCYCHIP','BASEMETAL')

print('solid? ',myFancyChip.wafer.solid)

waffle(myFancyChip, 176.3, width=80,bleedRadius=1,padx=500,layer='MARKERS')


myFancyChip.save(w)

for i in range(len(w.chips)):
    w.chips[i]=myFancyChip

# write all chips
w.populate()
w.save()