import numpy as np
import matplotlib as mpl
mpl.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
import matplotlib.patches as mpatches
from matplotlib.artist import Artist


import sys
def onHotswap():
    """
    Hotswap function

    The hotswap function
    """
    import time
    t = time.localtime(time.time())
    st = time.strftime("Hotswap: %Y-%m-%d %H:%M:%S", t)
    print st



class LineInteractor:
    """
    An line editor.

    Key-bindings

      't' toggle vertex markers on and off.  When vertex markers are on,
          you can move them, delete them


    """

    showverts = True
    epsilon = 10  # max pixel distance to count as a vertex hit

    def __init__(self,fig,ax,pt_black,pt_mid,pt_white,thickness=0.8, t0=0.1, t1=0.8, low=True, high=True, tapered=True):

        self.low = low
        self.high = high
        self.tapered = tapered
        self.background = None
        self.handle_colours = [[0,0,0],[.5,.5,.5],[1,1,1]]

        linedata = [pt_black, pt_mid, pt_white]

        self.ax = ax
        canvas = self.ax.figure.canvas

        self.t0 = t0
        self.t1 = t1
        self.thickness = thickness

        x, y = zip(*linedata)

        self.line, = ax.plot(x,y, animated=True)
        self.handles = ax.scatter(x,y, marker='s', color=self.handle_colours, edgecolors='k', animated=True)

        xr,yr = self.get_rect(x,y)

        
        self.poly = mpatches.Polygon(list(zip(xr, yr)), fill=False, animated=True)
        ax.add_patch(self.poly)
        #ax.draw_artist(self.poly)

        #do the polygon

        self._ind = None # the active vert

        canvas.mpl_connect('resize_event', self.resize_callback)
        canvas.mpl_connect('draw_event', self.draw_callback)
        canvas.mpl_connect('button_press_event', self.button_press_callback)
        canvas.mpl_connect('button_release_event', self.button_release_callback)
        canvas.mpl_connect('motion_notify_event', self.motion_notify_callback)
        #canvas.mpl_connect('key_press_event', self.key_press_callback)
        self.canvas = canvas


    def set_handle_col(self,col):
        col = col/np.max(col)
        col[col < 0 ] = 0
        col[col > 1 ] = 1
        self.handle_colours[1] = col
        self.handles.set_facecolors(self.handle_colours)

    #This is for the screenshot. given a new figure / ax, draw the polygon and line and points...
    def draw_things(self,axs):
        x,y = self.line.get_data()
        xr,yr = self.get_rect(x,y)
        poly = mpatches.Polygon(list(zip(xr, yr)), fill=False)
        axs.add_patch(poly)
        line, = axs.plot(x,y, marker='s', markersize=10, markerfacecolor='r')

    def set_parameters(self,w,t0,t1):
        self.thickness = w
        self.t0 = t0
        self.t1 = t1

        x,y = self.line.get_data()
        xr,yr = self.get_rect(x,y)
        self.poly.set_xy( list(zip(xr, yr)))

    def set_handle(self,pt_mid):
        x,y = self.line.get_data()
        xmin,xmax = self.ax.get_xlim()
        ymin,ymax = self.ax.get_ylim()
        x_ = pt_mid[0]
        if x_ < xmin:
            x_ = xmin
        elif x_ > xmax:
            x_ = xmax

        y_ = pt_mid[1]
        if y_ < ymin:
            y_ = ymin
        elif y_ > ymax:
            y_ = ymax

        x[1] = x_
        y[1] = y_

        xr,yr = self.get_rect(x,y)
        self.poly.set_xy( list(zip(xr, yr)))
        self.line.set_data(x, y)
        self.handles.set_offsets(np.c_[x,y])
        self.handles.set_facecolors(self.handle_colours)

    def get_handle(self):
        x,y = self.line.get_data()
        return x[1],y[1]

    def set_bw(self, pt_black, pt_white, pt_mid=None):
        if pt_mid is None:
            pt_mid = ((pt_black[0]+pt_white[0]) / 2, (pt_black[1]+pt_white[1]) / 2)

        linedata = np.array([pt_black, pt_mid, pt_white])
        x,y = linedata[:,0],linedata[:,1]
        xr,yr = self.get_rect(x,y)
        self.poly.set_xy( list(zip(xr, yr)))
        self.line.set_data(x, y)
        self.handles.set_offsets(np.c_[x,y])
        self.handles.set_facecolors(self.handle_colours)

    def distance(self,pt1,pt2):
        x1,y1 = pt1
        x2,y2 = pt2
        return np.sqrt((x1-x2)*(x1-x2)+(y1-y2)*(y1-y2))

    def get_rect(self,x,y):
        low = self.low
        high = self.high

        if self.tapered == True:
            t0 = self.t0
            t1 = self.t1
        else:
            t0 = 1.
            t1 = 0.

        #Is the middle point on top of either pt black or pt white?
        d1 = self.distance((x[0],y[0]),(x[1],y[1]))
        d2 = self.distance((x[1],y[1]),(x[2],y[2]))
        d3 = self.distance((x[0],y[0]),(x[2],y[2]))

        if (d1 == 0) or (d2 == 0):
            if d1 == 0:
                t0 = 0

            if d2 == 0:
                t1 = 0

            x0,x1 = x[0],x[2]
            y0,y1 = y[0],y[2]

            x0 = x1*self.t0+x0*(1.-t0)
            y0 = y1*self.t0+y0*(1.-t0)

            dx = x1 - x0 #delta x
            dy = y1 - y0 #delta y
            linelength = np.sqrt(dx * dx + dy * dy)
            dx /= linelength
            dy /= linelength
            #Ok, (dx, dy) is now a unit vector pointing in the direction of the line
            #A perpendicular vector is given by (-dy, dx)

            px0 = 0.5 * self.thickness * t0 * dy #perpendicular vector with lenght thickness * 0.5
            py0 = 0.5 * self.thickness * t0 * dx
            px1 = 0.5 * self.thickness * (1.-t1) * dy #perpendicular vector with lenght thickness * 0.5
            py1 = 0.5 * self.thickness * (1.-t1) * dx

            #print px0,py0,px1,py1

            xs = [x0-px0,x1-px1,x1+px1,x0+px0]
            ys = [y0+py0,y1+py1,y1-py1,y0-py0]

            return xs,ys



        x0,x1 = x[0],x[1]
        y0,y1 = y[0],y[1]

        x0 = x1*self.t0+x0*(1.-self.t0)
        y0 = y1*self.t0+y0*(1.-self.t0)

        dx = x1 - x0 #delta x
        dy = y1 - y0 #delta y
        linelength = np.sqrt(dx * dx + dy * dy)
        dx /= linelength
        dy /= linelength
        #Ok, (dx, dy) is now a unit vector pointing in the direction of the line
        #A perpendicular vector is given by (-dy, dx)
        if self.tapered == True:
            t0 = self.t0
            t1 = self.t1
        else:
            t0 = 1.
            t1 = 0.

        px0 = 0.5 * self.thickness * t0 * dy #perpendicular vector with lenght thickness * 0.5
        py0 = 0.5 * self.thickness * t0 * dx
        px1 = 0.5 * self.thickness * dy #perpendicular vector with lenght thickness * 0.5
        py1 = 0.5 * self.thickness * dx

        #print px0,py0,px1,py1

        xs1 = [x0-px0,x1-px1,x1+px1,x0+px0]
        ys1 = [y0+py0,y1+py1,y1-py1,y0-py0]

        x0,x1 = x[1],x[2]
        y0,y1 = y[1],y[2]

        x1 = x1*self.t1+x0*(1.-self.t1)
        y1 = y1*self.t1+y0*(1.-self.t1)

        dx = x1 - x0 #delta x
        dy = y1 - y0 #delta y
        linelength = np.sqrt(dx * dx + dy * dy)
        dx /= linelength
        dy /= linelength
        #Ok, (dx, dy) is now a unit vector pointing in the direction of the line
        #A perpendicular vector is given by (-dy, dx)
        px0 = 0.5 * self.thickness * dy #perpendicular vector with lenght thickness * 0.5
        py0 = 0.5 * self.thickness * dx
        px1 = 0.5 * self.thickness * (1.-t1) * dy #perpendicular vector with lenght thickness * 0.5
        py1 = 0.5 * self.thickness * (1.-t1) * dx

        xs2 = [x0-px0,x1-px1,x1+px1,x0+px0]
        ys2 = [y0+py0,y1+py1,y1-py1,y0-py0]

        if low==True and high==True:
            #calculate px1, py1
            #these are your 4 points (two for each of the intersecting linges):
            x1,x2,x3,x4 = xs1[0],xs1[1],xs2[0],xs2[1]
            y1,y2,y3,y4 = ys1[0],ys1[1],ys2[0],ys2[1]
            D = ((x1-x2)*(y3-y4)-(y1-y2)*(x3-x4))

            if D == 0:
                #Between the two

                if d1 == 0:
                    xs = xs2
                    ys = ys2
                elif d2 == 0:
                    xs = xs1
                    ys = ys1
                elif d1 > d3:
                    xs = xs1
                    ys = ys1
                elif d2 > d3:
                    xs = xs2
                    ys = ys2
                else: #if d1 <= d3 and d2 <= d3:
                    xs = [xs1[0], xs2[1], xs2[2], xs1[3]]
                    ys = [ys1[0], ys2[1], ys2[2], ys1[3]]

            else:
                px1 = ((x1*y2-y1*x2)*(x3-x4)-(x1-x2)*(x3*y4-y3*x4))/D
                py1 = ((x1*y2-y1*x2)*(y3-y4)-(y1-y2)*(x3*y4-y3*x4))/D
            
                x1,x2,x3,x4 = xs1[2],xs1[3],xs2[2],xs2[3]
                y1,y2,y3,y4 = ys1[2],ys1[3],ys2[2],ys2[3]

                D = ((x1-x2)*(y3-y4)-(y1-y2)*(x3-x4))

                px2 = ((x1*y2-y1*x2)*(x3-x4)-(x1-x2)*(x3*y4-y3*x4))/D
                py2 = ((x1*y2-y1*x2)*(y3-y4)-(y1-y2)*(x3*y4-y3*x4))/D

                xs = [xs1[0], px1, xs2[1], xs2[2], px2, xs1[3]]
                ys = [ys1[0], py1, ys2[1], ys2[2], py2, ys1[3]]
        elif low==True:
            xs = xs1
            ys = ys1
        else:
            xs = xs2
            ys = ys2

        return xs,ys

    def resize_callback(self,event):
        print "resizing..."
        self.background = None

    def draw_callback(self, event):
        print "Storing background..."
        if self.background is None:
            self.background = self.canvas.copy_from_bbox(self.ax.bbox)

        self.ax.draw_artist(self.poly)
        self.ax.draw_artist(self.line)
        self.ax.draw_artist(self.handles)
        self.canvas.blit(self.ax.bbox)
        
    def key_press_callback(self, event):
        'whenever a key is pressed'
        if not event.inaxes: return
        if event.key=='t':
            self.showverts = not self.showverts
            self.line.set_visible(self.showverts)
            if not self.showverts: self._ind = None

        self.canvas.draw()
        
    def get_ind_under_point(self, event):
        'get the index of the vertex under point if within epsilon tolerance'

        # display coords
        #print ">>>>",self.line.get_data()
        xy = np.asarray(zip(*self.line.get_data()) )
        xyt = self.line.get_transform().transform(xy)
        xt, yt = xyt[:, 0], xyt[:, 1]
        d = np.sqrt((xt-event.x)**2 + (yt-event.y)**2)
        ind = d.argmin()

        if d[ind]>=self.epsilon:
            ind = None

        return ind

    def button_press_callback(self, event):
        'whenever a mouse button is pressed'
        if not self.showverts: return
        if event.inaxes==None: return
        if event.button != 1: return
        ind = self.get_ind_under_point(event)
        if ind == 0 or ind == 2:
            ind = None

        if ind is not None:
            self.do_press()

        self._ind = ind

    def button_release_callback(self, event):
        'whenever a mouse button is released'
        if not self.showverts: return
        if event.button != 1: return

        if self._ind is not None:
            self.do_release()

        self._ind = None

    def key_press_callback(self, event):
        'whenever a key is pressed'
        if not event.inaxes: return
        if event.key=='t':
            self.showverts = not self.showverts
            self.line.set_visible(self.showverts)
            if not self.showverts: self._ind = None

        self.canvas.draw()

    def motion_notify_callback(self, event):
        'on mouse movement'
        if not self.showverts: return
        if self._ind is None: return
        if event.inaxes is None: return
        if event.button != 1: return
        x,y = self.line.get_data()
        #print x[self._ind], y[self._ind], '!=',
        x[self._ind] = event.xdata
        y[self._ind] = event.ydata
        xr,yr = self.get_rect(x,y)
        self.poly.set_xy( list(zip(xr, yr)))

        self.line.set_data(x, y)
        self.handles.set_offsets(np.c_[x,y])
        self.handles.set_facecolors(self.handle_colours)
        x,y = self.line.get_data()

        #print x[self._ind], y[self._ind], '==',
        self.canvas.restore_region(self.background)
        self.ax.draw_artist(self.poly)
        self.ax.draw_artist(self.line)
        self.ax.draw_artist(self.handles)
        self.canvas.blit(self.ax.bbox)
        x,y = self.line.get_data()
        #print x[self._ind], y[self._ind]

    def redraw(self,show=True):
        if self.background is None:
            return
        self.canvas.restore_region(self.background)
        if show:
            self.ax.draw_artist(self.poly)
            self.ax.draw_artist(self.line)
            self.ax.draw_artist(self.handles)
        self.canvas.blit(self.ax.bbox)

    def is_inside(self,pts):
        #contains_points(points, transform=None, radius=0.0)
        #Returns a bool array which is True if the path contains the corresponding point.
        #If transform is not None, the path will be transformed before performing the test.
        #radius allows the path to be made slightly larger or smaller.
        path = self.poly.get_path()
        wh = path.contains_points(pts, transform=None, radius=0.0)
        return wh

    def get_poly(self):
        return np.array(self.poly.get_xy(),np.float32)

    def do_press(self):
        print "pressed!"

    def do_release(self):
        #x,y = self.line.get_data()
        #print x
        #print y
        print "released!"

def main(argv=None):
    if argv is None:
        argv = sys.argv

    layout = (2,2)
    fig,subplots = plt.subplots(*layout,figsize=(15,15))

    interactors = []
    for ax in subplots.flat:
        ptb = (-1, -5)
        ptw = (0, 0)
        ptm = (5,1)
        t0 = 0.2
        t1 = 0.8

        interactors.append(LineInteractor(fig, ax, ptb, ptm, ptw, t0=t0, t1=t1))
        ax.set_title('drag vertices to update line')
        ax.set_xlim(-10,10)
        ax.set_ylim(-10,10)
        ax.set_aspect('equal')

    plt.show()

if __name__ == '__main__':
    main()

