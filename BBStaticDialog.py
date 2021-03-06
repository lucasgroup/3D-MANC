# -*- coding: utf-8 -*-
# Copyright (C) 2015, Egor Zindy <egor.zindy@manchester.ac.uk>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.

from __future__ import print_function
import Tkinter as tk
import ttk
from TkDialog import TkDialog
import tkFileDialog, tkMessageBox
import ast

list_graphs = ["C1 vs C2", "C1 vs C3", "C2 vs C3"]
#default_cols = "(1.0, 0.4, 0.0, 0.8), (0.4, 1.0, 0.0, 0.8), (0.2, 0.0, 1.0, 0.8), (1.0, 1.0, 1.0, 0.8)"
default_cols = " (0.5, 0.5, 0.5, 1.0), (0.3,1,1,.9), (0.5, 0.0, 0.5, 0.6), (1.0, 0.5, 0.2, 0.6)"
#default_sigmas = "10, 10, 10"
default_sigmas = "2,2,2"
print(type(ast.literal_eval("["+default_cols+"]")))
print(type(ast.literal_eval("["+default_sigmas+"]")))

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
    from matplotlib.figure import Figure
    import matplotlib as mpl
    mpl.use('TkAgg')
    import numpy as np
    hasMPL = True
except:
    hasMPL = False


###########################################################################
## The dialog
###########################################################################
class BBDialog(TkDialog):
    def __init__(self,nsel=1):
        TkDialog.__init__(self)

        #Here you can make things pretty
        self.arraychannel = None

        self.wm_geometry("700x800")
        self.title("Brainbow segmentation - Copyright (c) 2016 Egor Zindy")

        self.add_menu("File",["Open configuration","Save configuration","|","Exit"])
        self.add_menu("PCA Figures", ["Save Projections", "Save 3D graph", "Input Image", "Output Image", "|", "1_Include Polygons"])
        self.add_menu("PCA Matrix", ["Open File", "Save File", "Recompute", "Save HTML report", "|", "1_Unit transform"])
        self.add_menu("Help",["About"])

        self.bars_rgbl = ttk.Entry(self.mainframe,textvariable=self.arrayvar("bars_rgbl"))
        self.bars_rgbl.bind('<Return>', self.OnUpdateBars)
        widget = [
            self.bars_rgbl,
            ttk.Button(self.mainframe, text="Compute", command=self.OnUpdateBars)
        ]
        tooltip = "Input values for Red, Green, Blue and Lightness for each bar. RGBL values between 0 and 1"
        self.add_control("Bar colours",widget,tooltip=tooltip)

        self.bars_sigma= widget = ttk.Entry(self.mainframe,textvariable=self.arrayvar("bars_sigma"))
        self.bars_sigma.bind('<Return>', self.OnUpdateSigmas)
        tooltip = "Sigma values for R,G,B channels. Either enter a single value or three comma separated values"
        tick = (self.arrayvar("check_noise", "on"),"Add noise")
        self.add_control("RGB noise sigmas",widget,tick=tick,tooltip=tooltip)

        self.figure = Figure(figsize=(10,10), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure,master=self.mainframe)
        self.add_control(None,self.canvas.get_tk_widget())

        if 0:
            self.ctrl_sel1 = widget = ttk.Combobox(self.mainframe, textvariable=self.arrayvar("selection1"), values=list_graphs, exportselection=0, state="readonly", name="ctrl_sel1")
            tooltip = "The dropdown menu controls which two components are displayed in the 2-D PCA graph"
            tick = (self.arrayvar("check_masking", "on"),"Enable masking")
            self.add_control("Selection 1",widget, tick=tick, tooltip=tooltip)

        if 0: #nsel == 2:
            self.ctrl_sel2 = widget = ttk.Combobox(self.mainframe, textvariable=self.arrayvar("selection2"), values=list_graphs, exportselection=0, state="readonly", name="ctrl_sel2")
            tooltip = "The dropdown menu controls which two components are displayed in the 2-D PCA graph"
            tick = (self.arrayvar("check_masking", "on"),"Enable masking")
            self.add_control("Selection 2",widget, tick=tick, tooltip=tooltip)

        self.scale_bt = widget = tk.Scale(self.mainframe, variable=self.arrayvar("scale_bt"), from_ = 0, to=100, tickinterval=20, orient="horizontal", showvalue=True, name="scale_bt")
        tooltip = "The black threshold discards dark pixels"
        tick = (self.arrayvar("check_black", "on"),"Enable black mask")
        self.add_control("Black Threshold",widget, tick=tick, tooltip=tooltip)

        self.scale_wt = widget = tk.Scale(self.mainframe, variable=self.arrayvar("scale_wt"), from_ = 0, to=100, tickinterval=20, orient="horizontal", showvalue=True, name="scale_wt")
        tooltip = "The white threshold discards bright pixels"
        tick = (self.arrayvar("check_white", "on"),"Enable white mask")
        self.add_control("White Threshold",widget, tick=tick, tooltip=tooltip)

        self.scale_w = widget = tk.Scale(self.mainframe, variable=self.arrayvar("scale_w"), from_ = 0, to=200, tickinterval=20, orient="horizontal", showvalue=True, name="scale_w")
        tooltip = "The polygon width controls the sensitivity of the colour masking: broader=less sensitive, narrower=more sensitive"
        tick = (self.arrayvar("check_tapered", "on"),"Tapered polygon")
        self.add_control("Region Width",widget,tick=tick,tooltip=tooltip)

        """
        self.btn_input = ttk.Button(self.mainframe, text="Input Image", command=self.OnInput)
        self.btn_output = ttk.Button(self.mainframe, text="Output Image", command=self.OnOutput)
        self.btn_flat = ttk.Button(self.mainframe, text="Save projections", command=self.OnScreenshot)
        self.btn_3d = ttk.Button(self.mainframe, text="Save 3D graph", command=self.OnScreenshot3d)
        widget = [self.btn_flat, self.btn_3d, self.btn_input, self.btn_output]
        tick = (self.arrayvar("check_polygons", "on"),"Include polygons")
        self.add_control("PCA Figures",widget,tick=tick)

        self.btn_openpca = ttk.Button(self.mainframe, text="Open File", command=self.OnOpenPCA)
        self.btn_savepca = ttk.Button(self.mainframe, text="Save File ", command=self.OnSavePCA)
        self.btn_recompute = ttk.Button(self.mainframe, text="Recompute", command=self.OnRecompute)
        self.btn_unit = ttk.Button(self.mainframe, text="Unit Matrix", command=self.OnUnit)
        self.btn_report = ttk.Button(self.mainframe, text="Save HTML report", command=self.OnReport)
        widget = [self.btn_openpca, self.btn_savepca, self.btn_recompute, self.btn_report]
        tick = (self.arrayvar("check_unit", "off"),"Unit transform")
        self.add_control("PCA Matrix",widget,tick=tick)
        """

        #self.btn_export = widget = ttk.Button(self.mainframe, text="Send to Imaris", command=self.OnExport)
        #self.add_control(None,widget)

        #we have all the ingredients, now bake the dialog box!
        self.bake(has_cancel=False) #, has_preview=True) #"Calculate")
        self.SetDefaults()

    def OnDump(self,*args):
        '''Print the contents of the array'''
        print(self.arrayvar.get())

    def SetDefaults(self):
        #Here you set default values
        self.arrayvar["bars_sigma"] = default_sigmas
        self.arrayvar["bars_rgbl"] = default_cols

        self.arrayvar["scale_bt"] = 30
        self.arrayvar["scale_wt"] = 20
        self.arrayvar["scale_w"] = 25
        self.arrayvar["PCA_Matrix_Unit_transform"] = "off"

        #self.arrayvar["channel_r"] = 1
        #self.arrayvar["channel_g"] = 2
        #self.arrayvar["channel_b"] = 3
        #self.arrayvar["selection1"] = list_graphs[0]
        #self.arrayvar["selection2"] = list_graphs[1]

        # define options for opening or saving a file
        self.file_opt = options = {}
        options['defaultextension'] = '.mat'
        options['filetypes'] = [('all files', '.*'), ('matrix files', '.mat')]
        #options['initialdir'] = 'C:\\'
        options['initialfile'] = 'pca.mat'
        options['parent'] = self
        options['title'] = 'PCA matrix'

    def OnUpdateBars(self,*args):
        self.DoBars()

    def DoBars(self):
        print("Updating bars!")

    def OnUpdateSigmas(self,*args):
        self.DoSigmas()

    def DoSigmas(self):
        print("Updating sigmas!")

    def OnUpdateObjects(self,*args):
        self.UpdateObjects(update=True)

    def UpdateObjects(self, *args, **kwargs):
        print("Updating the objects...")

if __name__ == "__main__":
    app=BBDialog()
    app.SetDefaults()
    app.mainloop()

