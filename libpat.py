import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.patches import Ellipse
import mdp
import colorsys
from scipy.stats import gaussian_kde
import time

try:
    import nativebb
except:
    print "nativebb could not be found. Download / Install from http://github.com/lucasgroup/nativebb"

try:
    import libatrous
except:
    print "libatrous could not be found. Download / Install from http://github.com/zindy/libatrous"


class Analysis(object):
    def __init__(self,nbit=8):
        self.maxval = np.power(2,nbit)-1
        self.nbit = nbit
        self.normalise()
        self.sel_indexes = None

    def set_ssize(self,ssize):
        if ssize > 0:
            n = self.rgb_pca.shape[0] #np.product(self.r.shape)
            #print "n=%d" % n

            if 0:
                #This is just for display, doesn't matter if several crosses overlap.
                print ">>> From %d points, displaying %d" % (n, ssize)
                self.sel_indexes = np.random.choice(n,ssize) #,replace=False)
            elif 1:
                print ">>> Using Colour deduplication..."
                # This one is a bit more clever and tries grid deduplication
                r = self.rgb_values[:,0].astype(np.uint16)
                g = self.rgb_values[:,1].astype(np.uint16)
                b = self.rgb_values[:,2].astype(np.uint16)

                #Need at least 10 points in the grid location
                t_truth = 3
                self.sel_indexes = nativebb.dedupcol_indexes(r,g,b,self.nbit,7, t_truth)
                print "    from %d to %d unique." % (n,self.sel_indexes.shape[0])

            else:
                f = np.sum(self.rgb_values,axis=1)
                print f.shape
                mid = np.max(f) / 20
                truth = f < mid
                wh1 = np.nonzero(truth)[0]
                print wh1.shape
                wh2 = np.nonzero(1-truth)[0]
                print wh2.shape
                n1 = wh1.shape[0]
                n2 = wh2.shape[0]
                m1 = ssize/5
                m2 = ssize-m1

                if m1 > n1:
                    m1 = n1
                    ind1 = wh1
                else:
                    ind1 = np.random.choice(wh1,m1) #] wh1[np.random.choice(n1,ssize/4)]

                if m2 > n2:
                    m2 = n2
                    ind2 = wh2
                    percent = 100.
                else:
                    ind2 = np.random.choice(wh2,m2) #] wh1[np.random.choice(n1,ssize/4)]

                print "For r+g+b < %d, kept %d values (%.1f percent of the %d available pixels)" % (mid,m1,100.*m1/n1, n1)
                print "For r+g+b >= %d, kept %d values (%.1f percent of the %d available pixels)" % (mid,m2,100.*m2/n2, n2)

                self.sel_indexes = np.hstack((ind1,ind2))
                m = self.sel_indexes.shape[0]
                print "Overall kept %d out of %d (%.1f percent)" % (m,n,100.*m/n)
        else:
            self.sel_indexes = None

    def init_pca(self):
        #self.pcanode = mdp.nodes.PCANode()
        self.pcanode = mdp.nodes.NIPALSNode()
        rgb_,wh = self.get_pixels(threshold=0,remove_bg=True)
        print "begin pcanode.train()..."
        self.pcanode.train(rgb_)
        print "begin conversion..."
        self.rgb_pca = self.pcanode(rgb_)
        self.rgb_values = rgb_
        print "done!"

    def normalise(self):
        if self.r is None:
            return
        self.r[self.r < 0] = 0
        self.r[self.r > self.maxval] = self.maxval
        self.g[self.g < 0] = 0
        self.g[self.g > self.maxval] = self.maxval
        self.b[self.b < 0] = 0
        self.b[self.b > self.maxval] = self.maxval

    def add_poisson(self,lam=50):
        shape = self.r.shape
        self.r += np.random.poisson(lam,shape)
        self.g += np.random.poisson(lam,shape)
        self.b += np.random.poisson(lam,shape)
        self.normalise()
        return self.r, self.g, self.b

    def add_gaussian(self,sigma):
        print "adding noise!"
        if type(sigma) is list:
            sigma_r, sigma_g, sigma_b = sigma
        else:
            sigma_r = sigma
            sigma_g = sigma
            sigma_b = sigma

        shape = self.r.shape
        mean = 0
        self.r += np.random.normal(mean,sigma_r,shape).reshape(shape)
        self.g += np.random.normal(mean,sigma_g,shape).reshape(shape)
        self.b += np.random.normal(mean,sigma_b,shape).reshape(shape)
        self.normalise()
        return self.r, self.g, self.b

    def add_speckle(self):
        shape = self.r.shape
        self.r += self.r * np.random.randn(*shape).reshape(shape)
        self.g += self.g * np.random.randn(*shape).reshape(shape)
        self.b += self.b * np.random.randn(*shape).reshape(shape)
        self.normalise()
        return self.r, self.g, self.b

    def display(self,names=["Red","Green","Blue"]):
        #This displays the Green and Red projections side by side:
        fig, axs = plt.subplots(1,4, figsize=(20,10))

        axs[0].set_title(names[0]);
        axs[1].set_title(names[1]);
        axs[2].set_title(names[2]);
        axs[3].set_title("RGB");

        if self.r.ndim == 2:
            r,g,b = self.r, self.g, self.b
        elif self.r.ndim == 3:
            r = np.max(self.r,axis=0)
            g = np.max(self.g,axis=0)
            b = np.max(self.b,axis=0)
        else:
            raise IndexError("image size error: no more than 3 dimensions")

        rgb = np.dstack((r,g,b))

        im1 = axs[0].imshow(r,cmap="gray")
        im2 = axs[1].imshow(g,cmap="gray")
        im3 = axs[2].imshow(b,cmap="gray")

        #ma = np.max(rgb)
        ma = self.maxval
        rgb_uint8 = (rgb * 255. / ma).astype(np.uint8)

        im4 = axs[3].imshow(rgb_uint8)
        plt.show()


    def get_handle_from_pos(self,x,y):
        x = int(round(x))
        y = int(round(y))
        rgb = np.array([[self.r[y,x],self.g[y,x],self.b[y,x]]])
        #print ">>> rgb",rgb
        rgb_pca = self.pcanode(rgb)[0]
        return rgb_pca

    #dtype hex, float, uint8
    def get_rgb_col(self,handle,dtype=str):
        v = self.pcanode.inverse(np.array([handle]))[0]
        ma = np.max(v)
        if ma > 0:
            vv = (v/ma * 255.)
            vv[vv < 0] = 0
            vv[vv > 255] = 255

        r,g,b = vv.astype(np.uint8)

        if dtype == int:
            ret = [r, g, b]
        elif dtype == float:
            return v #tuple(v.tolist())
        else:
            ret = "#%02x%02x%02x" % (r,g,b)

        return ret

    def get_rgb_col_(self,wh,dtype=str):
        wh = wh.reshape(self.r.shape)
        if not True in wh:
            return "#000000"

        rmax = float(np.max(self.r[wh]))/self.maxval
        gmax = float(np.max(self.g[wh]))/self.maxval
        bmax = float(np.max(self.b[wh]))/self.maxval
        rmean = float(np.mean(self.r[wh]))/self.maxval
        gmean = float(np.mean(self.g[wh]))/self.maxval
        bmean = float(np.mean(self.b[wh]))/self.maxval

        #rmean = int(255.*(rmean+rmax)/2)
        #gmean = int(255.*(gmean+gmax)/2)
        #bmean = int(255.*(bmean+bmax)/2)

        rmean = rmean * 1.5
        gmean = gmean * 1.5
        bmean = bmean * 1.5
        if rmean > 1: rmean = 1
        if gmean > 1: gmean = 1
        if bmean > 1: bmean = 1

        if dtype == float:
            ret = rmean, gmean, bmean
        else:
            rmean = int(255*rmean)
            gmean = int(255*gmean)
            bmean = int(255*bmean)
            if dtype == int:
                ret = rmean, gmean, bmean
            else:
                ret = "#%02x%02x%02x" % (rmean,gmean,bmean)

        return ret

    #takes where, displays a pic
    def get_rgb_image(self,wh=None):
        if wh is None:
            r,g,b = self.r.copy(), self.g.copy(), self.b.copy()
        else:
            r = np.zeros(self.r.shape,self.r.dtype)
            g = np.zeros(self.g.shape,self.g.dtype)
            b = np.zeros(self.b.shape,self.b.dtype)

            wh = wh.reshape(r.shape)
            r[wh] = self.r[wh]
            g[wh] = self.g[wh]
            b[wh] = self.b[wh]

        if r.ndim == 3:
            r = np.max(r,axis=0)
            g = np.max(g,axis=0)
            b = np.max(b,axis=0)

        rgb = np.dstack((r,g,b))
        ma = self.maxval
        rgb_uint8 = (rgb * 255. / ma).astype(np.uint8)
        return rgb_uint8

    def display_rgb(self,axs=None,wh=None,im=None):
        if axs is None and im is None:
            return
        rgb_uint8 = self.get_rgb_image(wh=wh)

        if im is None:
            im = axs.imshow(rgb_uint8) #, animated=True)
        else:
            im.set_array(rgb_uint8)

        return im

    #This is to get back the luninosity data to push back into imaris
    def get_luma(self,wh=None):
        r = self.r.flatten()
        g = self.g.flatten()
        b = self.b.flatten()
        rgb = np.vstack([r,g,b])
        ma = np.max(rgb,axis=0)
        mi = np.min(rgb,axis=0)
        l = ((ma+mi)/2).reshape(self.r.shape)

        if not wh is None:
            wh = wh.reshape(self.r.shape)
            ll = np.zeros(self.r.shape,self.r.dtype)
            ll[wh] = l[wh]
            ll = (ll/float(np.max(ll))*self.maxval).astype(self.r.dtype)

        return ll

    def get_pixels(self, threshold=0, remove_bg=True):
        #sum_rgb = np.ravel(self.r + self.g + self.b)
        #rgb = np.dstack((self.r.flat/sum_rgb,self.g.flat/sum_rgb,self.b.flat/sum_rgb))[0]
        rgb = np.dstack((self.r.flat,self.g.flat,self.b.flat))[0]
        tt = None

        if remove_bg:
            tt = np.sum(rgb > threshold,axis=1) > 0
            n = rgb.shape[0]
            m = np.sum(tt)
            rgb = rgb[tt].astype(float)
            print "Threshold is %d. Kept %d out of %d (%.1f percent)" % (threshold,m,n,100.*m/n)

        return rgb,tt

    def plot_histogram(self,threshold=0, remove_bg=True):
        titles = ["Red", "Green", "Blue"]
        colors = ["red","green","blue"]
        rgb_,wh = self.get_pixels(threshold, remove_bg)

        fig, axs = plt.subplots(1,3, figsize=(20,5))
        #fig.subplots_adjust(hspace=20)
        for i in range(3):
            n, bins, patches = axs[i].hist(rgb_[:,i], 100, normed=1, facecolor=colors[i], alpha=0.75)
            axs[i].set_xlim(threshold,self.maxval+2)
            axs[i].set_title(titles[i])
        plt.show()

    def plot_pca(self, threshold=10, remove_bg=True,unit=True):
        rgb_,wh = self.get_pixels(threshold,remove_bg)
        if unit is True:
            rgb_pca = rgb_
        else:
            rgb_pca = self.pcanode(rgb_)

        #rgb_pca = mdp.pca(rgb_.astype(np.float))

        fig, axs = plt.subplots(1,3, figsize=(20,5))
        for i in range(3):
            print "Component %d range: %f %f" % (i+1,np.min(rgb_pca[:,i]),np.max(rgb_pca[:,i]))

            n, bins, patches = axs[i].hist(rgb_pca[:,i], 50, normed=1, range=[np.min(rgb_pca[:,i]),np.max(rgb_pca[:,i])],facecolor='green', alpha=0.75)
            #axs[i].set_title("PC%d" % (i+1));
            axs[i].set_title("Component %d" % (i+1));
        plt.show()

    def plot_zero(self,axs,c0,c1, unit=True):
        yzero = np.zeros(3)
        if not unit:
            yzero = self.pcanode([yzero])[0]
        print "(0,0,0)",yzero

        el = Ellipse((yzero[c0],yzero[c1]), 5, 5,edgecolor='k',facecolor='r')
        axs.add_patch(el)

        axs.annotate('(0,0,0)', xy=(yzero[c0],yzero[c1]), xycoords='data',
            xytext=(-100, 50), textcoords='offset points',
            size=15,
            # bbox=dict(boxstyle="round", fc="0.8"),
            arrowprops=dict(arrowstyle="fancy",
                            fc="0.6", ec="none",
                            patchB=el,
                            connectionstyle="angle3,angleA=0,angleB=-90"),
            )

    def plot_one(self,axs,c0,c1,unit=True):
        yzero = np.ones(3)*self.maxval
        if not unit:
            yzero = self.pcanode([yzero])[0]
        print "(1,1,1)",yzero

        el = Ellipse((yzero[c0],yzero[c1]), 5, 5,edgecolor='k',facecolor='g')
        axs.add_patch(el)

        axs.annotate('(1,1,1)', xy=(yzero[c0],yzero[c1]), xycoords='data',
            xytext=(-100, -50), textcoords='offset points',
            size=15,
            # bbox=dict(boxstyle="round", fc="0.8"),
            arrowprops=dict(arrowstyle="fancy",
                            fc="0.6", ec="none",
                            patchB=el,
                            connectionstyle="angle3,angleA=0,angleB=-90"),
            )

    def plot_pca2d(self, threshold=10, remove_bg=True, cmap="Paired", xlim=None, ylim=None,c0=0,c1=1,axs=None,unit=True):
        rgb_,wh = self.get_pixels(threshold, remove_bg)
        if unit is True:
            rgb_pca = rgb_
        else:
            rgb_pca = self.pcanode(rgb_)
        #rgb_pca = mdp.pca(rgb_.astype(np.float))

        if xlim is None:
            mi0, ma0 = np.min(rgb_pca[:,c0]), np.max(rgb_pca[:,c0])
        else:
            mi0, ma0 = xlim
        b0 = (ma0-mi0)*.1

        if ylim is None:
            mi1, ma1 = np.min(rgb_pca[:,c1]), np.max(rgb_pca[:,c1])
        else:
            mi1, ma1 = ylim
        b1 = (ma1-mi1)*.1

        print np.min(rgb_pca[:,c1]), np.max(rgb_pca[:,c1])

        #bin size
        bins0 = 100
        bins1 = 100
        H, xedges, yedges = np.histogram2d(rgb_pca[:,c1], rgb_pca[:,c0],range=[[mi1-b1,ma1+b1],[mi0-b0,ma0+b0]],bins=[bins1,bins0])
        H, xedges, yedges = np.histogram2d(rgb_pca[:,c1], rgb_pca[:,c0],range=[[mi1-b1,ma1+b1],[mi0-b0,ma0+b0]],bins=[bins1,bins0])

        if axs is None:
            fig, axs = plt.subplots(1,1, figsize=(10,10))

        im = axs.imshow(H,cmap=cmap,origin='lower',extent=[mi0-b0,ma0+b0,mi1-b1,ma1+b1])
        self.plot_zero(axs,c0,c1)
        self.plot_one(axs,c0,c1)
        axs.set_aspect(1)

        if is_unit:
            labels = ["Red", "Green", "Blue"]
            xs = labels[c0]
            ys = labels[c1]
        else:
            xs = "Component %d" % (c0+1)
            ys = "Component %d" % (c1+1)
        axs.set_xlabel(xs)
        axs.set_ylabel(ys)

    #wh is the true/false selection in the pca2d subset
    def get_selection(self,wh):
        ret = np.zeros(self.r.size,bool)
        t = time.time()
        print "zeroing..."
        ret[self.wh_selection[np.nonzero(wh)[0]]] = True
        print "done zeroing...",time.time()-t

        return ret

    def do_pca2d(self,threshold=10, remove_bg=True,unit=True): 
        self.rgb_selection,wh_selection = self.get_pixels(threshold, remove_bg)
        self.wh_selection = np.nonzero(wh_selection)[0]

        if unit:
            self.rgb_pca = self.rgb_selection.copy()
        else:
            self.rgb_pca = self.pcanode(self.rgb_selection)

    def plot_pca2d_dots(self, xlim=None, ylim=None, c0=0, c1=1, axs=None, scat=None, fullset=False,unit=True,handle=None,alpha=0.2,marker=10):
        if unit:
            ptb = np.zeros(3)
            ptw = np.ones(3)*self.maxval
        else:
            ptb = self.pcanode(np.zeros((1,3))*self.maxval)[0]
            ptw = self.pcanode(np.ones((1,3))*self.maxval)[0]

        rgb_pca = np.vstack([self.rgb_pca,ptb,ptw])
        if handle is not None:
            rgb_pca = np.vstack([rgb_pca,handle])


        if xlim is None:
            rgb_pca
            mi0, ma0 = np.min(rgb_pca[:,c0]), np.max(rgb_pca[:,c0])
            mi0 = np.min([mi0,ptb[c0],ptw[c0]])
            ma0 = np.max([ma0,ptb[c0],ptw[c0]])
            b0 = (ma0-mi0)*.1
            xlim = [mi0-b0,ma0+b0]
        else:
            mi0, ma0 = xlim

        if ylim is None:
            mi1, ma1 = np.min(rgb_pca[:,c1]), np.max(rgb_pca[:,c1])
            mi1 = np.min([mi1,ptb[c1],ptw[c1]])
            ma1 = np.max([ma1,ptb[c1],ptw[c1]])
            b1 = (ma1-mi1)*.1
            ylim = [mi1-b1,ma1+b1]
        else:
            mi1, ma1 = ylim

        x = self.rgb_pca[:,c0]
        y = self.rgb_pca[:,c1]
        ma = float(self.maxval)
        if self.sel_indexes is not None and fullset==False:
            #This is just for display, doesn't matter if several crosses overlap.
            indexes = self.sel_indexes
            ssize = indexes.shape[0]
            print "Will plot %d crosses" % ssize
            x = x[indexes]
            y = y[indexes]
            rgb_selection = np.zeros((ssize,4),float)
            rgb_selection[:,0] = self.rgb_selection[indexes,0]/ma
            rgb_selection[:,1] = self.rgb_selection[indexes,1]/ma
            rgb_selection[:,2] = self.rgb_selection[indexes,2]/ma
            rgb_selection[:,3] = alpha
        else:
            rgb_selection = self.rgb_selection/ma


        if axs is None and scat is None:
            fig, axs = plt.subplots(1,1, figsize=(10,10))

        #self.plot_zero(axs,c0,c1)
        #self.plot_one(axs,c0,c1)
        if scat is None:
            scat = axs.scatter(x,y, s=30, marker='+',color=rgb_selection,alpha=alpha)
            #scat = axs.scatter(x,y, s=marker, marker='.', edgecolors=None, color=rgb_selection,alpha=alpha)
        else:
            scat.set_offsets( np.array(zip(x, y)))
            scat.set_color(rgb_selection)

        if unit:
            labels = ["Red", "Green", "Blue"]
            xs = labels[c0]
            ys = labels[c1]
        else:
            xs = "Component %d" % (c0+1)
            ys = "Component %d" % (c1+1)
        axs.set_xlabel(xs)
        axs.set_ylabel(ys)

        if xlim is not None: axs.set_xlim(xlim[0],xlim[1])
        if ylim is not None: axs.set_ylim(ylim[0],ylim[1])

        return scat

    def update_3d_dots(self, scat, selected, alpha=0.2):
        ma = float(self.maxval)
        print np.min(selected),np.max(selected)

        rgb_selection = self.rgb_selection.copy()
        rgb_selection[np.invert(selected),:] = 0

        if self.sel_indexes is not None:
            #This is just for display, doesn't matter if several crosses overlap.
            indexes = self.sel_indexes
            ssize = indexes.shape[0]
            rgb = np.zeros((ssize,4),float)
            rgb[:,0] = rgb_selection[indexes,0]/ma
            rgb[:,1] = rgb_selection[indexes,1]/ma
            rgb[:,2] = rgb_selection[indexes,2]/ma
            rgb[:,3] = alpha
        else:
            rgb = rgb_selection

        print "update the colours?"
        scat.set_edgecolors(rgb)
        #scat.set_colors(rgb)
        scat.changed()



    def plot_pca3d_dots(self, xlim=None, ylim=None, zlim=None, axs=None, scat=None, fullset=False,unit=True):
        c0 = 0
        c1 = 1
        c2 = 2

        if unit:
            ptb = np.zeros(3)
            ptw = np.ones(3)
        else:
            ptb = self.pcanode(np.zeros((1,3))*self.maxval)[0]
            ptw = self.pcanode(np.ones((1,3))*self.maxval)[0]

        if xlim is None:
            mi0, ma0 = np.min(self.rgb_pca[:,c0]), np.max(self.rgb_pca[:,c0])
            mi0 = np.min([mi0,ptb[c0],ptw[c0]])
            ma0 = np.max([ma0,ptb[c0],ptw[c0]])
            b0 = (ma0-mi0)*.1
            xlim = [mi0-b0,ma0+b0]
        else:
            mi0, ma0 = xlim

        if ylim is None:
            mi1, ma1 = np.min(self.rgb_pca[:,c1]), np.max(self.rgb_pca[:,c1])
            mi1 = np.min([mi1,ptb[c1],ptw[c1]])
            ma1 = np.max([ma1,ptb[c1],ptw[c1]])
            b1 = (ma1-mi1)*.1
            ylim = [mi1-b1,ma1+b1]
        else:
            mi1, ma1 = ylim

        if zlim is None:
            mi2, ma2 = np.min(self.rgb_pca[:,c2]), np.max(self.rgb_pca[:,c2])
            mi2 = np.min([mi2,ptb[c2],ptw[c2]])
            ma2 = np.max([ma2,ptb[c2],ptw[c2]])
            b2 = (ma2-mi2)*.1
            zlim = [mi2-b2,ma2+b2]
        else:
            mi2, ma2 = zlim

        x = self.rgb_pca[:,c0]
        y = self.rgb_pca[:,c1]
        z = self.rgb_pca[:,c2]

        ma = float(self.maxval)
        alpha = 0.2
        if self.sel_indexes is not None and fullset==False:
            #This is just for display, doesn't matter if several crosses overlap.
            indexes = self.sel_indexes
            ssize = indexes.shape[0]
            x = x[indexes]
            y = y[indexes]
            z = z[indexes]
            rgb_selection = np.zeros((ssize,3),float)
            rgb_selection[:,0] = self.rgb_selection[indexes,0]/ma
            rgb_selection[:,1] = self.rgb_selection[indexes,1]/ma
            rgb_selection[:,2] = self.rgb_selection[indexes,2]/ma
            #rgb_selection[:,3] = alpha
        else:
            rgb_selection = self.rgb_selection/ma


        if axs is None and scat is None:
            fig, axs = plt.subplots(1,1, figsize=(10,10), projection='3d')

        #self.plot_zero(axs,c0,c1)
        #self.plot_one(axs,c0,c1)
        if scat is None:
            scat = axs.scatter(x,y,z, s=10, edgecolor='None', marker='+', c=rgb_selection,alpha=alpha, linewidth=1)
        else:
            scat.set_offsets( np.array(zip(x, y, z)))
            scat.set_color(rgb_selection)
            scat.changed()

        axs.set_xlabel("Component %d" % (c0+1))
        axs.set_ylabel("Component %d" % (c1+1))
        axs.set_zlabel("Component %d" % (c2+1))

        if xlim is not None: axs.set_xlim3d(xlim[0],xlim[1])
        if ylim is not None: axs.set_ylim3d(ylim[0],ylim[1])
        if zlim is not None: axs.set_zlim3d(zlim[0],zlim[1])
        axs.view_init(25,-110)

        return scat

    def plot_pca2d_density(self, xlim=None, ylim=None, c0=0, c1=1, axs=None, scat=None):
        ptb = self.pcanode(np.zeros((1,3))*self.maxval)[0]
        ptw = self.pcanode(np.ones((1,3))*self.maxval)[0]
        if xlim is None:
            mi0, ma0 = np.min(self.rgb_pca[:,c0]), np.max(self.rgb_pca[:,c0])
        else:
            mi0, ma0 = xlim
        b0 = (ma0-mi0)*.1

        if ylim is None:
            mi1, ma1 = np.min(self.rgb_pca[:,c1]), np.max(self.rgb_pca[:,c1])
        else:
            mi1, ma1 = ylim
        b1 = (ma1-mi1)*.1

        x = self.rgb_pca[:,c0]
        y = self.rgb_pca[:,c1]

        if axs is None and scat is None:
            fig, axs = plt.subplots(1,1, figsize=(10,10))

        #self.plot_zero(axs,c0,c1)
        #self.plot_one(axs,c0,c1)
        ma = float(self.maxval)

        # Calculate the point density
        xy = np.vstack([x[::100],y[::100]])
        z = gaussian_kde(xy)(xy)

        # Sort the points by density, so that the densest points are plotted last
        idx = z.argsort()
        x, y, z = x[idx], y[idx], z[idx]

        if scat is None:
            scat = axs.scatter(x, y, marker='o', c=z, s=30, edgecolor='')

        #axs.scatter(x,y, marker='+',color=rgb_/ma,alpha=0.1)
        axs.set_xlabel("Component %d" % (c0+1))
        axs.set_ylabel("Component %d" % (c1+1))

        if xlim is not None: axs.set_xlim(xlim[0],xlim[1])
        if ylim is not None: axs.set_ylim(ylim[0],ylim[1])

        return scat

class Pattern(Analysis):
    def __init__(self,size=(512,512),nbit=8):
        self.set_size(size)
        Analysis.__init__(self,nbit)

    def set_size(self,size):
        self.size = size
        self.r = np.zeros(self.size,float)
        self.g = np.zeros(self.size,float)
        self.b = np.zeros(self.size,float)


    def set_gradients(self,colors=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]],maxl=None):
        ncol = len(colors)
        bandwidth = self.size[1]/ncol/2
        self.r[:] = 0
        self.g[:] = 0
        self.b[:] = 0
        for i in range(ncol):
            arr = colors[i]
            h,l,s = colorsys.rgb_to_hls(arr[0],arr[1],arr[2])
            if len(arr) == 4:
                ml = arr[3]
            elif maxl is None:
                ml = l
            else:
                ml = maxl
            larr = np.linspace(0, ml, num=bandwidth/2)

            #larr = np.sqrt(larr)
            larr = larr*larr
            larr = np.concatenate((larr,larr[::-1]))
            bw = larr.shape[0]

            for j in range(bw):
                k = i*bw*2+j+bw/2
                r,g,b = colorsys.hls_to_rgb(h,larr[j],s)
                self.r[:,k] = self.maxval*r
                self.g[:,k] = self.maxval*g
                self.b[:,k] = self.maxval*b

        self.normalise()
        return self.r, self.g, self.b

    def set_colors(self,colors=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]):
        arr = np.array(colors,'f')
        shape = arr.shape
        ncol = shape[0]
        bandwidth = self.size[1]/ncol/2
        for i in range(ncol):
            bf = i*bandwidth*2
            bt = i*bandwidth*2+bandwidth
            self.r[:,bf:bt] = self.maxval*arr[i,0]
            self.g[:,bf:bt] = self.maxval*arr[i,1]
            self.b[:,bf:bt] = self.maxval*arr[i,2]

        self.normalise()
        return self.r, self.g, self.b

class Image(Analysis):
    def __init__(self,nbit=8):
        self.nbit = nbit

    def get_bandpass(self, input_array, scale1, scale2, kernel, lowpass = False):
        output = np.zeros(input_array.shape, np.float32)
        lowpass = input_array.astype(np.float32)
        for i in range(scale2+1):
            bandpass,lowpass = libatrous.iterscale(lowpass,kernel,i)
            if i >= scale1:
                output += bandpass
                
        if lowpass:
            output += lowpass

        return output


    def set_data(self,rgb):
        r = self.r = rgb[0]
        g = self.g = rgb[1]
        b = self.b = rgb[2]

        if r.dtype != g.dtype or r.dtype != b.dtype:
            raise ValueError("dtype mismatch: objects cannot be broadcast to a single dtype")

        if r.shape != g.shape or r.shape != b.shape:
            raise ValueError("shape mismatch: objects cannot be broadcast to a single shape")


        nbit = self.nbit
        #print "set_data, nbit=%d" % self.nbit
        if r.dtype == np.uint8 or r.dtype == np.uint16:
            r2, g2, b2 = r.copy(), g.copy(), b.copy()
            if r.dtype == np.uint8:
                nbit = 8
        else:
            r2 = r.astype(np.uint16)
            g2 = g.astype(np.uint16)
            b2 = b.astype(np.uint16)
            

        self.data = [r2,g2,b2]
        Analysis.__init__(self,nbit)

    #Threshold as a value or as a percent of maxval
    #scales are 0 indexed and highscale not included
    def clean(self,threshold=0,tp=None,scale1=1,scale2=4,filter_type=libatrous.SPL5):

        #disregard threshold and use tp as a % of maxval
        if tp is not None:
            threshold = self.maxval*tp/100.

        if self.r.ndim == 2:
            nz = 1
            ny,nx = self.r.shape
        elif self.r.ndim == 3:
            nz,ny,nx = self.r.shape

        #assume rgb first three channels
        rgb = np.zeros((nx*ny*nz,3),float)

        #At least 2 channels must be above the threshold value. Otherwise, set at 0
        sum_array = None

        kernel = libatrous.get_kernel(filter_type)
        for i in range(3):
            d = self.get_bandpass(self.data[i], scale1, scale2, kernel, lowpass = False)

            #Testing pixel brightness against threshold.
            if sum_array is None:
                sum_array = np.zeros(d.shape,'i')

            wh = d<threshold
            d[wh] = 0
            sum_array += wh.astype('i')
            rgb[:,i] = d.flat

        #At least 2 channels are below the threshold
        wh = (sum_array > 1).flatten()
        rgb[wh,:] = 0

        #Send the data back to Imaris
        ret = []
        for i in range(3):
            #save new channel
            d = rgb[:,i].reshape(sum_array.shape)
            ret.append(d)
 
        self.r,self.g,self.b = ret

    #Just so we know what we did to the output before sending it back to Imaris
    def clean_output(self,data,threshold=0,lowscale=1,scale2=4,filter_type=libatrous.CDF97):
        kernel = libatrous.get_kernel(filter_type)
        return self.get_bandpass(data, scale1, scale2, kernel, lowpass = False)

