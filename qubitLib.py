#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 14:48:45 2020

@author: sasha
"""
import numpy as np
import maskLib.MaskLib as m
from dxfwrite import DXFEngine as dxf
from dxfwrite import const
from dxfwrite.vector2d import midpoint, vadd, vsub, distance

#import maskLib.junctionLib as j
from maskLib.Entities import RoundRect, InsideCurve, CurveRect
from maskLib.microwaveLib import CPW_stub_open, CPW_round_pad, CPW_straight, Strip_straight, Strip_bend, Strip_taper, CPW_launcher, CPW_taper, Strip_stub_open, Strip_stub_short, Strip_pad
from maskLib.junctionLib import DolanJunction, JContact_tab, ManhattanJunction, JcalcTabDims, JContact_slot, JContact_tab, JSingleProbePad, JProbePads

from maskLib.utilities import kwargStrip



# ===============================================================================
# global functions to setup global variables in an arbitrary wafer object
# ===============================================================================

def setupXORlayer(wafer,XLAYER='XOR',xcolor=6):
    '''
    >>>>>>>>>>>>>>> Deprecated! Use wafer.setupXORlayer instead <<<<<<<<<<<<<<<<<<
    Sets a layer for XOR operations on all other layers. 
    OUT = ( LAYER1 or LAYER2 ... or LAYERN ) xor XLAYER 
    '''
    wafer.XLAYER=XLAYER
    wafer.addLayer(XLAYER, xcolor)

# ===============================================================================
# 3D transmon qubit functions (composite entities)
# ===============================================================================

qubit_defaults= {'sharp_jContactTab':{'r_out':0,'r_ins':0,'taboffs':3,'gapl':0,'tabl':0,'gapw':3,'tabw':2},
                 'sharp_junction':{'jpadr':0}}

def TransmonPad(chip,pos,padwidth=250,padheight=None,padradius=25,tab=False,tabShoulder = False,tabShoulderWidth=30,tabShoulderLength=80,tabShoulderRadius=None,flipped=False,rotation=0,bgcolor=None,**kwargs):
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



def Transmon3D(chip,pos,rotation=0,bgcolor=None,padh=200,padh2=200,padw=3000,padw2=3000,
               taperw=0,taperw2=0,leadw=85,leadw2=85,leadh=20,leadh2=20,separation=20,
               r_out=0.75,r_ins=0.75,taboffs=-0.05,steml=1.5,gapl=1.5,tabl=2,stemw=3,gapw=3,tabw=0.5,
               jpadTaper=10,jpadw=25,jpadh=16,jpadSeparation=28,jfingerl=4.5,jfingerex=1.5,jleadw=1,
               junctionClass=ManhattanJunction,**kwargs):
    '''
    Generates transmon paddles with a manhattan junction at the center. 
    Junction and contact tab parameters are monkey patched to Junction function through kwargs.
    
    padh, padh2: left,right transmon pad height
    padw, padw2: left,right  transmon pad width (or length)
    taperw, taperw2: left,right taper length from pad to lead
    leadw, leadw2: left,right lead width
    leadh, leadh2: left,right lead height
    separation: separation between leads (where junction goes)

    '''
    thisStructure = None
    if isinstance(pos,tuple):
        thisStructure = m.Structure(chip,start=pos,direction=rotation)
        
    def struct():
        if isinstance(pos,m.Structure):
            return pos
        elif isinstance(pos,tuple):
            return thisStructure
        else:
            return chip.structure(pos)
     
    if bgcolor is None: #color for junction, not undercut
        bgcolor = chip.wafer.bg()
    
    j_struct = struct().start
        
    #start where the junction is, move left to where left pad starts
    struct().shiftPos(-separation/2-leadw-padw)
    JSingleProbePad(chip,struct(),padwidth=padw,padheight=padh,tabShoulder=True,tabShoulderWidth=leadh,tabShoulderLength=leadw,flipped=False,padradius=None,
                      r_out=r_out,r_ins=r_ins,taboffs=taboffs,gapl=gapl,tabl=tabl,gapw=gapw,tabw=tabw,absoluteDimensions=True,**kwargs)
    struct().shiftPos(separation)
    JSingleProbePad(chip,struct(),padwidth=padw2,padheight=padh2,tabShoulder=True,tabShoulderWidth=leadh2,tabShoulderLength=leadw2,flipped=True,padradius=None,
                      r_out=r_out,r_ins=r_ins,taboffs=taboffs,gapl=gapl,tabl=tabl,gapw=gapw,tabw=tabw,absoluteDimensions=True,**kwargs)
                    #r_out=0,r_ins=0,taboffs=3,gapl=0,tabl=0,gapw=gapw,tabw=2,absoluteDimensions=True,**kwargs)
    
    #write the junction
    junctionClass(chip, j_struct,rotation=struct().direction,jpadTaper=jpadTaper,jpadw=jpadw,jpadh=jpadh,separation=jpadSeparation+jpadTaper,jfingerl=jfingerl,jfingerex=jfingerex,leadw=jleadw,**kwargs)
    
    

# ===============================================================================
# Planar (2D) qubit functions (composite entities)
# ===============================================================================

def Hamburgermon(chip,pos,rotation=0,
                   qwidth=1120,qheight=795,qr_out=200, minQbunToGnd=100,
                   qbunwidth=960,qbunthick=0,qbunr=60,qbunseparation=69.3751,
                   qccap_padw=40,qccap_padl=170,qccap_padr_out=10,qccap_padr_ins=4.5,qccap_gap=30,
                   qccapl=210,qccapw=0,qccapr_ins=30,qccapr_out=15,
                   qccap_steml=70,qccap_stemw=None,
                   XLAYER=None,bgcolor=None,**kwargs):
    '''
    Generates a hamburger shaped qubit. Needs XOR layers to define base metal layer. 
    Junction and contact tab parameters are monkey patched to Junction function through kwargs.
    '''
    thisStructure = None
    if isinstance(pos,tuple):
        thisStructure = m.Structure(chip,start=pos,direction=rotation)
        
    def struct():
        if isinstance(pos,m.Structure):
            return pos
        elif isinstance(pos,tuple):
            return thisStructure
        else:
            return chip.structure(pos)
        
    if bgcolor is None: #color for junction, not undercut
        bgcolor = chip.wafer.bg()
    
    #get layers from wafer
    if XLAYER is None:
        try:
            XLAYER = chip.wafer.XLAYER
        except AttributeError:
            chip.wafer.setupXORlayer()
            XLAYER = chip.wafer.XLAYER
            
    if qccap_stemw is None:
        try:
            qccap_stemw = struct().defaults['w']
        except KeyError:
            print('\x1b[33mw not defined in ',chip.chipID,'!\x1b[0m')
            qccap_stemw = 6
    
    #increase thicknesses if radii are too large
    qccapw = max(qccapw,2*qccapr_out)
    qbunthick = max(qbunthick,2*qbunr)
    qccap_padw = max(qccap_padw,2*qccap_padr_out)
    qccap_padl = max(qccap_padl,2*qccap_padr_out)
    
    #increase qubit width and height if buns are too close to ground
    qwidth = max(qwidth,qbunwidth+2*minQbunToGnd)
    qheight = max(qheight,max(qccap_steml+qccap_padl,qccap_gap+qccapl)+2*max(2*qbunr,qbunthick)+qbunseparation+minQbunToGnd)
    
    #cache junction position and figure out if we're using structures or not
    jxpos = qccap_steml+qccap_padl+qccap_gap+qbunthick+qbunseparation/2
    if thisStructure is not None:
        #not using structures
        struct().shiftPos(-jxpos)
    centerPos = struct().getPos((jxpos,0))
    
    #hole in basemetal (negative)
    chip.add(RoundRect(struct().start,qheight,qwidth,qr_out,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor,**kwargs))
    
    #xor defined qubit (positive)
    if qccap_padr_ins >0 and qccap_stemw+2*qccap_padr_ins < qccap_padw - 2*qccap_padr_out:
        chip.add(InsideCurve(struct().getPos((qccap_steml,qccap_stemw/2)),qccap_padr_ins,vflip=True,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
        chip.add(InsideCurve(struct().getPos((qccap_steml,-qccap_stemw/2)),qccap_padr_ins,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
        
    chip.add(dxf.rectangle(struct().start,qccap_steml,qccap_stemw,valign=const.MIDDLE,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargStrip(kwargs)))
    chip.add(RoundRect(struct().getPos((qccap_steml,0)),qccap_padl,qccap_padw,qccap_padr_out,valign=const.MIDDLE,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
    
    if qccapr_ins > 0:
        chip.add(InsideCurve(struct().getPos((jxpos-qbunseparation/2-qbunthick,qccap_padw/2+qccap_gap)),qccapr_ins,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
        chip.add(InsideCurve(struct().getPos((jxpos-qbunseparation/2-qbunthick,qccap_padw/2+qccap_gap+qccapw)),qccapr_ins,vflip=True,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
        
        chip.add(InsideCurve(struct().getPos((jxpos-qbunseparation/2-qbunthick,-qccap_padw/2-qccap_gap)),qccapr_ins,vflip=True,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
        chip.add(InsideCurve(struct().getPos((jxpos-qbunseparation/2-qbunthick,-qccap_padw/2-qccap_gap-qccapw)),qccapr_ins,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
        
    chip.add(RoundRect(struct().getPos((jxpos-qbunseparation/2-qbunthick,qccap_padw/2+qccap_gap)),qccapl,qccapw,qccapr_out,roundCorners=[1,0,0,1],halign=const.RIGHT,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
    chip.add(RoundRect(struct().getPos((jxpos-qbunseparation/2-qbunthick,-qccap_padw/2-qccap_gap)),qccapl,qccapw,qccapr_out,roundCorners=[1,0,0,1],halign=const.RIGHT,vflip=True,rotation=struct().direction,layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs))
    
    JProbePads(chip, centerPos,rotation=struct().direction,padwidth=qbunthick,padheight=qbunwidth,padradius=qbunr,separation=qbunseparation,
                 layer=XLAYER,bgcolor=chip.bg(XLAYER),**kwargs)
    
    ManhattanJunction(chip, centerPos, rotation=struct().direction,separation=qbunseparation, **kwargs)
    
    return centerPos,struct().direction
    
def Elephantmon(
    chip, structure, rotation=0, totalw=0, totall=0,
    tpad_width=200, tpad_height=300, tpad_gap_gnd=50,
    tpad_gap=100, rpad=10, **kwargs):

    """
    Generates an Elephantmon, which is similar to the Hamburgermon but does NOT use
    an XOR layer and uses a Dolan junction. Additional params can be passed to
    junctions used kwargs.
    If totalw, totall are specified to be non-zero, tpad_width and tpad_height are
        re-calculated based on tpad_gap and tpad_gap_gnd.
    """
    s = structure.clone()
    s.direction += rotation

    if totalw > 0:
        tpad_width = totalw-2*tpad_gap_gnd
    if totall > 0:
        tpad_height = (totall-2*tpad_gap_gnd-tpad_gap)/2
    

    s.shiftPos(tpad_width/2+tpad_gap_gnd)

    s_right = s.clone()
    s_right.direction += 90
    CPW_stub_open(chip, s_right, tpad_gap/2, r_ins=rpad, w=tpad_width, s=tpad_gap_gnd, flipped=True, **kwargs)
    JContact_tab(chip, s_right, **kwargs)

    s_right = s.cloneAlongLast()
    s_right.shiftPos(tpad_gap_gnd/2)
    s_right.direction += 90
    s_right.shiftPos(tpad_gap/2)
    Strip_straight(chip, s_right, length=tpad_height-rpad, w=tpad_gap_gnd, **kwargs)
    Strip_bend(chip, s_right, CCW=True, w=tpad_gap_gnd, radius=rpad+tpad_gap_gnd/2, **kwargs)
    Strip_straight(chip, s_right, length=tpad_width-2*rpad, w=tpad_gap_gnd, **kwargs)
    Strip_bend(chip, s_right, CCW=True, w=tpad_gap_gnd, radius=rpad+tpad_gap_gnd/2, **kwargs)
    Strip_straight(chip, s_right, length=tpad_height-rpad, w=tpad_gap_gnd, **kwargs)

    s_left = s.clone()
    s_left.direction -= 90
    CPW_stub_open(chip, s_left, tpad_gap/2, r_ins=rpad, w=tpad_width, s=tpad_gap_gnd, flipped=True, **kwargs)
    JContact_tab(chip, s_left, **kwargs)

    s_left = s.cloneAlongLast()
    s_left.shiftPos(tpad_gap_gnd/2)
    s_left.direction -= 90
    s_left.shiftPos(tpad_gap/2)
    Strip_straight(chip, s_left, length=tpad_height-rpad, w=tpad_gap_gnd, **kwargs)
    Strip_bend(chip, s_left, CCW=False, w=tpad_gap_gnd, radius=rpad+tpad_gap_gnd/2, **kwargs)
    Strip_straight(chip, s_left, length=tpad_width-2*rpad, w=tpad_gap_gnd, **kwargs)
    Strip_bend(chip, s_left, CCW=False, w=tpad_gap_gnd, radius=rpad+tpad_gap_gnd/2, **kwargs)
    Strip_straight(chip, s_left, length=tpad_height-rpad, w=tpad_gap_gnd, **kwargs)

    s.direction -= 90
    DolanJunction(chip, s, junctionl=tpad_gap, **kwargs)

def Xmon(
    chip, structure, rotation=0,
    xmonw=25, xmonl=150, xmon_gapw=20, xmon_gapl=30,
    r_out=None, r_ins=None, r_arm5=None,
    jj_loc=6, jj_reverse=False, junctionClass=ManhattanJunction,**kwargs):

    """
    Generates an Xmon (does NOT use an XOR layer) with a junction method specified by junctionClass.
    Additional params can be passed to junctions used kwargs.
    jj_loc in [0, 11] decides the location on the cross to place the junction:
        end of every arm and midway along every arm, counting clockwise
        from the start.
    xmonw, xmonl, xmon_gapw, and xmon_gapl can be either number or array. If array, uses those values
        for the corresponding arm (indexed clockwise 0 starting from the bottom arm)
    By default, draws the junction pointing toward ground. If jj_reverse, draws pointing toward
        pad at the specified location.
    """
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,structure)
        else:
            return chip.structure(structure)
    if r_out is None:
        try:
            r_out = struct().defaults['r_out']
        except KeyError:
            print('\x1b[33mr_out not defined in ',chip.chipID,'!\x1b[0m')
            r_out=0
    if r_ins is None:
        try:
            r_ins = struct().defaults['r_ins']
        except KeyError:
            #print('r_ins not defined in ',chip.chipID,'!\x1b[0m')
            r_ins=0
    
    if np.isscalar(xmonl): xmonl = [xmonl]*4
    if np.isscalar(xmonw): xmonw = [xmonw]*4
    if np.isscalar(xmon_gapl): xmon_gapl = [xmon_gapl]*4
    if np.isscalar(xmon_gapw): xmon_gapw = [xmon_gapw]*4

    for i in range(4):
        right = (i+1)%4
        left = (i-1)%4
        across = (i+2)%4
        min_length = max(xmonw[right]/2+xmon_gapw[right], xmonw[left]/2+xmon_gapw[left])
        if xmonl[i] < min_length:
            xmonl[i] = min_length
            xmon_gapw[i] = xmonw[across] + xmonw[across]/2
            xmonw[i] = 0
            xmon_gapl[i] = 0
    assert len(xmonl) == len(xmonw) == len(xmon_gapw) == len(xmon_gapl)

    add_arm = False
    if len(xmonl) == 5:
        add_arm = True
        # Add arm capability is very limited in cases where gap widths are not all equal

    s_start = struct().clone()
    s = struct().cloneAlong(distance=xmon_gapl[0]+xmonl[0], newDirection=rotation) # start in center of X
    s_jj_locs = [None]*12
    s_jj_ls = [0]*12

    center_to_start_arm_ud = max(xmonw[1]/2+xmon_gapw[1], xmonw[3]/2+xmon_gapw[3])
    center_to_start_arm_lr = max(xmonw[0]/2+xmon_gapw[0], xmonw[2]/2+xmon_gapw[2])

    cur = 2
    l = (cur-1)%4
    r = (cur+1)%4
    s_up = s.cloneAlong(newDirection=0)
    # fill left corner
    s_temp = s_up.cloneAlong(vector=(xmonw[l]/2, center_to_start_arm_lr/2+xmonw[cur]/4))
    Strip_straight(chip, s_temp, length=xmon_gapw[l], w=center_to_start_arm_lr-xmonw[cur]/2, **kwargs)
    s_temp = s_up.cloneAlong(vector=(xmonw[l]/2+xmon_gapw[l], (xmon_gapw[cur]+xmonw[cur])/2))
    Strip_straight(chip, s_temp, length=center_to_start_arm_ud-(xmonw[l]/2+xmon_gapw[l]), w=xmon_gapw[cur], **kwargs)
    # fill right corner
    center_to_start_arm = center_to_start_arm_lr
    if add_arm: center_to_start_arm += xmonw[4]/np.sqrt(2)
    s_temp = s_up.cloneAlong(vector=(xmonw[r]/2, -(center_to_start_arm/2+xmonw[cur]/4)))
    Strip_straight(chip, s_temp, length=xmon_gapw[r], w=center_to_start_arm-xmonw[cur]/2, **kwargs)
    s_temp = s_up.cloneAlong(vector=(xmonw[r]/2+xmon_gapw[r], -(xmon_gapw[cur]+xmonw[cur])/2))
    Strip_straight(chip, s_temp, length=center_to_start_arm_ud-(xmonw[r]/2+xmon_gapw[r]), w=xmon_gapw[cur], **kwargs)

    s_up.shiftPos(center_to_start_arm_ud)
    if xmonl[cur]-center_to_start_arm_ud > 0 and xmon_gapl[cur] > 0:
        CPW_straight(chip, s_up, length=xmonl[cur]-center_to_start_arm_ud, w=xmonw[cur], s=xmon_gapw[cur], **kwargs)
        CPW_stub_open(chip, s_up, length=xmon_gapl[cur], r_out=r_out, r_ins=r_ins, w=xmonw[cur], s=xmon_gapw[cur], **kwargs)
        s_jj_locs[6] = s_up.cloneAlongLast()
        s_jj_locs[5] = s_up.cloneAlongLast(vector=(-(xmonl[cur]-center_to_start_arm_ud)/2, xmonw[cur]/2), newDirection=90)
        s_jj_locs[7] = s_up.cloneAlongLast(vector=(-(xmonl[cur]-center_to_start_arm_ud)/2, -xmonw[cur]/2), newDirection=-90)
        s_jj_ls[6] = xmon_gapl[cur]
        s_jj_ls[5] = s_jj_ls[7] = xmon_gapw[cur]
    else:
        s_jj_locs[6] = s.cloneAlong(vector=(max(xmonw[l]/2, xmonw[r]/2), 0), newDirection=s_up.direction-s.direction)
        s_jj_ls[6] = max(xmon_gapw[l], xmon_gapw[r])

    cur = 0
    l = (cur-1)%4
    r = (cur+1)%4
    s_down = s.cloneAlong(newDirection=180)
    # fill left corner
    if not add_arm:
        s_temp = s_down.cloneAlong(vector=(xmonw[l]/2, center_to_start_arm_lr/2+xmonw[cur]/4))
        Strip_straight(chip, s_temp, length=xmon_gapw[l], w=center_to_start_arm_lr-xmonw[cur]/2, **kwargs)
        s_temp = s_down.cloneAlong(vector=(xmonw[l]/2+xmon_gapw[l], (xmon_gapw[cur]+xmonw[cur])/2))
        Strip_straight(chip, s_temp, length=center_to_start_arm_ud-(xmonw[l]/2+xmon_gapw[l]), w=xmon_gapw[cur], **kwargs)
    else: # add 5th arm
        assert xmon_gapw[l] == xmon_gapw[cur], 'Currently unsupported'
        s_temp = s_down.cloneAlong(vector=(xmonw[l]/2, xmonw[cur]/2), newDirection=45)
        s_temp.shiftPos(xmonw[4]/2 + xmon_gapw[cur]/np.sqrt(2))

        s_temp.shiftPos(xmon_gapw[cur]/np.sqrt(2) + xmon_gapw[4])
        s_temp_temp = s_temp.cloneAlong(newDirection=180)
        CPW_taper(chip, s_temp_temp, length=xmon_gapw[4], w0=xmonw[4], s0=xmon_gapw[4], w1=xmonw[4], s1=0, **kwargs)

        # inner rounded triangles
        if r_arm5 == None:
            r_arm5 = xmon_gapw[l]/4
        s_temp_l = s_temp_temp.cloneAlong(newDirection=-90)
        s_temp_l.shiftPos(xmonw[4]/2)
        s_temp_l.direction += 45
        s_temp_l = s_temp_l.cloneAlong(vector=(xmon_gapw[l]-r_arm5,0), newDirection=135)
        sub_tri_height = xmon_gapw[l]-r_arm5
        Strip_taper(chip, s_temp_l, length=(sub_tri_height)/np.sqrt(2), w0=0, w1=sub_tri_height*np.sqrt(2), **kwargs)
        s_temp_l = s_temp_l.cloneAlongLast(newDirection=-45)
        s_temp_l = s_temp_l.cloneAlongLast(vector=(0,-r_arm5/2))
        Strip_straight(chip, s_temp_l, sub_tri_height-r_arm5, w=r_arm5, **kwargs)
        s_temp_l = s_temp_l.cloneAlong(vector=(0,r_arm5/2), newDirection=-45)
        chip.add(CurveRect(s_temp_l.getPos(), height=r_arm5, radius=r_arm5, ralign=const.TOP,angle=90,rotation=0, **kwargs))

        s_temp_r = s_temp_temp.cloneAlong(newDirection=90)
        s_temp_r.shiftPos(xmonw[4]/2)
        s_temp_r.direction -= 45
        s_temp_r = s_temp_r.cloneAlong(vector=(xmon_gapw[cur]-r_arm5,0), newDirection=-135)
        sub_tri_height = xmon_gapw[cur]-r_arm5
        Strip_taper(chip, s_temp_r, length=(sub_tri_height)/np.sqrt(2), w0=0, w1=sub_tri_height*np.sqrt(2), **kwargs)
        s_temp_r = s_temp_r.cloneAlongLast(newDirection=45)
        s_temp_r = s_temp_r.cloneAlongLast(vector=(0,r_arm5/2))
        Strip_straight(chip, s_temp_r, sub_tri_height-r_arm5, w=r_arm5, **kwargs)
        s_temp_r = s_temp_r.cloneAlong(vector=(0,-r_arm5/2), newDirection=45)
        chip.add(CurveRect(s_temp_r.getPos(), height=r_arm5, radius=r_arm5, ralign=const.TOP, angle=90, rotation=0, **kwargs))

        # fill in outer triangles
        s_temp_r = s_temp.cloneAlong(vector=(0,-xmonw[4]/2-xmon_gapw[4]))
        chip.add(InsideCurve(s_temp_r.getPos(), height=r_arm5, radius=r_arm5, ralign=const.TOP, angle=45, rotation=0, **kwargs))
        s_temp_l = s_temp.cloneAlong(vector=(0,xmonw[4]/2+xmon_gapw[4]))
        chip.add(InsideCurve(s_temp_l.getPos(), height=r_arm5, radius=r_arm5, ralign=const.TOP, angle=45, rotation=45, **kwargs))

        # fill in actual arm of arm
        CPW_straight(chip, s_temp, length=xmonl[4]-distance(s_temp.getPos(), s.getPos()), w=xmonw[4], s=xmon_gapw[4], **kwargs)
        CPW_stub_open(chip, s_temp, length=xmon_gapl[4], r_out=r_out, r_ins=r_ins, w=xmonw[4], s=xmon_gapw[4], **kwargs)

        # fill in the leftover corners that would have been filled in here if there was no arm
        s_temp = s_down.cloneAlong(vector=(xmonw[l]/2+xmon_gapw[l]+xmonw[4]/np.sqrt(2), (xmon_gapw[cur]+xmonw[cur])/2))
        Strip_straight(chip, s_temp, length=center_to_start_arm_ud-(xmonw[l]/2+xmon_gapw[l]), w=xmon_gapw[cur], **kwargs)

    # fill right corner
    center_to_start_arm = center_to_start_arm_ud
    if add_arm: center_to_start_arm += xmonw[4]/np.sqrt(2)
    s_temp = s_down.cloneAlong(vector=(xmonw[r]/2, -(center_to_start_arm_lr/2+xmonw[cur]/4)))
    Strip_straight(chip, s_temp, length=xmon_gapw[r], w=center_to_start_arm_lr-xmonw[cur]/2, **kwargs)
    s_temp = s_down.cloneAlong(vector=(xmonw[r]/2+xmon_gapw[r], -(xmon_gapw[cur]+xmonw[cur])/2))
    Strip_straight(chip, s_temp, length=center_to_start_arm-(xmonw[r]/2+xmon_gapw[r]), w=xmon_gapw[cur], **kwargs)

    s_down.shiftPos(center_to_start_arm)
    if xmonl[cur]-center_to_start_arm > 0 and xmon_gapl[cur] > 0:
        CPW_straight(chip, s_down, length=xmonl[cur]-center_to_start_arm, w=xmonw[cur], s=xmon_gapw[cur], **kwargs)
        CPW_stub_open(chip, s_down, length=xmon_gapl[cur], r_out=r_out, r_ins=r_ins, w=xmonw[cur], s=xmon_gapw[cur], **kwargs)
        s_jj_locs[0] = s_down.cloneAlongLast()
        s_jj_locs[11] = s_down.cloneAlongLast(vector=(-(xmonl[cur]-center_to_start_arm)/2, xmonw[cur]/2), newDirection=90)
        s_jj_locs[1] = s_down.cloneAlongLast(vector=(-(xmonl[cur]-center_to_start_arm)/2, -xmonw[cur]/2), newDirection=-90)
        s_jj_ls[0] = xmon_gapl[cur]
        s_jj_ls[1] = s_jj_ls[11] = xmon_gapw[cur]
    else:
        s_jj_locs[0] = s.cloneAlong(vector=(-max(xmonw[l]/2, xmonw[r]/2), 0), newDirection=s_down.direction-s.direction)
        s_jj_ls[0] = max(xmon_gapw[l], xmon_gapw[r])

    cur = 1
    l = (cur-1)%4
    r = (cur+1)%4
    s_left = s.cloneAlong(newDirection=90)
    s_left.shiftPos(center_to_start_arm_lr)
    if xmonl[cur]-center_to_start_arm_lr > 0 and xmon_gapl[cur] > 0:
        CPW_straight(chip, s_left, length=xmonl[cur]-center_to_start_arm_lr, w=xmonw[cur], s=xmon_gapw[cur], **kwargs)
        CPW_stub_open(chip, s_left, length=xmon_gapl[cur], r_out=r_out, r_ins=r_ins, w=xmonw[cur], s=xmon_gapw[cur], **kwargs)
        s_jj_locs[3] = s_left.cloneAlongLast()
        s_jj_locs[2] = s_left.cloneAlongLast(vector=(-(xmonl[cur]-center_to_start_arm_lr)/2, xmonw[cur]/2), newDirection=90)
        s_jj_locs[4] = s_left.cloneAlongLast(vector=(-(xmonl[cur]-center_to_start_arm_lr)/2, -xmonw[cur]/2), newDirection=-90)
        s_jj_ls[3] = xmon_gapl[cur]
        s_jj_ls[2] = s_jj_ls[4] = xmon_gapw[cur]
    else:
        s_jj_locs[3] = s.cloneAlong(vector=(0, max(xmonw[l]/2, xmonw[r]/2)), newDirection=s_left.direction-s.direction)
        s_jj_ls[3] = max(xmon_gapw[l], xmon_gapw[r])

    cur = 3
    l = (cur-1)%4
    r = (cur+1)%4
    s_right = s.cloneAlong(newDirection=-90)
    center_to_start_arm = center_to_start_arm_lr
    if add_arm: center_to_start_arm += xmonw[4]/np.sqrt(2)
    s_right.shiftPos(center_to_start_arm)
    if xmonl[cur]-center_to_start_arm > 0 and xmon_gapl[cur] > 0:
        CPW_straight(chip, s_right, length=xmonl[cur]-center_to_start_arm, w=xmonw[cur], s=xmon_gapw[cur], **kwargs)
        CPW_stub_open(chip, s_right, length=xmon_gapl[cur], r_out=r_out, r_ins=r_ins, w=xmonw[cur], s=xmon_gapw[cur], **kwargs)
        s_jj_locs[9] = s_right.cloneAlongLast()
        s_jj_locs[8] = s_right.cloneAlongLast(vector=(-(xmonl[cur]-center_to_start_arm)/2, xmonw[cur]/2), newDirection=90)
        s_jj_locs[10] = s_right.cloneAlongLast(vector=(-(xmonl[cur]-center_to_start_arm)/2, -xmonw[cur]/2), newDirection=-90)
        s_jj_ls[9] = xmon_gapl[cur]
        s_jj_ls[8] = s_jj_ls[10] = xmon_gapw[cur]
    else:
        s_jj_locs[9] = s.cloneAlong(vector=(0, -max(xmonw[l]/2, xmonw[r]/2)), newDirection=s_right.direction-s.direction)
        s_jj_ls[8] = max(xmon_gapw[l], xmon_gapw[r])

    for i in range(len(s_jj_locs)): # Lincoln labs requires placing junctions on 5x5 nm grid
        s_jj = s_jj_locs[jj_loc]
        s_jj.updatePos(np.around(s_jj.getPos(), 2))

    s_jj = s_jj_locs[jj_loc]
    junctionl = s_jj_ls[jj_loc]
    JContact_tab(chip, s_jj.cloneAlong(newDirection=180), **kwargs)
    #keep junction method general
    junctionClass(chip,s_jj.cloneAlong(distance=junctionl/2), junctionl=junctionl, backward=jj_reverse, separation=junctionl,**kwargs)
    JContact_tab(chip, s_jj.cloneAlong(distance=junctionl), **kwargs)

    struct().updatePos(s_start.getPos()) # initial starting position
    return s # center of xmon

def XmonGeneral(chip,structure,q_height,r_qubit=None,w_qubit=None,s_qubit=None,
         jsep=None,secondlayer='XOR',taperw=50,leadw=8,junction_method=None,**kwargs):
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,structure)
        else:
            return chip.structure(structure)
    if w_qubit is None:
        try:
            w_qubit = struct().defaults['w']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    if s_qubit is None:
        try:
            s_qubit = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    if r_qubit is None:
        try:
            r_qubit = struct().defaults['r_ins']
        except KeyError:
            print('\x1b[33mr_ins not defined in ',chip.chipID,'!\x1b[0m')
            r_qubit=0
    if jsep is None:
        jsep = s_qubit/2
        
    #since length is the length of each arm,
    #define q_height as length from end to end of qubit ground plane slot
    #q_height=length*2+s_qubit*2
    length = q_height/2 - s_qubit
        
    chip.add(RoundRect(struct().start,q_height, w_qubit+2*s_qubit, r_qubit+s_qubit,rotation=struct().direction,valign=const.MIDDLE),struct(),q_height)
    #left and right arms
    sr=struct().cloneAlongLast((q_height/2,w_qubit/2+s_qubit),newDirection=90)
    sl=struct().cloneAlongLast((q_height/2,-w_qubit/2-s_qubit),newDirection=-90)
    
    Strip_stub_short(chip,sr,r_ins=r_qubit,w=w_qubit+2*s_qubit,flipped=True)
    Strip_stub_short(chip,sl,r_ins=r_qubit,w=w_qubit+2*s_qubit,flipped=True)
    chip.add(RoundRect(sr.start,q_height/2-w_qubit/2-s_qubit, w_qubit+2*s_qubit, r_qubit+s_qubit,roundCorners=[0,1,1,0],rotation=sr.direction,valign=const.MIDDLE))
    chip.add(RoundRect(sl.start,q_height/2-w_qubit/2-s_qubit, w_qubit+2*s_qubit, r_qubit+s_qubit,roundCorners=[0,1,1,0],rotation=sl.direction,valign=const.MIDDLE))
    sr.shiftPos(-s_qubit)
    sl.shiftPos(-s_qubit)
    #second layer
    Strip_stub_short(chip,sr,r_ins=r_qubit+s_qubit,w=w_qubit,flipped=True,layer=secondlayer)
    Strip_stub_short(chip,sl,r_ins=r_qubit+s_qubit,w=w_qubit,flipped=True,layer=secondlayer)
    chip.add(RoundRect(sr.start,q_height/2-w_qubit/2-s_qubit, w_qubit, r_qubit,roundCorners=[0,1,1,0],rotation=sr.direction,valign=const.MIDDLE,layer=secondlayer))
    chip.add(RoundRect(sl.start,q_height/2-w_qubit/2-s_qubit, w_qubit, r_qubit,roundCorners=[0,1,1,0],rotation=sl.direction,valign=const.MIDDLE,layer=secondlayer))
    
    
    struct().shiftPos(-q_height+s_qubit)
    Strip_pad(chip, struct(), q_height-2*s_qubit, w=w_qubit, r_out=r_qubit,layer=secondlayer)
    
    tablength,tabhwidth = JcalcTabDims(chip,struct().start,tabw=0.2,tabl=0.2,r_out=0.5,taboffs=-0.05,r_ins=0.5,gapw=0.8,ptDensity=20) 
    
    #Strip_taper(chip,struct(),s_qubit/2-jsep/2,w0=taperw,w1=leadw,layer=secondlayer)
    Strip_straight(chip, struct(), s_qubit/2-jsep/2-tablength, w=2*tabhwidth,layer=secondlayer)
    JContact_slot(chip,struct(),tabw=0.2,tabl=0.2,r_out=0.5,taboffs=-0.05,r_ins=0.5,gapw=0.8,ptDensity=20,layer=secondlayer,hflip=True)
    struct().shiftPos(-(s_qubit/2-jsep/2))
    CPW_taper(chip,struct(),s_qubit/2-jsep/2,w0=2*tabhwidth,w1=2*tabhwidth,s0=taperw/2-tabhwidth,s1=max(leadw/2-tabhwidth,0.001),layer=secondlayer)
    
    struct().shiftPos(jsep)
    #Strip_taper(chip,struct(),s_qubit/2-jsep/2,w0=leadw,w1=taperw,layer=secondlayer)
    CPW_taper(chip,struct(),s_qubit/2-jsep/2,w1=2*tabhwidth,w0=2*tabhwidth,s1=taperw/2-tabhwidth,s0=max(leadw/2-tabhwidth,0.001),layer=secondlayer)
    struct().shiftPos(-(s_qubit/2-jsep/2))
    JContact_slot(chip,struct(),tabw=0.2,tabl=0.2,r_out=0.5,taboffs=-0.05,r_ins=0.5,gapw=0.8,ptDensity=20,layer=secondlayer,hflip=False)
    Strip_straight(chip, struct(), s_qubit/2-jsep/2-tablength, w=2*tabhwidth,layer=secondlayer)
    struct().shiftPos(-s_qubit/2)
    if junction_method is not None:
        junction_method(chip,m.Structure(chip,start=struct().start,direction=chip.wafer.JANGLES[0],defaults=struct().defaults),jsep=jsep,leadw=leadw,**kwargs)
    
def CloverQubit(chip,structure,jsep=None,w_qubit=None,s_qubit=None,w_bridge=None,r_bridge=None,w_taper=6,l_taper=None,r_taper=None,ralign=const.BOTTOM,stem_l=None,q_sep=6,bgcolor=None,debug=False,junction_method=None,**kwargs):
    '''
    Draws a resonator shaped like a 4leaf clover. 
    jsep: inductor length (jsep)
    w_qubit: equivalent to the fillet radius of inner metal
    s_qubit: gap to ground
    w_bridge: overrides overall width of inductor bridge (must satisfy 2*r_bridge+w_taper <= w_bridge)
    r_bridge: overrides flare-out radius of inductor bridge (must satisfy 2*r_bridge + 2*l_taper+jsep <= s_qubit)
    w_taper: width of wide section of inductor
    l_taper: set to a length to override inductor-bridge contact rounding with a taper function (must satisfy 2*l_taper+jsep <= s_qubit)
    r_taper: overrides the inductor-bridge contact rounding radius (must satisfy 2*r_taper+w_ind <= w_taper && 2*r_taper+jsep <= s_qubit)
    '''
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        elif isinstance(structure,tuple):
            return m.Structure(chip,structure)
        else:
            return chip.structure(structure)
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    if w_qubit is None:
        try:
            w_qubit = struct().defaults['w']
        except KeyError:
            print('\x1b[33mw not defined in ',chip.chipID,'!\x1b[0m')
    if s_qubit is None:
        try:
            s_qubit = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ',chip.chipID,'!\x1b[0m')
    if jsep is None:
        jsep = s_qubit/2
    #assign manual inputs but override dumb inputs       
    jsep = min(s_qubit,jsep)
    if l_taper is not None and 2*l_taper + jsep <= s_qubit:
        r_taper = 0 #don't round the contact
    else:
        #set l_taper manually, and round the contact
        l_taper = max(min((s_qubit-jsep)/2.0,w_taper/2),0)#default to w_taper/2
        if r_taper is None: r_taper = l_taper #default to l_taper
        r_taper = max(min(r_taper,l_taper,(w_taper)/2.0),0)
    
    if w_bridge is not None and w_bridge >= w_taper:
        #w_bridge specified, constrain r_bridge
        if r_bridge is None: r_bridge = (s_qubit-jsep-2*l_taper)/2.0 #default to max space
        r_bridge = max(min(r_bridge,(s_qubit-jsep-2*l_taper)/2.0,(w_bridge-w_taper)/2.0),0)
    else:
        #w_bridge not specified.
        r_bridge = max((s_qubit-jsep-2*l_taper)/2.0,0)
        w_bridge = w_taper+2*r_bridge
    
    #internal variables
    r_0 = w_qubit/2 + s_qubit/2
    
    
    if isinstance(ralign,int):
        #by default the radius is defined as the inner radius
        if ralign == const.MIDDLE:
            dr = 0
        elif ralign == const.TOP: #anchored at TOP
            dr = -s_qubit/2.
        else:  # const.BOTTOM (anchored at BOTTOM)
            dr = s_qubit/2.
    else:
        dr = s_qubit*(ralign-0.5)
    
    #effective radii 
    r_ins=r_0-dr
    r_out=r_0+dr
    
    #print(2*(2*r_0 - r_out + w_bridge)-2*q_sep-2*10,2*r_ins+w_bridge,r_0,r_out,r_ins)
    
    #coupler pad
    CPW_round_pad(chip, struct(), pad_length=stem_l,pad_width=2*(r_ins-s_qubit/2)+w_bridge-2*q_sep,align_outer=True)
    struct().shiftPos(q_sep+s_qubit/2)
    #define sub-structures
    s_r = struct().cloneAlong((0,w_bridge/2),newDirection=90,defaults={'w':s_qubit})
    s_l = struct().cloneAlong((0,-w_bridge/2),newDirection=-90,defaults={'w':s_qubit})
    
    #debug
    if debug:
        chip.add(dxf.rectangle(struct().getPos(distance=dr), 2*r_0, 2*r_0+w_bridge,valign=const.MIDDLE,rotation=struct().direction,layer='FRAME'))
    
    #draw center, left right arms
    chip.add(dxf.rectangle(struct().start, s_qubit, w_bridge,valign=const.MIDDLE,halign=const.CENTER,rotation=struct().direction,bgcolor=bgcolor,**kwargStrip(kwargs)))
    
    Strip_bend(chip, s_r,CCW=False,radius=r_ins,bgcolor=bgcolor,**kwargStrip(kwargs))
    Strip_bend(chip, s_r,CCW=True,angle=270,radius=r_out,bgcolor=bgcolor,**kwargStrip(kwargs))
    Strip_bend(chip, s_r,CCW=False,angle=180,radius=r_ins,bgcolor=bgcolor,**kwargStrip(kwargs))
    Strip_bend(chip, s_r,CCW=True,angle=270,radius=r_out,bgcolor=bgcolor,**kwargStrip(kwargs))
    Strip_bend(chip, s_r,CCW=False,angle=90,radius=r_ins,bgcolor=bgcolor,**kwargStrip(kwargs))
    
    Strip_bend(chip, s_l,CCW=True,radius=r_ins,bgcolor=bgcolor,**kwargStrip(kwargs))
    Strip_bend(chip, s_l,CCW=False,angle=270,radius=r_out,bgcolor=bgcolor,**kwargStrip(kwargs))
    Strip_bend(chip, s_l,CCW=True,angle=180,radius=r_ins,bgcolor=bgcolor,**kwargStrip(kwargs))
    Strip_bend(chip, s_l,CCW=False,angle=270,radius=r_out,bgcolor=bgcolor,**kwargStrip(kwargs))
    Strip_bend(chip, s_l,CCW=True,angle=90,radius=r_ins,bgcolor=bgcolor,**kwargStrip(kwargs))
    
    if r_bridge >0:
        Strip_taper(chip,s_l,r_bridge,w1=jsep)
        Strip_taper(chip,s_r,r_bridge,w1=jsep)
        #Strip_stub_open(chip,s_r,r_out=r_bridge)
        #Strip_stub_open(chip,s_l,r_out=r_bridge)

    Strip_straight(chip,s_r,(w_taper)/2.,w=jsep,**kwargs)
    Strip_straight(chip,s_l,(w_taper)/2.,w=jsep,**kwargs)
    
    j_pos = s_l.start
    s_l.translatePos((0,-jsep/2),newDir=90)
    s_r.translatePos((0,-jsep/2),newDir=-90)
    JContact_tab(chip,s_l,tabw=0.2,tabl=0.2,r_out=0.5,taboffs=0.0,r_ins=0.5,stemw=0.8,steml=0,ptDensity=20)
    JContact_tab(chip,s_r,tabw=0.2,tabl=0.2,r_out=0.5,taboffs=0.0,r_ins=0.5,stemw=0.8,steml=0,ptDensity=20)
    
    if junction_method is not None:
        junction_method(chip,m.Structure(chip,start=j_pos,direction=chip.wafer.JANGLES[0],defaults=struct().defaults),jsep=jsep,**kwargs)
    
    