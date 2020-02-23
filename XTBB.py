# -*- coding: utf-8 -*-
#
#
#  Brainbow segmentation Python XTension  
#
#    <CustomTools>
#      <Menu name = "Brainbow plugins">
#       <Item name="Brainbow PCA segmentation (Three component selection)" icon="Python" tooltip="Brainbow segmentation based on PCA.">
#         <Command>PythonXT::XTBB(%i)</Command>
#       </Item>
#      </Menu>
#    </CustomTools>
#
# 
# Copyright (c) 2016 Egor Zindy <egor.zindy@manchester.ac.uk>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:

import matplotlib as mpl
mpl.use('TkAgg')
from mpl_toolkits.mplot3d import Axes3D
import nativebb

import BBDialog
import Tkinter as tk
import tkFileDialog
import ttk

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib.patheffects
import matplotlib.patches as patches
from mpl_toolkits.axes_grid1 import make_axes_locatable
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import numpy as np
import sys, traceback

import line_editor
import libpat
import time
import ast
import cPickle

import ImarisLib
import BridgeLib
from PIL import Image

import libatrous
import hotswap

DEBUG = True
TWOBYTWO = 0
THREEDEE = 1
H3 = 2
V3 = 3

def onHotswap():
    """
    Hotswap function

    The hotswap function
    """
    t = time.localtime(time.time())
    st = time.strftime("Hotswap: %Y-%m-%d %H:%M:%S", t)
    print st

###########################################################################
## Main application module
###########################################################################
class MyModule:
    def __init__(self,vImaris):
        self.vImaris = vImaris

        #Use a clone
        print "Making a clone..."
        #self.vDataSet = vImaris.GetDataSet()
        self.vDataSet = vImaris.GetDataSet().Clone()
        print "  done!"

        self.interactor_c12 = None
        self.interactor_c13 = None
        self.interactor_c32 = None

        #self.layout = THREEDEE
        self.layout = TWOBYTWO

        self.selection = None
        self.ssize = 40000

        self.nbit = 16
        self.maxval = 65535

        nx = self.vDataSet.GetSizeX()
        ny = self.vDataSet.GetSizeY()
        nz = self.vDataSet.GetSizeZ()
        nc = self.vDataSet.GetSizeC()


        self.Dialog=BBDialog.BBDialog(nsel=2)
        self.Dialog.set_icon(BridgeLib.GetIcon())
        self.Dialog.SetDefaults()

        self.Dialog.DoImport = self.DoImport
        self.Dialog.DoExport = self.DoExport
        
        self.Dialog.ctrl_r.config(from_=1, to=nc)
        self.Dialog.ctrl_g.config(from_=1, to=nc)
        self.Dialog.ctrl_b.config(from_=1, to=nc)

        self.Dialog.scale_bt.bind("<ButtonRelease-1>", self.do_release)
        self.Dialog.scale_wt.bind("<ButtonRelease-1>", self.do_release)
        self.Dialog.scale_w.bind("<ButtonRelease-1>", self.do_release)

        #Setting the grid resolution
        resx = float(self.vDataSet.GetExtendMaxX()) / nx
        resy = float(self.vDataSet.GetExtendMaxY()) / ny
        resz = float(self.vDataSet.GetExtendMaxZ()) / nz
        libatrous.set_grid(resx, resy, resz) 

        #For now, only save the parameters for the current channel. When changing channel, this data is erased.
        self.arrayvar_last = None

        self.sel0_comp = (0,1)
        self.sel1_comp = (0,2)
        self.sel2_comp = (2,1)
        self.handle_3d = None
        self.line3d = None

        self.scat_12 = None
        self.scat_13 = None
        self.scat_32 = None

        #This is where we keep rgb...
        self.rgb = np.zeros((nx*ny*nz,3),BridgeLib.GetType(self.vDataSet))

        fig = self.Dialog.figure

        if self.layout == THREEDEE:
            self.ax1 = ax1 = fig.add_subplot(2, 2, 1, aspect='equal')
            self.ax2 = ax2 = fig.add_subplot(2, 2, 2, aspect='equal')
            self.ax3 = ax3 = fig.add_subplot(2, 2, 3, projection='3d')
            self.ax4 = ax4 = fig.add_subplot(2, 2, 4, aspect='equal')
        elif self.layout == TWOBYTWO:
            self.ax2 = ax2 = fig.add_subplot(2, 2, 1, aspect='equal') #13
            self.ax4 = ax4 = fig.add_subplot(2, 2, 2, aspect='equal') #image
            self.ax1 = ax1 = fig.add_subplot(2, 2, 3, aspect='equal') #12
            self.ax3 = ax3 = fig.add_subplot(2, 2, 4, aspect='equal') #32
        elif self.layout == V3:
            self.ax3 = None
            self.ax1 = ax1 = fig.add_subplot(3, 1, 1, aspect='equal')
            self.ax2 = ax2 = fig.add_subplot(3, 1, 2, aspect='equal')
            self.ax4 = ax4 = fig.add_subplot(3, 1, 3, aspect='equal')
        else: #if self.layout == H3:
            self.ax3 = None
            self.ax1 = ax1 = fig.add_subplot(1, 3, 1, aspect='equal')
            self.ax2 = ax2 = fig.add_subplot(1, 3, 2, aspect='equal')
            self.ax4 = ax4 = fig.add_subplot(1, 3, 3, aspect='equal')

        self.InitDialog()
        #self.DoImport()
        self.Dialog.mainloop()

    def InitDialog(self):
        #Build the dialog

        #build the figure
        nc = self.vDataSet.GetSizeC()
        #fig = self.Dialog.figure
        #plt.show()

        #self.Dialog.ExitOK = self.ExitOK
        #self.Dialog.ExitCancel = self.ExitCancel
        self.Dialog.Update = self.Update

        #self.UpdateObjects()

    def DoImport(self,pca=True,newset=True,handle=None):
        arrayvar = self.Dialog.arrayvar
        is_unit = arrayvar["check_unit"] == "on"

        cr = int(self.Dialog.arrayvar["channel_r"])-1
        cg = int(self.Dialog.arrayvar["channel_g"])-1
        cb = int(self.Dialog.arrayvar["channel_b"])-1
        nz = self.vDataSet.GetSizeZ()

        rgb = []
        self.Dialog.config(cursor="wait")

        maxval = 0
        for i in [cr,cg,cb]:
            print "Importing channel %d" % (i+1)
            if nz == 1:
                d = BridgeLib.GetDataSlice(self.vDataSet,0,i,0) #.astype(np.float32)
            else:
                d = BridgeLib.GetDataVolume(self.vDataSet,i,0) #.astype(np.float32)
            rgb.append(d)
            m = np.max(d)
            if m > maxval:
                maxval = m

        self.nbit = int(np.ceil(np.log2(maxval)))
        self.maxval = pow(2,self.nbit)-1

        print "Using %d as maxval (maxval dataset = %d)" % (maxval,self.maxval)

        self.dataset = libpat.Image(self.nbit)
        self.dataset.set_data(rgb)

        print "doing the pca!"
        threshold = 0
        if pca is True:
            self.dataset.init_pca()

        self.Dialog.config(cursor="")

        print "plotting some crosses..."
        self.dataset.do_pca2d(threshold,unit=is_unit)
        self.dataset.set_ssize(self.ssize)

        h = handle
        if is_unit and h is not None:
            h = self.dataset.get_rgb_col(h,dtype=int)

        c0,c1 = self.sel0_comp
        self.scat_12 = self.dataset.plot_pca2d_dots(c0=c0,c1=c1,axs=self.ax1,scat=self.scat_12, unit=is_unit,handle=h)
        c0,c1 = self.sel1_comp
        self.scat_13 = self.dataset.plot_pca2d_dots(c0=c0,c1=c1,axs=self.ax2,scat=self.scat_13, unit=is_unit,handle=h)

        if self.layout == TWOBYTWO:
            c0,c1 = self.sel2_comp
            self.scat_32 = self.dataset.plot_pca2d_dots(c0=c0,c1=c1,axs=self.ax3,scat=self.scat_32, unit=is_unit,handle=h)

        self.im = self.dataset.display_rgb(axs=self.ax4)

        if self.layout == THREEDEE:
            self.scat_3d = self.dataset.plot_pca3d_dots(axs=self.ax3, unit=is_unit)
            self.display_3dline(self.ax3, unit=is_unit)

        #fig = self.Dialog.figure
        #fig.canvas.draw()
        self.InitPCA(handle=handle)

    def DoExport(self,*args):
        if self.selection is None:
            return

        name = "Cluster"
        data = self.dataset.get_luma(self.selection)
        #col = self.dataset.get_rgb_col(wh=self.selection,dtype=int)
        col = self.dataset.get_rgb_col(self.handle_3d, dtype=int) #wh=selection)
        self.AddChannel(data,name,col, add_filter=True,threshold=100)

    def DoInput(self,*args):
        file_path = tkFileDialog.asksaveasfilename(
                defaultextension=".tif", filetypes = [ 
                    ("TIFF bitmap format",'*.tif'),
                    ("PNG bitmap format",'*.png'),
                    ("All image files",('*.tif','*.png'))],
                parent=self.Dialog, title="Save the input image")

        if file_path == "":
            return

        rgb_uint8 = self.dataset.get_rgb_image()
        img = Image.fromarray(rgb_uint8)
        img.save(file_path)

    def DoOutput(self,*args):
        file_path = tkFileDialog.asksaveasfilename(
                defaultextension=".tif", filetypes = [ 
                    ("TIFF bitmap format",'*.tif'),
                    ("PNG bitmap format",'*.png'),
                    ("All image files",('*.tif','*.png'))],
                parent=self.Dialog, title="Save the output image")

        if file_path == "":
            return

        rgb_uint8 = self.dataset.get_rgb_image(wh=self.selection)
        img = Image.fromarray(rgb_uint8)
        img.save(file_path)

    def DoOpenPCA(self):
        self.Dialog.file_opt['title'] = 'Open a PCA matrix'
        filename = tkFileDialog.askopenfilename(**self.Dialog.file_opt)
        if filename == "":
            return

        f = open(filename, 'rb')
        pcanode = cPickle.load(f)
        self.dataset.pcanode = pcanode

        if hasattr(pcanode,"gui_values"):
            arrayvar = self.Dialog.arrayvar
            arrayvar.set(pcanode.gui_values)

        if hasattr(pcanode,"handle"):
            self.handle_3d = pcanode.handle
            #print "found a handle!",pcanode.handle
            #handle = pcanode(np.array([pcanode.handle]))[0]
            value_c0 = self.handle_3d[0]
            value_c1 = self.handle_3d[1]
            value_c2 = self.handle_3d[2]
            self.interactor_c12.set_handle((value_c0,value_c1))
            self.interactor_c13.set_handle((value_c0,value_c2))
            self.interactor_c32.set_handle((value_c2,value_c1))
        else:
            handle = self.get_handle()

        self.do_release()

        #self.DoImport(pca=False,newset=False,handle=handle)
        #fig = self.Dialog.figure
        #fig.canvas.draw()

    def DoSavePCA(self):
        self.Dialog.file_opt['title'] = 'Save the current PCA matrix'
        filename = tkFileDialog.asksaveasfilename(**self.Dialog.file_opt)
        if filename == "":
            return

        print "saving...",filename
        arrayvar = self.Dialog.arrayvar
        gui_values = arrayvar.get()
        handle = self.get_handle()
        #handle = self.dataset.get_rgb_col(self.get_handle(),dtype=int)
        print ">>>>",handle
        self.dataset.pcanode.handle = handle
        self.dataset.pcanode.gui_values = gui_values
        self.dataset.pcanode.save(filename,protocol=1)

    def DoRecompute(self,*args):
        self.DoImport(pca=True,newset=False,handle=self.get_handle())
        fig = self.Dialog.figure
        fig.canvas.draw()

    def DoUnit(self,*args):
        pass

    def DoReport(self,*args):
        file_path = tkFileDialog.asksaveasfilename(
                defaultextension=".html", filetypes = [ 
                    ("HTML reports",'*.html')],
                parent=self.Dialog, title="Save a HTML report")

        if file_path == "":
            return

        self.Dialog.config(cursor="wait")

        labels = self.Dialog.get_labels()
        arrayvar = self.Dialog.arrayvar
        values = arrayvar.get()
        keys = values.keys() #self.Dialog._controlnames
        keys.sort()
        #keys = ["bars_sigma","bars_rgbl","scale_bt","check_black","scale_wt","check_white"

        ptm = self.handle_3d
        col = self.dataset.get_rgb_col(ptm)
        html_string = '''<html>
                <head>
                    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.1/css/bootstrap.min.css">
                    <style>body{ margin:0 100; background:whitesmoke; }
                    .foo { border: 1px solid rgba(0, 0, 0, .2); background: %s;}
                    </style>
                </head>
                <body>
                    <h2>PCA coordinates:</h2>
                    <p class="foo"><b>HTML colour code:</b> %s</p>
        ''' % (col,col)

        col = self.dataset.get_rgb_col(ptm,dtype=float)
        html_string += '<p><b>Black point:</b> (%.1f,%.1f,%.1f)</p>\n' % tuple(self.ptb.tolist())
        html_string += '<p><b>White point:</b> (%.1f,%.1f,%.1f)</p>\n' % tuple(self.ptw.tolist())
        html_string += '<p><b>Handle point:</b> (%.1f,%.1f,%.1f)</p>\n' % tuple(ptm.tolist())
        html_string += '<p><b>Handle RGB col:</b> (%.1f,%.1f,%.1f)\n' % tuple(col.tolist())

        html_string += '<h2>PCA Forward matrix:</h2>\n'
        mat = self.dataset.pcanode.get_projmatrix()
        avg = self.dataset.pcanode.avg
        rgb = ["R","G","B"]
        pca = ["C0","C1","C2"]
        for pci in range(3):
            html_string += '<p><b>%s</b> = ' % pca[pci]
            for ci in range(3):
                html_string += "%.2f * (<b>%s</b> - %.2f) + "% (mat[ci,pci],rgb[ci],avg[ci])
            html_string = html_string[:-3]+"</p>\n"

        html_string += '<h2>PCA Back-projection:</h2>\n'
        mat = self.dataset.pcanode.get_recmatrix()
        rgb = ["R","G","B"]
        pca = ["C0","C1","C2"]
        for ci in range(3):
            html_string += '<p><b>%s</b> = ' % rgb[ci]
            for pci in range(3):
                html_string += "%.2f * <b>%s</b> + "% (mat[pci,ci],pca[pci])
            html_string = html_string+"%.2f</p>\n" % avg[ci]

        html_string += '<h2>Other values:</h2>\n'
        #print labels.keys()
        #print values.keys()
        for key in keys:
            if key not in labels.keys() or labels[key] is None or labels[key] == '':
                label = key
            else:
                label = labels[key]

            if label.startswith("RGB") or "polygons" in label or label == "menuitem":
                continue

            html_string += '<p><b>%s:</b> %s</p>\n' % (label,str(values[key]))

        html_string += '''
                </body>
            </html>'''

        f = open(file_path,"w")
        f.write(html_string)
        f.close()
        self.Dialog.config(cursor="")

    def DoScreenshot(self,*args):
        arrayvar = self.Dialog.arrayvar
        has_polygons = arrayvar["PCA_Figures_Include_Polygons"] == "on"

        file_path = tkFileDialog.asksaveasfilename(
                defaultextension=".tif", filetypes = [ 
                    ("TIFF bitmap format",'*.tif'),
                    ("PDF vector format",'*.pdf'),
                    ("PNG bitmap format",'*.png'),
                    ("SVG vector format",'*.svg'),
                    ("EMF vector format",'*.emf'),
                    ("All image files",('*.tif','*.pdf','*.png','*.svg','*.emf'))],
                parent=self.Dialog, title="Save a High Resolution Figure")

        if file_path == "":
            return

        self.Dialog.config(cursor="wait")

        fig = plt.figure(figsize=(15,15), dpi=100)
        ax2 = fig.add_subplot(2, 2, 1, aspect='equal')
        ax4 = fig.add_subplot(2, 2, 2, aspect='equal')
        ax1 = fig.add_subplot(2, 2, 3, aspect='equal')
        ax3 = fig.add_subplot(2, 2, 4, aspect='equal')

        c0,c1 = self.sel0_comp
        scat_12 = self.dataset.plot_pca2d_dots(c0=c0,c1=c1,axs=ax1)
        c0,c1 = self.sel1_comp
        scat_13 = self.dataset.plot_pca2d_dots(c0=c0,c1=c1,axs=ax2)
        c0,c1 = self.sel2_comp
        scat_32 = self.dataset.plot_pca2d_dots(c0=c0,c1=c1,axs=ax3)

        im = self.dataset.display_rgb(axs=ax4)

        print "done!"

        #use self.interactor_c12 to populate the new ax1...
        if has_polygons:
            self.interactor_c12.draw_things(ax1)
            self.interactor_c13.draw_things(ax2)
            self.interactor_c32.draw_things(ax3)

        #Then display the image in the second graph
        print "generating the image..."
        rgb_uint8 = self.im.get_array()
        ax4.imshow(rgb_uint8)
        print "done!"

        print "saving the figure..."
        fig.savefig(file_path, bbox_inches='tight')
        print "done!"

        self.Dialog.config(cursor="")

    def DoScreenshot3d(self,*args):
        arrayvar = self.Dialog.arrayvar
        has_polygons = arrayvar["PCA_Figures_Include_Polygons"] == "on"

        file_path = tkFileDialog.asksaveasfilename(
                defaultextension=".tif", filetypes = [ 
                    ("TIFF bitmap format",'*.tif'),
                    ("PDF vector format",'*.pdf'),
                    ("PNG bitmap format",'*.png'),
                    ("SVG vector format",'*.svg'),
                    ("EMF vector format",'*.emf'),
                    ("All image files",('*.tif','*.pdf','*.png','*.svg','*.emf'))],
                parent=self.Dialog, title="Save a High Resolution Figure")

        if file_path == "":
            return

        self.Dialog.config(cursor="wait")
        fig = plt.figure(figsize=(15,15), dpi=100)
        ax1 = fig.add_subplot(1, 1, 1, projection='3d')

        #Then add the two graphs...
        print "Generating the complete scatter plot..."
        scat = self.dataset.plot_pca3d_dots(axs=ax1,fullset=True)

        if has_polygons:
            self.display_3dline(ax1)

        print "done!"

        print "saving the figure..."
        fig.savefig(file_path, bbox_inches='tight')
        print "done!"

        self.Dialog.config(cursor="")

    def display_3dline(self,ax):
        if self.layout is not THREEDEE:
            return

        if self.line3d is None:
            ptm = self.handle_3d
            x = [self.ptb[0],ptm[0],self.ptw[0]]
            y = [self.ptb[1],ptm[1],self.ptw[1]]
            z = [self.ptb[2],ptm[2],self.ptw[2]]
            self.line3d, = ax.plot(x,y,z, marker='s', markersize=10, markerfacecolor='r')
        else:
            self.update_3dline(ax)

    def update_3dline(self,ax):
        if self.layout is not THREEDEE:
            return

        arr = np.array([self.ptb,self.handle_3d,self.ptw]).transpose()
        self.line3d.set_data(arr[0:2, :])
        self.line3d.set_3d_properties(arr[2, :])
        ax.draw_artist(self.line3d)
        fig = self.Dialog.figure
        fig.canvas.draw()

    def InitPCA(self,handle=None):
        #These are independent of the interactor view.
        arrayvar = self.Dialog.arrayvar
        is_unit = arrayvar["PCA_Matrix_Unit_transform"] == "on"

        maxval = self.maxval
        print ">>>Using %d as maxval" % maxval
        if is_unit:
            self.ptb = np.zeros(3)
            self.ptw = np.ones(3)*maxval
        else:
            self.ptb = self.dataset.pcanode(np.zeros((1,3))*maxval)[0]
            self.ptw = self.dataset.pcanode(np.ones((1,3))*maxval)[0]

        if handle is None: #or self.handle_3d is None:
            handle = self.handle_3d
            if handle is None:
                handle = (self.ptb + self.ptw)/2.
            else:
                if is_unit:
                    handle = self.dataset.get_rgb_col(handle,dtype=int)
                else:
                    handle = self.dataset.pcanode(np.array([handle]))[0]

            self.handle_3d = handle

        else:
            if is_unit:
                handle = self.dataset.get_rgb_col(handle,dtype=int)

        if self.interactor_c12 is None:
            low = arrayvar["check_black"] == "on"
            high = arrayvar["check_white"] == "on"
            tapered = arrayvar["check_tapered"] == "on"

            wt = float(arrayvar["scale_wt"])/100.
            bt = float(arrayvar["scale_bt"])/100.
            w = self.maxval*float(arrayvar["scale_w"])/500.

            fig = self.Dialog.figure
            #initialize the interactor_c12
            c0,c1 = self.sel0_comp

            ptb = [self.ptb[c0],self.ptb[c1]]
            ptw = [self.ptw[c0],self.ptw[c1]]
            ptm = [handle[c0],handle[c1]]

            self.interactor_c12 = line_editor.LineInteractor(fig,self.ax1,ptb,ptm,ptw,thickness=w,t0=bt,t1=wt,low=low,high=high,tapered=tapered)
            self.interactor_c12.do_press = self.do_press
            self.interactor_c12.do_release = self.do_release_12

            #initialize the interactor_c13
            c0,c1 = self.sel1_comp
            ptb = [self.ptb[c0],self.ptb[c1]]
            ptw = [self.ptw[c0],self.ptw[c1]]
            ptm = [handle[c0],handle[c1]]

            self.interactor_c13 = line_editor.LineInteractor(fig,self.ax2,ptb,ptm,ptw,thickness=w,t0=bt,t1=wt,low=low,high=high,tapered=tapered)
            self.interactor_c13.do_press = self.do_press
            self.interactor_c13.do_release = self.do_release_13

            #initialize the interactor_c32
            c0,c1 = self.sel2_comp
            ptb = [self.ptb[c0],self.ptb[c1]]
            ptw = [self.ptw[c0],self.ptw[c1]]
            ptm = [handle[c0],handle[c1]]

            self.interactor_c32 = line_editor.LineInteractor(fig,self.ax3,ptb,ptm,ptw,thickness=w,t0=bt,t1=wt,low=low,high=high,tapered=tapered)
            self.interactor_c32.do_press = self.do_press
            self.interactor_c32.do_release = self.do_release_32
        else:
            c0,c1 = self.sel0_comp
            ptb = [self.ptb[c0],self.ptb[c1]]
            ptw = [self.ptw[c0],self.ptw[c1]]
            ptm = [handle[c0],handle[c1]]
            self.interactor_c12.set_bw(ptb,ptw,ptm)

            c0,c1 = self.sel1_comp
            ptb = [self.ptb[c0],self.ptb[c1]]
            ptw = [self.ptw[c0],self.ptw[c1]]
            ptm = [handle[c0],handle[c1]]
            self.interactor_c13.set_bw(ptb,ptw,ptm)

            c0,c1 = self.sel2_comp
            ptb = [self.ptb[c0],self.ptb[c1]]
            ptw = [self.ptw[c0],self.ptw[c1]]
            ptm = [handle[c0],handle[c1]]
            self.interactor_c32.set_bw(ptb,ptw,ptm)

            #This is to force the interactor to reacquire the background image
            self.interactor_c12.background = None
            self.interactor_c13.background = None
            self.interactor_c32.background = None

            #This is to change the handle colour
            if is_unit:
                col = np.array(handle,dtype='f')/np.max(handle)
            else:
                col = self.dataset.get_rgb_col(handle,dtype=float)
            self.interactor_c12.set_handle_col(col)
            self.interactor_c13.set_handle_col(col)
            self.interactor_c32.set_handle_col(col)

        print "here?"
        self.do_release()
        #fig = self.Dialog.figure
        #fig.canvas.draw()
        #fig.canvas.flush_events()
        #plt.show()

    def Update(self, arrayvar, elementname):
        if elementname.startswith("channel_") or self.scat_12 is None:
            return

        low = arrayvar["check_black"] == "on"
        high = arrayvar["check_white"] == "on"
        show = arrayvar["check_masking"] == "on"
        tapered = arrayvar["check_tapered"] == "on"
        is_unit = arrayvar["PCA_Matrix_Unit_transform"] == "on"

        if elementname == "menuitem":
            if arrayvar[elementname] == 'PCA Figures/Save Projections':
                self.DoScreenshot()
            elif arrayvar[elementname] == 'PCA Figures/Save 3D graph':
                self.DoScreenshot3d()
            elif arrayvar[elementname] == 'PCA Figures/Input Image':
                self.DoInput()
            elif arrayvar[elementname] == 'PCA Figures/Output Image':
                self.DoOutput()
            elif arrayvar[elementname] == 'PCA Matrix/Open File':
                self.DoOpenPCA()
            elif arrayvar[elementname] == 'PCA Matrix/Save File':
                self.DoSavePCA()
            elif arrayvar[elementname] == 'PCA Matrix/Recompute':
                self.DoRecompute()
            elif arrayvar[elementname] == 'PCA Matrix/Unit transform':
                self.DoRecompute()
            elif arrayvar[elementname] == 'PCA Matrix/Save HTML report':
                self.DoReport()
            elif arrayvar[elementname] == 'File/Open configuration':
                self.interactor_c12.tapered = tapered
                self.interactor_c13.tapered = tapered
                self.interactor_c12.low = low
                self.interactor_c12.high = high
                self.interactor_c13.low = low
                self.interactor_c13.high = high
                if self.layout == TWOBYTWO:
                    self.interactor_c32.tapered = tapered
                    self.interactor_c32.low = low
                    self.interactor_c32.high = high
                handle = self.get_handle()
                self.DoImport(newset=False,handle=handle)
                fig = self.Dialog.figure
                fig.canvas.draw()
                return

        if elementname == "check_unit":
            handle = self.get_handle()
            self.DoImport(newset=False,handle=handle)
            fig = self.Dialog.figure
            fig.canvas.draw()
            return

        if elementname == "check_tapered":
            self.interactor_c12.tapered = tapered
            self.interactor_c13.tapered = tapered
            if self.layout == TWOBYTWO:
                self.interactor_c32.tapered = tapered
            self.do_release()

        if elementname == "check_black" or elementname == "check_white":
            self.interactor_c12.low = low
            self.interactor_c12.high = high
            self.interactor_c13.low = low
            self.interactor_c13.high = high
            if self.layout == TWOBYTWO:
                self.interactor_c32.low = low
                self.interactor_c32.high = high
            self.do_release()

        if elementname == "check_masking":
            if show and (high or low):
                #show the interactor_c12
                self.interactor_c12.redraw(show=True)
                self.interactor_c13.redraw(show=True)
                if self.layout == TWOBYTWO:
                    self.interactor_c32.redraw(show=True)

                #show the masked
                if self.selection is None:
                    xy = self.dataset.rgb_pca[:,self.sel0_comp].astype(np.float32)
                    poly_xy = self.interactor_c12.get_poly()
                    wh_12 = nativebb.isinside(xy,poly_xy)
                    #wh_12 = self.interactor_c12.is_inside(xy)

                    xy = self.dataset.rgb_pca[:,self.sel1_comp].astype(np.float32)
                    poly_xy = self.interactor_c13.get_poly()
                    wh_13 = nativebb.isinside(xy,poly_xy)
                    #wh_13 = self.interactor_c13.is_inside(xy)

                    #This is where we assign pixels in the two bands
                    wh = np.bitwise_and(wh_12,wh_13)
                    selection = self.dataset.get_selection(wh)
                else:
                    selection = self.selection
            elif self.interactor_c12 is not None:
                #hide the interactor_c12
                
                self.interactor_c12.redraw(show=False)
                self.interactor_c13.redraw(show=False)
                if self.layout == TWOBYTWO:
                    self.interactor_c32.redraw(show=False)
                selection = self.selection = None


                #show the original image
                self.dataset.display_rgb(im=self.im, axs=self.ax4) #

            self.dataset.display_rgb(wh=selection,im=self.im, axs=self.ax4) #
            self.ax4.draw_artist(self.im)
            fig = self.Dialog.figure
            fig.canvas.blit(self.ax4.bbox)

            return

        wt = float(self.Dialog.arrayvar["scale_wt"])/100.
        bt = float(self.Dialog.arrayvar["scale_bt"])/100.
        w = self.maxval*float(self.Dialog.arrayvar["scale_w"])/500.
        #selection1 = BBDialog.list_graphs.index(self.Dialog.arrayvar["selection1"])
        #selection2 = BBDialog.list_graphs.index(self.Dialog.arrayvar["selection2"])

        if elementname == "scale_wt" or elementname == "scale_bt" or elementname == "scale_w":
            return
            #self.do_release()

        if elementname[:-1] == "selection":
            handle_3d = self.get_handle()

            if elementname == "selection1":
                if selection1 == 0:
                    self.sel0_comp = (0,1)
                elif selection1 == 1:
                    self.sel0_comp = (0,2)
                elif selection1 == 2:
                    self.sel0_comp = (1,2)
            elif elementname == "selection2":
                if selection2 == 0:
                    self.sel1_comp = (0,1)
                elif selection2 == 1:
                    self.sel1_comp = (0,2)
                elif selection2 == 2:
                    self.sel1_comp = (1,2)

            #redraw
            c0,c1 = self.sel0_comp
            self.dataset.plot_pca2d_dots(c0=c0,c1=c1,scat=self.scat_12,axs=self.ax1,unit=is_unit)
            c0,c1 = self.sel1_comp
            self.dataset.plot_pca2d_dots(c0=c0,c1=c1,scat=self.scat_13,axs=self.ax2, unit=is_unit)

            #reinitialise with handle
            self.InitPCA()

            fig = self.Dialog.figure
            fig.canvas.draw()

    def get_handle(self, update_from=None):
        if update_from is None:
            return self.handle_3d

        if self.handle_3d is None:
            handle_3d = (self.ptb+self.ptw)/2.
        else:
            handle_3d = self.handle_3d

        if update_from == 0:
            c0, c1 = self.sel0_comp
            value_c0, value_c1 = self.interactor_c12.get_handle()
        elif update_from == 1:
            c0, c1 = self.sel1_comp
            value_c0, value_c1 = self.interactor_c13.get_handle()
        elif update_from == 2:
            c0, c1 = self.sel2_comp
            value_c0, value_c1 = self.interactor_c32.get_handle()

        handle_3d[c0] = value_c0
        handle_3d[c1] = value_c1

        #worse comes to the worse, the handle is half way through ptb and ptw

        self.handle_3d = handle_3d
        return handle_3d

    #Here we can add a channel...
    def AddChannel(self,data,name,col=[255,255,255], add_filter=True,threshold=100):
        print "using colour",col

        nc = self.vDataSet.GetSizeC()
        nz = self.vDataSet.GetSizeZ()
        nt = self.vDataSet.GetSizeT()

        if add_filter:
            print "filering..."
            #The filament
            filter_type=5
            low_scale = 2
            high_scale = 3
            add_lowpass = 0

            data = data.astype(np.float32)
            kernel = libatrous.get_kernel(filter_type)
            d = libatrous.get_bandpass(data,low_scale-1,high_scale,kernel,add_lowpass)
            if threshold > 0:
                d[d<threshold] = 0

        #push back
        tp = self.vImaris.GetVisibleIndexT()
        channel_out = BridgeLib.FindChannel(self.vDataSet,None,create=True,color=col)
        self.vDataSet.SetChannelName(channel_out,name)

        if DEBUG: print "Adding %s" % name,channel_out

        if data.ndim == 2:
            BridgeLib.SetDataSlice(self.vDataSet,d,0,channel_out,tp)
        else:
            BridgeLib.SetDataVolume(self.vDataSet,d,channel_out,tp)

        #Use the modified / cloned dataset
        self.vImaris.SetDataSet(self.vDataSet)

    def do_press(self):
        pass

    def do_release_12(self,evt=None):
        handle_3d = self.get_handle(update_from=0)
        c0,c1 = self.sel1_comp
        #print "released 12",c0,c1
        value_c0 = handle_3d[c0]
        value_c1 = handle_3d[c1]
        self.interactor_c13.set_handle((value_c0,value_c1))
        if self.layout == TWOBYTWO:
            c0,c1 = self.sel2_comp
            value_c0 = handle_3d[c0]
            value_c1 = handle_3d[c1]
            self.interactor_c32.set_handle((value_c0,value_c1))
        self.do_release(evt)

    def do_release_13(self,evt=None):
        handle_3d = self.get_handle(update_from=1)
        c0,c1 = self.sel0_comp
        #print c0,c1
        value_c0 = handle_3d[c0]
        value_c1 = handle_3d[c1]
        self.interactor_c12.set_handle((value_c0,value_c1))
        if self.layout == TWOBYTWO:
            c0,c1 = self.sel2_comp
            value_c0 = handle_3d[c0]
            value_c1 = handle_3d[c1]
            self.interactor_c32.set_handle((value_c0,value_c1))
        self.do_release(evt)

    def do_release_32(self,evt=None):
        handle_3d = self.get_handle(update_from=2)

        c0,c1 = self.sel1_comp
        value_c0 = handle_3d[c0]
        value_c1 = handle_3d[c1]
        self.interactor_c13.set_handle((value_c0,value_c1))

        c0,c1 = self.sel0_comp
        value_c0 = handle_3d[c0]
        value_c1 = handle_3d[c1]
        self.interactor_c12.set_handle((value_c0,value_c1))

        self.do_release(evt)

    def do_release(self,evt=None):
        if (self.Dialog.arrayvar["check_masking"] == "off"):
            return

        wt = float(self.Dialog.arrayvar["scale_wt"])/100.
        bt = float(self.Dialog.arrayvar["scale_bt"])/100.
        w = self.maxval*float(self.Dialog.arrayvar["scale_w"])/500.

        self.interactor_c12.set_parameters(w,bt,wt)
        self.interactor_c13.set_parameters(w,bt,wt)
        if self.layout == TWOBYTWO:
            self.interactor_c32.set_parameters(w,bt,wt)

        is_unit = self.Dialog.arrayvar["PCA_Matrix_Unit_transform"] == "on"
        if is_unit:
            col = self.handle_3d
        else:
            col = self.dataset.get_rgb_col(self.handle_3d,dtype=float)

        self.interactor_c12.set_handle_col(col)
        self.interactor_c13.set_handle_col(col)

        self.interactor_c12.redraw()
        self.interactor_c13.redraw()
        if self.layout == TWOBYTWO:
            self.interactor_c32.set_handle_col(col)
            self.interactor_c32.redraw()
        print "in do_release",self.handle_3d, col

        t = time.time()
        if 0:
            xy = self.dataset.rgb_pca[:,self.sel0_comp]
            wh_12 = self.interactor_c12.is_inside(xy)
            xy = self.dataset.rgb_pca[:,self.sel1_comp]
            wh_13 = self.interactor_c13.is_inside(xy)
        else:
            xy = self.dataset.rgb_pca[:,self.sel0_comp].astype(np.float32)
            poly_xy = self.interactor_c12.get_poly()
            wh_12 = nativebb.isinside(xy,poly_xy)
            xy = self.dataset.rgb_pca[:,self.sel1_comp].astype(np.float32)
            poly_xy = self.interactor_c13.get_poly()
            wh_13 = nativebb.isinside(xy,poly_xy)

        #This is where we assign pixels in the two bands
        wh = np.bitwise_and(wh_12,wh_13)
        self.selection = selection = self.dataset.get_selection(wh)

        if self.layout == THREEDEE: #self.ax3 is not None:
            self.dataset.update_3d_dots(self.scat_3d,wh)
            self.ax3.draw_artist(self.scat_3d)

        # Let's capture the background of the figure
        fig = self.Dialog.figure
        bg_1 = fig.canvas.copy_from_bbox(self.ax1.bbox)
        bg_2 = fig.canvas.copy_from_bbox(self.ax2.bbox)
        bg_3 = fig.canvas.copy_from_bbox(self.ax3.bbox)
        bg_4 = fig.canvas.copy_from_bbox(self.ax4.bbox)

        #left
        print "updating..."
        self.dataset.display_rgb(wh=selection,im=self.im) #axs=self.ax3) #
        self.ax4.draw_artist(self.im)
        fig.canvas.blit(self.ax4.bbox)
        print "done updating! (resize the window if you don't see any graphs after the initial import, I need to fix that)"
        #col = self.dataset.get_rgb_col(wh=selection)

        if 0:
            col = self.dataset.get_rgb_col(self.handle_3d) #wh=selection)
            style = ttk.Style()
            style.configure("Red.TCheckbutton", background=col)
            self.Dialog.btn_export.configure(style="Red.TCheckbutton")

        if self.layout == THREEDEE:
            self.update_3dline(self.ax3)

def XTBB(aImarisId):
    # Create an ImarisLib object
    vImarisLib = ImarisLib.ImarisLib()

    # Get an imaris object with id aImarisId
    vImaris = vImarisLib.GetApplication(aImarisId)

    # Check if the object is valid
    if vImaris is None:
        print "Could not connect to Imaris!"
        exit(1)

    vDataSet = vImaris.GetDataSet()
    if vDataSet is None:
        print "No data available!"
        exit(1)

    #The hotswap module watcher...
    #_watcher = hotswap.ModuleWatcher()
    #_watcher.run()

    aModule = MyModule(vImaris)


def main(argv=None):
    if argv is None:
        argv = sys.argv
    aModule = MyModule()

if __name__ == "__main__":
    main()



