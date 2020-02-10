# -*- coding: utf-8 -*-
"""
Created on Fri Oct  4 17:29:02 2019

@author: Sasha

Library for drawing standard microwave components (CPW parts, inductors, capacitors etc)
"""

import maskLib.MaskLib as m
from dxfwrite import DXFEngine as dxf
from dxfwrite import const
from dxfwrite.entities import Polyline
from dxfwrite.vector2d import vadd, vsub, vector2angle, magnitude, distance
from dxfwrite.algebra import rotate_2d

from maskLib.Entities import SolidPline, SkewRect, CurveRect, InsideCurve

from copy import deepcopy
from matplotlib.path import Path
from matplotlib.transforms import Bbox
import math

# ===============================================================================
# perforate the ground plane with a grid of squares, which avoid any polylines 
# ===============================================================================

def waffle(chip, grid_x, grid_y=None,width=10,height=None,exclude=None,padx=0,pady=None,bleedRadius=1,layer='0'):
    radius = max(int(bleedRadius),0)
    
    if exclude is None:
        exclude = ['FRAME']
    else:
        exclude.append('FRAME')
        
    if grid_y is None:
        grid_y = grid_x
    
    if height is None:
        height = width
        
    if pady is None:
        pady=padx
        
    nx, ny = list(map(int, [(chip.width) / grid_x, (chip.height) / grid_y]))
    occupied = [[False]*ny for i in range(nx)]
    for i in range(nx):
        occupied[i][0] = True
        occupied[i][-1] = True
    for i in range(ny):
        occupied[0][i] = True
        occupied[-1][i] = True
    
    for e in chip.chipBlock.get_data():
        if isinstance(e.__dxftags__()[0], Polyline):
            if e.layer not in exclude:
                o_x_list = []
                o_y_list = []
                plinePts = [v.__getitem__('location').__getitem__('xy') for v in e.__dxftags__()[0].get_data()]
                plinePts.append(plinePts[0])
                for p in plinePts:
                    o_x, o_y = list(map(int, (p[0] / grid_x, p[1] / grid_y)))
                    if 0 <= o_x < nx and 0 <= o_y < ny:
                        o_x_list.append(o_x)
                        o_y_list.append(o_y)
                        
                        #this will however ignore a rectangle with corners outside the chip...
                if o_x_list:
                    path = Path([[pt[0]/grid_x,pt[1]/grid_y] for pt in plinePts],closed=True)
                    for x in range(min(o_x_list)-1, max(o_x_list)+2):
                        for y in range(min(o_y_list)-1, max(o_y_list)+2):
                            try:
                                if path.contains_point([x+.5,y+.5]):
                                    occupied[x][y]=True
                                elif path.intersects_bbox(Bbox.from_bounds(x,y,1.,1.),filled=True):
                                    occupied[x][y]=True
                            except IndexError:
                                pass
       

    second_pass = deepcopy(occupied)
    for r in range(radius):
        for i in range(nx):
            for j in range(ny):
                if occupied[i][j]:
                    for ip, jp in [(i+1,j), (i-1,j), (i,j+1), (i,j-1)]:
                        try:
                            second_pass[ip][jp] = True
                        except IndexError:
                            pass
        second_pass = deepcopy(second_pass)
   
    for i in range(int(padx/grid_x),nx-int(padx/grid_x)):
        for j in range(int(pady/grid_y),ny-int(pady/grid_y)):
            if not second_pass[i][j]:
                pos = i*grid_x + grid_x/2., j*grid_y + grid_y/2.
                chip.add(dxf.rectangle(pos,width,height,bgcolor=chip.wafer.bg(),halign=const.CENTER,valign=const.MIDDLE,layer=layer) )   

# ===============================================================================
# basic NEGATIVE CPW function definitions
# ===============================================================================


def CPW_straight(chip,structure,length,w=None,s=None,bgcolor=None): #note: uses CPW conventions
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('w not defined in ',chip.chipID,'!')
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('s not defined in ',chip.chipID,'!')
            
    chip.add(dxf.rectangle(struct().getPos((0,-w/2)),length,-s,rotation=struct().direction,bgcolor=bgcolor))
    chip.add(dxf.rectangle(struct().getPos((0,w/2)),length,s,rotation=struct().direction,bgcolor=bgcolor),structure=structure,length=length)
        
    
def CPW_taper(chip,structure,length=None,w0=None,s0=None,w1=None,s1=None,bgcolor=None): #note: uses CPW conventions
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    if w0 is None:
        try:
            w0 = struct().defaults['w']
        except KeyError:
            print('w not defined in ',chip.chipID,'!')
    if s0 is None:
        try:
            s0 = struct().defaults['s']
        except KeyError:
            print('s not defined in ',chip.chipID,'!')
    if w1 is None:
        try:
            w1 = struct().defaults['w']
        except KeyError:
            print('w not defined in ',chip.chipID,'!')
    if s1 is None:
        try:
            s1 = struct().defaults['s']
        except KeyError:
            print('s not defined in ',chip.chipID,'!')
    #if undefined, make outer angle 30 degrees
    if length is None:
        length = math.sqrt(3)*abs(w0/2+s0-w1/2-s1)
    
    chip.add(SkewRect(struct().getPos((0,-w0/2)),length,s0,(0,w0/2-w1/2),s1,rotation=struct().direction,valign=const.TOP,edgeAlign=const.TOP,bgcolor=bgcolor))
    chip.add(SkewRect(struct().getPos((0,w0/2)),length,s0,(0,w1/2-w0/2),s1,rotation=struct().direction,valign=const.BOTTOM,edgeAlign=const.BOTTOM,bgcolor=bgcolor),structure=structure,length=length)
    
def CPW_stub_short(chip,structure,flipped=False,curve_ins=True,curve_out=True,r_out=None,w=None,s=None,bgcolor=None):
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('w not defined in ',chip.chipID,'!')
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('s not defined in ',chip.chipID,'!')
    if r_out is None:
        try:
            r_out = min(struct().defaults['r_out'],s/2)
        except KeyError:
            print('r_out not defined in ',chip.chipID,'!')
            r_out=0
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    
    
    if r_out > 0:
        
        dx = 0.
        if flipped:
            dx = min(s/2,r_out)
        
        l=min(s/2,r_out)
        
        if l<s/2:
            chip.add(dxf.rectangle(struct().getPos((dx,w/2+l)),l,s-2*l,halign=flipped and const.RIGHT or const.LEFT,valign=const.TOP,rotation=struct().direction,bgcolor=bgcolor))
            chip.add(dxf.rectangle(struct().getPos((dx,-w/2-l)),l,s-2*l,halign=flipped and const.RIGHT or const.LEFT,valign=const.BOTTOM,rotation=struct().direction,bgcolor=bgcolor))
        if curve_out:
            chip.add(CurveRect(struct().getPos((dx,w/2+s-l)),l,r_out,ralign=const.TOP,rotation=struct().direction,hflip=flipped,bgcolor=bgcolor))
            chip.add(CurveRect(struct().getPos((dx,-w/2-s+l)),l,r_out,ralign=const.TOP,rotation=struct().direction,hflip=flipped,vflip=True,bgcolor=bgcolor))
        else:
            chip.add(dxf.rectangle(struct().getPos((dx,w/2+s-l)),l,l,halign=flipped and const.RIGHT or const.LEFT,valign=const.TOP,rotation=struct().direction,bgcolor=bgcolor))
            chip.add(dxf.rectangle(struct().getPos((dx,-w/2-s+l)),l,l,halign=flipped and const.RIGHT or const.LEFT,valign=const.BOTTOM,rotation=struct().direction,bgcolor=bgcolor))
        if curve_ins:
            chip.add(CurveRect(struct().getPos((dx,w/2+l)),l,r_out,ralign=const.TOP,rotation=struct().direction,hflip=flipped,vflip=True,bgcolor=bgcolor))
            chip.add(CurveRect(struct().getPos((dx,-w/2-l)),l,r_out,ralign=const.TOP,rotation=struct().direction,hflip=flipped,bgcolor=bgcolor),structure=structure,length=l)
        else:
            chip.add(dxf.rectangle(struct().getPos((dx,w/2+l)),l,l,halign=flipped and const.RIGHT or const.LEFT,valign=const.BOTTOM,rotation=struct().direction,bgcolor=bgcolor))
            chip.add(dxf.rectangle(struct().getPos((dx,-w/2-l)),l,l,halign=flipped and const.RIGHT or const.LEFT,valign=const.TOP,rotation=struct().direction,bgcolor=bgcolor),structure=structure,length=l)

    else:
        CPW_straight(chip,structure,s/2,w=w,s=s,bgcolor=bgcolor)
        
def CPW_stub_open(chip,structure,r_out=None,r_ins=None,w=None,s=None,flipped=False,bgcolor=None):
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('w not defined ',chip.chipID)
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('s not defined ',chip.chipID)
    if r_out is None:
        try:
            r_out = struct().defaults['r_out']
        except KeyError:
            print('r_out not defined in ',chip.chipID,'!')
            r_out=0
    if r_ins is None:
        try:
            r_ins = struct().defaults['r_ins']
        except KeyError:
            print('r_ins not defined in ',chip.chipID,'!')
            r_ins=0
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    
    dx = 0.
    if flipped:
        dx = s

    if r_ins > 0:
        chip.add(InsideCurve(struct().getPos((dx,w/2)),r_ins,rotation=struct().direction,hflip=flipped,bgcolor=bgcolor))
        chip.add(InsideCurve(struct().getPos((dx,-w/2)),r_ins,rotation=struct().direction,hflip=flipped,vflip=True,bgcolor=bgcolor))
    if r_out >0:
        chip.add(CurveRect(struct().getPos((dx,w/2)),s,r_out,ralign=const.TOP,rotation=struct().direction,hflip=flipped,bgcolor=bgcolor))
        chip.add(dxf.rectangle(struct().getPos((dx,0)),flipped and -s or s,w,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor))
        chip.add(CurveRect(struct().getPos((dx,-w/2)),s,r_out,ralign=const.TOP,rotation=struct().direction,hflip=flipped,vflip=True,bgcolor=bgcolor),structure=structure,length=s)
    else:
        chip.add(dxf.rectangle(struct().start,s,w+2*s,valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor),structure=structure,length=s)
        
def CPW_stub_round(chip,structure,w=None,s=None,round_left=True,round_right=True,flipped=False,bgcolor=None):
    #same as stub_open, but preserves gap width along turn (so radii are defined by w, s)
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('w not defined ',chip.chipID)
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('s not defined ',chip.chipID)
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    
    dx = 0.
    if flipped:
        dx = s+w/2

    if False:#round_left and round_right:
        chip.add(CurveRect(struct().getPos((dx,w/2)),s,w/2,angle=180,ralign=const.BOTTOM,rotation=struct().direction,hflip=flipped,bgcolor=bgcolor),structure=structure,length=s+w/2)
    else:
        if round_left:
            chip.add(CurveRect(struct().getPos((dx,w/2)),s,w/2,angle=90,ralign=const.BOTTOM,rotation=struct().direction,hflip=flipped,bgcolor=bgcolor))
        else:
            chip.add(dxf.rectangle(struct().getPos((0,w/2)),s+w/2,s,rotation=struct().direction,bgcolor=bgcolor))
            chip.add(InsideCurve(struct().getPos((flipped and s or w/2,w/2)),w/2,rotation=struct().direction,hflip=flipped,bgcolor=bgcolor))
            chip.add(dxf.rectangle(struct().getPos((s+w/2-dx,w/2)),-s,-w/2,rotation=struct().direction,halign = flipped and const.RIGHT or const.LEFT, bgcolor=bgcolor))
        if round_right:
            chip.add(CurveRect(struct().getPos((dx,-w/2)),s,w/2,angle=90,ralign=const.BOTTOM,rotation=struct().direction,hflip=flipped,vflip=True,bgcolor=bgcolor),structure=structure,length=s+w/2)
        else:
            chip.add(dxf.rectangle(struct().getPos((0,-w/2)),s+w/2,-s,rotation=struct().direction,bgcolor=bgcolor))
            chip.add(InsideCurve(struct().getPos((flipped and s or w/2,-w/2)),w/2,rotation=struct().direction,hflip=flipped,vflip=True,bgcolor=bgcolor))
            chip.add(dxf.rectangle(struct().getPos((s+w/2-dx,-w/2)),-s,w/2,rotation=struct().direction,halign = flipped and const.RIGHT or const.LEFT, bgcolor=bgcolor),structure=structure,length=s+w/2)
    
def CPW_bend(chip,structure,angle=90,CCW=True,w=None,s=None,radius=None,ptDensity=120,bgcolor=None):
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('w not defined ',chip.chipID)
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('s not defined ',chip.chipID)
    if radius is None:
        try:
            radius = struct().defaults['radius']
        except KeyError:
            print('radius not defined in ',chip.chipID,'!')
            return
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
        
    while angle < 0:
        angle = angle + 360
    angle = angle%360
        
    chip.add(CurveRect(struct().start,s,radius,angle=angle,ptDensity=ptDensity,roffset=w/2,ralign=const.BOTTOM,rotation=struct().direction,vflip=not CCW,bgcolor=bgcolor))
    chip.add(CurveRect(struct().start,s,radius,angle=angle,ptDensity=ptDensity,roffset=-w/2,ralign=const.TOP,valign=const.TOP,rotation=struct().direction,vflip=not CCW,bgcolor=bgcolor))
    struct().updatePos(newStart=struct().getPos((radius*math.sin(math.radians(angle)),(CCW and 1 or -1)*radius*(math.cos(math.radians(angle))-1))),angle=CCW and -angle or angle)

def Wire_bend(chip,structure,angle=90,CCW=True,w=None,radius=None,bgcolor=None):
    #only defined for 90 degree bends
    if angle%90 != 0:
        return
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('w not defined ',chip.chipID)
    if radius is None:
        try:
            radius = struct().defaults['radius']
        except KeyError:
            print('radius not defined in ',chip.chipID,'!')
            return
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
        
    while angle < 0:
        angle = angle + 360
    angle = angle%360
        
    if radius-w/2 > 0:
        chip.add(CurveRect(struct().start,radius-w/2,radius,angle=angle,roffset=-w/2,ralign=const.TOP,valign=const.TOP,rotation=struct().direction,vflip=not CCW,bgcolor=bgcolor))
    for i in range(angle//90):
        chip.add(InsideCurve(struct().getPos(vadd(rotate_2d((radius+w/2,(CCW and 1 or -1)*(radius+w/2)),(CCW and -1 or 1)*math.radians(i*90)),(0,CCW and -radius or radius))),radius+w/2,rotation=struct().direction+(CCW and -1 or 1)*i*90,bgcolor=bgcolor,vflip=not CCW))
    struct().updatePos(newStart=struct().getPos((radius*math.sin(math.radians(angle)),(CCW and 1 or -1)*radius*(math.cos(math.radians(angle))-1))),angle=CCW and -angle or angle)

# ===============================================================================
# composite CPW function definitions
# ===============================================================================

def CPW_launcher(chip,struct,offset=0,length=None,padw=300,pads=160,w=None,s=None,r_ins=0,r_out=0,bgcolor=None):
    CPW_stub_open(chip,struct,r_out=r_out,r_ins=r_ins,w=padw,s=pads,flipped=True)
    CPW_straight(chip,struct,padw,w=padw,s=pads)
    CPW_taper(chip,struct,w0=padw,s0=pads)

def CPW_wiggles(chip,structure,length=None,nTurns=None,minWidth=None,maxWidth=None,CCW=True,start_bend = True,stop_bend=True,w=None,s=None,radius=None,bgcolor=None):
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if radius is None:
        try:
            radius = struct().defaults['radius']
        except KeyError:
            print('radius not defined in ',chip.chipID,'!')
            return
    #prevent dumb entries
    if nTurns is None:
        nTurns = 1
    elif nTurns < 1:
        nTurns = 1
    #is length constrained?
    if length is not None:
        if nTurns is None:
            nTurns = 1
        h = (length - (((start_bend+stop_bend)/2+2*nTurns)*math.pi - 2))/(4*nTurns)
        #is width constrained?
        if maxWidth is not None:
            while h>max(maxWidth,radius):
                nTurns = nTurns+1
                h = (length - (((start_bend+stop_bend)/2+2*nTurns)*math.pi - 2))/(4*nTurns)
        
    if (length is None) or (h is None) or (nTurns is None):
        print('not enough params specified for CPW_wiggles!')
        return
    if start_bend:
        CPW_bend(chip,structure,angle=90,CCW=CCW,w=w,s=s,radius=radius,bgcolor=bgcolor)
        if h > radius:
            CPW_straight(chip,structure,h-radius,w=w,s=s,bgcolor=bgcolor)
    else:
        CPW_straight(chip,structure,h,w=w,s=s,bgcolor=bgcolor)
    CPW_bend(chip,structure,angle=180,CCW=not CCW,w=w,s=s,radius=radius,bgcolor=bgcolor)
    CPW_straight(chip,structure,h+radius,w=w,s=s,bgcolor=bgcolor)
    if h > radius:
        CPW_straight(chip,structure,h-radius,w=w,s=s,bgcolor=bgcolor)
    CPW_bend(chip,structure,angle=180,CCW=CCW,w=w,s=s,radius=radius,bgcolor=bgcolor)
    if h > radius:
        CPW_straight(chip,structure,h-radius,w=w,s=s,bgcolor=bgcolor)
    for n in range(nTurns-1):
        CPW_straight(chip,structure,h+radius,w=w,s=s,bgcolor=bgcolor)
        CPW_bend(chip,structure,angle=180,CCW=not CCW,w=w,s=s,radius=radius,bgcolor=bgcolor)
        CPW_straight(chip,structure,h+radius,w=w,s=s,bgcolor=bgcolor)
        if h > radius:
            CPW_straight(chip,structure,h-radius,w=w,s=s,bgcolor=bgcolor)
        CPW_bend(chip,structure,angle=180,CCW=CCW,w=w,s=s,radius=radius,bgcolor=bgcolor)
        if h > radius:
            CPW_straight(chip,structure,h-radius,w=w,s=s,bgcolor=bgcolor)
    if stop_bend:
        CPW_bend(chip,structure,angle=90,CCW=not CCW,w=w,s=s,radius=radius,bgcolor=bgcolor)
    else:
        CPW_straight(chip,structure,radius,w=w,s=s,bgcolor=bgcolor)

def CPW_directTo(chip,from_structure,to_structure,to_flipped=True,w=None,s=None,radius=None,CW1_override=None,CW2_override=None,flip_angle=False,debug=False):
    def struct1():
        if isinstance(from_structure,m.Structure):
            return from_structure
        else:
            return chip.structure(from_structure)
    if radius is None:
        try:
            radius = struct1().defaults['radius']
        except KeyError:
            print('radius not defined in ',chip.chipID,'!')
            return
    #struct2 is only a local copy
    struct2 = isinstance(to_structure,m.Structure) and to_structure or chip.structure(to_structure)
    if to_flipped:
        struct2.direction=(struct2.direction+180.)%360
    
    CW1 = vector2angle(struct1().getGlobalPos(struct2.start)) < 0
    CW2 = vector2angle(struct2.getGlobalPos(struct1().start)) < 0

    target1 = struct1().getPos((0,CW1 and -2*radius or 2*radius))
    target2 = struct2.getPos((0,CW2 and -2*radius or 2*radius))
    
    #reevaluate based on center positions
    
    CW1 = vector2angle(struct1().getGlobalPos(target2)) < 0
    CW2 = vector2angle(struct2.getGlobalPos(target1)) < 0
    
    if CW1_override is not None:
        CW1 = CW1_override
    if CW2_override is not None:
        CW2 = CW2_override

    center1 = struct1().getPos((0,CW1 and -radius or radius))
    center2 = struct2.getPos((0,CW2 and -radius or radius))
    
    if debug:
        chip.add(dxf.line(struct1().getPos((-3000,0)),struct1().getPos((3000,0)),layer='FRAME'))
        chip.add(dxf.line(struct2.getPos((-3000,0)),struct2.getPos((3000,0)),layer='FRAME'))
        chip.add(dxf.circle(center=center1,radius=radius,layer='FRAME'))
        chip.add(dxf.circle(center=center2,radius=radius,layer='FRAME'))
    
    correction_angle=math.asin(abs(2*radius*(CW1 - CW2)/distance(center2,center1)))
    angle1 = abs(struct1().direction - math.degrees(vector2angle(vsub(center2,center1)))) + math.degrees(correction_angle)
    if flip_angle:
        angle1 = 360-abs(struct1().direction - math.degrees(vector2angle(vsub(center2,center1)))) + math.degrees(correction_angle)
    
    if debug:
        print(CW1,CW2,angle1,math.degrees(correction_angle))
    
    if angle1 > 270:
        if debug:
            print('adjusting to shorter angle')
        angle1 = min(angle1,abs(360-angle1))
    '''
    if CW1 - CW2 == 0 and abs(angle1)>100:
        if abs((struct1().getGlobalPos(struct2.start))[1]) < 2*radius:
            print('adjusting angle')
            angle1 = angle1 + math.degrees(math.asin(abs(2*radius/distance(center2,center1))))
            '''
    CPW_bend(chip,from_structure,angle=angle1,w=w,s=s,radius=radius, CCW=CW1)
    CPW_straight(chip,from_structure,distance(center2,center1)*math.cos(correction_angle),w=w,s=s)
    
    angle2 = abs(struct1().direction-struct2.direction)
    if angle2 > 270:
        angle2 = min(angle2,abs(360-angle2))
    CPW_bend(chip,from_structure,angle=angle2,w=w,s=s,radius=radius,CCW=CW2)

def wiggle_calc(chip,structure,length=None,nTurns=None,maxWidth=None,Width=None,start_bend = True,stop_bend=True,w=None,s=None,radius=None):
    #figure out 
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if radius is None:
        try:
            radius = struct().defaults['radius']
        except KeyError:
            print('radius not defined in ',chip.chipID,'!')
            return
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('w not defined ',chip.chipID)
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('s not defined ',chip.chipID)
    #prevent dumb entries
    if nTurns is None:
        nTurns = 1
    elif nTurns < 1:
        nTurns = 1
    #is length constrained?
    if length is not None:
        if nTurns is None:
            nTurns = 1
        h = (length - (((start_bend+stop_bend)/2+2*nTurns)*math.pi - 2))/(4*nTurns)
        #is width constrained?
        if Width is not None:
            #maxWidth corresponds to the wiggle width, while Width corresponds to the total width filled
            if maxWidth is not None:
                maxWidth = min(maxWidth,Width)
            else:
                maxWidth = Width
            while h+radius+w/2>maxWidth:
                nTurns = nTurns+1
                h = (length - (((start_bend+stop_bend)/2+2*nTurns)*math.pi - 2))/(4*nTurns)
    h = max(h,radius)
    return {'nTurns':nTurns,'h':h,'length':length}

def Inductor_wiggles(chip,structure,length=None,nTurns=None,maxWidth=None,Width=None,CCW=True,start_bend = True,stop_bend=True,pad_to_width=False,w=None,s=None,radius=None,bgcolor=None):
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if radius is None:
        try:
            radius = struct().defaults['radius']
        except KeyError:
            print('radius not defined in ',chip.chipID,'!')
            return
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('w not defined ',chip.chipID)
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('s not defined ',chip.chipID)
    #prevent dumb entries
    if nTurns is None:
        nTurns = 1
    elif nTurns < 1:
        nTurns = 1
    #is length constrained?
    if length is not None:
        if nTurns is None:
            nTurns = 1
        h = (length - (((start_bend+stop_bend)/2+2*nTurns)*math.pi - 2))/(4*nTurns)
        #is width constrained?
        if Width is not None:
            #maxWidth corresponds to the wiggle width, while Width corresponds to the total width filled
            if maxWidth is not None:
                maxWidth = min(maxWidth,Width)
            else:
                maxWidth = Width
            while h+radius+w/2>maxWidth:
                nTurns = nTurns+1
                h = (length - (((start_bend+stop_bend)/2+2*nTurns)*math.pi - 2))/(4*nTurns)
    else: #length is not contrained
        h= maxWidth-radius-w/2
    if h < radius:
        print('Warning: Wiggles too tight. Adjusting length')
    h = max(h,radius)
    if (h is None) or (nTurns is None):
        print('not enough params specified for CPW_wiggles!')
        return
    pm = (CCW - 0.5)*2
    
    #put rectangles on either side to line up with max width
    if pad_to_width:
        if Width is None:
            print('ERROR: cannot pad to width with Width undefined!')
        if start_bend:
            chip.add(dxf.rectangle(struct().getPos((0,h+radius+w/2)),(2*radius)+(nTurns)*4*radius,Width-(h+radius+w/2),rotation=struct().direction,bgcolor=bgcolor))
            chip.add(dxf.rectangle(struct().getPos((0,-h-radius-w/2)),(stop_bend)*(radius+w/2)+(nTurns)*4*radius + radius-w/2,(h+radius+w/2)-Width,rotation=struct().direction,bgcolor=bgcolor))
        else:
            chip.add(dxf.rectangle(struct().getPos((-h-radius-w/2,w/2)),(h+radius+w/2)-Width,(radius-w/2)+(nTurns)*4*radius,rotation=struct().direction,bgcolor=bgcolor))
            chip.add(dxf.rectangle(struct().getPos((h+radius+w/2,-radius)),Width-(h+radius+w/2),(stop_bend)*(radius+w/2)+(nTurns)*4*radius + w/2,rotation=struct().direction,bgcolor=bgcolor))
    #begin wiggles
    if start_bend:
        chip.add(dxf.rectangle(struct().getPos((0,pm*w/2)),radius+w/2,pm*(h+radius),rotation=struct().direction,bgcolor=bgcolor))
        Wire_bend(chip,structure,angle=90,CCW=CCW,w=w,radius=radius,bgcolor=bgcolor)
        if h > radius:
            chip.add(dxf.rectangle(struct().getPos((0,-pm*w/2)),h+w/2,pm*(radius-w/2),valign=const.BOTTOM,rotation=struct().direction,bgcolor=bgcolor),structure=struct(),length=h-radius)
        else:
            chip.add(dxf.rectangle(struct().getPos((0,-pm*w/2)),radius+w/2,pm*(radius-w/2),valign=const.BOTTOM,rotation=struct().direction,bgcolor=bgcolor))
    else:
        chip.add(dxf.rectangle(struct().getPos((0,-pm*w/2)),2*radius+w/2,pm*(radius-w/2),valign=const.BOTTOM,rotation=struct().direction,bgcolor=bgcolor),structure=struct(),length=radius)
        #struct().shiftPos(h)
    chip.add(dxf.rectangle(struct().getPos((0,pm*w/2)),-h-max(h,radius)-radius-w/2,pm*(2*radius-w),rotation=struct().direction,bgcolor=bgcolor))
    Wire_bend(chip,structure,angle=180,CCW=not CCW,w=w,radius=radius,bgcolor=bgcolor)
    struct().shiftPos(h+radius)
    if h > radius:
        struct().shiftPos(h-radius)
    chip.add(dxf.rectangle(struct().getPos((0,-pm*w/2)),-h-max(h,radius)-radius-w/2,pm*(-2*radius+w),rotation=struct().direction,bgcolor=bgcolor))
    Wire_bend(chip,structure,angle=180,CCW=CCW,w=w,radius=radius,bgcolor=bgcolor)
    if h > radius:
        struct().shiftPos(h-radius)
    for n in range(nTurns-1):
        struct().shiftPos(h+radius)
        chip.add(dxf.rectangle(struct().getPos((0,pm*w/2)),-h-max(h,radius)-radius-w/2,pm*(2*radius-w),rotation=struct().direction,bgcolor=bgcolor))
        Wire_bend(chip,structure,angle=180,CCW=not CCW,w=w,radius=radius,bgcolor=bgcolor)
        struct().shiftPos(2*h)
        chip.add(dxf.rectangle(struct().getPos((0,-pm*w/2)),-h-max(h,radius)-radius-w/2,pm*(-2*radius+w),rotation=struct().direction,bgcolor=bgcolor))
        Wire_bend(chip,structure,angle=180,CCW=CCW,w=w,radius=radius,bgcolor=bgcolor)
        struct().shiftPos(h-radius)
    chip.add(dxf.rectangle(struct().getLastPos((-radius-w/2,pm*w/2)),w/2+h,pm*(radius-w/2),rotation=struct().direction,bgcolor=bgcolor),structure=struct())
    if stop_bend:
        chip.add(dxf.rectangle(struct().getPos((radius+w/2,-pm*w/2)),h+radius,pm*(radius+w/2),rotation=struct().direction,bgcolor=bgcolor))
        Wire_bend(chip,structure,angle=90,CCW=not CCW,w=w,radius=radius,bgcolor=bgcolor)
    else:
        #CPW_straight(chip,structure,radius,w=w,s=s,bgcolor=bgcolor)
        chip.add(dxf.rectangle(struct().getPos((0,pm*w/2)),radius,pm*(radius-w/2),rotation=struct().direction,bgcolor=bgcolor),structure=struct(),length=radius)

def JellyfishResonator(chip,structure,width,height,l_ind,w_cap=None,s_cap=None,r_cap=None,w_ind=3,r_ind=6,ialign=const.BOTTOM,nTurns=None,maxWidth=None,CCW=True,bgcolor=None):
    #inductor params: wire width = w_ind, radius (sets pitch) = r_ind, total inductor wire length = l_ind. ialign determines where the inductor should align to, (TOP = bunch at capacitor)
    #capacitor params: wire width = w_cap, gap to ground = s_cap, nominal horseshoe bend radius = r_cap ()
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if r_cap is None:
        try:
            r_cap = struct().defaults['radius']
        except KeyError:
            print('radius not defined in ',chip.chipID,'!')
            return
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    if w_cap is None:
        try:
            w_cap = struct().defaults['w']
        except KeyError:
            print('w not defined ',chip.chipID)
    if s_cap is None:
        try:
            s_cap = struct().defaults['s']
        except KeyError:
            print('s not defined ',chip.chipID)
    if nTurns is None:
        nTurns = wiggle_calc(chip,struct(),length=l_ind,maxWidth=maxWidth,Width=(width - 2*(w_cap+2*s_cap))/2,w=w_ind,radius=r_ind)['nTurns']
    #override dumb inputs
    r_cap=min(s_cap+w_cap/2,r_cap)

    struct().defaults['w']=w_cap
    struct().defaults['s']=s_cap
    
    #calculate extra length
    inductor_pad = height - w_cap - 3*s_cap - (nTurns+0.5)*4*r_ind
    
    #assume structure starts in correct orientation
    chip.add(dxf.rectangle(struct().start,s_cap,width - 2*(w_cap+2*s_cap),valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor))
    
    s_r = struct().cloneAlong((s_cap+w_cap/2,-width/2 + 2*s_cap+w_cap),newDirection=-90)
    
    CPW_bend(chip,s_r,CCW=False,radius=r_cap)
    CPW_straight(chip,s_r,height-3*s_cap-w_cap*3/2)
    CPW_stub_round(chip,s_r,round_right = (inductor_pad >= 0),round_left=False)
    
    s_l = struct().cloneAlong((s_cap+w_cap/2,width/2 - 2*s_cap - w_cap),newDirection=90)
    
    CPW_bend(chip,s_l,radius=r_cap)
    CPW_straight(chip,s_l,height-3*s_cap-w_cap*3/2)
    CPW_stub_round(chip,s_l,round_left = (inductor_pad >= 0),round_right=False)
    
    s_0 = struct().cloneAlong((s_cap+w_cap,0))
    s_0.defaults['w']=w_ind
    s_0.defaults['radius']=r_ind
    CPW_stub_short(chip,s_0,s=(width - 2*(w_cap+2*s_cap)-w_ind)/2,r_out=r_cap-w_cap/2,curve_out=False,flipped=True)
    
    
    if inductor_pad < -s_cap-w_cap/2:
        #print('WARNING: capacitor is not long enough to cover inductor.')
        chip.add(dxf.rectangle(s_l.start,-inductor_pad-s_cap-w_cap/2,2*s_cap+w_cap,rotation=s_r.direction,valign=const.MIDDLE,bgcolor=bgcolor),structure=s_l,length=-inductor_pad-s_cap-w_cap/2)
        chip.add(dxf.rectangle(s_r.start,-inductor_pad-s_cap-w_cap/2,2*s_cap+w_cap,rotation=s_r.direction,valign=const.MIDDLE,bgcolor=bgcolor),structure=s_r,length=-inductor_pad-s_cap-w_cap/2)
    if inductor_pad < 0:
        chip.add(dxf.rectangle(s_l.start,w_cap/2+s_cap,-s_cap-w_cap/2,rotation=s_r.direction,bgcolor=bgcolor))
        chip.add(dxf.rectangle(s_r.start,w_cap/2+s_cap,s_cap+w_cap/2,rotation=s_r.direction,bgcolor=bgcolor))
        chip.add(CurveRect(s_l.start,w_cap/2+s_cap,w_cap/2+s_cap,ralign=const.TOP,rotation=struct().direction,bgcolor=bgcolor),structure=s_l,length=s_cap+w_cap/2)
        chip.add(CurveRect(s_r.start,w_cap/2+s_cap,w_cap/2+s_cap,ralign=const.TOP,rotation=struct().direction,vflip=True,bgcolor=bgcolor),structure=s_r,length=s_cap+w_cap/2)
        inductor_pad = inductor_pad + s_cap + w_cap/2 #in case extra length from capacitor stub is too much length
    
    if inductor_pad > 0:
        if ialign is const.BOTTOM:
            CPW_straight(chip,s_0,inductor_pad,s=(width - 2*(w_cap+2*s_cap)-w_ind)/2)
        elif ialign is const.MIDDLE:
            CPW_straight(chip,s_0,inductor_pad/2,s=(width - 2*(w_cap+2*s_cap)-w_ind)/2)
    Inductor_wiggles(chip,s_0,length=l_ind,maxWidth=maxWidth,Width=(width - 2*(w_cap+2*s_cap))/2,nTurns=nTurns,pad_to_width=True,CCW=CCW,bgcolor=bgcolor)
    if inductor_pad > 0:
        if ialign is const.TOP:
            CPW_straight(chip,s_0,inductor_pad,s=(width - 2*(w_cap+2*s_cap)-w_ind)/2)
        elif ialign is const.MIDDLE:
            CPW_straight(chip,s_0,inductor_pad/2,s=(width - 2*(w_cap+2*s_cap)-w_ind)/2)
    CPW_stub_short(chip,s_0,s=(width - 2*(w_cap+2*s_cap)-w_ind)/2,r_out=r_cap-w_cap/2,curve_out=False)
    
def DoubleJellyfishResonator(chip,structure,width,height,l_ind,w_cap=None,s_cap=None,r_cap=None,w_ind=3,r_ind=6,ialign=const.BOTTOM,nTurns=None,maxWidth=None,CCW=True,bgcolor=None):
    #inductor params: wire width = w_ind, radius (sets pitch) = r_ind, total inductor wire length = l_ind. ialign determines where the inductor should align to, (TOP = bunch at capacitor)
    #capacitor params: wire width = w_cap, gap to ground = s_cap, nominal horseshoe bend radius = r_cap ()
    def struct():
        if isinstance(structure,m.Structure):
            return structure
        else:
            return chip.structure(structure)
    if r_cap is None:
        try:
            r_cap = struct().defaults['radius']
        except KeyError:
            print('radius not defined in ',chip.chipID,'!')
            return
    if bgcolor is None:
        bgcolor = chip.wafer.bg()
    if w_cap is None:
        try:
            w_cap = struct().defaults['w']
        except KeyError:
            print('w not defined ',chip.chipID)
    if s_cap is None:
        try:
            s_cap = struct().defaults['s']
        except KeyError:
            print('s not defined ',chip.chipID)
    if l_ind is not None:
        if nTurns is None:
            nTurns = wiggle_calc(chip,struct(),length=l_ind,maxWidth=maxWidth,Width=(width - 2*(w_cap+2*s_cap))/4,w=w_ind,radius=r_ind)['nTurns']
        else:
            #l_ind given, nTurns given
            nTurns = max(nTurns,wiggle_calc(chip,struct(),length=l_ind,maxWidth=maxWidth,Width=(width - 2*(w_cap+2*s_cap))/4,w=w_ind,radius=r_ind)['nTurns'])
    #override dumb inputs
    r_cap=min(s_cap+w_cap/2,r_cap)

    struct().defaults['w']=w_cap
    struct().defaults['s']=s_cap
    
    #calculate extra length
    inductor_pad = height - w_cap - 3*s_cap - (nTurns+0.5)*4*r_ind
    
    #assume structure starts in correct orientation
    chip.add(dxf.rectangle(struct().start,s_cap,width - 2*(w_cap+2*s_cap),valign=const.MIDDLE,rotation=struct().direction,bgcolor=bgcolor))
    
    s_r = struct().cloneAlong((s_cap+w_cap/2,-width/2 + 2*s_cap+w_cap),newDirection=-90)
    s_l = struct().cloneAlong((s_cap+w_cap/2,width/2 - 2*s_cap - w_cap),newDirection=90)
    
    if height-3*s_cap-w_cap*3/2 > 0:
        CPW_bend(chip,s_l,radius=r_cap)
        CPW_bend(chip,s_r,CCW=False,radius=r_cap)
        CPW_straight(chip,s_l,height-3*s_cap-w_cap*3/2)
        CPW_straight(chip,s_r,height-3*s_cap-w_cap*3/2)
    else:
        CPW_straight(chip,s_l,s_cap+w_cap/2)
        CPW_straight(chip,s_r,s_cap+w_cap/2)
    CPW_stub_round(chip,s_l,round_left = (inductor_pad > 0) or (height-3*s_cap-w_cap*3/2 < 0),round_right=False) 
    CPW_stub_round(chip,s_r,round_right = (inductor_pad > 0) or (height-3*s_cap-w_cap*3/2 < 0),round_left=False)
    
    if height-3*s_cap-w_cap*3/2 < 0:
        s_l.updatePos(newStart=s_l.getPos((-s_cap -w_cap/2,-s_cap-w_cap/2)),angle=-90)
        s_r.updatePos(newStart=s_r.getPos((-s_cap -w_cap/2,s_cap+w_cap/2)),angle=90)
    
    s_0 = struct().cloneAlong((s_cap+w_cap,(width - 2*(w_cap+2*s_cap))/4))
    s_0.defaults['w']=w_ind
    s_0.defaults['radius']=r_ind
    CPW_stub_short(chip,s_0,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4,r_out=r_cap-w_cap/2,curve_out=False,flipped=True)
    
    s_1 = struct().cloneAlong((s_cap+w_cap,-(width - 2*(w_cap+2*s_cap))/4))
    s_1.defaults['w']=w_ind
    s_1.defaults['radius']=r_ind
    CPW_stub_short(chip,s_1,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4,r_out=r_cap-w_cap/2,curve_out=False,flipped=True)
    
    if inductor_pad < -s_cap-w_cap/2:
        #print('WARNING: capacitor is not long enough to cover inductor.')
        chip.add(dxf.rectangle(s_l.start,-inductor_pad-s_cap-w_cap/2,2*s_cap+w_cap,rotation=s_l.direction,valign=const.MIDDLE,bgcolor=bgcolor),structure=s_l,length=-inductor_pad-s_cap-w_cap/2)
        chip.add(dxf.rectangle(s_r.start,-inductor_pad-s_cap-w_cap/2,2*s_cap+w_cap,rotation=s_r.direction,valign=const.MIDDLE,bgcolor=bgcolor),structure=s_r,length=-inductor_pad-s_cap-w_cap/2)
    if inductor_pad < 0:
        chip.add(dxf.rectangle(s_l.start,w_cap/2+s_cap,-s_cap-w_cap/2,rotation=s_l.direction,bgcolor=bgcolor))
        chip.add(dxf.rectangle(s_r.start,w_cap/2+s_cap,s_cap+w_cap/2,rotation=s_r.direction,bgcolor=bgcolor))
        chip.add(CurveRect(s_l.start,w_cap/2+s_cap,w_cap/2+s_cap,ralign=const.TOP,rotation=s_l.direction,bgcolor=bgcolor),structure=s_l,length=s_cap+w_cap/2)
        chip.add(CurveRect(s_r.start,w_cap/2+s_cap,w_cap/2+s_cap,ralign=const.TOP,rotation=s_r.direction,vflip=True,bgcolor=bgcolor),structure=s_r,length=s_cap+w_cap/2)
        inductor_pad = inductor_pad + s_cap + w_cap/2 #in case extra length from capacitor stub is too much length
    
    if inductor_pad > 0:
        if ialign is const.BOTTOM:
            CPW_straight(chip,s_0,inductor_pad,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4)
            CPW_straight(chip,s_1,inductor_pad,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4)
        elif ialign is const.MIDDLE:
            CPW_straight(chip,s_0,inductor_pad/2,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4)
            CPW_straight(chip,s_1,inductor_pad/2,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4)
    Inductor_wiggles(chip,s_0,length=l_ind,maxWidth=maxWidth,Width=(width - 2*(w_cap+2*s_cap))/4,nTurns=nTurns,pad_to_width=True,CCW=True,bgcolor=bgcolor)
    Inductor_wiggles(chip,s_1,length=l_ind,maxWidth=maxWidth,Width=(width - 2*(w_cap+2*s_cap))/4,nTurns=nTurns,pad_to_width=True,CCW=False,bgcolor=bgcolor)
    if inductor_pad > 0:
        if ialign is const.TOP:
            CPW_straight(chip,s_0,inductor_pad,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4)
            CPW_straight(chip,s_1,inductor_pad,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4)
        elif ialign is const.MIDDLE:
            CPW_straight(chip,s_0,inductor_pad/2,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4)
            CPW_straight(chip,s_1,inductor_pad/2,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4)
    CPW_stub_short(chip,s_0,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4,r_out=r_cap-w_cap/2,curve_out=False)
    CPW_stub_short(chip,s_1,s=(width - 2*(w_cap+2*s_cap)-2*w_ind)/4,r_out=r_cap-w_cap/2,curve_out=False)
    
    
# ===============================================================================
# basic TWO-LAYER CPS function definitions
# ===============================================================================

    