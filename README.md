# 3D-MANC
A computational platform for extracting and reconstructing single neurons in 3D from multi-colour labelled populations

* **BBSTATIC.py** is a small standalone utility for testing the method.
* **XTBBFilter.py** is the Imaris XTension that pre-filters the images.
* **XTBB.py** is the main Imaris XTension used for extracting the neurons.

Compiled versions (Python 2.7 / Windows 64 bit) for all the native libraries are supplied here but the source code for each can be found on github:
* **libatrous:** https://github.com/zindy/libatrous
* **nativebb:** https://github.com/lucasgroup/nativebb

Additionally, the BridgeLib python module is used to facilitate communication between Python and Imaris: https://github.com/zindy/Imaris
