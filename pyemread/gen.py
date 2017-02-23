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

This is a set of functions designed for generating bitmaps of 
single/multi-line texts for reading, including txt/csv files specifying 
word-wise regions of interest, and visualizing saccades, fixations,
and time-stamped eye-movement data on bitmaps.

For usage, 
In python code, use: from pyemread import gen
Then, one can call all functions in the package using the namespace gen.
Or, one can use: import pyemread as pr, 
and then use pr.gen to call functions in gen.
"""

# import helper functions from _helperfunc_.py
import os as _os
import sys as _sys
import fnmatch as _fnmatch
import re as _re
import csv as _csv
import turtle as _turtle
import time as _time
import winsound as _ws
import pandas as _pd
import numpy as _np
from PIL import Image, ImageDraw, ImageFont
import matplotlib.font_manager as _font_manager
import codecs as _codecs
import matplotlib.pyplot as _plt


# make the system default codeing as "utf-8"
reload(_sys); _sys.setdefaultencoding("utf-8")


# global variables for language types
EngLangList = ['English', 'French', 'German', 'Dutch', 'Spanish', 'Italian', 'Greek']
ChnLangList = ['Chinese']
KJLangList = ['Korean', 'Japanese']
puncList = [u'，', u'。', u'、', u'：', u'？', u'！']


# dictionary for storing each word's information
class Dictlist(dict):
    def __setitem__(self, key, value):
        try:
            self[key]
        except KeyError:
            super(Dictlist, self).__setitem__(key, [])
        self[key].append(value)

        
def saveDict(fn,dict_rap):
    f = open(fn,'wb')
    w = _csv.writer(f)
    for key, val in dict_rap.items():
        w.writerow([key,eval(val)])
    f.close()
     

def readDict(fn):
    f = open(fn,'rb')
    dict_rap = Dictlist()
    for key, val in _csv.reader(f):
        dict_rap[key] = eval(val)
    f.close()
    return(dict_rap)
    

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# class for PRaster (generating bitmap of pararaphs) and Draw_Fix_Sac 
class FontDict(dict):
    """ 
    Build a list of installed fonts with meta-data.
    """
    def __init__(self):
        """
        This function returns a dict (fontdict) that includes a key for 
        each font family, with subkeys for each variant in the family 
        (e.g., fontdict['Arial']['Regular'] might contain 
        u'c:\\windows\\fonts\\arial.ttf'). Explore functionality in 
        font_manager to see if this is really needed. Especially check 
        into borrowing functionality from createFontList().
        fl=_font_manager.createFontList(_font_manager.findSystemFonts())
        """
        dict.__init__(self)
        fontpathlist = _font_manager.findSystemFonts()
        fontpathlist.sort() # Get paths to all installed font files (any system?).
        for fp in fontpathlist:
            fi = ImageFont.truetype(fp, 12)
            family = _re.sub('[ -._]', '', fi.getname()[0])
            try:    # will fail if font family does not already exist in self
                exec(family + '[fi.getname()[1]]=fp')
            except NameError:   # Make a new font family entry
                exec(family + '={}')
            exec('self[family] = eval(family)')
        
    def families(self):
        """
        Return a sorted list of font families contained in FontDict.
        """
        return(sorted(self.keys()))

    def familyN(self):
        """
        Number of font families in FontDict.
        """
        return(self.__len__())

    def familyGet(self, family):
        """
        Given a font family name, return a dict containing available styles
        in the family (keys) and paths to relevant font files (values).
        """
        if not self.has_key(family):
            return(None)
        else:
            return(self[family])

    def fontGet(self, family, style):
        """
        Given a font family name and a style name, return a u"" containing
        the full path to the relevant font file.
        """
        if not self.has_key(family):
            print ("Family '%s' does not exist." % (family,))
            return(None)
        else:
            if not self[family].has_key(style):
                print ("Family '%s' does not include style '%s'" % (family, style))
                return(None) # maybe return the available styles?
            else:
                return(self[family][style])

                
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# other helper functions
def _getRegDF(regfileDic, trial_type):
    """
    get the region file data frame from regfileNameList based on trialID
    arguments:
        regfileDic : a dictionary of region file
                     names and directories
        trial_type : current trial ID
    return:
        RegDF : region file data frame
    """
    regfileName = trial_type + '.region.csv'
    if not (regfileName in regfileDic.keys()):
        raise ValueError("invalid trial_type!")
    RegDF = _pd.read_csv(regfileDic[regfileName], sep=',')
    return RegDF


def _crtCSV_dic(sit, direct, subjID, csvfiletype):
    """
    create dictionary for different types of csv files
    arguments:
        sit         : situations 0: subjID is given; 1, no subjID
        direct      : root directory: all csv files should be in level 
                      subfolder whose name is the same as the ascii file
        subjID      : subject ID (for sit=0)
        csvfiletype : "_Stamp", "_Sac", "_crlSac", "_Fix", "_crlFix" 
    output:
        csvfileExist : whether or not csv file exists
        csvfileDic   : dictionary with key = subject ID, value = file with
                       directory
    """
    csvfileExist = True
    csvfileDic = {}
    
    targetfileEND = csvfiletype + '.csv'
    if sit == 0:
        fileName = _os.path.join(direct, subjID, subjID + targetfileEND)
        if _os.path.isfile(fileName):
            csvfileDic[subjID] = _os.path.join(direct, subjID, subjID + targetfileEND)
        else:            
            print subjID + csvfiletype + '.csv' + ' does not exist!'
            csvfileExist = False            
    elif sit == 1:
        # search all subfolders for ascii file
        for root, dirs, files in _os.walk(direct):
            for name in files:
                if name.endswith(targetfileEND):
                    csvfileDic[name.split(targetfileEND)[0]] = _os.path.join(direct, name.split(targetfileEND)[0], name)
        if len(csvfileDic) == 0:
            print 'No ascii files in subfolders!'
            csvfileExist = False                
    
    return csvfileExist, csvfileDic


def _crtRegion_dic(direct, regfileNameList):
    """
    create region file dictionary
    arguments:
        direct          : root directory, all region files should be there
        regfileNameList : list of region file names
    output:
        regfileExist : whether or not all region files in 
                       regfileNameList exist in the current directory
        regfileDic   : dictionary with key = region file name, value = 
                       file with directory
    """    
    regfileExist = True
    regfileDic = {}
    
    targetfileEND = '.region.csv'
    if len(regfileNameList) == 0:
        # automatically gather all region files in direct
        for file in _os.listdir(direct):
            if _fnmatch.fnmatch(file, '*' + targetfileEND):
                regfileDic[str(file)] = _os.path.join(direct, str(file))
        if len(regfileDic) == 0:
            print 'No region file exists in ' + direct + '!'
            regfileExist = False
    else:
        # check whether particular region file exists!            
        for regfile in regfileNameList:
            regfileName = _os.path.join(direct, regfile)
            if _os.path.isfile(regfileName):
                regfileDic[regfile] = regfileName
            else:
                print regfile + ' does not exist!'; regfileExist = False
    
    return regfileExist, regfileDic            


# helper functions for generating bitmap used for paragraph reading
def _InputDict(resDict, curKey, Name, langType, Word, length, height, baseline, curline, x1_pos, y1_pos, x2_pos, y2_pos, b_x1, b_y1, b_x2, b_y2):
    """
    Write result of each word into resDict. 
    Note that dictionary value may have a different 
    sequence as in the final csv
    """
    resDict[curKey] = Name 
    resDict[curKey] = langType
    resDict[curKey] = Word
    resDict[curKey] = length; resDict[curKey] = height
    resDict[curKey] = baseline; resDict[curKey] = curline
    resDict[curKey] = x1_pos; resDict[curKey] = y1_pos
    resDict[curKey] = x2_pos; resDict[curKey] = y2_pos
    resDict[curKey] = b_x1; resDict[curKey] = b_y1
    resDict[curKey] = b_x2; resDict[curKey] = b_y2    
    return(resDict)


def _writeCSV(regFile, resDict, codeMethod):
    """
    Write resDict to csv file: 
    Name, Language, WordID, Word, length, height, baseline, line_no, 
    x1_pos, y1_pos, x2_pos, y2_pos, b_x1, b_y1, b_x2, b_y2
    """
    DF = _pd.DataFrame(_np.zeros((len(resDict), 16)))
    col = ['Name', 'Language', 'WordID', 'Word', 'length', 'height', 
           'baseline', 'line_no', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos',
           'b_x1', 'b_y1', 'b_x2', 'b_y2']
    cur = 0    
    for key in resDict.keys():
        DF.loc[cur,0] = resDict[key][0]; DF.loc[cur,1] = resDict[key][1]
        DF.loc[cur,2] = key        
        DF.loc[cur,3] = resDict[key][2].encode(codeMethod)
        for i in _np.arange(3,15):
            DF.loc[cur,i+1] = int(resDict[key][i])
        cur += 1
    DF.columns = col; DF.sort(columns='WordID')
    DF.to_csv(regFile, index=False)


# helper functions for calculating descents and ascents of characters in words 
def _getStrikeAscents(fontFileName, size):
    """
    Build and return a dictionary of ascents (in pixels) for a font/size:
    For English:
    group1: u'bdfhijkl|()\"\''
    group2: u't'
    group3: u'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    group4: u'0123456789'
    group5: u'?!'
    group6: u'%&@$'
    For English-like languages (e.g., Spanish, French, Italian, Greek):
    group7: u'àáâãäåèéêëìíîïñòóôõöùúûüāăćĉċčēĕėěĩīĭńňōŏőŕřśŝšũūŭůűŵźżž'
    group8: u'ÀÁÂÃÄÅÆÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝĀĂĆĈĊČĎĒđĔĖĚĜĞĠĤĥĴĹĺłŃŇŊŌŎŐŒŔŘŚŜŠŤŦŨŪŬŮŰŴŶŸŹŻŽƁſ'
    group9: u'ßÞƀƄƚɓɫɬʖʕʔʡʢ'
    """
    ttf = ImageFont.truetype(fontFileName, size) # init the specified font resource
    (wd_o, ht_o) = ttf.getsize(u'o')    # used as the baseline character
    
    (wd_b, ht_b) = ttf.getsize(u'b')    # representative of group 1
    (wd_t, ht_t) = ttf.getsize(u't')    # representative of group 2
    (wd_A, ht_A) = ttf.getsize(u'A')    # representative of group 3
    (wd_0, ht_0) = ttf.getsize(u'0')    # representative of group 4
    (wd_ques, ht_ques) = ttf.getsize(u'?')  # representative of group 5
    (wd_and, ht_and) = ttf.getsize(u'&')    # representative of group 6
    
    (wd_sap, ht_sap) = ttf.getsize(u'à')   # representative of group 7
    (wd_cAp, ht_cAp) = ttf.getsize(u'À')   # representative of group 8 
    (wd_beta, ht_beta) = ttf.getsize(u'ß')  # representative of group 9
    
    return ({u'bdfhijkl|()\"\'': ht_b - ht_o,
             u't': ht_t - ht_o,
             u'ABCDEFGHIJKLMNOPQRSTUVWXYZ': ht_A - ht_o,
             u'0123456789': ht_0 - ht_o,
             u'?!': ht_ques - ht_o,
             u'%&@$': ht_and - ht_o,
             u'àáâãäåèéêëìíîïñòóôõöùúûüāăćĉċčēĕėěĩīĭńňōŏőŕřśŝšũūŭůűŵźżž': ht_sap - ht_o,
             u'ÀÁÂÃÄÅÆÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝĀĂĆĈĊČĎĒđĔĖĚĜĞĠĤĥĴĹĺłŃŇŊŌŎŐŒŔŘŚŜŠŤŦŨŪŬŮŰŴŶŸŹŻŽƁſ': ht_cAp - ht_o,
             u'ßÞƀƄƚɓɫɬʖʕʔʡʢ': ht_beta - ht_o             
            })


def _getStrikeCenters(fontFileName, size):  
    """
    Some fonts have no descents or ascents: u'acemnorsuvwxz'
    """    
    ttf = ImageFont.truetype(fontFileName, size) # init the specified font resource
    (wd_o, ht_o) = ttf.getsize(u'o')
    return (ht_o)


def _getStrikeDescents(fontFileName, size):
    """
    Build and return a dictionary of descents (in pixels) for a font/size.
    For English:
        group1: u'gpqy'
        group2: u'j'
        group3: u'Q@&$'
        group4: u','
        group5: u';'
        group6: (u'|()_'
    For English-like languages (e.g., Spanish, French, Italian, Greek):
        group7: u'çęŋųƍƹȝȷȿɿʅųƺņŗş'
        group8: u'ýÿĝğġģįĵţÿĝğġģįĵţ'
        group9: u'ÇĄĢĘĮĶĻļŅŖŞŢŲ'
    """
    ttf = ImageFont.truetype(fontFileName, size) # init the specified font resource
    (wd_o, ht_o) = ttf.getsize(u'o')    # used as the baseline for "gpqy"    
    (wd_g, ht_g) = ttf.getsize(u'g')

    (wd_i, ht_i) = ttf.getsize(u'i')    # used as the baseline for "j"
    (wd_j, ht_j) = ttf.getsize(u'j')

    (wd_O, ht_O) = ttf.getsize(u'O')    # used as the baseline for "Q@&$"
    (wd_Q, ht_Q) = ttf.getsize(u'Q')

    (wd_dot, ht_dot) = ttf.getsize(u'.')    # used as the baseline for ","
    (wd_comma, ht_comma) = ttf.getsize(u',')
    
    (wd_colon, ht_colon) = ttf.getsize(u':') # used as the baseline for ";"        
    (wd_semicolon, ht_semicolon) = ttf.getsize(u';')
    
    (wd_l, ht_l) = ttf.getsize(u'l')    # used as the baseline for "|()_"
    (wd_or, ht_or) = ttf.getsize(u'|')  
    
    (wd_scbelow, ht_scbelow) = ttf.getsize(u'ç')
    (wd_yhead, ht_yhead) = ttf.getsize(u'ý')
    (wd_cCbelow, ht_cCbelow) = ttf.getsize(u'Ç')
    
    return ({u'gpqy': ht_o - ht_g, 
             u'j': ht_i - ht_j,
             u'Q@&$': ht_O - ht_Q,
             u',': ht_dot - ht_comma,
             u';': ht_colon - ht_semicolon,
             u'|()_': ht_l - ht_or,
             u'çęŋųƍƹȝȷȿɿʅ': ht_o - ht_scbelow,
             u'ýÿĝğġģįĵţÿĝğġģįĵţ': ht_l - ht_yhead, 
             u'ÇĄĢĘĮĶĻļŅŖŞŢŲ': ht_O - ht_cCbelow 
            })


def _getKeyVal(char, desasc_dict):
    """
    get the value of the key that contains char    
    """
    val = 0
    for key in desasc_dict.keys():
        if key.find(char) != -1:
            val = desasc_dict[key]
            break            
    return (val)        


def _getdesasc(w, descents, ascents):
    """
    Calculate minimum descent and maximum ascent, 
    note that if there is no descent, no need to calculate ascent!
    """
    mdes, masc = 0, 0
    for c in w:
        mdes, masc = min(mdes, _getKeyVal(c, descents)), max(masc, _getKeyVal(c, ascents))
    return ((mdes, masc))


def _cAspect(imgfont, char):
    """
    Determine the wd to ht ratio for the letter char in the specified font.
    """
    return (float(imgfont.getsize(char)[1])/imgfont.getsize(char)[0])


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
# helper functions for drawing saccades and fixations    
def _rgb2gray(rgb):
    """
    convert a rgb turple to gray scale
    """
    return str(0.2989*rgb[0]/256.0 + 0.5870*rgb[1]/256.0 + 0.1140*rgb[2]/256.0)


def _image_SacFix(direct, subjID, bitmapNameList, Sac, crlSac, Fix, crlFix, RegDF, trialID, drawType, max_FixRadius, drawFinal, showFixDur, PNGopt):
    """
    draw saccade and fixation data of a trial
    arguments:
        direct         : directory to store drawn figures
        subjID         : subject ID
        bitmapNameList : list of the bitmap files as backgrounds 
        Sac            : saccade data of the trail
        crlSac         : cross line saccade data of the trial
        Fix            : fixation data of the trial
        crlFix         : cross line fixation data of the trial
        RegDF          : region file of the trail
        trialID        : trial ID
        drawType       : type of drawing:
                         'ALL': draw all results (mixing saccade with 
                                fixation, and mixing crossline saccade 
                                with crossline fixation)
                         'SAC': draw saccade results (saccades and 
                                crossline saccades)
                         'FIX': draw fixation results (fixation and
                                crossline fixations)
        max_FixRadius  : maximum radius of fixation circles shown 
        drawFinal      : whether (True) or not (False) draw fixations and
                         saccades after the ending of reading     
        showFixDur     : whether (True) or not (False) show number for 
                         fixations 
        PNGopt         : 0: use png file as background; 
                         1: draw texts from region file    
    the results are saved in png file    
    """
    # prepare bitmaps for displaying saccades and fixations
    fd = FontDict(); fontpath = fd.fontGet('LiberationMono','Regular')
    xsz = 18; ttf = ImageFont.truetype(fontpath, xsz)
    if PNGopt == 0:
        # open the bitmap of the paragraph
        img1 = Image.open(_os.path.join(direct, bitmapNameList[trialID])); draw1 = ImageDraw.Draw(img1)
        img2 = Image.open(_os.path.join(direct, bitmapNameList[trialID])); draw2 = ImageDraw.Draw(img2)
    elif PNGopt == 1:        
        descents = _getStrikeDescents(fontpath, xsz); ascents = _getStrikeAscents(fontpath, xsz)   
        fg = (0,0,0); bg = (232,232,232); dim = (1280,1024)
        # initialize images
        img1 = Image.new('RGB', dim, bg); draw1 = ImageDraw.Draw(img1) # 'RGB' specifies 8-bit per channel (32 bit color)
        img2 = Image.new('RGB', dim, bg); draw2 = ImageDraw.Draw(img2) # 'RGB' specifies 8-bit per channel (32 bit color)
        # draw texts and rectangles
        for curline in _pd.unique(RegDF.line_no):
            line = RegDF[RegDF.line_no==curline]; line.index = range(len(line))            
            # draw word one by one    
            for ind in range(len(line)):
                (mdes, masc) = _getdesasc(line.Word[ind], descents, ascents)  # calculate descent and ascent of each word
                # draw current word
                vpos_text = line.y1_pos[ind] + masc - xsz/4.5 - 1  # top edge of current word, masc - xsz/4.5 - 1 is offset!.
                draw1.text((line.x1_pos[ind], vpos_text), line.Word[ind], font=ttf, fill=fg) 
                draw2.text((line.x1_pos[ind], vpos_text), line.Word[ind], font=ttf, fill=fg) 

    if len(_np.unique(Fix.eye)) == 1:
        # single eye data
        SingleEye = True
        end_Fix = len(Fix); end_time = Fix.loc[end_Fix-1,'end_time']
        if not drawFinal:
            # get ending Fixation and ending time of reading
            for ind in range(end_Fix):
                if Fix.valid[ind] == 'yes' and _np.isnan(Fix.line_no[ind]):
                    end_Fix = ind
                    break
            end_time = Fix.loc[end_Fix-1,'end_time']
    else:
        # double eye data
        SingleEye = False        
        end_Fix_L = len(Fix[Fix.eye=='L']); end_time_L = Fix.loc[end_Fix_L-1,'end_time']
        end_Fix_R = len(Fix); end_time_R = Fix.loc[end_Fix_R-1,'end_time']
        if not drawFinal:
            # get ending Fixation and ending time of reading
            # left eye
            for ind in range(end_Fix_L):
                if Fix.eye[ind] == 'L' and Fix.valid[ind] == 'yes' and _np.isnan(Fix.line_no[ind]):
                    end_Fix_L = ind
                    break
            end_time_L = Fix.loc[end_Fix_L-1,'end_time']
            # right eye
            for ind in range(len(Fix[Fix.eye=='L']), end_Fix_R):
                if Fix.eye[ind] == 'R' and Fix.valid[ind] == 'yes' and _np.isnan(Fix.line_no[ind]):
                    end_Fix_R = ind
                    break
            end_time_R = Fix.loc[end_Fix_R-1,'end_time']

    # set up colors for saccades and fixations
    col_leftSac = 'blue'; col_rightSac = 'red'; col_leftEyeFix = 'green'; col_rightEyeFix = 'red'; col_num = 'blue'
    
    if drawType == 'ALL':            
        radius_ratio = max_FixRadius/max(Fix.duration)
        # draw img1
        if SingleEye:
            # draw fixations            
            for ind in range(end_Fix):
                if Fix.valid[ind] == 'yes':
                    r = Fix.duration[ind]*radius_ratio            
                    if Fix.eye[ind] == 'L': draw1.ellipse((Fix.x_pos[ind]-r, Fix.y_pos[ind]-r, Fix.x_pos[ind]+r, Fix.y_pos[ind]+r), outline=col_leftEyeFix, fill=col_leftEyeFix)
                    elif Fix.eye[ind] == 'R': draw1.ellipse((Fix.x_pos[ind]-r, Fix.y_pos[ind]-r, Fix.x_pos[ind]+r, Fix.y_pos[ind]+r), outline=col_rightEyeFix, fill=col_rightEyeFix)
                    if showFixDur: draw1.text((Fix.x_pos[ind], Fix.y_pos[ind]), str(Fix.duration[ind]), font=ttf, fill=col_num)
            # draw saccades
            for ind in range(len(Sac)):
                if Sac.loc[ind,'end_time'] <= end_time:
                    if Sac.x1_pos[ind] < Sac.x2_pos[ind]: draw1.line((Sac.x1_pos[ind], Sac.y1_pos[ind], Sac.x2_pos[ind], Sac.y2_pos[ind]), fill=col_rightSac, width=2)
                    else: draw1.line((Sac.x1_pos[ind], Sac.y1_pos[ind], Sac.x2_pos[ind], Sac.y2_pos[ind]), fill=col_leftSac, width=2)
        else:
            # draw left eye fixations
            for ind in range(end_Fix_L):
                if Fix.eye[ind] == 'L' and Fix.valid[ind] == 'yes':
                    r = Fix.duration[ind]*radius_ratio            
                    draw1.ellipse((Fix.x_pos[ind]-r, Fix.y_pos[ind]-r, Fix.x_pos[ind]+r, Fix.y_pos[ind]+r), outline=col_leftEyeFix, fill=col_leftEyeFix)
                    if showFixDur: draw1.text((Fix.x_pos[ind], Fix.y_pos[ind]), str(Fix.duration[ind]), font=ttf, fill=col_num)
            # draw right eye fixations
            for ind in range(len(Fix[Fix.eye=='L']), end_Fix_R):
                if Fix.eye[ind] == 'R' and Fix.valid[ind] == 'yes':
                    r = Fix.duration[ind]*radius_ratio            
                    draw1.ellipse((Fix.x_pos[ind]-r, Fix.y_pos[ind]-r, Fix.x_pos[ind]+r, Fix.y_pos[ind]+r), outline=col_rightEyeFix, fill=col_rightEyeFix)
                    if showFixDur: draw1.text((Fix.x_pos[ind], Fix.y_pos[ind]), str(Fix.duration[ind]), font=ttf, fill=col_num)
            # draw saccades            
            for ind in range(len(Sac)):
                if (Sac.eye[ind] == 'L' and Sac.loc[ind,'end_time'] <= end_time_L) or (Sac.eye[ind] == 'R' and Sac.loc[ind,'end_time'] <= end_time_R):
                    if Sac.x1_pos[ind] < Sac.x2_pos[ind]: draw1.line((Sac.x1_pos[ind], Sac.y1_pos[ind], Sac.x2_pos[ind], Sac.y2_pos[ind]), fill=col_rightSac, width=2)
                    else: draw1.line((Sac.x1_pos[ind], Sac.y1_pos[ind], Sac.x2_pos[ind], Sac.y2_pos[ind]), fill=col_leftSac, width=2)
                
        # draw img2
        # draw crossline fixations on img2        
        for ind in range(len(crlFix)):
            r = crlFix.duration[ind]*radius_ratio
            if crlFix.eye[ind] == 'L': draw2.ellipse((crlFix.x_pos[ind]-r, crlFix.y_pos[ind]-r, crlFix.x_pos[ind]+r, crlFix.y_pos[ind]+r), outline=col_leftEyeFix, fill=col_leftEyeFix)
            elif crlFix.eye[ind] == 'R': draw2.ellipse((crlFix.x_pos[ind]-r, crlFix.y_pos[ind]-r, crlFix.x_pos[ind]+r, crlFix.y_pos[ind]+r), outline=col_rightEyeFix, fill=col_rightEyeFix)
            if showFixDur: draw2.text((crlFix.x_pos[ind], crlFix.y_pos[ind]), str(crlFix.duration[ind]), font=ttf, fill=col_num)
        # draw crossline saccades on img2
        for ind in range(len(crlSac)):
            if crlSac.x1_pos[ind] < crlSac.x2_pos[ind]: draw2.line((crlSac.x1_pos[ind], crlSac.y1_pos[ind], crlSac.x2_pos[ind], crlSac.y2_pos[ind]), fill=col_rightSac, width=2)
            else: draw2.line((crlSac.x1_pos[ind], crlSac.y1_pos[ind], crlSac.x2_pos[ind], crlSac.y2_pos[ind]), fill=col_leftSac, width=2)

        # save img1 and img2
        img1.save(_os.path.join(direct, subjID, subjID + '_FixSac_trial' + str(trialID) + '.png'), 'PNG')
        img2.save(_os.path.join(direct, subjID, subjID + '_crlFixSac_trial' + str(trialID) + '.png'), 'PNG')                
    
    elif drawType == 'SAC':
        # draw saccades on img1
        if SingleEye:
            for ind in range(len(Sac)):
                if Sac.loc[ind,'end_time'] <= end_time:
                    if Sac.x1_pos[ind] < Sac.x2_pos[ind]: draw1.line((Sac.x1_pos[ind], Sac.y1_pos[ind], Sac.x2_pos[ind], Sac.y2_pos[ind]), fill=col_rightSac, width=2)
                    else: draw1.line((Sac.x1_pos[ind], Sac.y1_pos[ind], Sac.x2_pos[ind], Sac.y2_pos[ind]), fill=col_leftSac, width=2)
        else:                
            for ind in range(len(Sac)):
                if (Sac.eye[ind] == 'L' and Sac.loc[ind,'end_time'] <= end_time_L) or (Sac.eye[ind] == 'R' and Sac.loc[ind,'end_time'] <= end_time_R):
                    if Sac.x1_pos[ind] < Sac.x2_pos[ind]: draw1.line((Sac.x1_pos[ind], Sac.y1_pos[ind], Sac.x2_pos[ind], Sac.y2_pos[ind]), fill=col_rightSac, width=2)
                    else: draw1.line((Sac.x1_pos[ind], Sac.y1_pos[ind], Sac.x2_pos[ind], Sac.y2_pos[ind]), fill=col_leftSac, width=2)    
        
        # draw crossline saccades on img2
        for ind in range(len(crlSac)):
            if crlSac.x1_pos[ind] < crlSac.x2_pos[ind]: draw2.line((crlSac.x1_pos[ind], crlSac.y1_pos[ind], crlSac.x2_pos[ind], crlSac.y2_pos[ind]), fill=col_rightSac, width=2)
            else: draw2.line((crlSac.x1_pos[ind], crlSac.y1_pos[ind], crlSac.x2_pos[ind], crlSac.y2_pos[ind]), fill=col_leftSac, width=2)

        # save img1 and img2
        img1.save(_os.path.join(direct, subjID, subjID + '_Sac_trial' + str(trialID) + '.png'), 'PNG')
        img2.save(_os.path.join(direct, subjID, subjID + '_crlSac_trial' + str(trialID) + '.png'), 'PNG')        
        
    elif drawType == 'FIX':
        radius_ratio = max_FixRadius/max(Fix.duration)
        # draw fixations on img1        
        if SingleEye:
            for ind in range(end_Fix):
                if Fix.valid[ind] == 'yes':
                    r = Fix.duration[ind]*radius_ratio            
                    if Fix.eye[ind] == 'L': draw1.ellipse((Fix.x_pos[ind]-r, Fix.y_pos[ind]-r, Fix.x_pos[ind]+r, Fix.y_pos[ind]+r), outline=col_leftEyeFix, fill=col_leftEyeFix)
                    elif Fix.eye[ind] == 'R': draw1.ellipse((Fix.x_pos[ind]-r, Fix.y_pos[ind]-r, Fix.x_pos[ind]+r, Fix.y_pos[ind]+r), outline=col_rightEyeFix, fill=col_rightEyeFix)
                    if showFixDur: draw1.text((Fix.x_pos[ind], Fix.y_pos[ind]), str(Fix.duration[ind]), font=ttf, fill=col_num)
        else:
            # draw left eye fixations
            for ind in range(end_Fix_L):
                if Fix.eye[ind] == 'L' and Fix.valid[ind] == 'yes':
                    r = Fix.duration[ind]*radius_ratio            
                    draw1.ellipse((Fix.x_pos[ind]-r, Fix.y_pos[ind]-r, Fix.x_pos[ind]+r, Fix.y_pos[ind]+r), outline=col_leftEyeFix, fill=col_leftEyeFix)
                    if showFixDur: draw1.text((Fix.x_pos[ind], Fix.y_pos[ind]), str(Fix.duration[ind]), font=ttf, fill=col_num)
            # draw right eye fixations
            for ind in range(len(Fix[Fix.eye=='L']), end_Fix_R):
                if Fix.eye[ind] == 'R' and Fix.valid[ind] == 'yes':
                    r = Fix.duration[ind]*radius_ratio            
                    draw1.ellipse((Fix.x_pos[ind]-r, Fix.y_pos[ind]-r, Fix.x_pos[ind]+r, Fix.y_pos[ind]+r), outline=col_rightEyeFix, fill=col_rightEyeFix)
                    if showFixDur: draw1.text((Fix.x_pos[ind], Fix.y_pos[ind]), str(Fix.duration[ind]), font=ttf, fill=col_num)
        
        # draw crossline fixations on img2        
        for ind in range(len(crlFix)):
            r = crlFix.duration[ind]*radius_ratio
            if crlFix.eye[ind] == 'L': draw2.ellipse((crlFix.x_pos[ind]-r, crlFix.y_pos[ind]-r, crlFix.x_pos[ind]+r, crlFix.y_pos[ind]+r), outline=col_leftEyeFix, fill=col_leftEyeFix)
            elif crlFix.eye[ind] == 'R': draw2.ellipse((crlFix.x_pos[ind]-r, crlFix.y_pos[ind]-r, crlFix.x_pos[ind]+r, crlFix.y_pos[ind]+r), outline=col_rightEyeFix, fill=col_rightEyeFix)
            if showFixDur: draw2.text((crlFix.x_pos[ind], crlFix.y_pos[ind]), str(crlFix.duration[ind]), font=ttf, fill=col_num)
        
        # save img1 and img2
        img1.save(_os.path.join(direct, subjID, subjID + '_Fix_trial' + str(trialID) + '.png'), 'PNG') 
        img2.save(_os.path.join(direct, subjID, subjID + '_crlFix_trial' + str(trialID) + '.png'), 'PNG') 


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
# helper functions for animation of eye-movement
def _playWav(soundFile, cond):
    """
    play a sound in background
    arguments:
        soundfile : name of wav sound file
        cond      : 0, stop; 1, start
    """
    if _sys.platform.startswith('win'):
        # under Windows        
        if cond == 0: _ws.PlaySound(None, _ws.SND_ALIAS | _ws.SND_ASYNC)   # end sound
        elif cond == 1: _ws.PlaySound(soundFile, _ws.SND_ALIAS | _ws.SND_ASYNC) # start sound

    elif _sys.platform.startswith('linux') > -1:
        # under Linux/Mac
        _os.system("start " + soundFile)  


def _animate_EM(direct, subjID, bitmapFile, soundFile, Fix, trialID, max_FixRadius=3):
    """
    animation of eye-movement of a trial
    arguments:
        direct         : directory to store bitmaps
        subjID         : subject ID
        bitmapNameList : list of the bitmap files as backgrounds
        soundNameList  : list of the sound files to be played during
                         animation
        Fix            : fixation data of the trial
        trialID        : trial ID
        max_FixRadius  : maximum radius of the circle for fixation; 
                         default = 3
    """
    bitmapSize = Image.open(bitmapFile).size
    # create screen and turtle
    # create screen
    screen = _turtle.Screen()
    screen.screensize(bitmapSize[0], bitmapSize[1]); screen.bgpic(bitmapFile)
    if len(_np.unique(Fix.eye)) == 1:
        # single eye data
        screen.title('Subject: ' +  subjID + '; Trial: ' + str(trialID+1) + ' Eye: ' + _np.unique(Fix.eye)[0])
        # create turtle        
        fix = _turtle.Turtle(); 
        if _np.unique(Fix.eye)[0] == 'L': fix.color('green')
        elif _np.unique(Fix.eye)[0] == 'R': fix.color('red')
        fix.shape('circle'); fix.speed(0); fix.resizemode("user")
        fix.penup()
    elif len(_np.unique(Fix.eye)) == 2:
        # both eyes data: left eye green circle; right eye red circle
        screen.title('Subject: ' +  subjID + '; Trial: ' + str(trialID+1) + ' Left eye: Green; Right: Red')
        # create player turtle as fixation
        fix_Left = _turtle.Turtle(); fix_Left.color('green'); fix_Left.shape('circle'); fix_Left.speed(0); fix_Left.resizemode("user")
        fix_Left.penup()
        fix_Right = _turtle.Turtle(); fix_Right.color('red'); fix_Right.shape('circle'); fix_Right.speed(0); fix_Right.resizemode("user")
        fix_Right.penup()
    
    # define binding functions
    def startAni():
        if len(_np.unique(Fix.eye)) == 1:
            # single eye data
            # find the first fixation that starts after trialstart 
            ind = 0; curTime = Fix.loc[ind, 'recstart'] 
            while curTime > Fix.loc[ind, 'start_time']: ind += 1
            # start sound
            _playWav(soundFile, 1)
            st_time = _time.time()   # starting time
            # start screen and turtle player
            while ind < len(Fix) and not _np.isnan(Fix.loc[ind, 'line_no']):
                time_diff = (Fix.loc[ind, 'start_time'] - curTime)/1000
                curTime = Fix.loc[ind, 'start_time']    # update curTime
                now = _time.time()
                if time_diff - (now - st_time) > 0:
                    _time.sleep(time_diff - (now - st_time))
                st_time = _time.time()
                # draw eye fixation
                fix.setpos(Fix.loc[ind, 'x_pos'] - bitmapSize[0]/2, -(Fix.loc[ind, 'y_pos'] - bitmapSize[1]/2))
                fix.shapesize(Fix.loc[ind, 'duration']/max(Fix.duration)*max_FixRadius, Fix.loc[ind, 'duration']/max(Fix.duration)*max_FixRadius)
                ind += 1    # move to next fixation
        
        elif len(_np.unique(Fix.eye)) == 2:
            # both eyes data
            FixLeft, FixRight = Fix[Fix.eye == 'L'].reset_index(), Fix[Fix.eye == 'R'].reset_index()
            # find the first fixation that starts after trialstart
            indLeft, indRight = 0, 0
            curTime = FixLeft.loc[indLeft, 'recstart']
            while curTime > FixLeft.loc[indLeft, 'start_time']: indLeft += 1
            while curTime > FixRight.loc[indRight, 'start_time']: indRight += 1
            timeLeft, timeRight = FixLeft.loc[indLeft, 'start_time'], FixRight.loc[indRight, 'start_time']
            LeftFinish, RightFinish = False, False
            # start sound
            _playWav(soundFile, 1)
            st_time = _time.time()
            # start screen and turtle player            
            while not LeftFinish or not RightFinish:
                while timeLeft == timeRight and not LeftFinish and not RightFinish:
                    time_diff = (FixLeft.loc[indLeft, 'start_time'] - curTime)/1000
                    curTime = FixLeft.loc[indLeft, 'start_time']    # update curTime                        
                    now = _time.time()
                    if time_diff - (now - st_time) > 0: _time.sleep(time_diff - (now - st_time))
                    st_time = _time.time()
                    # draw left eye fixation
                    fix_Left.setpos(FixLeft.loc[indLeft, 'x_pos'] - bitmapSize[0]/2, -(FixLeft.loc[indLeft, 'y_pos'] - bitmapSize[1]/2))
                    fix_Left.shapesize(FixLeft.loc[indLeft, 'duration']/max(Fix.duration)*max_FixRadius, FixLeft.loc[indLeft, 'duration']/max(Fix.duration)*max_FixRadius)
                    indLeft += 1    # move to next fixation
                    if indLeft >= len(FixLeft) or _np.isnan(FixLeft.loc[indLeft, 'line_no']):
                        LeftFinish = True
                    else: timeLeft = FixLeft.loc[indLeft, 'start_time']   # move to next start_time
                    # draw right eye fixation
                    fix_Right.setpos(FixRight.loc[indRight, 'x_pos'] - bitmapSize[0]/2, -(FixLeft.loc[indLeft, 'y_pos'] - bitmapSize[1]/2))
                    fix_Right.shapesize(FixRight.loc[indRight, 'duration']/max(Fix.duration)*max_FixRadius, FixRight.loc[indRight, 'duration']/max(Fix.duration)*max_FixRadius)
                    indRight += 1   # move to next fixation
                    if indRight >= len(FixRight) or _np.isnan(FixRight.loc[indRight, 'line_no']):
                        RightFinish = True
                    else: timeRight = FixRight.loc[indRight, 'start_time']    # move to next start_time
                while (timeLeft < timeRight and not LeftFinish and not RightFinish) or (not LeftFinish and RightFinish):
                    time_diff = (FixLeft.loc[indLeft, 'start_time'] - curTime)/1000
                    curTime = FixLeft.loc[indLeft, 'start_time']    # update curTime
                    now = _time.time()
                    if time_diff - (now - st_time) > 0: _time.sleep(time_diff - (now - st_time))
                    st_time = _time.time()
                    # draw left eye fixation
                    fix_Left.setpos(FixLeft.loc[indLeft, 'x_pos'] - bitmapSize[0]/2, -(FixLeft.loc[indLeft, 'y_pos'] - bitmapSize[1]/2))
                    fix_Left.shapesize(FixLeft.loc[indLeft, 'duration']/max(Fix.duration)*max_FixRadius, FixLeft.loc[indLeft, 'duration']/max(Fix.duration)*max_FixRadius)
                    indLeft += 1    # move to next fixation
                    if indLeft >= len(FixLeft) or _np.isnan(FixLeft.loc[indLeft, 'line_no']):
                        LeftFinish = True
                    else: timeLeft = FixLeft.loc[indLeft, 'start_time']  # move to next start_time
                while (timeLeft > timeRight and not LeftFinish and not RightFinish) or (LeftFinish and not RightFinish):
                    time_diff = (FixRight.loc[indRight, 'start_time'] - curTime)/1000
                    curTime = FixRight.loc[indRight, 'start_time']
                    now = _time.time()
                    if time_diff - (now - st_time) > 0: _time.sleep(time_diff - (now - st_time))
                    st_time = _time.time()
                    # draw right eye fixation
                    fix_Right.setpos(FixRight.loc[indRight, 'x_pos'] - bitmapSize[0]/2, -(FixLeft.loc[indLeft, 'y_pos'] - bitmapSize[1]/2))
                    fix_Right.shapesize(FixRight.loc[indRight, 'duration']/max(Fix.duration)*max_FixRadius, FixRight.loc[indRight, 'duration']/max(Fix.duration)*max_FixRadius)
                    indRight += 1   # move to next fixation
                    if indRight >= len(FixRight) or _np.isnan(FixRight.loc[indRight, 'line_no']):
                        RightFinish = True
                    else: timeRight = FixRight.loc[indRight, 'start_time']   # move to next start_time                
                
    def endAni():
        _playWav(soundFile, 0)   # end sound            
        _turtle.exitonclick()    # end screen
    
    # set keyboard bindings
    _turtle.listen()
    _turtle.onkey(startAni, 's') # key 's' to start animation
    _turtle.onkey(endAni, 'e')  # key 'e' to end animation

    _playWav(soundFile, 0)   # end sound    
    _turtle.exitonclick() # click to quit


def _animate_EM_TimeStamp(direct, subjID, bitmapFile, soundFile, Stamp, trialID, max_FixRadius=3):
    """
    animation of eye-movement of a trial based on time stamped data
    arguments:
        direct         : directory to store bitmaps
        subjID         : subject ID
        bitmapNameList : list of the bitmap files as backgrounds
        soundNameList  : list of the sound files to be played during
                         animation
        Stamp          : time stamped data of the trial
        trialID        : trial ID
        max_FixRadius  : maximum radius of the circle for fixation; 
                         default = 3
    """
    bitmapSize = Image.open(bitmapFile).size
    # create screen and turtle
    # create screen
    screen = _turtle.Screen()
    screen.screensize(bitmapSize[0], bitmapSize[1]); screen.bgpic(bitmapFile)
    if _np.unique(Stamp.eye)[0] == 'L' or _np.unique(Stamp.eye)[0] == 'R':
        # single eye data
        screen.title('Subject: ' +  subjID + '; Trial: ' + str(trialID+1) + ' Eye: ' + _np.unique(Stamp.eye)[0])
        # create turtle        
        stamp = _turtle.Turtle(); 
        if _np.unique(Stamp.eye)[0] == 'L': stamp.color('green')
        elif _np.unique(Stamp.eye)[0] == 'R': stamp.color('red')
        stamp.shape('circle'); stamp.speed(0); stamp.resizemode("user")
        stamp.penup()
    else:
        # both eyes data: left eye green circle; right eye red circle
        screen.title('Subject: ' +  subjID + '; Trial: ' + str(trialID+1) + ' Left eye: Green; Right: Red')
        # create player turtle as fixation
        stamp_Left = _turtle.Turtle(); stamp_Left.color('green'); stamp_Left.shape('circle'); stamp_Left.speed(0); stamp_Left.resizemode("user")
        stamp_Left.penup()
        stamp_Right = _turtle.Turtle(); stamp_Right.color('red'); stamp_Right.shape('circle'); stamp_Right.speed(0); stamp_Right.resizemode("user")
        stamp_Right.penup()
    
    # define binding functions
    def startAni():
        if _np.unique(Stamp.eye)[0] == 'L' or _np.unique(Stamp.eye)[0] == 'R':
            # single eye data
            # show regularly time stamped data
            ind = 0; curTime = Stamp.loc[ind, 'recstart']; time_step = 1.0/Stamp.loc[ind, 'sampfreq']
            while curTime > Stamp.loc[ind, 'time']: ind += 1
            # start sound
            _playWav(soundFile, 1)
            # start screen and turtle player
            while ind < len(Stamp):
                if not _np.isnan(Stamp.loc[ind, 'x_pos1']):
                    # draw eye fixation
                    stamp.setpos(Stamp.loc[ind, 'x_pos1'] - bitmapSize[0]/2, -(Stamp.loc[ind, 'y_pos1'] - bitmapSize[1]/2))
                    stamp.shapesize(max_FixRadius, max_FixRadius)
                    ind += 1
                else: ind += 1    # move to next fixation
                _time.sleep(time_step)   
        
        else:
            # both eyes data
            # find the first fixation that starts after trialstart
            ind = 0; curTime = Stamp.loc[ind, 'recstart']; time_step = 1.0/Stamp.loc[ind, 'sampfreq']
            while curTime > Stamp.loc[ind, 'time']: ind += 1
            # start sound
            _playWav(soundFile, 1)
            # start screen and turtle player            
            while ind < len(Stamp):
                if not _np.isnan(Stamp.loc[ind, 'x_pos1']):
                    # draw left eye fixation
                    stamp_Left.setpos(Stamp.loc[ind, 'x_pos1'] - bitmapSize[0]/2, -(Stamp.loc[ind, 'y_pos1'] - bitmapSize[1]/2))
                    stamp_Left.shapesize(max_FixRadius, max_FixRadius)
                if not _np.isnan(Stamp.loc[ind, 'x_pos2']):
                    # draw right eye fixation
                    stamp_Right.setpos(Stamp.loc[ind, 'x_pos2'] - bitmapSize[0]/2, -(Stamp.loc[ind, 'y_pos2'] - bitmapSize[1]/2))
                    stamp_Right.shapesize(max_FixRadius, max_FixRadius)
                ind += 1    # move to next fixation
                _time.sleep(time_step)   
    
    def endAni():
        _playWav(soundFile, 0)   # end sound            
        _turtle.exitonclick()    # end screen
    
    # set keyboard bindings
    _turtle.listen()
    _turtle.onkey(startAni, 's') # key 's' to start animation
    _turtle.onkey(endAni, 'e')  # key 'e' to end animation

    _playWav(soundFile, 0)   # end sound    
    _turtle.exitonclick() # click to quit


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
        
