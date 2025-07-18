# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 13:02:59 2020

@author: sasha

Library for drawing standard junctions and other relevant components (contact tabs, etc)
"""

import maskLib.MaskLib as m
from dxfwrite import DXFEngine as dxf
from dxfwrite import const

from dxfwrite.vector2d import vadd
from dxfwrite.algebra import rotate_2d

from maskLib.Entities import SolidPline, CurveRect, RoundRect, InsideCurve, MiterJoint
from maskLib.microwaveLib import Strip_straight, Strip_taper, Strip_pad, Strip_stub_round, Strip_stub_open, CPW_taper, CPW_straight, CPW_stub_round

from maskLib.utilities import curveAB, kwargStrip

import math

# ===============================================================================
# global functions to setup global variables in an arbitrary wafer object
# these can 
# ===============================================================================

def setupJunctionLayers(wafer,JLAYER='JUNCTION',jcolor=1,ULAYER='UNDERCUT',ucolor=2,bandaid=False,BLAYER='BANDAID',bcolor=3):
    #add correct layers to wafer, and cache layer
    wafer.addLayer(JLAYER,jcolor)
    wafer.JLAYER=JLAYER
    wafer.addLayer(ULAYER,ucolor)
    wafer.ULAYER=ULAYER
    if bandaid:
        wafer.addLayer(BLAYER,bcolor)
        wafer.BLAYER=BLAYER

def setupJunctionAngles(wafer,JANGLES=[0,90]):
    '''
    Angles are defined as the angle in degrees *from which the evaporation is coming*.
    For example, if the first evaporation comes from the East, and the second from the north,
    the angles would be [0,90]. Add more angles to the list as needed.
    '''
    wafer.JANGLES = [angle % 360 for angle in JANGLES]
    
def setupManhattanJAngles(wafer,JANGLE1=0,flip=False):
    '''
    Sets up angles specifically for manhattan junction (Angle 2 is 90 deg CW or CCW from angle 1)
    '''
    JANGLE2 = JANGLE1 + 90
    if flip:
        JANGLE2 = JANGLE1 - 90
    setupJunctionAngles(wafer,[JANGLE1 % 360,JANGLE2 % 360])

# ===============================================================================
# contact pad functions (for ground plane)
# ===============================================================================
                                #stemw=3,steml=0.5,tabw=2,tabl=0.5,taboffs=-0.5,r_out=1.5,r_ins=1.5
def JcalcTabDims(chip,structure,gapw=3,gapl=0.5,tabw=2,tabl=0.5,taboffs=-0.5,r_out=1.5,r_ins=1.5,absoluteDimensions=False,stemw=None,steml=None,**kwargs):
    if stemw is not None:
        gapw = stemw
    if steml is not None:
        gapl = steml
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,start=structure,direction=0)
        else:
            return chip.structure(structure)
    if r_out is None:
        try:
            r_out = struct().defaults['r_out']
        except KeyError:
            #print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            r_out = 0
    if r_ins is None:
        try:
            r_ins = struct().defaults['r_ins']
        except KeyError:
            #print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            r_ins = 0
    #determine stem and tab lengths
    if absoluteDimensions:
        if gapl >= 2*r_out:
            gapl = gapl-2*r_out
        if tabl >= 2*r_ins:
            tabl = tabl-2*r_ins
            
    #returns length, half width
    return 2*r_out+gapl+taboffs+2*r_ins+tabl,(gapw/2+r_out+tabw+r_ins)
    
                                                                    #stemw=3,steml=0.5,tabw=2,tabl=0.5,taboffs=-0.5,r_out=1.5,r_ins=1.5
def JContact_slot(chip,structure,rotation=0,absoluteDimensions=False,gapw=3,gapl=0.5,tabw=2,tabl=0.5,taboffs=-0.5,r_out=1.5,r_ins=1.5,hflip=False,bgcolor=None,debug=False,**kwargs):
    '''
    Creates shapes forming a negative space puzzle piece slot (tab) with rounded corners, and adjustable angles. 
    No overlap : XOR mode compatible
    Centered on outside midpoint of gap
    
    gap: {width (gapw),height (gapl),r_out}
    tab: {slot width, (tabw),height (tabl), height offset (taboffs),r_ins}
    
    by default, absolute dimensions are off, so gap / tab lengths are determined by radii. gapl and tabl will then determine extra space between rounded corners.
    if absolute dimensions are on, then tab / gap lengths are determined only by gapl and tabl.
    
    set r_ins or r_out to None to inherit defaults from chip/structure
    '''
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,start=structure,direction=rotation)
        else:
            return chip.structure(structure)
    if r_out is None:
        try:
            r_out = struct().defaults['r_out']
        except KeyError:
            #print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            r_out = 0
    if r_ins is None:
        try:
            r_ins = struct().defaults['r_ins']
        except KeyError:
            #print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            r_ins = 0
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    
    tot_length,half_width = JcalcTabDims(chip,structure,gapw,gapl,tabw,tabl,taboffs,r_out,r_ins,absoluteDimensions)
    #determine stem and tab lengths
    if absoluteDimensions:
        if gapl >= 2*r_out:
            gapl = gapl-2*r_out
        else:
            print('\x1b[33mWarning:\x1b[0m gap too short in ',chip.chipID,'!')
        if tabl >= 2*r_ins:
            tabl = tabl-2*r_ins
        else:
            print('\x1b[33mWarning:\x1b[0m tab too short in ',chip.chipID,'!')
    
    if hflip:
        struct().shiftPos(tot_length,angle=180)
    
    if taboffs==0:
        theta=90
    else:
        theta = math.degrees(math.atan2(
            (r_ins + r_out)*(taboffs + r_ins + r_out)+ abs(tabw)*math.sqrt(max(tabw**2 + taboffs*(taboffs + 2*(r_ins + r_out)),0)),
            tabw*(-r_ins - r_out)+(taboffs + r_ins + r_out)*math.sqrt(max(tabw**2 + taboffs*(taboffs + 2*(r_ins + r_out)),0))*abs(tabw)/tabw))
    inside_ptx = tot_length-tabl-r_ins*(1+math.sin(math.radians(theta))- (1- math.cos(math.radians(theta)))/math.tan(math.radians(theta)))
    
    chip.add(SolidPline(struct().getPos(),rotation=struct().direction,points=[(gapl+r_out,gapw/2+r_out),
                                                                              (gapl+r_out*(1+math.sin(math.radians(theta))),gapw/2+r_out*(1-math.cos(math.radians(theta)))),
                                                                              (inside_ptx,half_width),(0,half_width),(0,gapw/2+r_out)],bgcolor=bgcolor,**kwargs))
    chip.add(SolidPline(struct().getPos(),rotation=struct().direction,points=[(gapl+r_out,-gapw/2-r_out),
                                                                              (gapl+r_out*(1+math.sin(math.radians(theta))),-gapw/2-r_out*(1-math.cos(math.radians(theta)))),
                                                                              (inside_ptx,-half_width),(0,-half_width),(0,-gapw/2-r_out)],bgcolor=bgcolor,**kwargs))
    
    if r_out>0:
        if debug:
            chip.add(dxf.circle(r_out,struct().getPos((r_out+gapl,gapw/2+r_out)),layer='FRAME',**kwargs))
            chip.add(dxf.circle(r_out,struct().getPos((r_out+gapl,-gapw/2-r_out)),layer='FRAME',**kwargs))
        chip.add(CurveRect(struct().getPos((r_out,gapw/2+r_out)), r_out, r_out,ralign=const.TOP,hflip=True,vflip=True,rotation=struct().direction,bgcolor=bgcolor, **kwargs))
        chip.add(CurveRect(struct().getPos((r_out,-gapw/2-r_out)), r_out, r_out,ralign=const.TOP,hflip=True,rotation=struct().direction,bgcolor=bgcolor, **kwargs))
        if gapl > 0:
            chip.add(dxf.rectangle(struct().getPos((r_out,gapw/2)),gapl,r_out,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
            chip.add(dxf.rectangle(struct().getPos((r_out,-gapw/2)),gapl,-r_out,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
        chip.add(CurveRect(struct().getPos((r_out+gapl,gapw/2+r_out)), r_out, r_out,ralign=const.TOP,angle=theta,vflip=True,rotation=struct().direction,bgcolor=bgcolor, **kwargs))
        chip.add(CurveRect(struct().getPos((r_out+gapl,-gapw/2-r_out)), r_out, r_out,ralign=const.TOP,angle=theta,rotation=struct().direction,bgcolor=bgcolor, **kwargs))
    
    if r_ins>0:
        if debug:
            chip.add(dxf.circle(r_ins,struct().getPos((tot_length-r_ins-tabl,half_width-r_ins)),layer='FRAME',**kwargs))
            chip.add(dxf.circle(r_ins,struct().getPos((tot_length-r_ins-tabl,-half_width+r_ins)),layer='FRAME',**kwargs))
        chip.add(InsideCurve(struct().getPos((tot_length,half_width)), r_ins, rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        chip.add(InsideCurve(struct().getPos((tot_length,-half_width)), r_ins, vflip=True,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        
        chip.add(InsideCurve(struct().getPos((inside_ptx,half_width)), r_ins,angle=180-theta,hflip=True, rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        chip.add(InsideCurve(struct().getPos((inside_ptx,-half_width)), r_ins,angle=180-theta,hflip=True, vflip=True,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
    
    if hflip:
        struct().shiftPos(0,angle=180)
    else:
        struct().shiftPos(tot_length)
    
    
def JContact_tab(chip,structure,rotation=0,absoluteDimensions=False,stemw=3,steml=0.5,tabw=2,tabl=0.5,taboffs=-0.5,r_out=1.5,r_ins=1.5,hflip=False,bgcolor=None,debug=False,**kwargs):
    '''
    Creates shapes forming a puzzle piece tab with rounded corners, and adjustable angles. 
    No overlap : XOR mode compatible
    Centered on bottom midpoint of stem
    
    stem: {width (stemw),height (steml),r_out}
    tab: {slot width, (tabw),height (tabl), height offset (taboffs),r_ins}
    
    by default, absolute dimensions are off, so stem / tab lengths are determined by radii. steml and tabl will then determine extra space between rounded corners.
    if absolute dimensions are on, then tab / stem lengths are determined only by steml and tabl.
    
    set r_ins or r_out to None to inherit defaults from chip/structure
    '''
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,start=structure,direction=rotation)
        else:
            return chip.structure(structure)
    if r_out is None:
        try:
            r_out = struct().defaults['r_out']
        except KeyError:
            #print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            r_out = 0
    if r_ins is None:
        try:
            r_ins = struct().defaults['r_ins']
        except KeyError:
            #print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            r_ins = 0
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    
    tot_length,half_width = JcalcTabDims(chip,structure,stemw,steml,tabw,tabl,taboffs,r_out,r_ins,absoluteDimensions)
    #determine stem and tab lengths
    if absoluteDimensions:
        if steml >= 2*r_ins:
            steml = steml-2*r_ins
        else:
            print('\x1b[33mWarning:\x1b[0m stem too short in ',chip.chipID,'!')
        if tabl >= 2*r_out:
            tabl = tabl-2*r_out
        else:
            print('\x1b[33mWarning:\x1b[0m tab too short in ',chip.chipID,'!')
    
    if hflip:
        struct().shiftPos(tot_length,angle=180)
    
    if taboffs==0:
        theta=90
    else:
        theta = math.degrees(math.atan2(
            (r_out + r_ins)*(taboffs + r_out + r_ins)+ abs(tabw)*math.sqrt(tabw**2 + taboffs*(taboffs + 2*(r_out + r_ins))),
            tabw*(-r_out - r_ins)+(taboffs + r_out + r_ins)*math.sqrt(tabw**2 + taboffs*(taboffs + 2*(r_out + r_ins)))*abs(tabw)/tabw))
    inside_ptx = r_ins + steml + r_ins*(math.sin(math.radians(theta))- (1- math.cos(math.radians(theta)))/math.tan(math.radians(theta)))
    
    chip.add(SolidPline(struct().getPos(),rotation=struct().direction,points=[(tot_length-tabl-r_out,half_width-r_out),
                                                                              (tot_length-tabl-r_out*(1+math.sin(math.radians(theta))),half_width-r_out*(1-math.cos(math.radians(theta)))),
                                                                              (inside_ptx,stemw/2),(tot_length,stemw/2),(tot_length,half_width-r_out)],bgcolor=bgcolor,**kwargs))
    chip.add(SolidPline(struct().getPos(),rotation=struct().direction,points=[(tot_length-tabl-r_out,-half_width+r_out),
                                                                              (tot_length-tabl-r_out*(1+math.sin(math.radians(theta))),-half_width+r_out*(1-math.cos(math.radians(theta)))),
                                                                              (inside_ptx,-stemw/2),(tot_length,-stemw/2),(tot_length,-half_width+r_out)],bgcolor=bgcolor,**kwargs))
    
    chip.add(dxf.rectangle(struct().getPos(),tot_length,stemw,valign=const.MIDDLE,bgcolor=bgcolor,rotation=struct().direction,**kwargStrip(kwargs)))
    
    if r_out>0:
        if debug:
            chip.add(dxf.circle(r_out,struct().getPos((tot_length-r_out-tabl,half_width-r_out)),layer='FRAME',**kwargs))
            chip.add(dxf.circle(r_out,struct().getPos((tot_length-r_out-tabl,-half_width+r_out)),layer='FRAME',**kwargs))
            
        chip.add(CurveRect(struct().getPos((tot_length-r_out,half_width-r_out)), r_out, r_out,ralign=const.TOP,rotation=struct().direction,bgcolor=bgcolor, **kwargs))
        chip.add(CurveRect(struct().getPos((tot_length-r_out,-half_width+r_out)), r_out, r_out,ralign=const.TOP,vflip=True,rotation=struct().direction,bgcolor=bgcolor, **kwargs))
        if tabl > 0:
            chip.add(dxf.rectangle(struct().getPos((tot_length-r_out,half_width-r_out)),-tabl,r_out,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
            chip.add(dxf.rectangle(struct().getPos((tot_length-r_out,-half_width+r_out)),-tabl,-r_out,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
        chip.add(CurveRect(struct().getPos((2*r_ins + steml + taboffs + r_out,half_width-r_out)), r_out, r_out,ralign=const.TOP,angle=theta,hflip=True,rotation=struct().direction,bgcolor=bgcolor, **kwargs))
        chip.add(CurveRect(struct().getPos((2*r_ins + steml + taboffs + r_out,-half_width+r_out)), r_out, r_out,ralign=const.TOP,angle=theta,hflip=True,vflip=True,rotation=struct().direction,bgcolor=bgcolor, **kwargs))
        
        
    if r_ins>0:
        if debug:
            chip.add(dxf.circle(r_ins,struct().getPos((r_ins+steml,stemw/2+r_ins)),layer='FRAME',**kwargs))
            chip.add(dxf.circle(r_ins,struct().getPos((r_ins+steml,-stemw/2-r_ins)),layer='FRAME',**kwargs))
        chip.add(InsideCurve(struct().getPos((0,stemw/2)), r_ins, hflip=True,vflip=True,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        chip.add(InsideCurve(struct().getPos((0,-stemw/2)), r_ins, hflip=True,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        
        chip.add(InsideCurve(struct().getPos((inside_ptx,stemw/2)), r_ins, angle=180-theta,vflip=True,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
        chip.add(InsideCurve(struct().getPos((inside_ptx,-stemw/2)), r_ins, angle=180-theta,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
    
    if hflip:
        struct().shiftPos(0,angle=180)
    else:
        struct().shiftPos(tot_length)
        
    
def JSingleProbePad(chip,pos,padwidth=250,padheight=None,padradius=25,tab=False,tabShoulder = False,tabShoulderWidth=30,tabShoulderLength=80,tabShoulderRadius=None,flipped=False,rotation=0,bgcolor=None,**kwargs):
    '''
    Creates a rectangular pad with rounded corners, and a JContactTab on one end (defaults to right)
    No overlap : XOR mode compatible
    
    Optionally set tabShoulder to True to extend a thinner lead from the main contact pad.
    '''
    def struct():
        if isinstance(pos,m.Structure):
            return pos
        elif isinstance(pos,tuple):
            return m.Structure(chip,start=pos,direction=rotation)
        else:
            return chip.structure(pos)
    if tabShoulderRadius is None:
        try:
            tabShoulderRadius = struct().defaults['r_out']
        except KeyError:
            #print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            tabShoulderRadius = 0
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    
    if padheight is None:
        padheight=padwidth
        
    if padradius is None:
        try:
            padradius = struct().defaults['r_out']
        except KeyError:
            #print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            padradius = 0
    
    tablength,tabhwidth = JcalcTabDims(chip,pos,**kwargs)    
    
    if tab:
        #positive tab
        if not flipped:
            chip.add(RoundRect(struct().start,padwidth,padheight,padradius,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs),structure=struct(),length=padwidth)
            if tabShoulder:
                chip.add(RoundRect(struct().start,tabShoulderLength,tabShoulderWidth,tabShoulderRadius,roundCorners=[0,1,1,0],valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs),structure=struct(),length=tabShoulderLength)
        JContact_tab(chip,struct(),hflip = flipped,**kwargs)
        if flipped:
            if tabShoulder:
                chip.add(RoundRect(struct().start,tabShoulderLength,tabShoulderWidth,tabShoulderRadius,roundCorners=[1,0,0,1],valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs),structure=struct(),length=tabShoulderLength)
            chip.add(RoundRect(struct().start,padwidth,padheight,padradius,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
    else:
        #slot
        if not flipped:
            if tabShoulder:
                chip.add(RoundRect(struct().start,padwidth,padheight,padradius,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs),structure=struct(),length=padwidth)
                chip.add(RoundRect(struct().getPos((0,tabhwidth)),tabShoulderLength,tabShoulderWidth/2 - tabhwidth,min(tabShoulderRadius,(tabShoulderWidth/2 - tabhwidth)/2),roundCorners=[0,0,1,0],rotation=struct().direction,bgcolor=bgcolor,**kwargs))
                chip.add(RoundRect(struct().getPos((0,-tabhwidth)),tabShoulderLength,tabShoulderWidth/2 - tabhwidth,min(tabShoulderRadius,(tabShoulderWidth/2 - tabhwidth)/2),roundCorners=[0,1,0,0],valign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
                chip.add(dxf.rectangle(struct().start,tabShoulderLength-tablength,2*tabhwidth,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=struct(),length=tabShoulderLength-tablength)
            else:
                chip.add(RoundRect(struct().getPos((0,tabhwidth)),padwidth,padheight/2 - tabhwidth,padradius,roundCorners=[0,0,1,1],rotation=struct().direction,bgcolor=bgcolor,**kwargs))
                chip.add(RoundRect(struct().getPos((0,-tabhwidth)),padwidth,padheight/2 - tabhwidth,padradius,roundCorners=[1,1,0,0],valign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
                chip.add(dxf.rectangle(struct().start,padwidth-tablength,2*tabhwidth,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=struct(),length=padwidth-tablength)
        JContact_slot(chip,struct(),hflip = not flipped,**kwargs)
        if flipped:
            if tabShoulder:
                chip.add(RoundRect(struct().getPos((-tablength,tabhwidth)),tabShoulderLength,tabShoulderWidth/2 - tabhwidth,min(tabShoulderRadius,(tabShoulderWidth/2 - tabhwidth)/2),roundCorners=[0,0,0,1],rotation=struct().direction,bgcolor=bgcolor,**kwargs))
                chip.add(RoundRect(struct().getPos((-tablength,-tabhwidth)),tabShoulderLength,tabShoulderWidth/2 - tabhwidth,min(tabShoulderRadius,(tabShoulderWidth/2 - tabhwidth)/2),roundCorners=[1,0,0,0],valign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
                chip.add(dxf.rectangle(struct().start,tabShoulderLength-tablength,2*tabhwidth,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)),structure=struct(),length=tabShoulderLength-tablength)
                chip.add(RoundRect(struct().start,padwidth,padheight,padradius,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs),structure=struct(),length=padwidth)
            else:
                chip.add(RoundRect(struct().getPos((-tablength,tabhwidth)),padwidth,padheight/2 - tabhwidth,padradius,roundCorners=[0,0,1,1],rotation=struct().direction,bgcolor=bgcolor,**kwargs))
                chip.add(RoundRect(struct().getPos((-tablength,-tabhwidth)),padwidth,padheight/2 - tabhwidth,padradius,roundCorners=[1,1,0,0],valign=const.TOP,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
                chip.add(dxf.rectangle(struct().start,padwidth-tablength,2*tabhwidth,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
            
            
def JProbePads(chip,structure,padwidth=250,separation=40,rotation=0,**kwargs):
    #cache the structure locally. needed since we call structure methods (shiftPos) on the structure
    thisStructure = None
    if isinstance(structure,tuple):
        thisStructure = m.Structure(chip,start=structure,direction=rotation)
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return thisStructure
        else:
            return chip.structure(structure)
    #cache start
    pos = struct().start
    struct().shiftPos(-separation/2-padwidth)
    JSingleProbePad(chip,struct(),padwidth=padwidth,flipped=False,**kwargs)
    struct().shiftPos(separation)
    JSingleProbePad(chip,struct(),padwidth=padwidth,flipped=True,**kwargs) 
    struct().updatePos(pos) #shift back to where we started        
    
    
def ManhattanJunction(chip,structure,rotation=0,separation=40,jpadw=20,jpadr=2,jpadh=None,jpadOverhang=5,jpadTaper=0,
                      jfingerw=0.13,jfingerl=5.0,jfingerex=1.0,
                      leadw=2.0,leadr=0.5,
                      ucdist=0.6,
                      JANGLE1=None,JANGLE2=None,
                      JLAYER=None,ULAYER=None,bgcolor=None,**kwargs):
    '''
    Set jpadr to None to use chip-wide defaults (r_out).
    '''
    #cache the structure locally. needed since we call structure methods (shiftPos) on the structure
    thisStructure = None
    if isinstance(structure,tuple):
        thisStructure = m.Structure(chip,start=structure,direction=rotation)
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return thisStructure
        else:
            return chip.structure(structure)
    if jpadr is None:
        try:
            jpadr = struct().defaults['r_out']
        except KeyError:
            #print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            jpadr = 0
    if jpadh is None:
        jpadh = jpadw
    if bgcolor is None: #color for junction, not undercut
        bgcolor = chip.wafer.bg()
    #get layers from wafer
    if JLAYER is None:
        try:
            JLAYER = chip.wafer.JLAYER
        except AttributeError:
            setupJunctionLayers(chip.wafer)
            JLAYER = chip.wafer.JLAYER
    if ULAYER is None:
        try:
            ULAYER = chip.wafer.ULAYER
        except AttributeError:
            setupJunctionLayers(chip.wafer)
            ULAYER = chip.wafer.ULAYER
    
    #cache start position and figure out if we're using structures or not
    '''
    if thisStructure is None:
        #using structures
        struct().shiftPos(separation/2)
    '''
    centerPos = struct().start
    
    if JANGLE2 is None:
        if JANGLE1 is None:
            try:
                JANGLE2 = chip.wafer.JANGLES[1] % 360
                JANGLE1 = chip.wafer.JANGLES[0] % 360
                if (JANGLE1 + 90) % 360 != JANGLE2:
                    #switch angle 1 and 2
                    JANGLE2 = JANGLE1
                    JANGLE1 = JANGLE2-90

            except AttributeError:
                setupManhattanJAngles(chip.wafer)
                JANGLE2 = chip.wafer.JANGLES[1] % 360
                JANGLE1 = chip.wafer.JANGLES[0] % 360
        else:
            JANGLE2 = JANGLE1 % 360
            JANGLE1 = JANGLE2-90
    else:
        JANGLE2 = JANGLE2 % 360
        JANGLE1 = JANGLE2-90
    
    # determine angle of structure relative to junction fingers
    angle = (struct().direction - (JANGLE2 - 90)) % 360
    if angle > 180:
        struct().shiftPos(0,angle=180)
        angle = angle % 180
    rot = math.radians(angle)
    #angle should now be between [0,180)
    if angle <= 45:
        left_top = False
        right_top = True
        right_switch = False
    elif angle <= 90:
        left_top = True
        right_top = False
        right_switch = False
    else:
        left_top = True
        right_top = True
        right_switch = True
    
    # adjust overhang to account for taper
    if jpadTaper > 0:
        jpadOverhang = jpadOverhang + jpadTaper
    
    '''
    # ==================== UNDERCUT LAYER ====================
    # do this first so undercut lines don't obscure junction lines
    '''
    if ucdist > 0:
        # -------------------- junction pads -----------------------
        rot0 = min(max(math.radians(angle),0),math.radians(90))
        rot90 = min(max(math.radians(angle)-math.radians(90),0),math.radians(90))
        
        '''
        = = = = = = = = = = = LEFT LEAD = = = = = = = = = = = = =
        '''
        
        jpadUCL=SolidPline(centerPos,rotation=struct().direction,bgcolor=chip.bg(ULAYER),layer=ULAYER,solidFillQuads=True)
        # - - - - - - - hug pad - - - - - - - 
        if angle < 90:
            if jpadTaper > 0:
                jpadUCL.add_vertex((-separation/2+jpadOverhang-jpadTaper,-jpadh/2))
            else: # corner 1
                jpadUCL.add_vertices(curveAB((-separation/2+jpadOverhang-jpadTaper-jpadr*(1-math.cos(rot)),-jpadh/2+jpadr*(1-math.sin(rot))),
                                             (-separation/2+jpadOverhang-jpadTaper-jpadr,-jpadh/2),
                                             clockwise=True,angleDeg=90-angle))
        if angle < 180: # corner 2
            jpadUCL.add_vertices(curveAB((-separation/2+jpadOverhang-jpadTaper-jpadw+jpadr*(1-math.sin(rot90)),-jpadh/2+jpadr*(1-math.cos(rot90))),
                                         (-separation/2+jpadOverhang-jpadTaper-jpadw,-jpadh/2+jpadr),
                                         clockwise=True,angleDeg=min(180-angle,90)))
        
        # corner 3 (this one never goes away)
        jpadUCL.add_vertices(curveAB((-separation/2+jpadOverhang-jpadTaper-jpadw,jpadh/2-jpadr),
                                     (-separation/2+jpadOverhang-jpadTaper-jpadw+jpadr,jpadh/2),
                                     clockwise=True))
        
        # corner 4
        if angle > 0:
            if jpadTaper >0:
                jpadUCL.add_vertex((-separation/2+jpadOverhang-jpadTaper,jpadh/2))
            else:
                jpadUCL.add_vertices(curveAB((-separation/2+jpadOverhang-jpadTaper-jpadr,jpadh/2),
                                             (-separation/2+jpadOverhang-jpadTaper-jpadr*(1-math.sin(rot0)),jpadh/2-jpadr*(1-math.cos(rot0))),
                                             clockwise=True,angleDeg=min(angle,90)))
        if jpadTaper <=0:
            if angle > 90:
                jpadUCL.add_vertex((-separation/2+jpadOverhang,
                               -(jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2+ucdist*max(-math.cos(rot),math.sin(rot))))
            # - - - - - - - extend pad - - - - - -
            
            if angle > 90:
                jpadUCL.add_vertex((-separation/2+jpadOverhang-ucdist*math.cos(rot),
                               -(jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2+ucdist*max(-math.cos(rot),math.sin(rot))))
        # corner 4
        if angle > 0:
            if jpadTaper >0:
                jpadUCL.add_vertex((-separation/2+jpadOverhang-jpadTaper-ucdist*math.cos(rot),jpadh/2 + ucdist* max(math.sin(rot),-math.cos(rot))))
            else:
                jpadUCL.add_vertices(curveAB((-separation/2+jpadOverhang-jpadTaper-jpadr*(1-math.sin(rot0))-ucdist*math.cos(rot),jpadh/2 -jpadr*(1-math.cos(rot0)) + ucdist* max(math.sin(rot),-math.cos(rot))),
                                             (-separation/2+jpadOverhang-jpadTaper-jpadr-ucdist*math.cos(rot),jpadh/2 + ucdist* max(math.sin(rot),-math.cos(rot))),
                                             clockwise=False,angleDeg=min(angle,90)))
        
        
        # corner 3 (this one never goes away)
        jpadUCL.add_vertices(curveAB((-separation/2+jpadOverhang-jpadTaper-jpadw+jpadr + (math.cos(rot)>math.sin(rot) and -ucdist*math.cos(rot) or -ucdist*math.sin(rot)),jpadh/2+ucdist*max(math.sin(rot),-math.cos(rot))),
                                     (-separation/2+jpadOverhang-jpadTaper-jpadw -ucdist*max(math.sin(rot),math.cos(rot)),jpadh/2-jpadr + ucdist*math.sin(rot0)),
                                     clockwise=False))
        if angle < 180: # corner 2
            jpadUCL.add_vertices(curveAB((-separation/2+jpadOverhang-jpadTaper-jpadw-ucdist*max(math.sin(rot),math.cos(rot)),-jpadh/2+jpadr -ucdist*math.cos(rot)),
                                         (-separation/2+jpadOverhang-jpadTaper-jpadw+jpadr*(1-math.sin(rot90))-ucdist*max(math.sin(rot),math.cos(rot)),-jpadh/2+jpadr*(1-math.cos(rot90))-ucdist*math.cos(rot)),
                                         clockwise=False,angleDeg=min(180-angle,90)))
        
        if angle < 90: 
            if jpadTaper > 0:
                jpadUCL.add_vertex((-separation/2+jpadOverhang-jpadTaper-ucdist*math.sin(rot),-jpadh/2-ucdist*math.cos(rot)))
            else: # corner 1
                jpadUCL.add_vertices(curveAB((-separation/2+jpadOverhang-jpadTaper-jpadr-ucdist*math.sin(rot),-jpadh/2-ucdist*math.cos(rot)),
                                             (-separation/2+jpadOverhang-jpadTaper-jpadr*(1-math.cos(rot))-ucdist*math.sin(rot),-jpadh/2+jpadr*(1-math.sin(rot))-ucdist*math.cos(rot)),
                                             clockwise=False,angleDeg=90-angle))
        chip.add(jpadUCL)
        
        if angle > 90 and jpadTaper <=0:
            jpadUCL2=SolidPline(centerPos,rotation=struct().direction,bgcolor=chip.bg(ULAYER),layer=ULAYER,solidFillQuads=True)
            # - - - - - - - hug pad - - - - - - -
            jpadUCL2.add_vertex((-separation/2+jpadOverhang,
                       -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2))
            # corner 1
            jpadUCL2.add_vertices(curveAB((-separation/2+jpadOverhang-jpadTaper,-jpadh/2+jpadr),
                                         (-separation/2+jpadOverhang-jpadTaper-jpadr*(1-math.cos(rot90)),-jpadh/2+jpadr*(1-math.sin(rot90))),
                                             clockwise=True,angleDeg=min(angle-90,90)))
            # - - - - - - - extend pad - - - - - - -
            # corner 1
            jpadUCL2.add_vertices(curveAB((-separation/2+jpadOverhang-jpadTaper-jpadr*(1-math.cos(rot90))-ucdist*math.cos(rot),
                                          -jpadh/2+jpadr*(1-math.sin(rot90))+ucdist*math.sin(rot)),
                                         (-separation/2+jpadOverhang-jpadTaper-ucdist*math.cos(rot),-jpadh/2+jpadr+ucdist*math.sin(rot)),
                                             clockwise=False,angleDeg=min(angle-90,90)))
            jpadUCL2.add_vertex((-separation/2+jpadOverhang-ucdist*math.cos(rot),
                           -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2))
            chip.add(jpadUCL2)
        '''
        = = = = = = = = = = = RIGHT LEAD = = = = = = = = = = = = =
        '''
        
        if (angle < 90 and jpadTaper > 0) or (angle < 180 and jpadTaper <= 0): 
            
            jpadUCR=SolidPline(centerPos,rotation=struct().direction,bgcolor=chip.bg(ULAYER),layer=ULAYER,solidFillQuads=True)
            # - - - - - - - hug pad - - - - - - - 
            if angle < 90: # corner 1
                jpadUCR.add_vertices(curveAB((jpadw+separation/2-jpadOverhang+jpadTaper-jpadr*(1-math.cos(rot)),-jpadh/2+jpadr*(1-math.sin(rot))),
                                             (jpadw+separation/2-jpadOverhang+jpadTaper-jpadr,-jpadh/2),
                                             clockwise=True,angleDeg=90-angle))
            if jpadTaper > 0:
                if angle < 90:
                    jpadUCR.add_vertex((jpadw+separation/2-jpadOverhang+jpadTaper-jpadw,-jpadh/2))
            elif angle < 180: # corner 2
                jpadUCR.add_vertices(curveAB((jpadw+separation/2-jpadOverhang+jpadTaper-jpadw+jpadr*(1-math.sin(rot90)),-jpadh/2+jpadr*(1-math.cos(rot90))),
                                             (jpadw+separation/2-jpadOverhang+jpadTaper-jpadw,-jpadh/2+jpadr),
                                             clockwise=True,angleDeg=min(180-angle,90)))
            if jpadTaper <=0:
                if right_top:
                    # j finger stems from top of right lead
                    if not right_switch:
                        # angle is 0-45 deg
                        jpadUCR.add_vertices([(separation/2-jpadOverhang,
                                           -(jfingerl-jfingerex)*math.sin(rot)-leadw+jfingerw*math.cos(rot)/2-ucdist*math.cos(rot)),
                                              (separation/2-jpadOverhang-ucdist*math.cos(rot),
                                           -(jfingerl-jfingerex)*math.sin(rot)-leadw+jfingerw*math.cos(rot)/2-ucdist*math.cos(rot))])
                    else:
                        # angle is 91-180 deg
                        jpadUCR.add_vertices([
                            (separation/2-jpadOverhang,
                                           (jfingerl-jfingerex)*math.cos(rot)-leadw+jfingerw*math.sin(rot)/2),
                            (separation/2-jpadOverhang-ucdist*math.sin(rot),
                                           (jfingerl-jfingerex)*math.cos(rot)-leadw+jfingerw*math.sin(rot)/2)
                            ])
                else:
                    # angle is 46-90 deg
                    jpadUCR.add_vertices([(separation/2-jpadOverhang,
                                       (jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2-ucdist*math.cos(rot)),
                                          (separation/2-jpadOverhang-ucdist*math.sin(rot),
                                       (jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2-ucdist*math.cos(rot))
                                          ])
            # - - - - - - - extend pad - - - - - -
            
            if jpadTaper > 0:
                if angle < 90:
                    jpadUCR.add_vertex((jpadw+separation/2-jpadOverhang+jpadTaper-jpadw-ucdist*max(math.sin(rot),math.cos(rot)),-jpadh/2 -ucdist*math.cos(rot)))
            elif angle < 180: # corner 2
                jpadUCR.add_vertices(curveAB((jpadw+separation/2-jpadOverhang+jpadTaper-jpadw-ucdist*max(math.sin(rot),math.cos(rot)),-jpadh/2+jpadr -ucdist*math.cos(rot)),
                                             (jpadw+separation/2-jpadOverhang+jpadTaper-jpadw+jpadr*(1-math.sin(rot90))-ucdist*max(math.sin(rot),math.cos(rot)),-jpadh/2+jpadr*(1-math.cos(rot90))-ucdist*math.cos(rot)),
                                             clockwise=False,angleDeg=min(180-angle,90)))
            
            if angle < 90: # corner 1
                jpadUCR.add_vertices(curveAB((jpadw+separation/2-jpadOverhang+jpadTaper-jpadr-ucdist*math.sin(rot),-jpadh/2-ucdist*math.cos(rot)),
                                             (jpadw+separation/2-jpadOverhang+jpadTaper-jpadr*(1-math.cos(rot))-ucdist*math.sin(rot),-jpadh/2+jpadr*(1-math.sin(rot))-ucdist*math.cos(rot)),
                                             clockwise=False,angleDeg=90-angle))
            chip.add(jpadUCR)
            
        if (jpadTaper > 0 and angle > 0) or jpadTaper <= 0:
            jpadUCR2=SolidPline(centerPos,rotation=struct().direction,bgcolor=chip.bg(ULAYER),layer=ULAYER,solidFillQuads=True)
            # - - - - - - - hug pad - - - - - - - 
            if jpadTaper >0:
                if angle > 0:
                    jpadUCR2.add_vertex((separation/2-jpadOverhang+jpadTaper,jpadh/2))
            else:
                if right_top:
                    # j finger stems from top of right lead
                    if not right_switch:
                        # angle is 0-45 deg
                        jpadUCR2.add_vertex((separation/2-jpadOverhang,
                                           -(jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2+ucdist*math.sin(rot)))
                    else:
                        # angle is 91-180 deg
                        jpadUCR2.add_vertex((separation/2-jpadOverhang,
                                           (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2+ucdist*max(math.sin(rot),-math.cos(rot))))
                else:
                    # angle is 46-90 deg
                    jpadUCR2.add_vertex((separation/2-jpadOverhang,
                                       (jfingerl-jfingerex)*math.cos(rot)+leadw-jfingerw*math.sin(rot)/2+ucdist*math.sin(rot)))
                    
                # corner 3 (this one never goes away)
                jpadUCR2.add_vertices(curveAB((jpadw+separation/2-jpadOverhang+jpadTaper-jpadw,jpadh/2-jpadr),
                                             (jpadw+separation/2-jpadOverhang+jpadTaper-jpadw+jpadr,jpadh/2),
                                             clockwise=True))
            
            # corner 4
            if angle > 0:
                jpadUCR2.add_vertices(curveAB((jpadw+separation/2-jpadOverhang+jpadTaper-jpadr,jpadh/2),
                                                 (jpadw+separation/2-jpadOverhang+jpadTaper-jpadr*(1-math.sin(rot0)),jpadh/2-jpadr*(1-math.cos(rot0))),
                                                 clockwise=True,angleDeg=min(angle,90)))
            
            # corner 1
            if angle >90:
                jpadUCR2.add_vertices(curveAB((jpadw+separation/2-jpadOverhang+jpadTaper,-jpadh/2+jpadr),
                                             (jpadw+separation/2-jpadOverhang+jpadTaper-jpadr*(1-math.cos(rot90)),-jpadh/2+jpadr*(1-math.sin(rot90))),
                                                 clockwise=True,angleDeg=min(angle-90,90)))
                # - - - - - - - extend pad - - - - - - -
                # corner 1
                jpadUCR2.add_vertices(curveAB((jpadw+separation/2-jpadOverhang+jpadTaper-jpadr*(1-math.cos(rot90))-ucdist*math.cos(rot),
                                              -jpadh/2+jpadr*(1-math.sin(rot90))+ucdist*math.sin(rot)),
                                             (jpadw+separation/2-jpadOverhang+jpadTaper-ucdist*math.cos(rot),-jpadh/2+jpadr+ucdist*math.sin(rot)),
                                                 clockwise=False,angleDeg=min(angle-90,90)))
            
            # corner 4
            if angle > 0:
                jpadUCR2.add_vertices(curveAB((jpadw+separation/2-jpadOverhang+jpadTaper-jpadr*(1-math.sin(rot0))-ucdist*math.cos(rot),jpadh/2 -jpadr*(1-math.cos(rot0)) + ucdist* max(math.sin(rot),-math.cos(rot))),
                                                 (jpadw+separation/2-jpadOverhang+jpadTaper-jpadr-ucdist*math.cos(rot),jpadh/2 + ucdist* max(math.sin(rot),-math.cos(rot))),
                                                 clockwise=False,angleDeg=min(angle,90)))
            
            
            if jpadTaper >0:
                if angle > 0:
                    jpadUCR2.add_vertex((separation/2-jpadOverhang+jpadTaper+ (math.cos(rot)>math.sin(rot) and -ucdist*math.cos(rot) or -ucdist*math.sin(rot)),jpadh/2+ucdist*max(math.sin(rot),-math.cos(rot))))
            else:
                # corner 3 (this one never goes away)
                jpadUCR2.add_vertices(curveAB((jpadw+separation/2-jpadOverhang+jpadTaper-jpadw+jpadr + (math.cos(rot)>math.sin(rot) and -ucdist*math.cos(rot) or -ucdist*math.sin(rot)),jpadh/2+ucdist*max(math.sin(rot),-math.cos(rot))),
                                             (jpadw+separation/2-jpadOverhang+jpadTaper-jpadw -ucdist*max(math.sin(rot),math.cos(rot)),jpadh/2-jpadr + ucdist*math.sin(rot0)),
                                             clockwise=False))
                if right_top:
                    # j finger stems from top of right lead
                    if not right_switch:
                        # angle is 0-45 deg
                        jpadUCR2.add_vertex((separation/2-jpadOverhang-ucdist*math.cos(rot),
                                           -(jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2+ucdist*math.sin(rot)))
                    else:
                        # angle is 91-180 deg
                        jpadUCR2.add_vertex((separation/2-jpadOverhang-ucdist*math.sin(rot),
                                           (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2+ucdist*max(math.sin(rot),-math.cos(rot))))
                else:
                    # angle is 46-90 deg
                    jpadUCR2.add_vertex((separation/2-jpadOverhang-ucdist*math.sin(rot),
                                       (jfingerl-jfingerex)*math.cos(rot)+leadw-jfingerw*math.sin(rot)/2+ucdist*math.sin(rot)))
                    
            chip.add(jpadUCR2)


        # -------------------- junction taper ----------------------
        
        if jpadTaper >0:
            # left taper
            if left_top:
                l_tap_rot_0 = math.atan(jpadTaper/(jpadh/2-(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2))
                l_tap_rot_1 = math.atan(jpadTaper/(jpadh/2+(jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2))
                
                if  l_tap_rot_0 > rot: # bottom angle 2
                    chip.add(SolidPline(centerPos, points=[
                        rotate_2d((-separation/2+jpadOverhang-ucdist*math.sin(rot),
                                   -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang-jpadTaper-ucdist*math.sin(rot),-jpadh/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang-jpadTaper,-jpadh/2),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang,
                                   -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang,
                                   -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction))
                        ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                elif angle < 90:
                    # bottom angle 2
                    chip.add(SolidPline(centerPos, points=[
                        rotate_2d((-separation/2+jpadOverhang-ucdist*math.cos(rot)*math.tan(l_tap_rot_0),
                                   -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang,
                                   -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang,
                                   -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction))
                        ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                if l_tap_rot_1 > math.pi/2 - rot:
                    chip.add(SolidPline(centerPos, points=[
                        rotate_2d((-separation/2+jpadOverhang-ucdist*math.cos(rot),
                                   -(jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2+ucdist*max(math.sin(rot),-math.cos(rot))),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang,
                                   -(jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2+ucdist*max(math.sin(rot),-math.cos(rot))),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang,
                                   -(jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang-jpadTaper,jpadh/2),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang-jpadTaper-ucdist*math.cos(rot),jpadh/2+ucdist*max(math.sin(rot),-math.cos(rot))),math.radians(struct().direction))
                        ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                else:
                    chip.add(SolidPline(centerPos, points=[
                        rotate_2d((-separation/2+jpadOverhang-ucdist*math.sin(rot)*math.tan(l_tap_rot_1),
                                   -(jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang,
                                   -(jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang,
                                   -(jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2),math.radians(struct().direction))
                        ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                    
            else:
                l_tap_rot_0 = math.atan(jpadTaper/(jpadh/2+(jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2))
                l_tap_rot_1 = math.atan(jpadTaper/(jpadh/2-(jfingerl-jfingerex)*math.cos(rot)-leadw-jfingerw*math.sin(rot)/2))
                #print('taper angle ',math.degrees(l_tap_rot_1),',@',90-angle)
                if  l_tap_rot_0 > rot: # bottom angle 2
                    chip.add(SolidPline(centerPos, points=[
                        rotate_2d((-separation/2+jpadOverhang-ucdist*math.sin(rot),
                                   (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang-jpadTaper-ucdist*math.sin(rot),-jpadh/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang-jpadTaper,-jpadh/2),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang,
                                   (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang,
                                   (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction))     
                        ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                elif angle < 90:
                    chip.add(SolidPline(centerPos, points=[
                        rotate_2d((-separation/2+jpadOverhang-ucdist*math.cos(rot)*math.tan(l_tap_rot_0),
                                   (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang,
                                   (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang,
                                   (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction))     
                        ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                if l_tap_rot_1 > math.pi/2 - rot:
                    chip.add(SolidPline(centerPos, points=[
                        rotate_2d((-separation/2+jpadOverhang-ucdist*math.cos(rot),
                                   (jfingerl-jfingerex)*math.cos(rot)+leadw+jfingerw*math.sin(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang,
                                   (jfingerl-jfingerex)*math.cos(rot)+leadw+jfingerw*math.sin(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang,
                                   (jfingerl-jfingerex)*math.cos(rot)+leadw+jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang-jpadTaper,jpadh/2),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang-jpadTaper-ucdist*math.cos(rot),jpadh/2+ucdist*math.sin(rot)),math.radians(struct().direction))
                        ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                elif angle > 0:
                    chip.add(SolidPline(centerPos, points=[
                        rotate_2d((-separation/2+jpadOverhang-ucdist*math.sin(rot)*math.tan(l_tap_rot_1),
                                   (jfingerl-jfingerex)*math.cos(rot)+leadw+jfingerw*math.sin(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang,
                                   (jfingerl-jfingerex)*math.cos(rot)+leadw+jfingerw*math.sin(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                        rotate_2d((-separation/2+jpadOverhang,
                                   (jfingerl-jfingerex)*math.cos(rot)+leadw+jfingerw*math.sin(rot)/2),math.radians(struct().direction))
                        ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
            
            # right taper
            if right_top:
                if not right_switch:
                    # angle is 0-45 deg
                    chip.add(SolidPline(centerPos, points=[
                        rotate_2d((separation/2-jpadOverhang,
                               -(jfingerl-jfingerex)*math.sin(rot)-leadw+jfingerw*math.cos(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                        rotate_2d((separation/2-jpadOverhang,
                               -(jfingerl-jfingerex)*math.sin(rot)-leadw+jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                        rotate_2d((separation/2-jpadOverhang+jpadTaper,-jpadh/2),math.radians(struct().direction)),
                        rotate_2d((separation/2-jpadOverhang+jpadTaper-ucdist*math.cos(rot),-jpadh/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                        rotate_2d((separation/2-jpadOverhang-ucdist*math.cos(rot),
                               -(jfingerl-jfingerex)*math.sin(rot)-leadw+jfingerw*math.cos(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction))
                        ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                    if angle > 0:
                        chip.add(SolidPline(centerPos, points=[
                            rotate_2d((separation/2-jpadOverhang,
                                       -(jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang,
                                       -(jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang+jpadTaper,jpadh/2),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang+jpadTaper-ucdist*math.cos(rot),jpadh/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang-ucdist*math.cos(rot),
                                       -(jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction))
                            ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                    else:
                        chip.add(SolidPline(centerPos, points=[
                            rotate_2d((separation/2-jpadOverhang-ucdist*math.cos(rot),
                                       -(jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang,
                                       -(jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang+jpadTaper,jpadh/2),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang+jpadTaper-ucdist*math.cos(rot),jpadh/2+ucdist*math.sin(rot)),math.radians(struct().direction))
                            ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                else:
                    # angle is 91-180 deg
                    r_tap_rot_0 = math.atan(jpadTaper/(jpadh/2 + (jfingerl-jfingerex)*math.cos(rot)-leadw+jfingerw*math.sin(rot)/2))
                    
                    if math.degrees(r_tap_rot_0) + angle < 180 and angle < 180:
                        chip.add(SolidPline(centerPos, points=[
                            rotate_2d((separation/2-jpadOverhang-ucdist*(math.sin(rot)+math.cos(rot)*math.tan(r_tap_rot_0)),
                                       (jfingerl-jfingerex)*math.cos(rot)-leadw+jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang,
                                       (jfingerl-jfingerex)*math.cos(rot)-leadw+jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang+jpadTaper,-jpadh/2),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang+jpadTaper-ucdist*math.sin(rot),-jpadh/2-ucdist*math.cos(rot)),math.radians(struct().direction))
                            ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                    if angle < 180:
                        chip.add(SolidPline(centerPos, points=[
                            rotate_2d((separation/2-jpadOverhang,
                               (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2+ucdist*max(math.sin(rot),-math.cos(rot))),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang,
                               (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang+jpadTaper,jpadh/2),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang+jpadTaper-ucdist*math.sin(rot),jpadh/2+ucdist*max(math.sin(rot),-math.cos(rot))),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang-ucdist*math.sin(rot),
                               (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2+ucdist*max(math.sin(rot),-math.cos(rot))),math.radians(struct().direction))
                            ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                    else:
                        chip.add(SolidPline(centerPos, points=[
                            rotate_2d((separation/2-jpadOverhang,
                               (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2+ucdist*max(math.sin(rot),-math.cos(rot))),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang,
                               (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang+jpadTaper,jpadh/2),math.radians(struct().direction)),
                            rotate_2d((separation/2-jpadOverhang+jpadTaper-ucdist*math.sin(rot),jpadh/2+ucdist*max(math.sin(rot),-math.cos(rot))),math.radians(struct().direction))
                            ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
            else:
                # angle is 46 - 90 deg
                if angle < 90:
                    chip.add(SolidPline(centerPos, points=[
                        rotate_2d((separation/2-jpadOverhang,
                                   (jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                        rotate_2d((separation/2-jpadOverhang,
                                   (jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                        rotate_2d((separation/2-jpadOverhang+jpadTaper,-jpadh/2),math.radians(struct().direction)),
                        rotate_2d((separation/2-jpadOverhang+jpadTaper-ucdist*math.sin(rot),-jpadh/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                        rotate_2d((separation/2-jpadOverhang-ucdist*math.sin(rot),
                                   (jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction))
                        ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                else:
                    chip.add(SolidPline(centerPos, points=[
                        rotate_2d((separation/2-jpadOverhang,
                                   (jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                        rotate_2d((separation/2-jpadOverhang+jpadTaper,-jpadh/2),math.radians(struct().direction)),
                        rotate_2d((separation/2-jpadOverhang+jpadTaper-ucdist*math.sin(rot),-jpadh/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                        rotate_2d((separation/2-jpadOverhang-ucdist*math.sin(rot),
                                   (jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction))
                        ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                
                chip.add(SolidPline(centerPos, points=[
                    rotate_2d((separation/2-jpadOverhang,
                               (jfingerl-jfingerex)*math.cos(rot)+leadw-jfingerw*math.sin(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang,
                               (jfingerl-jfingerex)*math.cos(rot)+leadw-jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang+jpadTaper,jpadh/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang+jpadTaper-ucdist*math.sin(rot),jpadh/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang-ucdist*math.sin(rot),
                               (jfingerl-jfingerex)*math.cos(rot)+leadw-jfingerw*math.sin(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                    
                    ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                
                
        # -------------------- junction fingers --------------------
        chip.add(dxf.rectangle(vadd(centerPos,rotate_2d((-jfingerex,0),#rotate about center
                                                        math.radians(JANGLE2))), jfingerex<=0 and 2*jfingerex or -ucdist, min(3*jfingerw,2*jfingerex), rotation=JANGLE2,
                               valign=const.MIDDLE,layer=ULAYER,bgcolor=chip.bg(ULAYER),**kwargStrip(kwargs)))
        if jfingerex >0:
            chip.add(dxf.rectangle(vadd(centerPos,rotate_2d((-jfingerex,0),#rotate about center
                                                            math.radians(JANGLE1))), -ucdist, min(3*jfingerw,2*jfingerex), rotation=JANGLE1,
                                   valign=const.MIDDLE,layer=ULAYER,bgcolor=chip.bg(ULAYER),**kwargStrip(kwargs)))
            
        # -------------------- junction leads ---------------------
        if left_top: 
            # j finger stems from top of left lead
            # angle is 46-180 deg
            if angle < 180:
                # ANGLE 1 undercut
                chip.add(SolidPline(centerPos, points=[
                    rotate_2d((-separation/2+jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                    rotate_2d((jfingerl-jfingerex,-jfingerw/2),math.radians(JANGLE1)),
                    rotate_2d((jfingerl-jfingerex-ucdist,-jfingerw/2),math.radians(JANGLE1)),
                    rotate_2d((-separation/2+jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction))
                    ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
            if math.sin(rot) < -math.cos(rot):
                # ANGLE 2 undercut
                chip.add(SolidPline(centerPos, points=[
                    rotate_2d((jfingerl-jfingerex,-jfingerw/2-ucdist),math.radians(JANGLE1)),
                    rotate_2d((jfingerl-jfingerex,-jfingerw/2+ucdist*math.tan(rot)),math.radians(JANGLE1)),
                    rotate_2d((-separation/2+jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                    rotate_2d((-separation/2+jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction))
                    ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
            if angle <90:
                # ANGLE 2 undercut
                chip.add(SolidPline(centerPos, points=[
                    rotate_2d(((jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2,
                           -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                    rotate_2d((-separation/2+jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                    rotate_2d((-separation/2+jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                    rotate_2d(((jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2-ucdist*math.sin(rot),
                           -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction))
                    ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
            elif angle > 90:
                # ANGLE 1 undercut
                chip.add(SolidPline(centerPos, points=[
                    rotate_2d((jfingerl-jfingerex,jfingerw/2),math.radians(JANGLE1)),
                    rotate_2d((jfingerl-jfingerex-ucdist,jfingerw/2),math.radians(JANGLE1)),
                    rotate_2d(((jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2 - ucdist*math.cos(rot),
                           -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2 + ucdist*math.sin(rot)),math.radians(struct().direction)),
                    rotate_2d(((jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2,
                           -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2),math.radians(struct().direction))
                    ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
        else:# angle is 0-45 deg
            # j finger stems from bottom of left lead
            if angle > 0:
                # ANGLE 1 undercut
                chip.add(SolidPline(centerPos, points=[
                    rotate_2d((-separation/2+jpadOverhang,
                               (jfingerl-jfingerex)*math.cos(rot)+leadw+jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                    rotate_2d((-separation/2+jpadOverhang,
                               (jfingerl-jfingerex)*math.cos(rot)+leadw+jfingerw*math.sin(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                    rotate_2d(((jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2-ucdist*math.cos(rot),
                               (jfingerl-jfingerex)*math.cos(rot)+leadw+jfingerw*math.sin(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                    rotate_2d(((jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2,
                               (jfingerl-jfingerex)*math.cos(rot)+leadw+jfingerw*math.sin(rot)/2),math.radians(struct().direction))
                    ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
            # ANGLE 2 undercut
            chip.add(SolidPline(centerPos, points=[
                rotate_2d((-separation/2+jpadOverhang,
                           (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                rotate_2d((jfingerl-jfingerex,jfingerw/2),math.radians(JANGLE2)),
                rotate_2d((jfingerl-jfingerex-ucdist,jfingerw/2),math.radians(JANGLE2)),
                rotate_2d((-separation/2+jpadOverhang,
                           (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2- ucdist*math.cos(rot)),math.radians(struct().direction))
                ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
        
        if right_top:
            # j finger stems from top of right lead
            if not right_switch:
                # JANGLE1 is our finger
                # angle is 0-45 deg
                
                # ANGLE 1 undercut
                chip.add(SolidPline(centerPos, points=[
                    rotate_2d((jfingerl-jfingerex-ucdist,-jfingerw/2),math.radians(JANGLE1)),
                    rotate_2d((jfingerl-jfingerex,-jfingerw/2),math.radians(JANGLE1)),
                    rotate_2d(((jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2,
                               -(jfingerl-jfingerex)*math.sin(rot)-leadw+jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                    rotate_2d(((jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2-ucdist*math.cos(rot),
                               -(jfingerl-jfingerex)*math.sin(rot)-leadw+jfingerw*math.cos(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction))
                    ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                if angle > 0:
                    # ANGLE 1 undercut
                    chip.add(SolidPline(centerPos, points=[
                        rotate_2d((jfingerl-jfingerex-ucdist,jfingerw/2),math.radians(JANGLE1)),
                        rotate_2d((jfingerl-jfingerex,jfingerw/2),math.radians(JANGLE1)),
                        rotate_2d((separation/2-jpadOverhang,
                               -(jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                        rotate_2d((separation/2-jpadOverhang,
                               -(jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction))
                        ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                # ANGLE 2 undercut
                chip.add(SolidPline(centerPos, points=[
                    rotate_2d(((jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2,
                           -(jfingerl-jfingerex)*math.sin(rot)-leadw+jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(rot)-leadw+jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(rot)-leadw+jfingerw*math.cos(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                    rotate_2d(((jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2-ucdist*math.sin(rot),
                           -(jfingerl-jfingerex)*math.sin(rot)-leadw+jfingerw*math.cos(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                    rotate_2d(((jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2-ucdist*math.cos(rot)*math.tan(rot),
                           -(jfingerl-jfingerex)*math.sin(rot)-leadw+jfingerw*math.cos(rot)/2+ucdist*math.sin(rot)*math.tan(rot)),math.radians(struct().direction))
                    ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
            else:
                # JANGLE2 is our finger
                # angle is 91-180 deg
                if angle < 180:
                    # ANGLE 2 undercut
                    chip.add(SolidPline(centerPos, points=[
                        rotate_2d((jfingerl-jfingerex,-jfingerw/2),math.radians(JANGLE2)),
                        rotate_2d((jfingerl-jfingerex-ucdist,-jfingerw/2),math.radians(JANGLE2)),
                        rotate_2d(((jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2-ucdist*math.sin(rot),
                               (jfingerl-jfingerex)*math.cos(rot)-leadw+jfingerw*math.sin(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                        rotate_2d(((jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2,
                               (jfingerl-jfingerex)*math.cos(rot)-leadw+jfingerw*math.sin(rot)/2),math.radians(struct().direction))
                        ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                if angle > 90:
                    # ANGLE 2 undercut
                    chip.add(SolidPline(centerPos, points=[
                        rotate_2d((jfingerl-jfingerex,jfingerw/2),math.radians(JANGLE2)),
                        rotate_2d((jfingerl-jfingerex-ucdist,jfingerw/2),math.radians(JANGLE2)),
                        rotate_2d((separation/2-jpadOverhang,
                               (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                        rotate_2d((separation/2-jpadOverhang,
                                   (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2),math.radians(struct().direction))
                        ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
                if math.sin(rot)>-math.cos(rot):
                    # ANGLE 1 undercut
                    chip.add(SolidPline(centerPos, points=[
                        rotate_2d((separation/2-jpadOverhang,
                               (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction)),
                        rotate_2d((jfingerl-jfingerex,jfingerw/2-ucdist/math.tan(rot)),math.radians(JANGLE2)),
                        rotate_2d((jfingerl-jfingerex,jfingerw/2+ucdist),math.radians(JANGLE2)),
                        rotate_2d((separation/2-jpadOverhang,
                               (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction))
                        ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
        else:
            # j finger stems from bottom of right lead
            # JANGLE2 is our finger
            # angle is 46-90 deg
            if angle < 90:
                # ANGLE 2 undercut
                chip.add(SolidPline(centerPos, points=[
                    rotate_2d((jfingerl-jfingerex-ucdist,-jfingerw/2),math.radians(JANGLE2)),
                    rotate_2d((jfingerl-jfingerex,-jfingerw/2),math.radians(JANGLE2)),
                    rotate_2d((separation/2-jpadOverhang,
                       (jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang,
                       (jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction))
                    ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
            # ANGLE 2 undercut
            chip.add(SolidPline(centerPos, points=[
                rotate_2d((jfingerl-jfingerex-ucdist,jfingerw/2),math.radians(JANGLE2)),
                rotate_2d((jfingerl-jfingerex,jfingerw/2),math.radians(JANGLE2)),
                rotate_2d(((jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2,
                           (jfingerl-jfingerex)*math.cos(rot)+leadw-jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                rotate_2d(((jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2-ucdist*math.sin(rot),
                           (jfingerl-jfingerex)*math.cos(rot)+leadw-jfingerw*math.sin(rot)/2-ucdist*math.cos(rot)),math.radians(struct().direction))
                ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
            # ANGLE 1 undercut
            chip.add(SolidPline(centerPos, points=[
                rotate_2d(((jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2,
                           (jfingerl-jfingerex)*math.cos(rot)+leadw-jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                rotate_2d((separation/2-jpadOverhang,
                           (jfingerl-jfingerex)*math.cos(rot)+leadw-jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                rotate_2d((separation/2-jpadOverhang,
                           (jfingerl-jfingerex)*math.cos(rot)+leadw-jfingerw*math.sin(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                rotate_2d(((jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2-ucdist*math.cos(rot),
                           (jfingerl-jfingerex)*math.cos(rot)+leadw-jfingerw*math.sin(rot)/2+ucdist*math.sin(rot)),math.radians(struct().direction)),
                rotate_2d(((jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2-ucdist*math.sin(rot)/math.tan(rot),
                           (jfingerl-jfingerex)*math.cos(rot)+leadw-jfingerw*math.sin(rot)/2-ucdist*math.cos(rot)/math.tan(rot)),math.radians(struct().direction))
                ],bgcolor=chip.bg(ULAYER),layer=ULAYER))
        
    '''
    # ==================== JUNCTION LAYER ====================
    '''
    
    # -------------------- junction pads --------------------
    
    chip.add(RoundRect(struct().getPos((-separation/2+jpadOverhang-jpadTaper,0)),jpadw,jpadh,jpadr,roundCorners = (jpadTaper > 0) and [1,0,0,1] or [1,1,1,1],
                       valign=const.MIDDLE,halign=const.RIGHT,rotation=struct().direction,bgcolor=bgcolor,layer=JLAYER,**kwargs))
    chip.add(RoundRect(struct().getPos((separation/2-jpadOverhang+jpadTaper,0)),jpadw,jpadh,jpadr,roundCorners = (jpadTaper > 0) and [0,1,1,0] or [1,1,1,1],
                       valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,layer=JLAYER,**kwargs))
    
    # -------------------- junction fingers --------------------
    
    chip.add(dxf.rectangle(vadd(centerPos,rotate_2d((-jfingerex,0),#rotate about center
                                                    math.radians(JANGLE2))), jfingerl, jfingerw, rotation=JANGLE2,
                           valign=const.MIDDLE,layer=JLAYER,bgcolor=bgcolor,**kwargStrip(kwargs)))
    if jfingerex >0:
        chip.add(dxf.rectangle(vadd(centerPos,rotate_2d((-jfingerex,0),#rotate about center
                                                        math.radians(JANGLE1))), jfingerex-jfingerw/2, jfingerw, rotation = JANGLE1,
                               valign=const.MIDDLE,layer=JLAYER,bgcolor=bgcolor,**kwargStrip(kwargs)))
    chip.add(dxf.rectangle(vadd(centerPos,rotate_2d((max(jfingerw/2,-jfingerex),0),#rotate about center
                                                    math.radians(JANGLE1))), min(jfingerl-jfingerex-jfingerw/2,jfingerl), jfingerw, rotation = JANGLE1,
                           valign=const.MIDDLE,layer=JLAYER,bgcolor=bgcolor,**kwargStrip(kwargs)))
    
    # -------------------- junction leads --------------------    
    if left_top:
        # j finger stems from top of left lead
        chip.add(SolidPline(centerPos, points=[
            rotate_2d((-separation/2+jpadOverhang,
                       -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
            rotate_2d(((jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2,
                       -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
            rotate_2d((jfingerl-jfingerex,jfingerw/2),math.radians(JANGLE1)),
            rotate_2d((jfingerl-jfingerex,-jfingerw/2),math.radians(JANGLE1)),
            rotate_2d((-separation/2+jpadOverhang,
                       -(jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2),math.radians(struct().direction))
            ],bgcolor=bgcolor,layer=JLAYER))
        if jpadTaper > 0:
            chip.add(SolidPline(centerPos, points=[
                rotate_2d((-separation/2+jpadOverhang-jpadTaper,jpadh/2),math.radians(struct().direction)),
                rotate_2d((-separation/2+jpadOverhang-jpadTaper,-jpadh/2),math.radians(struct().direction)),
                rotate_2d((-separation/2+jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(rot)-leadw-jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                rotate_2d((-separation/2+jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2),math.radians(struct().direction))
                ],bgcolor=bgcolor,layer=JLAYER))
    else:
        # j finger stems from bottom of left lead
        chip.add(SolidPline(centerPos, points=[
            rotate_2d((-separation/2+jpadOverhang,
                       (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
            rotate_2d((jfingerl-jfingerex,jfingerw/2),math.radians(JANGLE2)),
            rotate_2d((jfingerl-jfingerex,-jfingerw/2),math.radians(JANGLE2)),
            rotate_2d(((jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2,
                       (jfingerl-jfingerex)*math.cos(rot)+leadw+jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
            rotate_2d((-separation/2+jpadOverhang,
                       (jfingerl-jfingerex)*math.cos(rot)+leadw+jfingerw*math.sin(rot)/2),math.radians(struct().direction))
            ],bgcolor=bgcolor,layer=JLAYER))
        if jpadTaper > 0:
            chip.add(SolidPline(centerPos, points=[
                rotate_2d((-separation/2+jpadOverhang-jpadTaper,jpadh/2),math.radians(struct().direction)),
                rotate_2d((-separation/2+jpadOverhang-jpadTaper,-jpadh/2),math.radians(struct().direction)),
                rotate_2d((-separation/2+jpadOverhang,
                       (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                rotate_2d((-separation/2+jpadOverhang,
                       (jfingerl-jfingerex)*math.cos(rot)+leadw+jfingerw*math.sin(rot)/2),math.radians(struct().direction))
                ],bgcolor=bgcolor,layer=JLAYER))
    
    if right_top:
        # j finger stems from top of right lead
        if not right_switch:
            # JANGLE1 is our finger
            chip.add(SolidPline(centerPos, points=[
                rotate_2d((separation/2-jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(rot)-leadw+jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                rotate_2d(((jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2,
                           -(jfingerl-jfingerex)*math.sin(rot)-leadw+jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                rotate_2d((jfingerl-jfingerex,-jfingerw/2),math.radians(JANGLE1)),
                rotate_2d((jfingerl-jfingerex,jfingerw/2),math.radians(JANGLE1)),
                rotate_2d((separation/2-jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2),math.radians(struct().direction))
                ],bgcolor=bgcolor,layer=JLAYER))
            if jpadTaper > 0:
                chip.add(SolidPline(centerPos, points=[
                    rotate_2d((separation/2-jpadOverhang+jpadTaper,jpadh/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang+jpadTaper,-jpadh/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(rot)-leadw+jfingerw*math.cos(rot)/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang,
                           -(jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2),math.radians(struct().direction))
                    ],bgcolor=bgcolor,layer=JLAYER))
        else:
            # JANGLE2 is our finger
            chip.add(SolidPline(centerPos, points=[
                rotate_2d((separation/2-jpadOverhang,
                           (jfingerl-jfingerex)*math.cos(rot)-leadw+jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                rotate_2d(((jfingerl-jfingerex)*math.sin(rot)+jfingerw*math.cos(rot)/2,
                           (jfingerl-jfingerex)*math.cos(rot)-leadw+jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                rotate_2d((jfingerl-jfingerex,-jfingerw/2),math.radians(JANGLE2)),
                rotate_2d((jfingerl-jfingerex,jfingerw/2),math.radians(JANGLE2)),
                rotate_2d((separation/2-jpadOverhang,
                           (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2),math.radians(struct().direction))
                ],bgcolor=bgcolor,layer=JLAYER))
            if jpadTaper > 0:
                chip.add(SolidPline(centerPos, points=[
                    rotate_2d((separation/2-jpadOverhang+jpadTaper,jpadh/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang+jpadTaper,-jpadh/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang,
                           (jfingerl-jfingerex)*math.cos(rot)-leadw+jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                    rotate_2d((separation/2-jpadOverhang,
                           (jfingerl-jfingerex)*math.cos(rot)+jfingerw*math.sin(rot)/2),math.radians(struct().direction))
                    ],bgcolor=bgcolor,layer=JLAYER))
    else:
        # j finger stems from bottom of right lead
        # JANGLE2 is our finger
        chip.add(SolidPline(centerPos, points=[
            rotate_2d((separation/2-jpadOverhang,
                       (jfingerl-jfingerex)*math.cos(rot)+leadw-jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
            rotate_2d(((jfingerl-jfingerex)*math.sin(rot)-jfingerw*math.cos(rot)/2,
                       (jfingerl-jfingerex)*math.cos(rot)+leadw-jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
            rotate_2d((jfingerl-jfingerex,jfingerw/2),math.radians(JANGLE2)),
            rotate_2d((jfingerl-jfingerex,-jfingerw/2),math.radians(JANGLE2)),
            rotate_2d((separation/2-jpadOverhang,
                       (jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2),math.radians(struct().direction))
            ],bgcolor=bgcolor,layer=JLAYER))
        if jpadTaper > 0:
            chip.add(SolidPline(centerPos, points=[
                rotate_2d((separation/2-jpadOverhang+jpadTaper,jpadh/2),math.radians(struct().direction)),
                rotate_2d((separation/2-jpadOverhang+jpadTaper,-jpadh/2),math.radians(struct().direction)),
                rotate_2d((separation/2-jpadOverhang,
                   (jfingerl-jfingerex)*math.cos(rot)-jfingerw*math.sin(rot)/2),math.radians(struct().direction)),
                rotate_2d((separation/2-jpadOverhang,
                   (jfingerl-jfingerex)*math.cos(rot)+leadw-jfingerw*math.sin(rot)/2),math.radians(struct().direction))
                ],bgcolor=bgcolor,layer=JLAYER))

def manhattan_squid_curvy(chip,structure,pad=7,jsep=20,leadw=13,palmw=2,palml=6,bridgew=0.7,fingerw=0.2,finger2w=0.25,fingerl=0.8,fingerextra=0.8,undercut=0.6,ULAYER=None,ptDensity=20):
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,structure)
        else:
            return chip.structure(structure)
        
    JLAYER = chip.wafer.JLAYER
    if ULAYER is None:
        ULAYER = chip.wafer.ULAYER
    
    r_out = leadw/2
    struct().defaults['w']=pad
    struct().defaults['r_out']=r_out
    s1 = struct().cloneAlong(distance = -jsep/2-max(r_out,pad))
    s2 = struct().cloneAlong(distance = jsep/2+max(r_out,pad),newDirection=180)
    
    
    #pads
    for sign,s in zip([-1,1],[s1,s2]):
        CPW_stub_round(chip, s.cloneAlong(distance=-undercut), w=leadw,s=undercut,ptDensity=ptDensity+2,flipped=True,layer=ULAYER)
        Strip_stub_open(chip, s, w=leadw,length=pad,r_out=r_out,flipped=True,layer=JLAYER,ptDensity=ptDensity)
        #some math
        r_miter = (palmw-math.sqrt(2)*leadw/2)/(math.sqrt(2)-2)
        jsep_padding = jsep/2-(r_miter+leadw/2)/2-(fingerl+palml+palmw/2)/math.sqrt(2)#if this is negative, problem!
        
        CPW_straight(chip,s.cloneAlong(distance=-(pad-r_out)),pad-r_out+jsep_padding,w=leadw,s=undercut,layer=ULAYER)
        if jsep_padding>0:
            Strip_straight(chip, s, jsep_padding, w=leadw,layer=JLAYER)
        
        chip.add(MiterJoint(s.start,height=leadw/2,w1=palmw,valign=const.TOP,rotation=s.direction,layer=JLAYER,ptDensity=2*ptDensity))
        chip.add(MiterJoint(s.start,height=leadw/2,w1=palmw,valign=const.TOP,vflip=True,rotation=s.direction,layer=JLAYER,ptDensity=2*ptDensity))
        #undercut for joints
        
        chip.add(CurveRect(s.getPos((0,-leadw/2)),height=undercut,radius=r_miter,angle=45,ptDensity=2*ptDensity,valign=const.TOP,ralign=const.TOP,layer=ULAYER,rotation=s.direction))
        chip.add(CurveRect(s.getPos((0,leadw/2)),height=undercut,radius=r_miter,angle=45,ptDensity=2*ptDensity,vflip=True,valign=const.TOP,ralign=const.TOP,layer=ULAYER,rotation=s.direction))
        s_l = s.cloneAlong(distance=(leadw/2+r_miter)/math.sqrt(2),angle=sign*45,newDirection=sign*45)
        s_r = s.cloneAlong(distance=(leadw/2+r_miter)/math.sqrt(2),angle=-sign*45,newDirection=-sign*45)
        chip.add(CurveRect(s_l.getPos((0,-sign*palmw/2)),height=undercut,radius=r_miter,angle=45,ptDensity=2*ptDensity,hflip=True,vflip=sign<0,valign=const.TOP,ralign=const.TOP,layer=ULAYER,rotation=s_l.direction))
        chip.add(CurveRect(s_r.getPos((0,sign*palmw/2)),height=undercut,radius=r_miter,angle=45,ptDensity=2*ptDensity,hflip=True,vflip=sign>0,valign=const.TOP,ralign=const.TOP,layer=ULAYER,rotation=s_r.direction))
        #tapers
        CPW_taper(chip,s_l.clone(),length=palml,w0=palmw,s0=undercut,s1=0,w1=fingerw,offset=(0,-sign*(palmw-fingerw)/2),layer=ULAYER)
        CPW_taper(chip,s_r.clone(),length=palml,w0=palmw,s0=undercut,s1=0,w1=finger2w,offset=(0,sign*(palmw-finger2w)/2),layer=ULAYER)
        Strip_taper(chip, s_l, w0=palmw,length=palml,w1=fingerw,offset=(0,-sign*(palmw-fingerw)/2),layer=JLAYER)
        Strip_taper(chip, s_r, w0=palmw,length=palml,w1=finger2w,offset=(0,sign*(palmw-finger2w)/2),layer=JLAYER)
        #jfingers
        if sign > 0:
            Strip_straight(chip, s_l, fingerl+fingerw+fingerextra, w=fingerw,layer=JLAYER)
            Strip_straight(chip, s_r, fingerl+finger2w+fingerextra, w=finger2w,layer=JLAYER)
        else:
            Strip_straight(chip, s_l, fingerl, w=fingerw,layer=JLAYER)
            Strip_straight(chip, s_r, fingerl, w=finger2w,layer=JLAYER)
            s_l.shiftPos(fingerw)
            s_r.shiftPos(finger2w)
            Strip_straight(chip, s_l, fingerextra, w=fingerw,layer=JLAYER)
            Strip_straight(chip, s_r, fingerextra, w=finger2w,layer=JLAYER)
        Strip_straight(chip, s_l, undercut, w=2*fingerw,layer=ULAYER)
        Strip_straight(chip, s_r, undercut, w=2*finger2w,layer=ULAYER)

def DolanJunction(
    chip, structure, junctionl, jfingerw=0.5, rotation=0,
    jarmw=3, jpadw=15, jpadl=20, jpadr=0,jpadoverhang=5, # dimensions for contact tab overlap
    jfingerl=1.36,jtaperl=2-1.36-0.140,jgap=0.140, # fixed for LL
    backward=False, # if True, draw so points toward current structure location
    JANGLE=None, JLAYER=None,ULAYER=None,bgcolor=None,lincolnLabs=False,**kwargs):
    # centered such that taper starts at current position
    # junctionl is the gap distance we wish to cover

    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,structure)
        else:
            return chip.structure(structure)

    #get layers from wafer
    if JLAYER is None:
        try:
            JLAYER = chip.wafer.JLAYER
        except AttributeError:
            setupJunctionLayers(chip.wafer)
            JLAYER = chip.wafer.JLAYER
    if ULAYER is None:
        try:
            ULAYER = chip.wafer.ULAYER
        except AttributeError:
            setupJunctionLayers(chip.wafer)
            ULAYER = chip.wafer.ULAYER

    if JANGLE is None:
        try:
            JANGLE = chip.wafer.JANGLES[0] % 360
        except AttributeError:
            setupJunctionAngles(chip.wafer, [struct().direction])
            JANGLE = chip.wafer.JANGLES[0] % 360
    # assert chip.wafer.JANGLES[0] % 180 == struct().direction % 180, 'Need Dolan junction to be in same direction as JANGLE'

    if lincolnLabs and not (0.1 < jfingerw < 3): print('WARNING: fingerw out of range. Recommended 0.150 < jfingerw < 3')

    # Junction layer
    struct().direction += rotation
    if backward: struct().direction += 180
    struct().shiftPos(-junctionl/2-jpadw+jpadoverhang)
    Strip_pad(chip, struct(), jpadw, w=jpadl, r_out=jpadr,layer=JLAYER) # contact pad
    Strip_straight(chip, struct(), length=junctionl/2-jtaperl-jpadoverhang, w=jarmw, layer=JLAYER)
    if lincolnLabs: ucstruct = struct().clone() 
    Strip_taper(chip, struct(), length=jtaperl, w0=jarmw, w1=jfingerw, layer=JLAYER)
    Strip_straight(chip, struct(), length=jfingerl, w=jfingerw, layer=JLAYER)

    if lincolnLabs:
        struct().shiftPos(jgap) # gap
    else:
        Strip_straight(chip, struct(), length=jgap, w=max(jarmw,jfingerw), layer=ULAYER)

    Strip_straight(chip, struct(), length=junctionl/2-jgap-jfingerl-jpadoverhang, w=jarmw, layer=JLAYER)
    Strip_pad(chip, struct(), jpadw, w=jpadl, r_out=jpadr, layer=JLAYER) # contact pad

    # Undercut layer
    if lincolnLabs:
        Strip_taper(chip, ucstruct, length=jtaperl, w0=jarmw, w1=jfingerw, layer=ULAYER)
        Strip_straight(chip, ucstruct, length=jfingerl+jgap, w=jfingerw, layer=ULAYER)



