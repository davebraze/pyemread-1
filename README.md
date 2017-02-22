## pyemread

This is a set of functions designed for assisting with stimulus
creation and eye-movement (EM) data analysis of single/multi-line text
reading experiments. The package contains functions for (a) generating
bitmaps of single/multi-line texts for reading, including txt/csv
files specifying word-wise regions of interest, (b) extract saccades 
and fixations detected by eye trackers (SRR eyelink devices) during 
reading, (c) classify saccades, fixations, and time-stamped EM data 
into text lines and word regions, and identify cross-line saccades, 
fixations, and time-stamped EM data, (d) visualize saccades, fixations,
 and time-stamped eye-movement data on bitmaps;  and (e) calculate 
regional summaries of widely-adopted EM measures used in reading research.

### Installation

This is a pure python package. So installation should be
straightforward (we hope). From a shell prompt try:
```
> pip install git+https://github.com/gtojty/pyemread.git
```
OR, you can fork the source tree from github to your machine and then,
from within the top level of the source tree do:
```
> python setup.py install
```

### Usage

In python code, simple use:
```
import pyemread as pr
```
Then, one can call all functions in the package using the namespace py.

