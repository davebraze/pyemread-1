## pyemread

This is a set of functions designed for assisting with stimulus
creation and eye-movement data analysis of single/multi-line text
reading experiments. The package contains functions for (a) generating
bitmaps of single/multi-line texts for reading, including txt/csv
files specifying wordwise regions of interest, (b) extract and
visualize saccades and fixations detected by eye trackers (SRR eyelink
devices) during reading, (c) and calculate regional summaries of
widely-adopted eye-movement measures used in reading research.

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
