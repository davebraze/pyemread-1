## pyemread

This is a set of functions designed for assisting with stimulus
creation and eye-movement (EM) data analysis of single/multi-line text
reading experiments. 

The package contains of three modules each involving a set of functions:
(a) gen: functions in this module help to generate bitmaps of 
single/multi-line texts for reading, including txt/csv files specifying 
word-wise regions of interest, and visualize saccades, fixations, and 
ime-stamped eye-movement data on bitmaps; 
(b)	ext: functions in this module aim to extract saccades and fixations 
detected by eye trackers (SRR eyelink devices) during reading and 
classifying them into different text lines (module); 
(c)	cal: functions in this module can calculate regional summaries of 
widely-adopted EM measures used in reading research (module).

### Installation

From a shell prompt try:
```
> pip install git+https://github.com/gtojty/pyemread.git
```
OR, you can fork the source tree from github to your machine and then,
from within the top level of the source tree do:
```
> python setup.py install
```

### Usage

Simply use:
```
import pyemread as pr
```
Then, you can call all functions in the package using the namespace py, 
e.g., py.gen.FUNCTION.

OR, you can import specific module by typing:
```
from pyemread import gen
```
Then, you can call functions in that particular module using the 
namespace gen, e.g., gen.FUNCTION. 

