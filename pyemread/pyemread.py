# -*- coding: utf-8 -*-
"""
Created on Wed Feb 22 09:21:44 2017

__author__ = "Tao Gong and David Braze"
__copyright__ = "Copyright 2017, The Pyemread Project"
__credits__ = ["Tao Gong", "David Braze", "Jonathan Gordils", "Hosung Nam"]
__license__ = "MIT"
__version__ = "0.1.0"
__maintainer__ = ["Tao Gong", "David Braze"]
__email__ = ["gtojty@gmail.com", "davebraze@gmail.com"]
__status__ = "Production"

This is a set of functions designed for assisting with stimulus creation 
and eye-movement (EM) data analysis of single/multi-line text reading 
experiments. The package contains functions for (a) generating bitmaps of 
single/multi-line texts for reading, including txt/csv files specifying 
word-wise regions of interest, (b) extract saccades and fixations detected
 by eye trackers (SRR eyelink devices) during reading, (c) classify 
saccades, fixations, and time-stamped EM data into text lines and word 
regions, and identify cross-line saccades, fixations, and time-stamped EM 
data, (d) visualize saccades, fixations, and time-stamped eye-movement 
data on bitmaps;  and (e) calculate regional summaries of widely-adopted 
EM measures used in reading research.

For installation,
This is a pure python package. So installation should be straightforward
(we hope). From a shell prompt try:
> pip install git+https://github.com/gtojty/pyemread.git
OR, you can fork the source tree from github to your machine and then,
from within the top level of the source tree do:
> python setup.py install
For usage, 
In python code, use: import pyemread as pr
Then, one can call all functions in the package using the namespace py.
"""

# import helper functions from _helperfunc_.py
from _helperfunc_ import *
import codecs as _codecs
import matplotlib.pyplot as _plt


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# user functions for generating bitmaps and region files
def Praster(direct, fontpath, stPos, langType, codeMethod='utf_8', 
            text=[u'The quick brown fox jumps over the lazy dog.', 
                  u'The lazy tabby cat sleeps in the sun all afternoon.'],
            dim=(1280,1024), fg=(0,0,0), bg=(232,232,232), wfont=None, 
            regfile=True, lmargin=86, tmargin=86, linespace=43, 
            fht=18, fwd=None, bbox=False, bbox_big=False, ID='test', 
            addspace=18, log=False):
    """
    Rasterize 'text' using 'font' according to the specified parameters. 
    Intended for single/multiple line texts.
    
    Arguments:
        direct          : directory storing the bitmap and/or region file
        fontpath        : fully qualified path to font file
        stPos           : starting from top left corner ('TopLeft') or 
                          center ('Center') or auto ('Auto')        
        langType        : type of language in shown text: 'English' or
                          'Korean'/'Chinese'/'Japanese'
        codeMethod      : for linux: utf_8; for Windows: cp1252
        text=[]         : text to be rasterized as a list of lines
        dim=(1280,1024) : (x,y) dimension of bitmap 
        fg=(0,0,0)      : RGB font color
        bg=(232,232,232): RGB background color
        wfont=None      : font used for watermark. Only relevant if 
                          watermark=True.
        regfile=True    : create word-wise regionfile by default
        lmargin=86      : left margin in pixels
        tmargin=86      : top margin in pixels.  NOTE ORIGIN IS IN 
                          BOTTOM LEFT CORNER
        linespace=43    : linespacing in pixels (baseline to baseline)
        fht=18          : font height in pixels (vertical distance between
                          the highest and lowest painted pixel considering
                          every character in the font). Makes more sense 
                          to specify _width_, but ImageFont.truetype() 
                          wants a ht). Not every font obeys; see, e.g., 
                          "BrowalliaUPC Regular"
        fwd=None        : towards character width in pixels. Takes 
                          precedence over fht. 
        bbox=False      : draw bounding box around each word.
        bbox_big=False  : draw bounding box around the whole line of word.        
        ID='test'       : unique ID for stim, used to build filenames for
                          bitmap and regions. Also included in watermark.
        addspace        : the extra pixels you want to add above the top
                          and below the bottom of each line of texts
        log             : log for recording intermediate result
    """
    if not isinstance(text, (list, tuple)):
        raise ValueError("text argument must be a list of text string(s), not a bare string!")
    
    if fwd: # Reset fht if fwd is specified. This isn't working quite like I'd like. See full set of font species for details.
        ttf = ImageFont.truetype(fontpath, fht) # init the specified font resource
        std_char = u'n' # u'n' is used as a standard character for calculating font size 
        casp = _cAspect(ttf, std_char)  
        fht= int(round(fwd*casp))
        ttf = ImageFont.truetype(fontpath, fht) # re-init the specified font resource
        (wd, ht) = ttf.getsize(std_char)  
    else:
        ttf = ImageFont.truetype(fontpath, fht) # init the specified font resource
    
    # initialize the image
    img = Image.new('RGB', dim, bg) # 'RGB' specifies 8-bit per channel (32 bit color)
    draw = ImageDraw.Draw(img)
    
    ### open the region file: use _codecs.open() to properly support writing unicode strings
    if regfile: 
        resDict = Dictlist(); curKey = 1

    # output file: 
    #       id: story id 
    #      len: length of each word, include ahead bracket or quotation, or behind punctuation, 
    #   height: getsize() for single character is fine! not for words!
    # baseline: base line of each line of words
    #     line_no: line number      
    # rec_x1, rec_y1, rec_x2, rec_y2: the rectangle bounding text of each word (not working properly due to error of getsize)
    # brec_x1, brec_y1, brec_x2, brec_y2: the rectangle bounding text based on the line (work properly!)      
    
    ### Paint each line onto the image a word at a time, including preceding space.
    if stPos == 'Center': 
        if langType == 'Chinese' or langType == 'Japanese' or langType == 'Korean': vpos = dim[1]/2.0 + fht/2.0 
        else: vpos = dim[1]/2.0 # single line! center 1st line of text in the middle
    elif stPos == 'TopLeft': 
        if langType == 'Chinese' or langType == 'Japanese' or langType == 'Korean': vpos = tmargin + fht/2.0
        else: vpos = tmargin  # multiple lines! initialize vertical position to the top margin!
    if stPos == 'Auto':
        if langType == 'Chinese' or langType == 'Japanese' or langType == 'Korean': vpos = dim[1]/2.0 - (len(text)-1)/2.0*linespace + fht/2.0      
        else: vpos = dim[1]/2.0 - (len(text)-1)/2.0*linespace
    
    if langType in EngLangList:
        # create descents and ascents dictionaries
        descents = _getStrikeDescents(fontpath, fht); ascents = _getStrikeAscents(fontpath, fht)

        if log: 
            import json
            logfileH = _codecs.open(_os.path.join(direct, 'Praster.log'), 'wb', encoding=codeMethod)
            logfileH.write('ascents\n'); json.dump(ascents, logfileH); logfileH.write('\n')
            logfileH.write('descents\n'); json.dump(descents, logfileH); logfileH.write('\n')
            logfileH.close()  # close log file
        
        # show English text
        curline = 1
        for line in text:
            # break line into list of words and do some cleanup
            words = line.split(' ')
            if words.count(''): words.remove('')           # remove empty strings.
            words = [_re.sub('^', ' ', w) for w in words]   # add a space to beginning of each word.
            if len(words) > 0: words[0] = words[0].strip() # remove space from beginning of first word in each line, guarding against empty wordlists.

            # paint the line into the image, one word at a time 
            # calculate the minimum descent and maximum height in all words on the same line
            mdes_all, mht_all = 0, 0
            for w in words:
                for c in w:
                    mdes_all = min(mdes_all, _getKeyVal(c, descents))    # get the biggest descent based on characters
                (wd, ht) = ttf.getsize(w)   # get the biggest height based on words (getsize function has offsets!)
                mht_all = max(mht_all, ht)
            aboveBase, belowBase = mht_all + mdes_all, mdes_all

            # paint the line into the image, one word at a time 
            xpos1 = lmargin # let edge of current word
            for w in words:
                wordlen = len(w) # should maybe trim leading space ?? punctuation ??    
                (wd, ht) = ttf.getsize(w)   # only wd is accurate
                xpos2 = xpos1 + wd    # right edge of current word
            
                (mdes, masc) = _getdesasc(w, descents, ascents)  # calculate descent and ascent of each word
                ht = _getStrikeCenters(fontpath, fht) + masc - mdes  # calculate word height based on character
                
                # get word's border
                vpos1 = vpos - ht - mdes; vpos2 = vpos1 + ht

                # draw current word
                if _sys.platform.startswith('win'): vpos1_text = vpos - _getStrikeCenters(fontpath, fht) # Windows system   
                elif _sys.platform.startswith('linux') > -1: vpos1_text = vpos - _getStrikeCenters(fontpath, fht) - fht/4.5 - 1 # # Linux system: add some offset (fht/4.5 - 1)
                draw.text((xpos1, vpos1_text), w, font=ttf, fill=fg) 
                
                # outline word region
                if bbox: draw.rectangle([(xpos1, vpos1), (xpos2, vpos2)], outline=fg)
                
                # outline line region
                vpos1_b, vpos2_b = vpos - aboveBase, vpos - belowBase    
                if bbox_big: draw.rectangle([(xpos1, vpos1_b - addspace), (xpos2, vpos2_b + addspace)], outline=fg)
                            
                # output word regions
                if regfile:
                    #wo = '%s|%s|%s|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d' % (id, langType, w, wordlen, ht, vpos, curline,
                    #                                                   xpos1, vpos1, xpos2, vpos2, xpos1, vpos1_b - addspace, xpos2, vpos2_b + addspace)
                    #regfileH.write(wo+'\n')
                    resDict = _InputDict(resDict, curKey, ID, langType, w, wordlen, ht, vpos, curline, xpos1, vpos1, xpos2, vpos2, xpos1, vpos1_b - addspace, xpos2, vpos2_b + addspace)
                    curKey += 1
                
                xpos1 = xpos2   # shift to next word's left edge
        
            if vpos >= dim[1] + linespace: 
                raise ValueError("%d warning! %s has too many words! They cannot be shown within one screen!" % (vpos, id))
            else:
                vpos += linespace   # shift to next line
                curline += 1    
    
    elif langType in ChnLangList:      
        # show Chinese text
        curline = 1
        for line in text:
            # break line into list of words and do some cleanup
            words = line.split('|')
            
            # paint the line into the image, one word at a time 
            xpos1 = lmargin # let edge of current word
            for w in words:
                wordlen = len(w) # should maybe trim leading space ?? punctuation ??    
                (wd, ht) = ttf.getsize(w)
                xpos2 = xpos1 + wd    # right edge of current word
                
                # get word's border
                vpos1 = vpos - ht; vpos2 = vpos1 + ht            
            
                # draw current word
                vpos1_text = vpos1  # top edge of current word
                draw.text((xpos1, vpos1_text), w, font=ttf, fill=fg) 
                
                # outline word region!
                if bbox: draw.rectangle([(xpos1, vpos1), (xpos2, vpos2)], outline=fg)
                
                # outline line region!    
                aboveBase, belowBase = ht, 0
                vpos1_b, vpos2_b = vpos - aboveBase, vpos - belowBase    
                if bbox_big: draw.rectangle([(xpos1, vpos1_b - addspace), (xpos2, vpos2_b + addspace)], outline=fg)
            
                # output word regions
                if regfile:
                    #wo = '%s|%s|%s|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d' % (id, langType, w, wordlen, ht, vpos, curline,
                    #                                                   xpos1, vpos1, xpos2, vpos2, xpos1, vpos1_b - addspace, xpos2, vpos2_b + addspace)
                    #regfileH.write(wo+'\n')
                    resDict = _InputDict(resDict, curKey, ID, langType, w, wordlen, ht, vpos, curline, xpos1, vpos1, xpos2, vpos2, xpos1, vpos1_b - addspace, xpos2, vpos2_b + addspace)
                    curKey += 1
                
                xpos1 = xpos2   # shift to next word's left edge
        
            if vpos >= dim[1] + linespace: 
                raise ValueError("%d warning! %s has too many words! They cannot be shown within one screen!" % (vpos, id))
            else:
                vpos += linespace   # shift to next line
                curline += 1        

    elif langType in KJLangList:
        # show Korean or Japanese text
        curline = 1
        for line in text:
            # break line into list of words and do some cleanup
            words = line.split(' ')
            if words.count(''): words.remove('')           # remove empty strings.
            words = [_re.sub('^', ' ', w) for w in words]   # add a space to beginning of each word.
            if len(words) > 0: words[0] = words[0].strip() # remove space from beginning of first word in each line, guarding against empty wordlists.
            # if the previous word ending with a punctuation, remove added space of the next word
            for ind_w in range(1, len(words)):
                if words[ind_w-1][-1] in puncList:
                    words[ind_w] = _re.sub('^ ', '', words[ind_w])          
            
            # paint the line into the image, one word at a time 
            xpos1 = lmargin # let edge of current word
            for w in words:
                wordlen = len(w) # should maybe trim leading space ?? punctuation ??    
                (wd, ht) = ttf.getsize(w)
                xpos2 = xpos1 + wd    # right edge of current word
            
                # get word's border
                vpos1 = vpos - ht; vpos2 = vpos1 + ht            
                
                # draw current word
                if _sys.platform.startswith('win'):
                    # Windows system
                    if langType == 'Korean': vpos1_text = vpos - ht
                    elif langType == 'Japanese': vpos1_text = vpos
                elif _sys.platform.startswith('linux') > -1: vpos1_text = vpos - fht*13/15.0 # Linux system: add some offset (fht/4.5 - 1)
                #vpos1_text = vpos1  # top edge of current word
                draw.text((xpos1, vpos1_text), w, font=ttf, fill=fg) 
            
                # outline word region
                if bbox: draw.rectangle([(xpos1, vpos1), (xpos2, vpos2)], outline=fg)
                
                # outline line region    
                aboveBase, belowBase = ht, 0
                vpos1_b, vpos2_b = vpos - aboveBase, vpos - belowBase    
                if bbox_big: draw.rectangle([(xpos1, vpos1_b - addspace), (xpos2, vpos2_b + addspace)], outline=fg)
                    
                # output word regions
                if regfile:
                    #wo = '%s|%s|%s|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d' % (id, langType, w, wordlen, ht, vpos, curline,
                    #                                                   xpos1, vpos1, xpos2, vpos2, xpos1, vpos1_b - addspace, xpos2, vpos2_b + addspace)
                    #regfileH.write(wo+'\n')
                    resDict = _InputDict(resDict, curKey, ID, langType, w, wordlen, ht, vpos, curline, xpos1, vpos1, xpos2, vpos2, xpos1, vpos1_b - addspace, xpos2, vpos2_b + addspace)
                    curKey += 1
                
                xpos1 = xpos2   # shift to next word's left edge
        
            if vpos >= dim[1] + linespace: 
                raise ValueError("%d warning! %s has too many words! They cannot be shown within one screen!" % (vpos, id))
            else:
                vpos += linespace   # shift to next line
                curline += 1        
    
    else:
        raise ValueError("invalid langType %s !" % langType)
    
    # if wfont:
    #     wsize=12
    #     wttf=ImageFont.truetype(wfont, wsize)             # maybe turn off ...
    #     # set wcol, check validity of color
    #     wcol_R = bg[0]-2
    #     if wcol_R < 0: wcol_R = 0
    #     wcol_G = bg[1]-2
    #     if wcol_G < 0: wcol_G = 0
    #     wcol_B = bg[2]-2
    #     if wcol_B < 0: wcol_B = 0
    #     wcol=(wcol_R, wcol_G, wcol_B)
    #     #wcol=(bg[0]-2, bg[1]-2, bg[2]-2)                 # set wm color. FIXME: add error checking to ensure we have a valid color.
    #     draw.text((14, 14), id, font=wttf, fill=wcol)     # label image with stim ID
    
    # Wrap up
    if regfile: _writeCSV(_os.path.join(direct, ID + '.region.csv'), resDict, codeMethod)
        
    img.save(_os.path.join(direct, ID + '.png'), 'PNG') # write bitmap file


def Gen_Bitmap_RegFile(direct, fontName, stPos, langType, textFileNameList, genmethod=2, codeMethod='utf_8', dim=(1280,1024), fg=(0,0,0), bg=(232,232,232), 
    lmargin=215, tmargin=86, linespace=65, fht=18, fwd=None, bbox=False, bbox_big=False, ID='story', addspace=18, log=False):
    """
    generate the bitmaps (PNG) and region files of single/multiple line 
    story from text file
    arguments:
        direct           : directory of for text files
        fontName         : name of a font, e.g. 'LiberationMono'
        langType         : type of language in shown text: 'English' 
                           or 'Korean'/'Chinese'/'Japanese'
        textFileNameList : a list of one or multiple text file 
                           for generating bitmaps
        stPos            : starting from top left corner ('TopLeft')
                           or center ('Center') or auto ('Auto')         
        genmethod        : methods to generate: 
                           0: simple test (simple texts); 
                           1: read from one text file; 
                           2: read from many text files;
        (the following arguments are identical to Praster)    
        codeMethod       : for linux: utf_8; for Windows: cp1252
        dim=(1280,1024)  : (x,y) dimension of bitmap 
        fg=(0,0,0)       : RGB font color
        bg=(232,232,232) : RGB background color
        lmargin=86       : left margin in pixels
        tmargin=86       : top margin in pixels NOTE ORIGIN IS IN 
                           BOTTOM LEFT CORNER
        linespace=43     : linespacing in pixels
        fht=18           : font height in pixels (max vertical 
                           distance between highest and lowest 
                           painted pixel considering every character
                           in the font). Makes more sense to specify 
                           _width_, but ImageFont.truetype() wants 
                           a ht). Not every font obeys; see, e.g., 
                           "BrowalliaUPC Regular"
        fwd=None         : towards character width in pixels. 
                           Takes precedence over xsz. 
        bbox=False       : draw bounding box around each word.
        bbox_big=False   : draw bounding box around the whole 
                           line of word.        
        addspace         : the extra pixels you want to add above 
                           the top and below the bottom of each 
                           line of texts
        log              : log for recording intermediate result
    output: for genmethods = 1, generate png and region files
    """
    if langType in EngLangList:
        # for English, get fontpath from FontDict()
        fd = FontDict(); fontpath = fd.fontGet(fontName,'Regular')    
        # set up font related information
        fontpathlist = _font_manager.findSystemFonts() # Get paths to all installed font files (any system?).
        fontpathlist.sort()
    else:
        # for other languages, directly use .ttc or .tff font file name
        fontpath = fontName 
    
    if genmethod == 0:
        # Simple tests.
        if langType in EngLangList:
            Praster(direct, fontpath, stPos, langType, fht=fht, bbox=True, log=True)
            Praster(direct, fontpath, stPos, langType, text=[u'This is a test.', u'This is another.'], fht=fht)
            Praster(direct, fontpath, stPos, langType, text=[u'This is a one-liner.'], fht=fht)
        elif langType in ChnLangList:
            Praster(direct, fontpath, stPos, langType, text=[u'我们|爱|你。', u'为什么|不让|他|走？'], fht=fht)
        elif langType == 'Korean':
            Praster(direct, fontpath, stPos, langType, text=[u'저는 7년 동안 한국에서 살았어요', u'이름은 무엇입니까?'], fht=fht)
        elif langType == 'Japanese':
            Praster(direct, fontpath, stPos, langType, text=[u'むかし、 むかし、 ある ところ に', u'おじいさん と おばあさん が いました。'], fht=fht)
        else:
            raise ValueError("invalid langType %s!" % langType)
    
    elif genmethod == 1:
        # first, check whether the text file exists
        txtfile = textFileNameList[0]; realtxtfile = _os.path.join(direct, txtfile)
        if not _os.path.isfile(realtxtfile):
            print txtfile + ' does not exist!'
        else:
            # read from a single text file (containing many stories)
            infileH = _codecs.open(realtxtfile, mode="rb", encoding=codeMethod)
            print "Read text file: ", infileH.name; lines = infileH.readlines(); infileH.close()
            lines[0] = _re.sub(u"\ufeff", u"", lines[0]) # remove file starter '\ufeff'     
            
            tmp0 = [ii for ii in lines if not _re.match("^#", ii)] # Squeeze out comments: lines that start with '#'
            tmp1 = ''.join(tmp0)    # join list of strings into one long string
             
            tmp2 = _re.split(u"\r\n\r\n", tmp1)  
                   # Split string to lists by delimiter "\r\n\r\n", which corresponds to blank line in original text file (infileH).
                   # At this point, each list item corresponds to 1, possibly multi-line, string.
                   # Each list item is to be rendered as a single bitmap.
            tmp2[len(tmp2)-1] = _re.sub(u"\r\n$", u"", tmp2[len(tmp2)-1])    # remove "\r\n" at the ending of the last line
            tmp3 = [_re.split("\r\n", ii) for ii in tmp2]    # split each item into multiple lines, one string per line.

            for i, P in enumerate(tmp3): 
                s = "storyID = %02.d line = %d" % (i+1, len(P)); print(s)
                Praster(direct, fontpath, stPos, langType, codeMethod=codeMethod, text=P, dim=dim, fg=fg, bg=bg, lmargin=lmargin, tmargin=tmargin, linespace=linespace, 
                        fht=fht, fwd=fwd, bbox=bbox, bbox_big=bbox_big, ID=ID+'%02.d' % (i+1), addspace=addspace, log=log)

    elif genmethod == 2:
        # read from multiple text files
        if len(textFileNameList) == 0:
            # automatically read all text files in direct
            for file in _os.listdir(direct):
                if _fnmatch.fnmatch(file, '*.txt'):
                    textFileNameList.append(str(file))
        else:
            # read specific text files in direct; check whether the file exists!
            for txtfile in textFileNameList:
                ID = txtfile.split('.')[0]; realtxtfile = _os.path.join(direct, txtfile)
                if not _os.path.isfile(realtxtfile):
                    print ID + ' does not exist!'
                    textFileNameList.remove(txtfile)
        # read available text files and generate bitmaps and region files    
        for txtfile in textFileNameList:
            # read from the text file   
            ID = txtfile.split('.')[0]; realtxtfile = _os.path.join(direct, txtfile)
            infileH = _codecs.open(realtxtfile, mode="rb", encoding=codeMethod)
            print "Read text file: ", infileH.name; lines = infileH.readlines(); infileH.close()
            lines[0] = _re.sub(u"\ufeff", u"", lines[0]) # remove file starter '\ufeff'     
            
            tmp0 = [ii for ii in lines if not _re.match("^#", ii)] # Squeeze out comments: lines that start with '#'
            tmp1 = [_re.sub(u"\r\n$", u"", ii) for ii in tmp0]    # remove "\r\n" at the ending of each line
            
            Praster(direct, fontpath, stPos, langType, codeMethod=codeMethod, text=tmp1, dim=dim, fg=fg, bg=bg, lmargin=lmargin, tmargin=tmargin, linespace=linespace, 
                    fht=fht, fwd=fwd, bbox=bbox, bbox_big=bbox_big, ID=ID, addspace=addspace, log=log)
  

def updReg(direct, regfileNameList, addspace):
    """
    update old style region file into new style and save
    arguments:
        direct          : directory of the old region file
        regfileNameList : list of names of old region files
        addspace        : added space for bigger boundary 
                          surrounding lines of texts
    """
    for trialID in range(len(regfileNameList)):
        RegDF = _pd.read_csv(_os.path.join(direct, regfileNameList[trialID]), sep=',', header=None)
        RegDF.columns = ['Name', 'Word', 'length', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos']
        # add WordID
        RegDF['WordID'] = range(1,len(RegDF)+1)        
        # add line        
        RegDF['line_no'] = 0
        lineInd = 1; lineReg_low = 0; cur_y = RegDF.y2_pos[0]
        for curind in range(len(RegDF)):
            if RegDF.y2_pos[curind] >= cur_y + 20:
                lineReg_up = curind
                for ind in range(lineReg_low, lineReg_up):
                    RegDF.loc[ind,'line_no'] = lineInd
                lineInd += 1; lineReg_low = lineReg_up; cur_y = RegDF.y2_pos[curind]
        if lineReg_up < len(RegDF):
            # add the remaining to another line
            for ind in range(lineReg_low, len(RegDF)):
                RegDF.loc[ind,'line_no'] = lineInd
        # add baseline
        RegDF['baseline'] = 0        
        for lineNum in _np.unique(RegDF.line_no):
            RegDF.loc[RegDF.line_no==lineNum,'baseline'] = min(RegDF.loc[RegDF.line_no==lineNum,'y2_pos'])
        # add height
        RegDF['height'] = 0
        for line in range(len(RegDF)):
            RegDF.loc[line,'height'] = RegDF.loc[line,'y2_pos'] - RegDF.loc[line,'y1_pos']        
        # add b_x1, b_y1, b_x2, b_y2    
        RegDF['b_x1'] = RegDF.x1_pos; RegDF['b_y1'] = 0; RegDF['b_x2'] = RegDF.x2_pos; RegDF['b_y2'] = 0
        for lineNum in _np.unique(RegDF.line_no):
            RegDF.loc[RegDF.line_no==lineNum,'b_y1'] = max(RegDF.loc[RegDF.line_no==lineNum,'y1_pos']) - addspace
            RegDF.loc[RegDF.line_no==lineNum,'b_y2'] = min(RegDF.loc[RegDF.line_no==lineNum,'y2_pos']) + addspace
        RegDF = RegDF[['Name', 'WordID', 'Word', 'length', 'height', 'baseline', 'line_no', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos', 'b_x1', 'b_y1', 'b_x2', 'b_y2']]     
        RegDF.to_csv(_os.path.join(direct, regfileNameList[trialID]), index=False)            

    
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# user functions obtaining basic information from data files
def read_SRRasc(direct, subjID, ExpType, rec_lastFix=False, lump_Fix=True, ln=50, zn=50, mn=50):
    """
    read SRR ascii file and extract saccades and fixations
    arguments:
        direct      : directory for storing output files
        subjID      : subject ID
        ExpType     : type of experiments: 'RAN', 'RP'
        rec_lastFix : whether (True)or not (False) include the last 
                      fixation of a trial and allow it to trigger 
                      regression; default = False
        lump_Fix    : whether (True) or not (False) lump short fixations;
                      default = True
        ln          : for lumping fixations, maximum duration of a 
                      fixation to "lump"; default = 50. Fixation <= this 
                      value is subject to lumping with adjacent and near
                      enough (determined by zN) fixations
        zn          : for lumping fixations, maximum distance (in pixels)
                      between two fixations for "lumping"; default = 50, 
                      roughly 1.5 character (12/8s)
        mn          : for lumping fixations, minimum legal fixation
                      duration; default = 50 ms
    output:
        SacDF : saccade data in different trials
        FixDF : fixation data in different trials
    """    
    # first, check whether the ascii and region files are there:
    ascfileExist, ascfileDic = _crtASC_dic(0, direct, subjID)
    
    # second, process the files
    if ascfileExist:
        f = open(ascfileDic[subjID], 'r'); print "Read ASC: ", f.name; lines = f.readlines(); f.close()   # read EMF file    
        script, sessdate, srcfile = _getHeader(lines)    # get header lines    
        T_idx, T_lines = _getTrialReg(lines) # get trial regions
    
        SacDF = _pd.DataFrame(columns=('subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'trialstart', 'trialend', 'tdur', 'recstart', 'recend', 'blinks', 'eye', 'start_time', 'end_time', 'duration', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos', 'ampl', 'pk', 'line_no'))
        FixDF = _pd.DataFrame(columns=('subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'trialstart', 'trialend', 'tdur', 'recstart', 'recend', 'blinks', 'eye', 'start_time', 'end_time', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid', 'line_no', 'region_no'))        
    
        for ind in range(len(T_lines)):
            triallines = lines[T_lines[ind,0]+1:T_lines[ind,1]]; trialID = int(T_idx[ind,0].split(' ')[-1])
            blinklines, fixlines, saclines, sampfreq, eyerec = _getBlink_Fix_Sac_SampFreq_EyeRec(triallines, 0)
            trial_type, trialstart, trialend, tdur, recstart, recend = _gettdur(triallines)
            # read saccade data
            print "Read Sac: Trial ", str(trialID), " Type ", trial_type
            SacDFtemp = _recSac(ExpType, trialID, blinklines, saclines, sampfreq, eyerec, script, sessdate, srcfile, trial_type, trialstart, trialend, tdur, recstart, recend)
            SacDF = SacDF.append(SacDFtemp, ignore_index=True)
            # read fixation data
            print "Read Fix: Trial ", str(trialID), " Type ", trial_type
            FixDFtemp = _recFix(ExpType, trialID, blinklines, fixlines, sampfreq, eyerec, script, sessdate, srcfile, trial_type, trialstart, trialend, tdur, recstart, recend, rec_lastFix, lump_Fix, ln, zn, mn)        
            FixDF = FixDF.append(FixDFtemp, ignore_index=True)
                
        return SacDF, FixDF


def write_Sac_Report(direct, subjID, SacDF):
    """
    write SacDF to csv file
    """
    SacDF.to_csv(_os.path.join(direct, subjID, subjID + '_Sac.csv'), index=False)


def write_Fix_Report(direct, subjID, FixDF):
    """
    write FixDF to csv file
    """
    FixDF.to_csv(_os.path.join(direct, subjID, subjID + '_Fix.csv'), index=False)


def write_TimeStamp_Report(direct, subjID, StampDF):
    """
    write StampDF to csv file
    """    
    StampDF.to_csv(_os.path.join(direct, subjID, subjID + '_Stamp.csv'), index=False)


def read_write_SRRasc(direct, subjID, ExpType, rec_lastFix=False, lump_Fix=True, ln=50, zn=50, mn=50):
    """
    processing a subject's saccades and fixations, read them from ascii 
    files and write them into csv files
    arguments:
        direct      : directory containing specific asc file, the output
                      csv files are stored there
        subjID      : subject ID
        ExpType     : type of experiments: 'RAN', 'RP'
        rec_lastFix : whether (True)or not (False) include the last 
                      fixation of a trial and allow it to trigger 
                      regression; default = False
        lump_Fix    : whether (True) or not (False) lump short fixations;
                      default = True
        ln          : for lumping fixations, maximum duration of a 
                      fixation to "lump"; default = 50. Fixation <= this
                      value is subject to lumping with adjacent and near 
                      enough (determined by zN) fixations
        zn          : for lumping fixations, maximum distance (in pixels) 
                      between two fixations for "lumping"; default = 50, 
                      roughly 1.5 character (12/8s)
        mn          : for lumping fixations, minimum legal fixation
                      duration; default = 50 ms
    output:
        SacDF : saccade data in different trials
        FixDF : fixation data in different trials   
        All these data frames are stored into csv files    
    """
    SacDF, FixDF = read_SRRasc(direct, subjID, ExpType, rec_lastFix, lump_Fix, ln, zn, mn)
    write_Sac_Report(direct, subjID, SacDF)
    write_Fix_Report(direct, subjID, FixDF)

    
def read_write_SRRasc_b(direct, ExpType, rec_lastFix=False, lump_Fix=True, ln=50, zn=50, mn=50):
    """
    processing all subjects' saccades and fixations, read them from ascii 
    files and write them into csv files
    arguments:
        direct      : directory containing all asc files
        ExpType     : type of experiments: 'RAN', 'RP'
        rec_lastFix : whether (True)or not (False) include the last
                      fixation of a trial and allow it to trigger 
                      regression; default = False
        lump_Fix    : whether (True) or not (False) lump short 
                      fixations; default = True
        ln          : for lumping fixations, maximum duration of a 
                      fixation to "lump"; default = 50. 
                      Fixation <= this value is subject to lumping 
                      with adjacent and near enough (determined by zN)
                      fixations
        zn          : for lumping fixations, maximum distance 
                      (in pixels) between two fixations for "lumping";
                      default = 50, roughly 1.5 character (12/8s)
        mn          : for lumping fixations, minimum legal fixation 
                      duration; default = 50 ms
    output:
        SacDF : saccade data in different trials
        FixDF : fixation data in different trials
        All these data frames are stored into csv files    
    """
    ascfileExist, ascfileDic = _crtASC_dic(1, direct, '')
    if ascfileExist:            
        for subjID in ascfileDic:
            SacDF, FixDF = read_SRRasc(direct, subjID, ExpType, rec_lastFix, lump_Fix, ln, zn, mn)
            write_Sac_Report(direct, subjID, SacDF); write_Fix_Report(direct, subjID, FixDF)


# user function for getting time-stamped data
def read_TimeStamp(direct, subjID, ExpType):
    """
    read SRR ascii file and extract time stamped eye movements
    arguments:
        direct  : directory for storing output files
        subjID  : subject ID
        ExpType : type of experiments: 'RAN', 'RP'
    output:
        StampDF : time stamped eye movement data in different trials
    """    
    # first, check whether ascii file is there:
    ascfileExist, ascfileDic = _crtASC_dic(0, direct, subjID)
    
    # second, process the files
    if ascfileExist:
        f = open(ascfileDic[subjID], 'r'); print "Read ASC: ", f.name; lines = f.readlines(); f.close()   # read EMF file    
        script, sessdate, srcfile = _getHeader(lines)    # get header lines    
        T_idx, T_lines = _getTrialReg(lines) # get trial regions
    
        StampDF = _pd.DataFrame(columns=('subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'trialstart', 'trialend', 'tdur', 'recstart', 'recend', 'blinks', 'eye', 'time', 'x_pos1', 'y_pos1', 'pup_size1', 'x_pos2', 'y_pos2', 'pup_size2', 'line_no', 'gaze_region_no', 'label', 'error_free', 'Fix_Sac'))        
        for ind in range(len(T_lines)):
            triallines = lines[T_lines[ind,0]+1:T_lines[ind,1]]; trialID = int(T_idx[ind,0].split(' ')[-1])
            blinklines, stamplines, sampfreq, eyerec = _getBlink_Fix_Sac_SampFreq_EyeRec(triallines, 1)
            trial_type, trialstart, trialend, tdur, recstart, recend = _gettdur(triallines)
            # read time stamped eye-movement data
            print "Read Stamped Eye Movements: Trial ", str(trialID), "; Type ", trial_type
            StampDFtemp = _recTimeStamp(ExpType, trialID, blinklines, stamplines, sampfreq, eyerec, script, sessdate, srcfile, trial_type, trialstart, trialend, tdur, recstart, recend)        
            StampDF = StampDF.append(StampDFtemp, ignore_index=True)
                
        return StampDF


def read_Stamp(direct, subjID, ExpType):
    """
    read SRR ascii file and extract time stamped eye movements
    arguments:
        direct  : directory for storing output files
        subjID  : subject ID
        ExpType : type of experiments: 'RAN', 'RP'
    output:
        StampDF : time stamped eye movement data in different trials
    """    
    # first, check whether ascii file is there:
    ascfileExist, ascfileDic = _crtASC_dic(0, direct, subjID)
    
    ETRANfileExist = True
    ETRANfileName = _os.path.join(direct, 'ETRAN.csv')
    if not _os.path.isfile(ETRANfileName):
        print ETRANfileName + ' does not exist!'; ETRANfileExist = False
    else:
        ETRANDF = _pd.read_csv(ETRANfileName); ETRANDF.SubjectID = ETRANDF.SubjectID.str.lower()
    
    # second, process the files
    if ascfileExist and ETRANfileExist:
        f = open(ascfileDic[subjID], 'r'); print "Read ASC: ", f.name; lines = f.readlines(); f.close()   # read EMF file    
        script, sessdate, srcfile = _getHeader(lines)    # get header lines    
        T_idx, T_lines = _getTrialReg(lines) # get trial regions
    
        StampDF = _pd.DataFrame(columns=('subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'trialstart', 'trialend', 'tdur', 'recstart', 'recend', 'blinks', 'eye', 'time', 'x_pos1', 'y_pos1', 'pup_size1', 'x_pos2', 'y_pos2', 'pup_size2', 'line_no', 'gaze_region_no', 'label', 'error_free', 'Fix_Sac'))        
        for ind in range(len(T_lines)):
            triallines = lines[T_lines[ind,0]+1:T_lines[ind,1]]; trialID = int(T_idx[ind,0].split(' ')[-1])
            blinklines, stamplines, sampfreq, eyerec = _getBlink_Fix_Sac_SampFreq_EyeRec(triallines, 1)
            trial_type, trialstart, trialend, tdur, recstart, recend = _gettdur(triallines)
            error_free = _getErrorFree(ETRANDF, subjID, trial_type)
            # read time stamped eye-movement data
            print "Read Stamped Eye Movements: Trial ", str(trialID), "; Type ", trial_type
            StampDFtemp = _recTimeStamp(ExpType, trialID, blinklines, stamplines, sampfreq, eyerec, script, sessdate, srcfile, trial_type, trialstart, trialend, tdur, recstart, recend, error_free)        
            StampDF = StampDF.append(StampDFtemp, ignore_index=True)
                
        return StampDF


def read_write_TimeStamp(direct, subjID, ExpType):
    """
    processing a subject's time stamped data, read them from ascii files 
    and write them into csv files
    arguments:
        direct  : directory containing specific asc file, the output csv 
                  files are stored there
        subjID  : subject ID
        ExpType : type of experiments: 'RAN', 'RP'
    output:
        StampDF : time stamped data in different trials
        The data frame is stored into a csv file    
    """
    StampDF = read_TimeStamp(direct, subjID, ExpType)
    write_TimeStamp_Report(direct, subjID, StampDF)


def read_write_TimeStamp_b(direct, ExpType):
    """
    processing all subjects' time stamped data, read them from ascii files
    and write them into csv files
    arguments:
        direct  : directory containing all asc files
        ExpType : type of experiments: 'RAN', 'RP'
    output:
        StampDF : time stamped data in different trials
        The data frames are stored into csv files    
    """
    ascfileExist, ascfileDic = _crtASC_dic(1, direct, '')    
    if ascfileExist:
        for subjID in ascfileDic.keys():
            StampDF = read_TimeStamp(direct, subjID, ExpType)
            write_TimeStamp_Report(direct, subjID, StampDF)


def cal_crlSacFix(direct, subjID, regfileNameList, ExpType, classify_method='DIFF', recStatus=True, diff_ratio=0.6, frontrange_ratio=0.2, y_range=60, addCharSp=1):
    """
    read csv data file of subj and extract crossline saccades and
    fixations and update line numbers of original saccades and 
    fixations
    arguments:
        direct             : directory for storing csv and output files
        subjID             : subject ID
        regionfileNameList : a list of region file names (trial_id will
                             help select corresponding region files)
        ExpType            : type of experiments: 'RAN', 'RP'
        classify_method    : fixation method: 
                             'DIFF': based on difference in x_axis; 
                             'SAC': based on crosslineSac ('SAC' is
                             preferred since saccade is kinda more 
                             accurate!); default = 'DIFF'
        recStatus          : whether (True) or not (False) record 
                             questionable saccades and fixations; 
                             default = True
        diff_ratio         : for calculating crossline saccades(fixations),
                             the ratio of maximum distance between the 
                             center of the last word and the center of 
                             the first word in a line; default = 0.6
        frontrange_ratio   : for calculating crossline saccades(fixations),
                             the ratio to check backward crossline 
                             saccade or fixation: such saccade or 
                             fixation usually starts around the line
                             beginning; default = 0.2
        y_range            : for calculating crossline saccades(fixations),
                             the biggest y difference indicating the eyes 
                             are crossing lines or moving away from that 
                             line (this must be similar to the distance 
                             between two lines); default = 60
        addCharSp          : number of single character space added to 
                             EMF for catching overshoot fixations; 
                             default = 1
    output:
        newSacDF : saccade data in different trials with updated line
                   numbers
        crlSac   : crossline saccade data in different trials
        newFixDF : fixation data in different trials with updated line
                   numbers
        crlFix   : crossline fixation data in different trials
    """
    # first, check whether the required files are there:
    SacfileExist, SacfileDic = _crtCSV_dic(0, direct, subjID, '_Sac')
    FixfileExist, FixfileDic = _crtCSV_dic(0, direct, subjID, '_Fix')
    regfileExist, regfileDic = _crtRegion_dic(direct, regfileNameList)
    
    # second, process the files
    if SacfileExist and FixfileExist and regfileExist:
        SacDF = _pd.read_csv(SacfileDic[subjID], sep=',')
        FixDF = _pd.read_csv(FixfileDic[subjID], sep=',')    
        newSacDF = _pd.DataFrame()
        newFixDF = _pd.DataFrame()     
        crlSac = _pd.DataFrame(columns=('subj', 'trial_id', 'eye', 'startline', 'endline', 'SaclineIndex', 'start_time', 'end_time', 'duration', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos', 'ampl', 'pk'))
        crlFix = _pd.DataFrame(columns=('subj', 'trial_id', 'eye', 'startline', 'endline', 'FixlineIndex', 'start_time', 'end_time', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid'))
        print "Subj: ", subjID
    
        for trialID in _np.unique(map(int,SacDF.trial_id)):
            RegDF = _getRegDF(regfileDic, _np.unique(SacDF.trial_type[SacDF.trial_id == trialID])[0])  # get region file
            _modRegDF(RegDF, addCharSp) # modify mod_x1 and mod_x2 position of word regions
            # get saccade data and crossline saccade data
            print "Get crlSac: Trial ", str(trialID), " Type ", _np.unique(SacDF.trial_type[SacDF.trial_id == trialID])[0]
            SacDFtemp = SacDF[SacDF.trial_id==trialID].reset_index(); crlSactemp, question = _getcrlSac(RegDF, SacDFtemp, diff_ratio, frontrange_ratio, y_range)
            newSacDF = newSacDF.append(SacDFtemp, ignore_index=True); crlSac = crlSac.append(crlSactemp, ignore_index=True)
            if recStatus and question:
                logfile = open(_os.path.join(direct, 'log.txt'), 'a+')
                logfile.write('Subj: ' + subjID + ' Trial ' + str(trialID) + ' crlSac start/end need check!\n')
                logfile.close()        
            
            # get fixation data and crossline fixation data
            print "Get Fix: Trial ", str(trialID), " Type ", _np.unique(SacDF.trial_type[SacDF.trial_id == trialID])[0]
            FixDFtemp = FixDF[FixDF.trial_id==trialID].reset_index(); crlFixtemp, question = _getcrlFix(RegDF, crlSactemp, FixDFtemp, classify_method, diff_ratio, frontrange_ratio, y_range)
            
            # assign region_no in FixDFtemp
            for curFix in range(len(FixDFtemp)):
                if not _np.isnan(FixDFtemp.loc[curFix, 'line_no']):
                    indlist = RegDF[(RegDF['line_no'] == FixDFtemp.loc[curFix,'line_no']) & ((RegDF['mod_x1'] <= FixDFtemp.loc[curFix,'x_pos']) & (RegDF['mod_x2'] >= FixDFtemp.loc[curFix,'x_pos']))].index.tolist()
                    if len(indlist) == 1:
                        FixDFtemp.loc[curFix,'region_no'] = int(RegDF.WordID[indlist[0]])
                    else:
                        FixDFtemp.loc[curFix,'region_no'] = _np.nan
                else:
                    FixDFtemp.loc[curFix,'region_no'] = _np.nan
            
            newFixDF = newFixDF.append(FixDFtemp, ignore_index=True); crlFix = crlFix.append(crlFixtemp, ignore_index=True)
            if recStatus and question:
                logfile = open(_os.path.join(direct, 'log.txt'), 'a+')
                logfile.write('Subj: ' + subjID + ' Trial ' + str(trialID) + ' crlFix start/end need check!\n')  
                logfile.close()
            
        return newSacDF, crlSac, newFixDF, crlFix
    

def write_Sac_crlSac(direct, subjID, SacDF, crlSac):
    """
    write modified saccades and crossline saccades to csv files
    arguments:
        direct : directory for storing csv files
        subjID : subject ID
        SacDF  : saccade data in different trials with updated line
                 numbers
        crlSac : crossline saccade data in different trials
    """            
    SacDF.to_csv(_os.path.join(direct, subjID, subjID + '_Sac.csv'), index=False)
    crlSac.to_csv(_os.path.join(direct, subjID, subjID + '_crlSac.csv'), index=False)


def write_Fix_crlFix(direct, subjID, FixDF, crlFix):
    """
    write modified fixations and crossline fixations to csv files
    arguments:
        direct : directory for storing csv files
        subjID : subject ID
        FixDF  : fixation data in different trials with updated line
                 numbers
        crlFix : crossline fixation data in different trials
    """            
    FixDF.to_csv(_os.path.join(direct, subjID, subjID + '_Fix.csv'), index=False)
    crlFix.to_csv(_os.path.join(direct, subjID, subjID + '_crlFix.csv'), index=False)


def cal_write_SacFix_crlSacFix(direct, subjID, regfileNameList, ExpType, classify_method='DIFF', recStatus=True, diff_ratio=0.6, frontrange_ratio=0.2, y_range=60, addCharSp=1):
    """
    processing a subject's saccades and fixations, read them from csv
    files and store them into csv files
    arguments:
        direct           : directory containing all asc files
        subjID           : subject ID
        regfileNameList  : a list of region file names (trial_id will help
                           select corresponding region files)
        ExpType          : type of experiments: 'RAN', 'RP'
        classify_method  : fixation method: 
                           'DIFF': based on difference in x_axis; 
                           'SAC': based on crosslineSac ('SAC' is
                           preferred since saccade is kinda more 
                           accurate!); default = 'DIFF'
        recStatus        : whether (True) or not (False) record 
                           questionable saccades and fixations; 
                           default = True 
        diff_ratio       : for calculating crossline saccades(fixations),
                           the ratio of maximum distance between the 
                           center of the last word and the center of 
                           the first word in a line; default = 0.6
        frontrange_ratio : for calculating crossline saccades(fixations),
                           the ratio to check backward crossline saccade
                           or fixation: such saccade or fixation usually
                           starts around the line beginning; default = 0.2
        y_range          : for calculating crossline saccades(fixations),
                           the biggest y difference indicating the eyes 
                           are crossing lines or moving away from that 
                           line (this must be similar to the distance 
                           between two lines); default = 60
        addCharSp        : number of single character space added to EMF
                           for catching overshoot fixations; default = 1
    output:
        SacDF  : saccade data in different trials with updated line 
                 numbers of different subjects
        crlSac : crossline saccade data in different trials of different
                 subjects
        FixDF  : fixation data in different trials with updated line
                 numbers of different subjects
        crlFix : crossline fixation data in different trials of different
                 subjects
        All these data frames are stored in csv files
    """
    SacDF, crlSac, FixDF, crlFix = cal_crlSacFix(direct, subjID, regfileNameList, ExpType, classify_method, recStatus, diff_ratio, frontrange_ratio, y_range, addCharSp)
    write_Sac_crlSac(direct, subjID, SacDF, crlSac); write_Fix_crlFix(direct, subjID, FixDF, crlFix)


def cal_write_SacFix_crlSacFix_b(direct, regfileNameList, ExpType, classify_method='DIFF', recStatus=True, diff_ratio=0.6, frontrange_ratio=0.2, y_range=60, addCharSp=1):
    """
    processing all subjects' saccades and fixations, read them from csv 
    files and store them into csv files
    arguments:
        direct           : directory containing all asc files
        regfileNameList  : a list of region file names (trial_id will help
                           select corresponding region files)
        ExpType          : type of experiments: 'RAN', 'RP'
        classify_method  : fixation method: 
                           'DIFF': based on difference in x_axis; 
                           'SAC': based on crosslineSac ('SAC' is preferred
                           since saccade is kinda more accurate!); 
                           default = 'DIFF'
        recStatus        : whether (True) or not (False) record 
                           questionable saccades and fixations; 
                           default = True 
        diff_ratio       : for calculating crossline saccades(fixations), 
                           the ratio of maximum distance between the center
                           of the last word and the center of the first 
                           word in a line; default = 0.6
        frontrange_ratio : for calculating crossline saccades(fixations), 
                           the ratio to check backward crossline saccade 
                           or fixation: such saccade or fixation usually 
                           starts around the line beginning; default = 0.2
        y_range          : for calculating crossline saccades(fixations), 
                           the biggest y difference indicating the eyes 
                           are crossing lines or moving away from that 
                           line (this must be similar to the distance 
                           between two lines); default = 60
        addCharSp        : number of single character space added to EMF 
                           for catching overshoot fixations; default = 1
    output:
        SacDF  : saccade data in different trials with updated line 
                 numbers of different subjects
        crlSac : crossline saccade data in different trials of different
                 subjects
        FixDF  : fixation data in different trials with updated line
                 numbers of different subjects
        crlFix : crossline fixation data in different trials of different
                 subjects
    """
    SacfileExist, SacfileDic = _crtCSV_dic(1, direct, '', '_Sac')
    FixfileExist, FixfileDic = _crtCSV_dic(1, direct, '', '_Fix')
    regfileExist, regfileDic = _crtRegion_dic(direct, regfileNameList)
    if SacfileExist and FixfileExist and regfileExist:
        for subjID in SacfileDic.keys():
            cal_write_SacFix_crlSacFix(direct, subjID, regfileNameList, ExpType, classify_method, recStatus, diff_ratio, frontrange_ratio, y_range, addCharSp)
    
    
def read_cal_SRRasc(direct, subjID, regfileNameList, ExpType, classify_method='DIFF', recStatus=True, diff_ratio=0.6, frontrange_ratio=0.2, y_range=60, addCharSp=1, rec_lastFix=False, lump_Fix=True, ln=50, zn=50, mn=50):
    """
    read ASC file and extract the fixation and saccade data and calculate
    crossline saccades and fixations
    arguments:
        direct             : directory for storing output files
        subjID             : subject ID
        regionfileNameList : a list of region file names (trial_id will 
                             help select corresponding region files)
        ExpType            : type of experiments: 'RAN', 'RP'
        classify_method    : fixation method: 
                             'DIFF': based on difference in x_axis; 
                             'SAC': based on crosslineSac ('SAC' is
                             preferred since saccade is kinda more
                             accurate!); default = 'DIFF'
        recStatus          : whether (True) or not (False) record 
                             questionable saccades and fixations;
                             default = True 
        diff_ratio         : for calculating crossline saccades(fixations),
                             the ratio of maximum distance between the 
                             center of the last word and the center of 
                             the first word in a line; default = 0.6
        frontrange_ratio   : for calculating crossline saccades(fixations),
                             the ratio to check backward crossline saccade
                             or fixation: such saccade or fixation usually
                             starts around the line beginning; default = 
                             0.2
        y_range            : for calculating crossline saccades(fixations),
                             the biggest y difference indicating the eyes
                             are crossing lines or moving away from that
                             line (this must be similar to the distance 
                             between two lines); default = 60
        addCharSp          : number of single character space added to 
                             RegDF for catching overshoot fixations; 
                             default = 1
        rec_lastFix        : whether (True)or not (False) include the 
                             last fixation of a trial and allow it to
                             trigger regression; default = False
        lump_Fix           : whether (True) or not (False) lump short
                             fixations; default = True
        ln                 : for lumping fixations, maximum duration of
                             a fixation to "lump"; default = 50. Fixation
                             <= this value is subject to lumping with 
                             adjacent and near enough (determined by zN) 
                             fixations
        zn                 : for lumping fixations, maximum distance (in 
                             pixels) between two fixations for "lumping";
                             default = 50, roughly 1.5 character (12/8s)
        mn                 : for lumping fixations, minimum legal fixation
                             duration; default = 50 ms
    output:
        SacDF    : saccade data in different trials
        crlSacDF : crossline saccade data in different trials
        FixDF    : fixation data in different trials
        crlFixDF : crossline fixation data in different trials
    """
    # first, check whether the ascii and region files are there:
    ascfileExist, ascfileDic = _crtASC_dic(0, direct, subjID)
    regfileExist, regfileDic = _crtRegion_dic(direct, regfileNameList)
    
    # second, process the files
    if ascfileExist and regfileExist:
        # read EMF file
        f = open(ascfileDic[subjID], 'r'); print "Read ASC: ", f.name; lines = f.readlines(); f.close()   # read EMF file    
        script, sessdate, srcfile = _getHeader(lines)    # get header lines    
        T_idx, T_lines = _getTrialReg(lines) # get trial regions
    
        SacDF = _pd.DataFrame(columns=('subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'trialstart', 'trialend', 'tdur', 'recstart', 'recend', 'blinks', 'eye', 'start_time', 'end_time', 'duration', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos', 'ampl', 'pk', 'line_no'))
        FixDF = _pd.DataFrame(columns=('subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'trialstart', 'trialend', 'tdur', 'recstart', 'recend', 'blinks', 'eye', 'start_time', 'end_time', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid', 'line_no', 'region_no'))        
        crlSac = _pd.DataFrame(columns=('subj', 'trial_id', 'eye', 'startline', 'endline', 'SaclineIndex', 'start_time', 'end_time', 'duration', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos', 'ampl', 'pk'))
        crlFix = _pd.DataFrame(columns=('subj', 'trial_id', 'eye', 'startline', 'endline', 'FixlineIndex', 'start_time', 'end_time', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid'))
    
        for ind in range(len(T_lines)):
            triallines = lines[T_lines[ind,0]+1:T_lines[ind,1]]; trialID = int(T_idx[ind,0].split(' ')[-1])
            blinklines, fixlines, saclines, sampfreq, eyerec = _getBlink_Fix_Sac_SampFreq_EyeRec(triallines, 0)
            trial_type, trialstart, trialend, tdur, recstart, recend = _gettdur(triallines)
            RegDF = _getRegDF(regfileDic, trial_type)  # get region file
            _modRegDF(RegDF, addCharSp) # modify mod_x1 and mod_x2 position of word regions
            # read saccade data and get crossline saccade
            print "Read Sac and Get crlSac: Trial ", str(trialID), " Type ", trial_type
            SacDFtemp = _recSac(ExpType, trialID, blinklines, saclines, sampfreq, eyerec, script, sessdate, srcfile, trial_type, trialstart, trialend, tdur, recstart, recend)
            crlSactemp, question = _getcrlSac(RegDF, SacDFtemp, diff_ratio, frontrange_ratio, y_range)
            SacDF = SacDF.append(SacDFtemp, ignore_index=True); crlSac = crlSac.append(crlSactemp, ignore_index=True)
            if recStatus and question:
                logfile = open(_os.path.join(direct, 'log.txt'), 'a+')
                logfile.write('Subj: ' + SacDFtemp.subj[0] + ' Trial ' + str(trialID) + ' crlSac start/end need check!\n')
                logfile.close()

            # read fixation data and get crossline fixation
            print "Read Fix and Get crlFix: Trial ", str(trialID), " Type ", trial_type
            FixDFtemp = _recFix(ExpType, trialID, blinklines, fixlines, sampfreq, eyerec, script, sessdate, srcfile, trial_type, trialstart, trialend, tdur, recstart, recend, rec_lastFix, lump_Fix, ln, zn, mn)        
            crlFixtemp, question = _getcrlFix(RegDF, crlSactemp, FixDFtemp, classify_method, diff_ratio, frontrange_ratio, y_range)
            
            # assign region_no in FixDFtemp
            for curFix in range(len(FixDFtemp)):
                if not _np.isnan(FixDFtemp.loc[curFix, 'line_no']):
                    indlist = RegDF[(RegDF['line_no'] == FixDFtemp.loc[curFix,'line_no']) & ((RegDF['mod_x1'] <= FixDFtemp.loc[curFix,'x_pos']) & (RegDF['mod_x2'] >= FixDFtemp.loc[curFix,'x_pos']))].index.tolist()
                    if len(indlist) == 1:
                        FixDFtemp.loc[curFix,'region_no'] = int(RegDF.WordID[indlist[0]])
                    else:
                        FixDFtemp.loc[curFix,'region_no'] = _np.nan
                else:
                    FixDFtemp.loc[curFix,'region_no'] = _np.nan
            
            FixDF = FixDF.append(FixDFtemp, ignore_index=True); crlFix = crlFix.append(crlFixtemp, ignore_index=True)
            if recStatus and question:
                logfile = open(_os.path.join(direct, 'log.txt'), 'a+')
                logfile.write('Subj: ' + FixDFtemp.subj[0] + ' Trial ' + str(trialID) + ' crlFix start/end need check!\n')
                logfile.close()
    
        return SacDF, crlSac, FixDF, crlFix
        

def read_cal_write_SRRasc(direct, subjID, regfileNameList, ExpType, classify_method='DIFF', recStatus=True, diff_ratio=0.6, frontrange_ratio=0.2, y_range=60, addCharSp=1, rec_lastFix=False, lump_Fix=True, ln=50, zn=50, mn=50):
    """
    processing a subject's fixation and saccade data
    arguments:
        direct           : directory containing all asc files
        subjID           : subject ID
        regfileNameList  : a list of region file names (trial_id will help
                           select corresponding region files)
        ExpType          : type of experiments: 'RAN', 'RP'
        classify_method  : fixation method: 
                           'DIFF': based on difference in x_axis; 
                           'SAC': based on crosslineSac ('SAC' is 
                           preferred since saccade is kinda more 
                           accurate!); default = 'DIFF'
        recStatus        : whether (True) or not (False) record 
                           questionable saccades and fixations, 
                           default = True 
        diff_ratio       : for calculating crossline saccades(fixations),
                           the ratio of maximum distance between the 
                           center of the last word and the center of 
                           the first word in a line; default = 0.6
        frontrange_ratio : for calculating crossline saccades(fixations),
                           the ratio to check backward crossline saccade
                           or fixation: such saccade or fixation usually
                           starts around the line beginning; default = 0.2
        y_range          : for calculating crossline saccades(fixations),
                           the biggest y difference indicating the eyes
                           are crossing lines or moving away from that 
                           line (this must be similar to the distance 
                           between two lines); default = 60
        addCharSp        : number of single character space added to 
                           RegDF for catching overshoot fixations; 
                           default = 1
        rec_lastFix      : whether (True)or not (False) include the last
                           fixation of a trial and allow it to trigger 
                           regression; default = False
        lump_Fix         : whether (True) or not (False) lump short 
                           fixations; default = True
        ln               : for lumping fixations, maximum duration of a 
                           fixation to "lump"; default = 50. Fixation <=
                           this value is subject to lumping with adjacent
                           and near enough (determined by zN) fixations
        zn               : for lumping fixations, maximum distance (in 
                           pixels) between two fixations for "lumping";
                           default = 50, roughly 1.5 character (12/8s)
        mn               : for lumping fixations, minimum legal fixation
                           duration; default = 50 ms
    output:
        SacDF    : saccade data in different trials of different subjects
        crlSacDF : crossline saccade data in different trials of different
                   subjects
        FixDF    : fixation data in different trials of different subjects
        crlFixDF : crossline fixation data in different trials of different
                   subjects
        All these data frames are stored into csv files    
    """
    SacDF, crlSac, FixDF, crlFix = read_cal_SRRasc(direct, subjID, regfileNameList, ExpType, classify_method, recStatus, diff_ratio, frontrange_ratio, y_range, addCharSp, rec_lastFix, lump_Fix, ln, zn, mn)
    write_Sac_crlSac(direct, subjID, SacDF, crlSac)
    write_Fix_crlFix(direct, subjID, FixDF, crlFix)

  
def read_cal_write_SRRasc_b(direct, regfileNameList, ExpType, classify_method='DIFF', rec_lastFix=False, lump_Fix=True, ln=50, zn=50, mn=50, recStatus=True, diff_ratio=0.6, frontrange_ratio=0.2, y_range=60, addCharSp=1):
    """
    processing all subjects' fixation and saccade data
    arguments:
        direct           : directory containing all asc files
        regfileNameList  : a list of region file names (trial_id will help
                           select corresponding region files)
        ExpType          : type of experiments: 'RAN', 'RP'
        classify_method  : fixation method: 
                           'DIFF': based on difference in x_axis; 
                           'SAC': based on crosslineSac ('SAC' is 
                           preferred since saccade is kinda more 
                           accurate!); default = 'DIFF'
        rec_lastFix      : whether (True)or not (False) include the last
                           fixation of a trial and allow it to trigger
                           regression; default = False
        lump_Fix         : whether (True) or not (False) lump short
                           fixations; default = True
        ln               : for lumping fixations, maximum duration of a
                           fixation to "lump"; default = 50. Fixation <=
                           this value is subject to lumping with adjacent
                           and near enough (determined by zN) fixations
        zn               : for lumping fixations, maximum distance (in 
                           pixels) between two fixations for "lumping"; 
                           default = 50, roughly 1.5 character (12/8s)
        mn               : for lumping fixations, minimum legal fixation
                           duration; default = 50 ms
        recStatus        : whether (True) or not (False) record 
                           questionable saccades and fixations; default 
                           = True 
        diff_ratio       : for calculating crossline saccades(fixations),
                           the ratio of maximum distance between the 
                           center of the last word and the center of the
                           first word in a line; default = 0.6
        frontrange_ratio : for calculating crossline saccades(fixations),
                           the ratio to check backward crossline saccade
                           or fixation: such saccade or fixation usually
                           starts around the line beginning; default = 0.2
        y_range          : for calculating crossline saccades(fixations),
                           the biggest y difference indicating the eyes
                           are crossing lines or moving away from that
                           line (this must be similar to the distance 
                           between two lines); default = 60
        addCharSp        : number of single character space added to RegDF
                           for catching overshoot fixations; default = 1
    output:
        SacDF    : saccade data in different trials of different subjects
        crlSacDF : crossline saccade data in different trials of different
                   subjects
        FixDF    : fixation data in different trials of different subjects
        crlFixDF : crossline fixation data in different trials of different
                   subjects
        All these data frames are stored into csv files    
    """
    ascfileExist, ascfileDic = _crtASC_dic(1, direct, '')
    regfileExist, regfileDic = _crtRegion_dic(direct, regfileNameList)
    if ascfileExist and regfileExist:
        for subjID in ascfileDic.keys():
            read_cal_write_SRRasc(direct, subjID, regfileNameList, ExpType, classify_method, recStatus, diff_ratio, frontrange_ratio, y_range, addCharSp, rec_lastFix, lump_Fix, ln, zn, mn)


def cal_TimeStamp(direct, subjID, regfileNameList, ExpType, align_method, addCharSp=1):
    """
    read csv time stamped data file of subj and extract crossline saccades
    and fixations and update line numbers of original saccades and fixations
    arguments:
        direct             : directory for storing time stamped csv and 
                             output files
        subjID             : subject ID
        regionfileNameList : a list of region file names (trial_id will 
                             help select corresponding region files)
        ExpType            : type of experiments: 'RAN', 'RP'
        align_method       : 'FixRep': based on FixRepDF; 
                             'Fix_Sac': based on SacDF, FixDF
        addCharSp          : number of single character space added to EMF
                             for catching overshoot fixations; default = 1
    output:
        newStampDF : time stamped data in different trials with updated
                     line numbers
        
    """
    # first, check whether the stamp and region files are there:
    StampfileExist, StampfileDic = _crtCSV_dic(0, direct, subjID, '_Stamp')
    regfileExist, regfileDic = _crtRegion_dic(direct, regfileNameList)
    
    if align_method == 'FixRep':
        FixRepExist, FixRepDic = _crtFixRepDic(0, direct, subjID)        
    elif align_method == 'Fix_Sac':
        SacfileExist, SacfileDic = _crtCSV_dic(0, direct, subjID, '_Sac')
        FixfileExist, FixfileDic = _crtCSV_dic(0, direct, subjID, '_Fix')

    # second, process the files
    if StampfileExist and regfileExist and ((align_method == 'FixRep' and FixRepExist) or (align_method == 'Fix_Sac' and SacfileExist and FixfileExist)):
        StampDF = _pd.read_csv(StampfileDic[subjID], sep=',')    
        newStampDF = _pd.DataFrame()     
        print "Subj: ", subjID
        
        if align_method == 'FixRep':
            FixRepDF = _pd.read_csv(FixRepDic[subjID], sep='\t')
            SacDF = _np.nan; FixDF = _np.nan;
        elif align_method == 'Fix_Sac':
            FixRepDF = _np.nan
            SacDF = _pd.read_csv(SacfileDic[subjID], sep=',')
            FixDF = _pd.read_csv(FixfileDic[subjID], sep=',')     

        for trialID in _np.unique(map(int,StampDF.trial_id)):
            trial_type = _np.unique(StampDF.trial_type[StampDF.trial_id == trialID])[0]
            trialstart = _np.unique(StampDF.trialstart[StampDF.trial_id == trialID])[0]
            RegDF = _getRegDF(regfileDic, trial_type)  # get region file
            _modRegDF(RegDF, addCharSp) # modify mod_x1 and mod_x2 position of word regions
            # get time stamped data and crossline time stamped data
            print "Get crlStamp: Trial ", str(trialID), " Type ", _np.unique(StampDF.trial_type[StampDF.trial_id == trialID])[0]  
            StampDFtemp = StampDF[StampDF.trial_id==trialID].reset_index()
            _calTimeStamp(align_method, trial_type, trialstart, RegDF, StampDFtemp, FixRepDF, SacDF, FixDF)

            newStampDF = newStampDF.append(StampDFtemp, ignore_index=True)
                        
        return newStampDF


def cal_write_TimeStamp(direct, subjID, regfileNameList, ExpType, align_method, addCharSp=1):
    """
    processing a subject's time stamped data, read them from csv files and
    store them into csv files
    arguments:
        direct          : directory containing all asc files
        subjID          : subject ID
        regfileNameList : a list of region file names (trial_id will help 
                          select corresponding region files)
        ExpType         : type of experiments: 'RAN', 'RP'
        align_method    : 'FixRep': based on FixRepDF; 
                          'Fix_Sac': based on SacDF, FixDF
        addCharSp       : number of single character space added to EMF
                          for catching overshoot fixations; default = 1
    output:
        StampDF : time stamped data in different trials with updated line
                  numbers of different subjects
        All these data frames are stored in csv files
    """
    StampDF = cal_TimeStamp(direct, subjID, regfileNameList, ExpType, align_method, addCharSp)
    write_TimeStamp_Report(direct, subjID, StampDF)


def cal_write_TimeStamp_b(direct, regfileNameList, ExpType, align_method, addCharSp=1):
    """
    processing all subjects' time stamped data, read them from csv files
    and store them into csv files
    arguments:
        direct          : directory containing all asc files
        regfileNameList : a list of region file names (trial_id will help
                          select corresponding region files)
        ExpType         : type of experiments: 'RAN', 'RP'
        align_method    : 'FixRep': based on FixRepDF; 
                          'Fix_Sac': based on SacDF, FixDF
        addCharSp       : number of single character space added to EMF
                          for catching overshoot fixations; default = 1
    output:
        StampDF    : time stamped data in different trials with updated
                     line numbers of different subjects
        crlStampDF : crossline time stamped data in different trials of
                     different subjects
    """
    StampfileExist, StampfileDic = _crtCSV_dic(1, direct, '', '_Stamp')
    regfileExist, regfileDic = _crtRegion_dic(direct, regfileNameList)
    if StampfileExist and regfileExist:
        for subjID in StampfileDic.keys():
            StampDF = cal_TimeStamp(direct, subjID, regfileNameList, ExpType, align_method, addCharSp)
            write_TimeStamp_Report(direct, subjID, StampDF)


def read_cal_TimeStamp(direct, subjID, regfileNameList, ExpType, align_method, addCharSp=1):
    """
    read ASC file and extract the time stamped data and calculate cossline
    time stamped data
    arguments:
        direct             : directory for storing output files
        subjID             : subject ID
        regionfileNameList : a list of region file names (trial_id will
                             help select corresponding region files)
        ExpType            : type of experiments: 'RAN', 'RP'
        align_method       : 'FixRep': using fixation report data;
                             'Fix_Sac': using fixation data extracted
                             and aligned automatically
        addCharSp          : number of single character space added to  
                             RegDF for catching overshoot fixations; 
                             default = 1
    output:
        StampDF : time stamped data in different trials
    """
    # first, check whether the ascii and region files are there:
    ascfileExist, ascfileDic = _crtASC_dic(0, direct, subjID)
    regfileExist, regfileDic = _crtRegion_dic(direct, regfileNameList)
    
    ETRANfileExist = True
    #ETRANfileName = _os.path.join(direct, 'ETRAN.csv')
    #if not _os.path.isfile(ETRANfileName):
    #    print ETRANfileName + ' does not exist!'; ETRANfileExist = False
    #else:
    #    ETRANDF = _pd.read_csv(ETRANfileName); ETRANDF.SubjectID = ETRANDF.SubjectID.str.lower()
    
    if align_method == 'FixRep':
        FixRepExist, FixRepDic = _crtFixRepDic(0, direct, subjID)        
    elif align_method == 'Fix_Sac':
        SacfileExist, SacfileDic = _crtCSV_dic(0, direct, subjID, '_Sac')
        FixfileExist, FixfileDic = _crtCSV_dic(0, direct, subjID, '_Fix')
    
    # second, process the files
    if ascfileExist and regfileExist and ETRANfileExist and ((align_method == 'FixRep' and FixRepExist) or (align_method == 'Fix_Sac' and SacfileExist and FixfileExist)):
        # read EMF file
        f = open(ascfileDic[subjID], 'r'); print "Read ASC: ", f.name; lines = f.readlines(); f.close()   # read EMF file    
        script, sessdate, srcfile = _getHeader(lines)    # get header lines    
        T_idx, T_lines = _getTrialReg(lines) # get trial regions
    
        StampDF = _pd.DataFrame(columns=('subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'trialstart', 'trialend', 'tdur', 'recstart', 'recend', 'blinks', 'eye', 'time', 'x_pos1', 'y_pos1', 'pup_size1', 'x_pos2', 'y_pos2', 'pup_size2', 'line_no', 'gaze_region_no', 'label', 'error_free', 'Fix_Sac'))
        
        if align_method == 'FixRep':
            FixRepDF = _pd.read_csv(FixRepDic[subjID], sep='\t')
            SacDF = _np.nan; FixDF = _np.nan;
        elif align_method == 'Fix_Sac':
            FixRepDF = _np.nan
            SacDF = _pd.read_csv(SacfileDic[subjID], sep=',')
            FixDF = _pd.read_csv(FixfileDic[subjID], sep=',')          
            
        for ind in range(len(T_lines)):
            triallines = lines[T_lines[ind,0]+1:T_lines[ind,1]]; trialID = int(T_idx[ind,0].split(' ')[-1])
            blinklines, stamplines, sampfreq, eyerec = _getBlink_Fix_Sac_SampFreq_EyeRec(triallines, 1)
            trial_type, trialstart, trialend, tdur, recstart, recend = _gettdur(triallines)
            error_free = 1
     #      error_free = _getErrorFree(ETRANDF, subjID, trial_type)            
            RegDF = _getRegDF(regfileDic, trial_type)  # get region file
            _modRegDF(RegDF, addCharSp) # modify mod_x1 and mod_x2 position of word regions
            # read saccade data and get crossline saccade
            print "Read Time Stamped Data: Trial ", str(trialID), " Type ", trial_type
            StampDFtemp = _recTimeStamp(ExpType, trialID, blinklines, stamplines, sampfreq, eyerec, script, sessdate, srcfile, trial_type, trialstart, trialend, tdur, recstart, recend, error_free)        
            _calTimeStamp(align_method, trial_type, trialstart, RegDF, StampDFtemp, FixRepDF, SacDF, FixDF)
            
            StampDF = StampDF.append(StampDFtemp, ignore_index=True)

        return StampDF


def read_cal_write_TimeStamp(direct, subjID, regfileNameList, ExpType, align_method, addCharSp=1):
    """
    processing a subject's time stamped data
    arguments:
        direct          : directory containing all asc files
        subjID          : subject ID
        regfileNameList : a list of region file names (trial_id will help
                          select corresponding region files)
        ExpType         : type of experiments: 'RAN', 'RP'
        align_method    : 'FixRep': using fixation report data; 
                          'Fix_Sac': using fixation data extracted and
                          aligned automatically
        addCharSp       : number of single character space added to RegDF
                          for catching overshoot fixations; default = 1
    output:
        StampDF : time stamped data in different trials of different
                  subjects
        All these data frames are stored into csv files    
    """
    StampDF = read_cal_TimeStamp(direct, subjID, regfileNameList, ExpType, align_method, addCharSp)
    write_TimeStamp_Report(direct, subjID, StampDF)


def read_cal_write_TimeStamp_b(direct, regfileNameList, ExpType, align_method, addCharSp=1):
    """
    processing all subjects' time stamped data
    arguments:
        direct          : directory containing all asc files
        regfileNameList : a list of region file names (trial_id will help
                          select corresponding region files)
        ExpType         : type of experiments: 'RAN', 'RP'
        align_method    : 'FixRep': using fixation report data; 
                          'Fix_Sac': using fixation data extracted and
                          aligned automatically
        addCharSp       : number of single character space added to RegDF
                          for catching overshoot fixations; default = 1
    output:
        StampDF    : time stamped data in different trials of different
                     subjects
        crlStampDF : crossline time stamped data in different trials of
                     different subjects
        All these data frames are stored into csv files    
    """
    ascfileExist, ascfileDic = _crtASC_dic(1, direct, '')  
    regfileExist, regfileDic = _crtRegion_dic(direct, regfileNameList)
    if ascfileExist and regfileExist:
        for subjID in ascfileDic.keys():
            read_cal_write_TimeStamp(direct, subjID, regfileNameList, ExpType, align_method, addCharSp)

    
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# user functions for drawing saccades and fixations    
def draw_SacFix(direct, subjID, regfileNameList, bitmapNameList, drawType, max_FixRadius=30, drawFinal=False, showFixDur=False, PNGopt=0):    
    """
    read and draw saccade and fixation data
    arguments:
        direct          : directory storing csv and region files
        subjID          : subject ID
        regfileNameList : a list of region files (trial_id will help
                          select corresponding region files)
        bitmapNameList  : a list of png bitmaps showing the paragraphs
                          shown to the subject
        drawType        : type of drawing:
                          'ALL': draw all results (mixing saccade with
                                 fixation, and mixing crossline saccade
                                 with crossline fixation)
                          'SAC': draw saccade results (saccades and
                                 crossline saccades)
                          'FIX': draw fixation results (fixation and
                                 crossline fixations)
        max_FixRadius   : maximum radius of fixation circles for showing;
                          default = 30 
        drawFinal       : whether (True) or not (False) draw fixations and
                          saccades after the ending of reading; 
                          default = False
        showFixDur      : whether (True) or not (False) show number for
                          fixations; default = False 
        PNGopt          : 0: use png file as background; 
                          1: draw texts from region file; default = 0 
    output:
        when drawOpt == 'ALL'
            subj_FixSac_trial*.png    : showing the fixations and saccades
                                        of subj in different trials
            subj_crlFixSac_trial*.png : showing the crossline fixations
                                        and saccades of subj in different
                                        trials
        when drawType == 'SAC': subj_Sac_trial*.png; subj_crlSac_trial*.png
        when drawType == 'FIX': subj_Fix_trial*.png; subj_crlFix_trial*.png        
    """
    # first, check whether the required files are there:
    if drawType == 'ALL':
        SacfileExist, SacfileDic = _crtCSV_dic(0, direct, subjID, '_Sac')
        crlSacfileExist, crlSacfileDic = _crtCSV_dic(0, direct, subjID, '_crlSac')
        FixfileExist, FixfileDic = _crtCSV_dic(0, direct, subjID, '_Fix')        
        crlFixfileExist, crlFixfileDic = _crtCSV_dic(0, direct, subjID, '_crlFix')
    if drawType == 'SAC':
        SacfileExist, SacfileDic = _crtCSV_dic(0, direct, subjID, '_Sac')
        crlSacfileExist, crlSacfileDic = _crtCSV_dic(0, direct, subjID, '_crlSac')
    if drawType == 'FIX':
        FixfileExist, FixfileDic = _crtCSV_dic(0, direct, subjID, '_Fix')        
        crlFixfileExist, crlFixfileDic = _crtCSV_dic(0, direct, subjID, '_crlFix')
    
    regfileExist, regfileDic = _crtRegion_dic(direct, regfileNameList)
                
    if PNGopt == 0:
        bitmapExist = True
        if len(bitmapNameList) == 0:
            # automatically gather all region files in direct
            for file in _os.listdir(direct):
                if _fnmatch.fnmatch(file, '*.png'):
                    bitmapNameList.append(str(file))
        else:
            # check whether particular region file exists!
            for bitmapfile in bitmapNameList:
                bitmapfileName = _os.path.join(direct, bitmapfile)
                if not _os.path.isfile(bitmapfileName):
                    print bitmapfile + ' does not exist!'; bitmapExist = False 
                       
    # second, process the files
    if SacfileExist and FixfileExist and crlSacfileExist and crlFixfileExist and regfileExist and ((PNGopt == 0 and bitmapExist) or PNGopt == 1):
        # read files
        SacDF = _pd.read_csv(SacfileDic[subjID], sep=','); crlSacDF = _pd.read_csv(crlSacfileDic[subjID], sep=',')
        FixDF = _pd.read_csv(FixfileDic[subjID], sep=','); crlFixDF = _pd.read_csv(crlFixfileDic[subjID], sep=',')
    
        # draw fixation and saccade data on a picture
        for trialID in range(len(regfileDic)):
            RegDF = _getRegDF(regfileDic, _np.unique(SacDF.trial_type[SacDF.trial_id == trialID])[0])  # get region file
            print "Draw Sac and Fix: Subj: " + subjID + ", Trial: " + str(_np.unique(SacDF.trial_type[SacDF.trial_id == trialID]))
            Sac = SacDF[SacDF.trial_id == trialID].reset_index(); crlSac = crlSacDF[crlSacDF.trial_id == trialID].reset_index()
            Fix = FixDF[FixDF.trial_id == trialID].reset_index(); crlFix = crlFixDF[crlFixDF.trial_id == trialID].reset_index()    
            _image_SacFix(direct, subjID, bitmapNameList, Sac, crlSac, Fix, crlFix, RegDF, trialID, drawType, max_FixRadius, drawFinal, showFixDur, PNGopt)


def draw_SacFix_b(direct, regfileNameList, bitmapNameList, method, max_FixRadius=30, drawFinal=False, showNum=False, PNGmethod=0):
    """
    drawing of all subjects' fixation and saccade data figures
    arguments:
        direct          : directory containing all csv files
        regfileNameList : a list of region file names (trial_id will help
                          select corresponding region files)
        bitmapNameList  : a list of png bitmaps showing the paragraphs
                          shown to the subject
        drawFinal       : whether (True) or not (False) draw fixations and
                          saccades after the ending of reading     
        method          : drawing method:
                          'ALL': draw all results (mixing saccade with
                                 fixation, and mixing crossline saccade
                                 with crossline fixation)
                          'SAC': draw saccade results (saccades and
                                 crossline saccades)
                          'FIX': draw fixation results (fixation and
                                 crossline fixations)
        max_FixRadius   : maximum radius of fixation circles for showing;
                          default = 30 
        drawFinal       : whether (True) or not (False) draw fixations and
                          saccades after the ending of reading; 
                          default = False
        showNum         : whether (True) or not (False) show number for
                          fixations; default = False
        PNGmethod       : whether use png file as background (0) or draw
                          texts from region file (1); default = 0     
    output:
        when method == 'ALL'
            *_FixSac_trial*.png    : showing the fixations and saccades of
                                     all subjects in different trials
            *_crlFixSac_trial*.png : showing the crossline fixations and
                                     saccades of all subjects in different
                                     trials
        when method == 'SAC': *_Sac_trial*.png; *_crlSac_trial*.png
        when method == 'FIX': *_Fix_trial*.png; *_crlFix_trial*.png            
    """
    subjlist = []
    for root, dirs, files in _os.walk(direct):
        for name in files:
            if name.endswith(".asc"):
                subjlist.append(name.split('.')[0])
    subjlist = _np.unique(subjlist)
    if len(subjlist) == 0:
        print 'No csv files in the directory!'      

    regfileExist, regfileDic = _crtRegion_dic(direct, regfileNameList)

    if PNGmethod == 0:
        bitmapExist = True
        if len(bitmapNameList) == 0:
            # automatically gather all region files in direct
            for file in _os.listdir(direct):
                if _fnmatch.fnmatch(file, '*.png'):
                    bitmapNameList.append(str(file))
        else:
            # check whether particular region file exists!
            for bitmapfile in bitmapNameList:
                bitmapfileName = _os.path.join(direct, bitmapfile)
                if not _os.path.isfile(bitmapfileName):
                    print bitmapfile + ' does not exist!'; bitmapExist = False    
    
    if regfileExist and ((PNGmethod == 0 and bitmapExist) or PNGmethod == 1):
        for subjID in subjlist:
            draw_SacFix(direct, subjID, regfileNameList, bitmapNameList, method, max_FixRadius, drawFinal, showNum, PNGmethod)


def draw_blinks(direct, trialNum):
    """
    draw histogram of individual blinks
    arguments: 
        direct   : directory storing csv files
        trialNum : number of trials in each subject's data
    output: histogram    
    """
    subjlist = []
    for file in _os.listdir(direct):
        if _fnmatch.fnmatch(file, '*.asc'):
            subjlist.append(file.split('.')[0])
            
    for trialID in range(trialNum):
        blinksdata = []
        for subj in subjlist:
            FixDF = _pd.read_csv(_os.path.join(direct, subj + '_Fix.csv'), sep=',')
            FixDFtemp = FixDF[FixDF.trial_id==trialID].reset_index(); blinksdata.append(FixDFtemp.blinks[0])
        # draw histogram    
        fig = _plt.figure()
        ax = fig.add_subplot(111)
        ax.hist(blinksdata, bins=20, normed=True)
        ax.set_title('Histogram of Blinks (trial = ' + str(trialID) + '; n= ' + str(len(blinksdata)) + ')')
        ax.set_xlabel('No. Blinks'); ax.set_ylabel('Frequency')
        _plt.show()
        _plt.savefig(direct + '/Hist_blinks_trial' + str(trialID) + '.png')
    

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# user functions for animation of eye-movement
def changePNG2GIF(direct):
    """
    change PNG bitmaps in direct to GIF bitmaps for animation
    argument:
        direct : directory storing PNG bitmaps, the created GIF bitmaps
                 are also there
    """
    PNGList = []
    for file in _os.listdir(direct):
        if _fnmatch.fnmatch(file, '*.png'):
            PNGList.append(str(file))
    if len(PNGList) == 0:
        print 'PNG bitmap is missing!'
    else:
        for PNGfile in PNGList:
            im = Image.open(_os.path.join(direct, PNGfile))
            im = im.convert('RGB').convert('P', palette = Image.ADAPTIVE)
            im.save(_os.path.join(direct, PNGfile.split('.')[0] + '.gif'))


def animate(direct, subjID, trialID):
    """
    draw animation of a trial
    arguments: 
        direct  : directory of bitmaps, sound files, and fixation csv files
        subjID  : subject ID        
        trialID : trial ID
    """
    csvExist = False
    csvlist = []
    for file in _os.listdir(_os.path.join(direct, subjID)):
        if _fnmatch.fnmatch(file, '*_Fix*.csv'):
            csvlist.append(str(file))
    if len(csvlist) == 0: print 'No csv files in the directory!'        
    for csvfile in csvlist:
        if csvfile.split('_Fix')[0] == subjID:
            csvfile_subj = csvfile; csvExist = True
    if not csvExist: print 'Data of ' + subjID + ' is missing!'
    
    bitmapExist = False
    bitmapNameList = []
    for file in _os.listdir(direct):
        if _fnmatch.fnmatch(file, '*.gif'):
            bitmapNameList.append(str(file))
    if len(bitmapNameList) == 0: print 'GIF bitmap is missing!'        
    if trialID < 0 or (len(bitmapNameList) > 1 and trialID >= len(bitmapNameList)):
        print 'Invalid trial ID!'
    else: bitmapExist = True
    
    soundExist, trialExist = False, False    
    soundNameList = []
    for file in _os.listdir(_os.path.join(direct, subjID)):
        if _fnmatch.fnmatch(file, '*.wav'):
            soundNameList.append(str(file))
    if len(soundNameList) == 0: print 'Sound file is missing!'        
    for soundfile in soundNameList:
        if soundfile.split('-')[0] == subjID:
            soundExist = True
            if soundfile.split('-')[1].split('.')[0] == str(trialID + 1):
                soundfile_subj = soundfile; trialExist = True
    if not soundExist or not trialExist: print 'Sound data of ' + subjID + ' is missing!'
    
    if csvExist and bitmapExist and soundExist and trialExist:
        csvFix = _os.path.join(direct, subjID, csvfile_subj); FixDF = _pd.read_csv(csvFix, sep=',')
        Fix = FixDF[FixDF.trial_id == trialID].reset_index()
        if len(bitmapNameList) == 1: bitmapFile = _os.path.join(direct, bitmapNameList[0])
        else: bitmapFile = _os.path.join(direct, bitmapNameList[trialID])
        soundFile = _os.path.join(direct, subjID, soundfile_subj)    
        
        _animate_EM(direct, subjID, bitmapFile, soundFile, Fix, trialID)


def animate_TimeStamp(direct, subjID, trialID):
    """
    draw animation of a trial using time stamped data
    arguments: 
        direct  : directory storing bitmaps, sound files, and time stamped
                  csv files
        subjID  : subject ID        
        trialID : trial ID
    """
    csvExist = False
    csvlist = []
    for file in _os.listdir(_os.path.join(direct, subjID)):
        if _fnmatch.fnmatch(file, '*_Stamp.csv'):
            csvlist.append(str(file))
    if len(csvlist) == 0: print 'No csv files in the directory!'        
    for csvfile in csvlist:
        if csvfile.split('_Stamp')[0] == subjID:
            csvfile_subj = csvfile; csvExist = True
    if not csvExist: print 'Data of ' + subjID + ' is missing!'
    
    bitmapExist = False
    bitmapNameList = []
    for file in _os.listdir(direct):
        if _fnmatch.fnmatch(file, '*.gif'):
            bitmapNameList.append(str(file))
    if len(bitmapNameList) == 0: print 'GIF bitmap is missing!'        
    if trialID < 0 or (len(bitmapNameList) > 1 and trialID >= len(bitmapNameList)):
        print 'Invalid trial ID!'
    else: bitmapExist = True
    
    soundExist, trialExist = False, False    
    soundNameList = []
    for file in _os.listdir(_os.path.join(direct, subjID)):
        if _fnmatch.fnmatch(file, '*.wav'):
            soundNameList.append(str(file))
    if len(soundNameList) == 0: print 'Sound file is missing!'        
    for soundfile in soundNameList:
        if soundfile.split('-')[0] == subjID:
            soundExist = True
            if soundfile.split('-')[1].split('.')[0] == str(trialID + 1):
                soundfile_subj = soundfile; trialExist = True
    if not soundExist or not trialExist: print 'Sound data of ' + subjID + ' is missing!'
    
    if csvExist and bitmapExist and soundExist and trialExist:
        csvStamp = _os.path.join(direct, subjID, csvfile_subj); StampDF = _pd.read_csv(csvStamp, sep=',')
        Stamp = StampDF[StampDF.trial_id == trialID].reset_index()
        if len(bitmapNameList) == 1: bitmapFile = _os.path.join(direct, bitmapNameList[0])
        else: bitmapFile = _os.path.join(direct, bitmapNameList[trialID])
        soundFile = _os.path.join(direct, subjID, soundfile_subj)    
        
        _animate_EM_TimeStamp(direct, subjID, bitmapFile, soundFile, Stamp, trialID)
        

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# user functions for calculating eye-movement measures
def cal_write_EM(direct, subjID, regfileNameList, addCharSp=1):
    """
    read fixation and saccade data of subj and calculate eye-movement 
    measures
    arguments:
        direct             : directory for storing csv and output files
        subjID             : subject ID
        regionfileNameList : a list of region file names (trial_id
                             will help select corresponding region files)
        addCharSp          : number of single character space added to EMF
                             for catching overshoot fixations; default = 1
    output:
        write each trial's results to csv files
    """
    # first, check whether the required files are there:
    SacfileExist, SacfileDic = _crtCSV_dic(0, direct, subjID, '_Sac')
    FixfileExist, FixfileDic = _crtCSV_dic(0, direct, subjID, '_Fix')    
    regfileExist, regfileDic = _crtRegion_dic(direct, regfileNameList)
    
    # second, process the files
    if SacfileExist and FixfileExist and regfileExist:
        SacDF = _pd.read_csv(SacfileDic[subjID], sep=',')   # read saccade data
        FixDF = _pd.read_csv(FixfileDic[subjID], sep=',')   # read fixation data
        for trialID in range(len(regfileDic)):
            RegDF = _getRegDF(regfileDic, _np.unique(SacDF.trial_type[SacDF.trial_id == trialID])[0]) # get region file 
            SacDFtemp = SacDF[SacDF.trial_id==trialID].reset_index()  # get saccade of the trial
            FixDFtemp = FixDF[FixDF.trial_id==trialID].reset_index()  # get fixation of the trial
            
            if len(_np.unique(SacDFtemp.eye)) == 1:
                # single eye data
                if _np.unique(SacDFtemp.eye)[0] == 'L': print 'Cal EM measures: Subj: ' + subjID + ', Trial: ' + str(trialID) + ' Left Eye'
                elif _np.unique(SacDFtemp.eye)[0] == 'R': print 'Cal EM measures: Subj: ' + subjID + ', Trial: ' + str(trialID) + ' Right Eye'
                # create result data frame
                EMDF = _pd.DataFrame(_np.zeros((len(RegDF), 36)))
                EMDF.columns = ['subj', 'trial_id', 'trial_type', 'trialstart', 'trialend', 'tdur', 'recstart', 'recend', 'blinks', 'eye', 'tffixos', 'tffixurt', 'tfixcnt', 'tregrcnt', 'region', 'reglen', 'word', 'line_no', 'x1_pos', 'x2_pos', 'mod_x1', 'mod_x2',
                                'fpurt', 'fpcount', 'fpregres', 'fpregreg', 'fpregchr', 'ffos', 'ffixurt', 'spilover', 'rpurt', 'rpcount', 'rpregreg', 'rpregchr', 'spurt', 'spcount']
                # copy values from FixDF about the whole trial               
                EMDF.subj = subjID; EMDF.trial_id = FixDFtemp.trial_id[0]; EMDF.trial_type = FixDFtemp.trial_type[0]
                EMDF.trialstart = FixDFtemp.trialstart[0]; EMDF.trialend = FixDFtemp.trialend; EMDF.tdur = FixDFtemp.tdur[0]; EMDF.recstart = FixDFtemp.recstart[0]; EMDF.recend = FixDFtemp.recend[0]
                EMDF.blinks = FixDFtemp.blinks[0]; EMDF.eye = FixDFtemp.eye[0]
                # copy values from RegDF about region        
                EMDF.region = RegDF.WordID; EMDF.reglen = RegDF.length; EMDF.word = RegDF.Word; EMDF.line_no = RegDF.line_no; EMDF.x1_pos = RegDF.x1_pos; EMDF.x2_pos = RegDF.x2_pos
                _modEM(EMDF, addCharSp) # modify EMF's mod_x1 and mod_x2
                _cal_EM(RegDF, FixDFtemp, SacDFtemp, EMDF)
                # store results
                if _np.unique(SacDFtemp.eye)[0] == 'L':
                    nameEM = _os.path.join(direct, subjID, subjID + '_EM_trial' + str(trialID) + '_L.csv'); EMDF.to_csv(nameEM, index=False)
                elif _np.unique(SacDFtemp.eye)[0] == 'R':
                    nameEM = _os.path.join(direct, subjID, subjID + '_EM_trial' + str(trialID) + '_R.csv'); EMDF.to_csv(nameEM, index=False)   
            else:
                # double eye data
                SacDFtemp_L = SacDFtemp[SacDFtemp.eye=='L'].reset_index(); SacDFtemp_R = SacDFtemp[SacDFtemp.eye=='R'].reset_index()                 
                FixDFtemp_L = FixDFtemp[FixDFtemp.eye=='L'].reset_index(); FixDFtemp_R = FixDFtemp[FixDFtemp.eye=='R'].reset_index()
                
                print "Cal EM measures: Subj: " + subjID + ", Trial: " + str(trialID) + ' Left Eye'
                # create result data frame
                EMDF_L = _pd.DataFrame(_np.zeros((len(RegDF), 36)))
                EMDF_L.columns = ['subj', 'trial_id', 'trial_type', 'trialstart', 'trialend', 'tdur', 'recstart', 'recend', 'blinks', 'eye', 'tffixos', 'tffixurt', 'tfixcnt', 'tregrcnt', 'region', 'reglen', 'word', 'line_no', 'x1_pos', 'x2_pos', 'mod_x1', 'mod_x2',
                                  'fpurt', 'fpcount', 'fpregres', 'fpregreg', 'fpregchr', 'ffos', 'ffixurt', 'spilover', 'rpurt', 'rpcount', 'rpregreg', 'rpregchr', 'spurt', 'spcount']
                # copy values from FixDF about the whole trial               
                EMDF_L.subj = subjID; EMDF_L.trial_id = FixDFtemp_L.trial_id[0]; EMDF_L.trial_type = FixDFtemp_L.trial_type[0]
                EMDF_L.trialstart = FixDFtemp_L.trialstart[0]; EMDF_L.trialend = FixDFtemp_L.trialend[0]; EMDF_L.tdur = FixDFtemp_L.tdur[0]; EMDF_L.recstart = FixDFtemp_L.recstart[0]; EMDF_L.recend = FixDFtemp_L.recend[0]
                EMDF_L.blinks = FixDFtemp_L.blinks[0]; EMDF_L.eye = FixDFtemp_L.eye[0]
                # copy values from RegDF about region        
                EMDF_L.region = RegDF.WordID; EMDF_L.reglen = RegDF.length; EMDF_L.word = RegDF.Word; EMDF_L.line_no = RegDF.line_no; EMDF_L.x1_pos = RegDF.x1_pos; EMDF_L.x2_pos = RegDF.x2_pos
                _modEM(EMDF_L, addCharSp) # modify EMF's mod_x1 and mod_x2
                _cal_EM(RegDF, FixDFtemp_L, SacDFtemp_L, EMDF_L)
                # store results
                nameEM_L = _os.path.join(direct, subjID, subjID + '_EM_trial' + str(trialID) + '_L.csv'); EMDF_L.to_csv(nameEM_L, index=False)
            
                print "Cal EM measures: Subj: " + subjID + ", Trial: " + str(trialID) + ' Right Eye'
                # create result data frame
                EMDF_R = _pd.DataFrame(_np.zeros((len(RegDF), 36)))
                EMDF_R.columns = ['subj', 'trial_id', 'trial_type', 'trialstart', 'trialend', 'tdur', 'recstart', 'recend', 'blinks', 'eye', 'tffixos', 'tffixurt', 'tfixcnt', 'tregrcnt', 'region', 'reglen', 'word', 'line_no', 'x1_pos', 'x2_pos', 'mod_x1', 'mod_x2',
                                  'fpurt', 'fpcount', 'fpregres', 'fpregreg', 'fpregchr', 'ffos', 'ffixurt', 'spilover', 'rpurt', 'rpcount', 'rpregreg', 'rpregchr', 'spurt', 'spcount']
                # copy values from FixDF about the whole trial               
                EMDF_R.subj = subjID; EMDF_R.trial_id = FixDFtemp_R.trial_id[0]; EMDF_R.trial_type = FixDFtemp_R.trial_type[0]
                EMDF_R.trialstart = FixDFtemp_R.trialstart[0]; EMDF_R.trialend = FixDFtemp_R.trialend[0]; EMDF_R.tdur = FixDFtemp_R.tdur[0]; EMDF_R.recstart = FixDFtemp_R.recstart[0]; EMDF_R.recend = FixDFtemp_R.recend[0]
                EMDF_R.blinks = FixDFtemp_R.blinks[0]; EMDF_R.eye = FixDFtemp_R.eye[0]
                # copy values from RegDF about region        
                EMDF_R.region = RegDF.WordID; EMDF_R.reglen = RegDF.length; EMDF_R.word = RegDF.Word; EMDF_R.line_no = RegDF.line_no; EMDF_R.x1_pos = RegDF.x1_pos; EMDF_R.x2_pos = RegDF.x2_pos
                _modEM(EMDF_R, addCharSp) # modify EMF's mod_x1 and mod_x2
                _cal_EM(RegDF, FixDFtemp_R, SacDFtemp_R, EMDF_R)
                # store results
                nameEM_R = _os.path.join(direct, subjID, subjID + '_EM_trial' + str(trialID) + '_R.csv'); EMDF_R.to_csv(nameEM_R, index=False)


def cal_write_EM_b(direct, regfileNameList, addCharSp=1):
    """
    batch calculating all subjects' EMF measures
    arguments:
        direct          : directory containing all csv files
        regfileNameList : a list of region file names (trial_id will help
                          select corresponding region files)
        addCharSp       : number of single character space added to EMF
                          for catching overshoot fixations; default = 1
    output:
        write each subject's each trial's results to csv files        
    """
    SacfileExist, SacfileDic = _crtCSV_dic(1, direct, '', '_Sac')
    FixfileExist, FixfileDic = _crtCSV_dic(1, direct, '', '_Fix')    
    regfileExist, regfileDic = _crtRegion_dic(direct, regfileNameList)    
    if SacfileExist and FixfileExist and regfileExist:
        for subjID in SacfileDic.keys():
            cal_write_EM(direct, subjID, regfileNameList)  


def mergeCSV(direct, regfileNameList, subjID):
    """
    merge csv files of eye-movement stamped data and audio csv file
    arguments:
        direct          : current directory storing results, each subject's
                          data are in one subfolder with the same subject ID
        regfileNameList : list of region files
        subjID          : subject ID
    output:
        subjID_merge.csv
    """    
    StampfileExist, StampfileDic = _crtCSV_dic(0, direct, subjID, '_Stamp')
    regfileExist, regfileDic = _crtRegion_dic(direct, regfileNameList)
    if StampfileExist and regfileExist:
        print 'SubjID ', subjID
        mergeDF = _pd.DataFrame()
        
        EMDF = _pd.read_csv(StampfileDic[subjID], sep=',')
        EMDF['gaze_time'] = EMDF.time - EMDF.recstart; 
        EMDF['audio_time'] = _np.nan; EMDF['audio_label'] = _np.nan; EMDF['audio_region_no'] = _np.nan

        trialList = list(_np.unique(EMDF.trial_type))
        for trial in trialList:
            print 'Processing Trial ', trial
            # get region file
            RegDF = _pd.read_csv(regfileDic[trial+'.region.csv'])
            # get ETime file    
            aufile = _os.path.join(direct, subjID, subjID + '-' + trial + '_ETime.csv')
            if not _os.path.isfile(aufile):
                print aufile + ' does not exist!' 
            else:            
                AUDF = _pd.read_csv(aufile, sep = ',', header=None)
                AUDF.columns = ['audio_label', 'audio_time']
                AUDF.audio_label = AUDF.audio_label.str.lower()
                AUDF.loc[AUDF.audio_label == 'sp', 'audio_label'] = _np.nan
                AUDF.audio_time = AUDF.audio_time.astype(float)*1000
                # find merge point!
                EMDFtemp = EMDF[EMDF.trial_type == trial].reset_index()            
                for ind in range(len(EMDFtemp)-1):
                    if EMDFtemp.gaze_time[ind] < AUDF.audio_time[0] and EMDFtemp.gaze_time[ind+1] >= AUDF.audio_time[0]:
                        for ind2 in range(ind+1, ind+1+len(AUDF)):
                            EMDFtemp.loc[ind2, 'audio_time'] = AUDF.audio_time[ind2-ind-1]
                            EMDFtemp.loc[ind2, 'audio_label'] = AUDF.audio_label[ind2-ind-1]
                        break
                
                # add audio_region_no (only for error_free trials)
                if EMDFtemp.error_free[0] == 1:
                    cur_region = 1; cur_label = list(RegDF.Word[RegDF.WordID==cur_region])[0]
                    ind = 0
                    while ind < len(EMDFtemp):
                        while ind < len(EMDFtemp) and EMDFtemp.loc[ind, 'audio_label'] != cur_label: ind += 1
                        while ind < len(EMDFtemp) and EMDFtemp.loc[ind, 'audio_label'] == cur_label:
                            EMDFtemp.loc[ind, 'audio_region_no'] = cur_region; ind += 1
                        cur_region += 1
                        if cur_region < 37:
                            cur_label = list(RegDF.Word[RegDF.WordID==cur_region])[0]
                    
                mergeDF = mergeDF.append(EMDFtemp, ignore_index=True)
            
        # store results file
        mergeDF = mergeDF.sort(['trial_id','time'], ascending=True)
        mergefileName = _os.path.join(direct, subjID, subjID + '_Merge.csv')
        mergeDF.to_csv(mergefileName, index=False)            
    
    
def mergeCSV_b(direct, regfileNameList):
    """
    merge csv files of eye-movement stamped data and audio csv file of all
    agents
    arguments:
        direct          : current directory storing results, each subject's
                          data are in one subfolder with the same subject ID
        regfileNameList : list of region files
    output:
        subjID_merge.csv for each subject
    """
    StampfileExist, StampfileDic = _crtCSV_dic(1, direct, '', '_Stamp')
    regfileExist, regfileDic = _crtRegion_dic(direct, regfileNameList)
    if StampfileExist and regfileExist:
        for subjID in StampfileDic.keys():
            mergeCSV(direct, regfileNameList, subjID)

