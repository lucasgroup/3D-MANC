# -*- coding: utf-8 -*-
#
#
#  Cluster Python XTension  
#  Inspired by the ImageJ image calculator
#
#    <CustomTools>
#      <Menu name = "Brainbow plugins">
#       <Item name="Brainbow stack filter" icon="Python" tooltip="Filter stack and remove pure RGB neurons.">
#         <Command>PythonXT::XTSetup(%i)</Command>
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
import ImarisLib
import BridgeLib

#import ezatrous
#import atrous3d
import libatrous
import numpy as np

import time

###########################################################################
## Main application module
###########################################################################
class Module:
    def __init__(self,vImaris):
        self.vImaris = vImaris

        #Use a clone
        print "Making a clone..."
        self.vDataSet = vImaris.GetDataSet().Clone()
        print "  done!"

        #Setting the grid resolution
        nx = self.vDataSet.GetSizeX()
        ny = self.vDataSet.GetSizeY()
        nz = self.vDataSet.GetSizeZ()
        resx = float(self.vDataSet.GetExtendMaxX()) / nx
        resy = float(self.vDataSet.GetExtendMaxY()) / ny
        resz = float(self.vDataSet.GetExtendMaxZ()) / nz

        #Setting the grid resolution
        libatrous.set_grid(resx, resy, resz) 

        #For now, only save the parameters for the current channel. When changing channel, this data is erased.
        self.arrayvar_last = None

        #Record the channel visibility (important if you add channels)
        self.RecordVisibility()
        self.data = None

    def run(self,threshold=1,low_scale=2,high_scale=5,filter_type=1,add_lowpass=False,interactive=True):
        nx = self.vDataSet.GetSizeX()
        ny = self.vDataSet.GetSizeY()
        nz = self.vDataSet.GetSizeZ()
        miset,maset = BridgeLib.GetRange(self.vDataSet)

        print "Fetching channel data (%dx%dx%d)..." % (nx,ny,nz)
        if self.data is None:
            data = []
            for i in range(3):
                print "  channel %d/%d" % (i+1,3)
                if nz == 1:
                    d = BridgeLib.GetDataSlice(self.vDataSet,0,i,0).astype(np.float32)
                else:
                    d = BridgeLib.GetDataVolume(self.vDataSet,i,0).astype(np.float32)
                data.append(d)
            self.data = data
        else:
            print "Using cached data..."

        if interactive:
            threshold = BridgeLib.query_num("The Threshold in percent (max channels=%d)"%maset,threshold,[0,100])

        threshold = threshold / 100.
        print("Using threshold=%.2f%% full range, value=%d" % (threshold*100, maset*threshold))
        threshold = maset*threshold

        #assume rgb first three channels
        rgb = np.zeros((nx*ny*nz,3),float)

        #At least 2 channels must be above the threshold value. Otherwise, set at 0
        sum_array = None

        kernel = libatrous.get_kernel(filter_type)

        print "Filtering the channels using low_scale=%d high_scale=%d, filter=%d, add_lowpass=%d" % (low_scale,high_scale,filter_type,add_lowpass)
        for i in range(3):
            print "  channel %d/%d" % (i+1,3)
            d = self.data[i].astype(np.float32)
            d = libatrous.get_bandpass(d,low_scale-1,high_scale-1,kernel,add_lowpass)

            #Testing pixel brightness against threshold.
            if sum_array is None:
                sum_array = np.zeros(d.shape,'i')

            wh = d<threshold
            d[wh] = 0
            sum_array += wh
            rgb[:,i] = d.flat

        #At least 2 channels are below the threshold
        wh = (sum_array > 1).flatten()
        rgb[wh,:] = 0

        #Send the data back to Imaris
        ret = []
        for i in range(3):
            #save new channel
            d = rgb[:,i].reshape(sum_array.shape)
            #print d.dtype,d.shape,np.min(d),np.max(d)

            name = self.vDataSet.GetChannelName(i)+" (clean)"
            color = BridgeLib.GetChannelColorRGBA(self.vDataSet,i)
            print "Updating '%s', color=" % name,color
            channel_out = BridgeLib.FindChannel(self.vDataSet,name,create=True,color=color)
            BridgeLib.SetDataVolume(self.vDataSet,d,channel_out,self.vImaris.GetVisibleIndexT())
            ret.append(d)
 
        #Use the modified / cloned dataset
        self.vImaris.SetDataSet(self.vDataSet)

        self.rgb = rgb
        self.RestoreVisibility()
        return ret

    def RecordVisibility(self):
        #Record the channel visibility
        self.chanvis = []
        nc = self.vDataSet.GetSizeC()
        for i in range(nc):
            self.chanvis.append(self.vImaris.GetChannelVisibility(i))

    def RestoreVisibility(self):
        if self.chanvis is None:
            return

        nc = len(self.chanvis)
        #Set the channel visibility back
        for i in range(nc):
            ci = self.chanvis[i]
            self.vImaris.SetChannelVisibility(i,ci)

    
def XTSetup(aImarisId):
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

    MM = Module(vImaris)
    MM.run()

    exit(0)
