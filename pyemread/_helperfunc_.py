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

This is a set of helper functions to be called by pyemread.py.
"""

# imported packages
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


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# helper functions obtaining basic information from data files
def _getHeader(lines):
    """
    get header information
    argument:
        lines : data lines
    return:
        script   : script file
        sessdate : session date
        srcfile  : source file
    """
    header = [] 
    for line in lines:
        line = line.rstrip()
        if _re.search('^[*][*] ', line):
            header.append(line)
       
    # get basic information from header lines       
    for line in header:
        if _re.search('RECORDED BY', line):
            script = line.split(' ')[3]
        if _re.search('DATE:', line):
            sessdate = line.split(': ')[1]
        if _re.search('CONVERTED FROM', line):
            m = _re.search(' FROM (.+?) using', line)
            if m:
                #srcfile = _os.path.basename(m.group(1))
                srcfile = m.group(1).split('\\')[-1]
    
    return script, sessdate, srcfile            


def _getLineInfo(FixRep_cur):
    """
    get time information from FixReportLines
    argument:
        FixRep_cur : current trial's fix report lines DF
    return:
        line_idx  : fixed lines
        line_time : starting and ending time in each line
    """
    totlines = int(max(FixRep_cur.CURRENT_FIX_LABEL))
    line_idx = []; line_time = []
    for cur in range(1,totlines):
        line_idx.append(cur)
        subFixRep = FixRep_cur[FixRep_cur.CURRENT_FIX_LABEL==cur].reset_index()
        line_time.append([subFixRep.loc[0,'CURRENT_FIX_START'], 
                          subFixRep.loc[len(subFixRep)-1,'CURRENT_FIX_END']])        
    
    return line_idx, line_time


def _getTrialReg(lines):
    """
    get the region (line range) of each trial
    argument:
        lines : data lines
    return:
        T_idx   : trail start and ending lines
        T_lines : trail start and ending line indices
    """
    trial_start = []; trial_start_lines = []
    trial_end = []; trial_end_lines = []
    cur = 0
    for line in lines:
        if _re.search('TRIALID', line):
            trial_start.append(line); trial_start_lines.append(cur)
        if _re.search('TRIAL_RESULT', line):
            trial_end.append(line); trial_end_lines.append(cur)
        cur += 1
    
    if len(trial_start) != len(trial_end):
        raise ValueError("Trial starting and ending mismatch!")

    T_idx = _np.column_stack((trial_start, trial_end)); T_lines = _np.column_stack((trial_start_lines, trial_end_lines))
    return T_idx, T_lines
    
    
def _getBlink_Fix_Sac_SampFreq_EyeRec(triallines, datatype):
    """
    get split blink, fixation, and saccade data lines, and sampling 
    frequency and eye recorded
    argument:
        triallines : data lines of a trial
        datatype   : 0, record fixation and saccade; 
                     1, record time stamped data
    return:
        blinklines; fixlines; saclines; stamplines
        sampfreq; eyerec
    """
    blinklines = []
    if datatype == 0:
        fixlines = []; saclines = []
    elif datatype == 1:
        stamplines = []
    for line in triallines:
        if datatype == 0:
            if _re.search('^EBLINK', line): blinklines.append(line.split())
            if _re.search('^EFIX', line): fixlines.append(line.split())
            if _re.search('^ESACC', line): saclines.append(line.split())
            if _re.search('!MODE RECORD', line):
                sampfreq = int(line.split()[5]); eyerec = line.split()[-1]
        elif datatype == 1:
            if _re.search('^EBLINK', line): blinklines.append(line.split())
            if _re.search('^[0-9]', line): stamplines.append(line.split())
            if _re.search('!MODE RECORD', line):
                sampfreq = int(line.split()[5]); eyerec = line.split()[-1]
    if datatype == 0: return blinklines, fixlines, saclines, sampfreq, eyerec
    elif datatype == 1: return blinklines, stamplines, sampfreq, eyerec        
 
   
def _gettdur(triallines):
    """
    get estimated trial duration
    argument:
        triallines : data lines of a trial
    return:
        trialstart : starting time of the trial
        trialend   : ending time of the trial
        tdur       : estimated trial duration 
        
    """
    trial_type, trialstart, trialend, tdur, recstart, recend = _np.nan, 0, 0, 0, 0, 0
    for line in triallines:
        if _re.search('!V TRIAL_VAR picture_name', line): trial_type = (line.split()[-1]).split('.')[0]
        if _re.search('^START', line): trialstart = int(line.split()[1])
        if _re.search('^END', line): trialend = int(line.split()[1])
        if _re.search('ARECSTART', line): recstart = int(line.split()[1]) - int(line.split()[2])
        if _re.search('ARECSTOP', line): recend = int(line.split()[1]) - int(line.split()[2])
    tdur = trialend - trialstart        
    return trial_type, trialstart, trialend, tdur, recstart, recend        


def _getErrorFree(ETRANDF, subjID, trial_type):
    """
    get trial_type's error_free
    """
    return int(ETRANDF.loc[ETRANDF.SubjectID == 'a' + subjID, ETRANDF.columns == 'etRan_' + trial_type + 'ErrorFree'].iloc[0,0])


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

    
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# helper functions geting crossline information based on region files, 
def _getCrossLineInfo(RegDF):
    """
    get cross line information from region file
    arguments:
        RegDF : region file data frame (with line information)
    return:
        CrossLineInfo : list of dictionaries marking the cross line 
                        information: center of the last word of the 
                        previous line and center of the first word of the
                        next line 
    """
    CrossLineInfo = []
    for ind in range(len(RegDF)-1):
        if RegDF.line_no[ind]+1 == RegDF.line_no[ind+1]:
            # line crossing! record
            dic = {}
            # center of the last word of the previous line
            dic['p'] = RegDF.loc[ind,'line_no'];
            dic['p_x'] = (RegDF.loc[ind,'x1_pos'] + RegDF.loc[ind,'x2_pos'])/2.0; dic['p_y'] = (RegDF.loc[ind,'y1_pos'] + RegDF.loc[ind,'y2_pos'])/2.0
            # center of the first word of the next line
            dic['n'] = RegDF.loc[ind+1,'line_no'];
            dic['n_x'] = (RegDF.loc[ind+1,'x1_pos'] + RegDF.loc[ind+1,'x2_pos'])/2.0; dic['n_y'] = (RegDF.loc[ind+1,'y1_pos'] + RegDF.loc[ind+1,'y2_pos'])/2.0
            CrossLineInfo.append(dic)
    
    return CrossLineInfo 


# helper functions for lumping short fixations (< 50ms)
def _lumpTwoFix(Df, ind1, ind2, direc, addtime):
    """
    lump two adjacent fixation data line (ind1 and ind2)
    direc =  1: next (ind1 < ind2); 
            -1: previous (ind1 > ind2)
    Df as a data frame is mutable, no need to return Df
    """
    if direc == 1:
        if ind1 >= ind2:
            raise ValueError('Warning! Wrong direction in lumping!')
        # lump
        Df.loc[ind1,'end_time'] = Df.loc[ind2,'end_time']
        Df.loc[ind1,'duration'] = Df.loc[ind1,'end_time'] - Df.loc[ind1,'start_time'] + addtime # new duration
        Df.loc[ind1,'x_pos'] = (Df.loc[ind1,'x_pos'] + Df.loc[ind2,'x_pos'])/2.0; Df.loc[ind1,'y_pos'] = (Df.loc[ind1,'y_pos'] + Df.loc[ind2,'y_pos'])/2.0   # mean x_pos, mean y_pos
        Df.loc[ind1,'pup_size'] = (Df.loc[ind1,'pup_size'] + Df.loc[ind2,'pup_size'])/2.0  # mean pup_size
    elif direc == -1:
        if ind1 <= ind2:
            raise ValueError('Warning! Wrong direction in lumping!')
        # lump
        Df.loc[ind1,'start_time'] = Df.loc[ind2,'start_time']
        Df.loc[ind1,'duration'] = Df.loc[ind1,'end_time'] - Df.loc[ind1,'start_time'] + addtime # new duration
        Df.loc[ind1,'x_pos'] = (Df.loc[ind1,'x_pos'] + Df.loc[ind2,'x_pos'])/2.0; Df.loc[ind1,'y_pos'] = (Df.loc[ind1,'y_pos'] + Df.loc[ind2,'y_pos'])/2.0    # mean x_pos, mean y_pos
        Df.loc[ind1,'pup_size'] = (Df.loc[ind1,'pup_size'] + Df.loc[ind2,'pup_size'])/2.0   # mean pup_size
    

def _lumpMoreFix(Df, ind, ind_list, addtime):
    """
    lump ind with inds in ind_list
    Df as a data frame is mutable, no need to return Df
    """
    Df.loc[ind,'end_time'] = Df.loc[ind_list[-1],'end_time']  # use the last one's ending time for the lumped ending time
    Df.loc[ind,'duration'] = Df.loc[ind,'end_time'] - Df.loc[ind,'start_time'] + addtime # new duration
    for item in ind_list:           
        Df.loc[ind,'x_pos'] += Df.loc[item,'x_pos']; Df.loc[ind,'y_pos'] += Df.loc[item,'y_pos']
        Df.loc[ind,'pup_size'] += Df.loc[item,'pup_size']
    Df.loc[ind,'x_pos'] /= float(len(ind_list)+1); Df.loc[ind,'y_pos'] /= float(len(ind_list)+1)  # mean x_pos, mean y_pos
    Df.loc[ind,'pup_size'] /= float(len(ind_list)+1)   # mean pup_size                    

    
def _lumpFix(Df, endindex, short_index, addtime, ln, zn):
    """
    lump fixation
    arguments:
        Df          : fixation data for lumping 
        short_index : list of index of fixation having short duration
        addtime     : adjusting time for duration, calculated based on
                      sampling frequency
        ln          : in lumping, maximum duration of a fixation to 
                      "lump"; default = 50. Fixation <= this value is 
                      subject to lumping with adjacent and near enough 
                      (determined by zN) fixations
        zn          : in lumping, maximum distance (in pixels) between 
                      two fixations for "lumping"; default = 50, roughly
                      1.5 character (12/8s)
    return:
        Df : although Df as a data frame is mutable, due to possible 
             dropping and reindexing, we need to return Df
    """
    droplist = []; cur = 0
    while cur < len(short_index):
        if short_index[cur] == 0:
            # the first fixation
            # check the next one
            next_list = []; ind = cur + 1
            while ind < len(short_index) and short_index[ind] == short_index[ind-1] + 1 and abs(Df.x_pos[short_index[ind]] - Df.x_pos[short_index[cur]]) <= zn:
                # the next fixation is also a short fixation and within the zN distance                    
                next_list.append(short_index[ind]); ind += 1                
            
            if len(next_list) != 0:                
                _lumpMoreFix(Df, short_index[cur], next_list, addtime)   # lump short_index[cur] and items in next_list
                # mark items in next_list for dropping
                for item in next_list:
                    droplist.append(item)                        
                # further check the next fixation!
                if Df.duration[short_index[cur]] <= ln:
                    if next_list[-1] + 1 <= endindex and abs(Df.x_pos[short_index[cur]] - Df.x_pos[next_list[-1]+1]) <= zn:
                        _lumpTwoFix(Df, short_index[cur], next_list[-1]+1, 1, addtime)   # there are next item in Df and it can be further lumped together
                        droplist.append(next_list[-1]+1)    # mark next_list[-1]+1 for dropping
                # jump over these lumped ones
                cur += len(next_list)                
            else:
                # no consecutive short fixation for lumping, check the next one
                if short_index[cur] + 1 <= endindex and abs(Df.x_pos[short_index[cur]] - Df.x_pos[short_index[cur]+1]) <= zn:
                    _lumpTwoFix(Df, short_index[cur], short_index[cur]+1, 1, addtime)    # lump short_index[cur] and short_index[cur]+1
                    droplist.append(short_index[cur]+1) # mark short_index[cur]+1 for dropping
                    
        elif short_index[cur] == endindex:
            # the last fixation, only check the previous one
            if not (short_index[cur] - 1 in droplist) and abs(Df.x_pos[short_index[cur]] - Df.x_pos[short_index[cur]-1]) <= zn:
                _lumpTwoFix(Df, short_index[cur], short_index[cur]-1, -1, addtime)   # lump short_index[cur] and short_index[cur]-1
                droplist.append(short_index[cur]-1) # mark short_index[cur]-1 for dropping
                
        else:
            # check both next and previous fixation
            # check the next one
            next_list = []; ind = cur + 1
            while ind < len(short_index) and short_index[ind] == short_index[ind-1] + 1 and abs(Df.x_pos[short_index[ind]] - Df.x_pos[short_index[cur]]) <= zn:
                # the next fixation is also a short fixation and can be lumped together!                    
                next_list.append(short_index[ind]); ind += 1                
            if len(next_list) != 0:
                # lump short_index[cur] and items in next_list
                _lumpMoreFix(Df, short_index[cur], next_list, addtime)# mark items in next_list for dropping
                for item in next_list:
                    droplist.append(item)
                    
                # further check the previous and next fixation!
                if Df.duration[short_index[cur]] <= ln:
                    dist_next, dist_prev = 0.0, 0.0
                    if next_list[-1] + 1 <= endindex and not (next_list[-1] + 1 in droplist) and abs(Df.x_pos[short_index[cur]] - Df.x_pos[next_list[-1]+1]) <= zn:
                        dist_next = abs(Df.x_pos[short_index[cur]] - Df.x_pos[next_list[-1]+1])
                    if not (short_index[cur]-1 in droplist) and abs(Df.x_pos[short_index[cur]] - Df.x_pos[short_index[cur]-1]) <= zn:
                        dist_prev = abs(Df.x_pos[short_index[cur]] - Df.x_pos[short_index[cur]-1])
                    
                    if dist_next != 0.0 and dist_prev == 0.0:                        
                        _lumpTwoFix(Df, short_index[cur], next_list[-1]+1, 1, addtime)   # lump next                  
                        droplist.append(next_list[-1]+1)    # mark next_list[-1]+1 for dropping
                    elif dist_next == 0.0 and dist_prev != 0.0:                        
                        _lumpTwoFix(Df, short_index[cur], short_index[cur]-1, -1, addtime)   # lump previous                       
                        droplist.append(short_index[cur]-1) # mark short_index[cur]-1 for dropping 
                    elif dist_next != 0.0 and dist_prev != 0.0:
                        if dist_next < dist_prev:
                            _lumpTwoFix(Df, short_index[cur], next_list[-1]+1, 1, addtime)   # lump next first!
                            droplist.append(next_list[-1]+1)    # mark next_list[-1]+1 for dropping
                            # further check previous
                            if Df.duration[short_index[cur]] <= ln and abs(Df.x_pos[short_index[cur]] - Df.x_pos[short_index[cur]-1]) <= zn:
                                _lumpTwoFix(Df, short_index[cur], short_index[cur]-1, -1, addtime)   # lump previous                        
                                droplist.append(short_index[cur]-1)# mark short_index[cur]-1 for dropping
                        else:
                            _lumpTwoFix(Df, short_index[cur], short_index[cur]-1, -1, addtime)   # lump previous first!                       
                            droplist.append(short_index[cur]-1) # mark short_index[cur]-1 for dropping
                            # further check next
                            if Df.duration[short_index[cur]] <= ln and abs(Df.x_pos[short_index[cur]] - Df.x_pos[next_list[-1]+1]) <= zn:
                                _lumpTwoFix(Df, short_index[cur], next_list[-1]+1, 1, addtime)   # lump next                    
                                droplist.append(next_list[-1]+1)    # mark next_list[-1]+1 for dropping            

                # jump over these lumped ones    
                cur += len(next_list)
            else:
                # check the previous and next fixation!
                dist_next, dist_prev = 0.0, 0.0
                if short_index[cur] + 1 <= endindex and abs(Df.x_pos[short_index[cur]] - Df.x_pos[short_index[cur]+1]) <= zn:
                    dist_next = abs(Df.x_pos[short_index[cur]] - Df.x_pos[short_index[cur]+1])
                if not (short_index[cur]-1 in droplist) and abs(Df.x_pos[short_index[cur]] - Df.x_pos[short_index[cur]-1]) <= zn:
                    dist_prev = abs(Df.x_pos[short_index[cur]] - Df.x_pos[short_index[cur]-1])
                    
                if dist_next != 0.0 and dist_prev == 0.0:
                    _lumpTwoFix(Df, short_index[cur], short_index[cur]+1, 1, addtime)    # lump next                    
                    droplist.append(short_index[cur]+1) # mark short_index[cur]+1 for dropping
                elif dist_next == 0.0 and dist_prev != 0.0:                    
                    _lumpTwoFix(Df, short_index[cur], short_index[cur]-1, -1, addtime)   # lump previous
                    droplist.append(short_index[cur]-1) # mark short_index[cur]-1 for dropping
                elif dist_next != 0.0 and dist_prev != 0.0:
                    if dist_next < dist_prev:
                        _lumpTwoFix(Df, short_index[cur], short_index[cur]+1, 1, addtime)    # lump next first!                   
                        droplist.append(short_index[cur]+1) # mark short_index[cur]+1 for dropping
                        # further check previous
                        if Df.duration[short_index[cur]] <= ln and abs(Df.x_pos[short_index[cur]] - Df.x_pos[short_index[cur]-1]) <= zn:
                            _lumpTwoFix(Df, short_index[cur], short_index[cur]-1, -1, addtime)   # lump previous
                            droplist.append(short_index[cur]-1)# mark short_index[cur]-1 for dropping
                    else:                        
                        _lumpTwoFix(Df, short_index[cur], short_index[cur]-1, -1, addtime)   # lump previous first!                        
                        droplist.append(short_index[cur]-1) # mark short_index[cur]-1 for dropping
                        # further check next
                        if Df.duration[short_index[cur]] <= ln and abs(Df.x_pos[short_index[cur]] - Df.x_pos[short_index[cur]+1]) <= zn:
                            _lumpTwoFix(Df, short_index[cur], short_index[cur]+1, 1, addtime)    # lump next                  
                            droplist.append(short_index[cur]+1) # mark short_index[cur]+1 for dropping
        
        # after lumping or not, if short_index[cur]'s duration is still less than lN, delete it! 
        if Df.loc[short_index[cur],'duration'] <= ln:
            droplist.append(short_index[cur])            
        # move to next short fixation
        cur += 1    
    
    if droplist != []:
        # drop ind lumped to other inds, and reindex rows
        Df = Df.drop(droplist)                
        Df = Df.reset_index(drop=True)
    return Df
    
    
def _mergeFixLines(startline, endline, Df):
    """
    merge continuous rightward and leftward fixations
    arguments:
        startline : search starting line
        endline   : search ending line
        Df        : fixation data frame
    """
    mergelines = []
    ind = startline
    while ind < endline - 1:
        stl, edl = ind, ind + 1
        if Df.loc[edl,'x_pos'] - Df.loc[stl,'x_pos'] > 0:
            # rightward fixations
            mergelines.append((stl, edl, Df.loc[edl,'x_pos'] - Df.loc[stl,'x_pos'], 0))  # rightward fixations
        elif Df.loc[edl,'x_pos'] - Df.loc[stl,'x_pos'] <= 0:
            # leftward fixations
            # keep searching till it becomes a rightward fixations
            nextl = edl + 1
            while nextl < endline and Df.loc[nextl,'x_pos'] - Df.loc[edl,'x_pos'] <= 0:
                edl = nextl; nextl += 1
            mergelines.append((stl, edl, Df.loc[edl,'x_pos'] - Df.loc[stl,'x_pos'], 1))  # leftward fixations
        ind = edl
    return mergelines

    
def _getCrosslineFix(CrossLineInfo, startline, endline, Df, diff_ratio, frontrange_ratio):
    """
    collect all cross-line fixations in lines
    arguments:
        CrossLineInfo    : cross line information from region file
        startline        : search starting line
        endline          : search ending line
        Df               : fixation data frame
        diff_ratio       : for calculating crossline saccades(fixations), 
                           the ratio of maximum distance between the center
                           of the last word and the center of the first
                           word in a line; default = 0.6
        frontrange_ratio : for calculating crossline saccades(fixations),
                           the ratio to check backward crossline saccade
                           or fixation: such saccade or fixation usually
                           starts around the line beginning; default = 0.2
    return:
        lines   : list of turples storing cross-line fixations
        curline : the current line in Df
    """
    # merge rightward fixations and leftward fixations
    lines = []; mergelines = _mergeFixLines(startline, endline, Df)    
    curline, ind = 0, 0 # curline records the current mergeline Fix data, ind records the current CrossLineInfo
    while ind < len(CrossLineInfo):
        curCross = CrossLineInfo[ind]; FixDistThres = diff_ratio*(curCross['p_x'] - curCross['n_x'])    # set up the maximum fixation distance to be identified as a cross-line fixation
        if mergelines[curline][3] == 0 and mergelines[curline][2] >= FixDistThres and Df.loc[mergelines[curline][0],'x_pos'] <= curCross['n_x'] + frontrange_ratio*(curCross['p_x'] - curCross['n_x']):
            if ind != 0:
                # rightward backward crossline fixation
                # move curCross to the back
                if ind > 0:
                    ind -= 1; curCross = CrossLineInfo[ind]; FixDistThres = diff_ratio*(curCross['p_x'] - curCross['n_x'])
                # record backward cross-line fixation using previous curCross
                lines.append((-1, curCross['n'], curCross['p'], mergelines[curline][1]))
        if mergelines[curline][3] == 1 and mergelines[curline][2] <= -FixDistThres:
            # leftward forward crossline fixation
            # further check which fixation is the start of the next line
            # two criteria: 
            # first, if there is one big jump in x value bigger than FixDistThres, use that fixation as the cross line fixation
            FindOne = False            
            stl1 = mergelines[curline][0]
            for nextl in range(mergelines[curline][0]+1,mergelines[curline][1]+1):
                if Df.loc[nextl,'x_pos'] - Df.loc[nextl-1,'x_pos'] <= -FixDistThres:
                    stl1 = nextl; FindOne = True
                    break
            if FindOne:
                lines.append((1, curCross['p'], curCross['n'], stl1))
            else:
                # second, 1) find the first fixation having the biggest x value change 
                stl1 = mergelines[curline][0]; bigX = 0
                for nextl in range(mergelines[curline][0]+1,mergelines[curline][1]+1):
                    if Df.loc[nextl-1,'x_pos'] - Df.loc[nextl,'x_pos'] > bigX:
                        bigX = Df.loc[nextl-1,'x_pos'] - Df.loc[nextl,'x_pos']; stl1 = nextl
                # 2) find the fixation having the biggest y value change     
                stl2 = mergelines[curline][0]; bigY = 0
                for nextl in range(mergelines[curline][0]+1,mergelines[curline][1]+1):
                    if Df.loc[nextl,'y_pos'] - Df.loc[nextl-1,'y_pos'] > bigY:
                        bigY = Df.loc[nextl,'y_pos'] - Df.loc[nextl-1,'y_pos']; stl2 = nextl
                # compare stline1 and stline2
                lines.append((1, curCross['p'], curCross['n'], max(stl1,stl2)))
            # move curCross to the next
            if ind < len(CrossLineInfo) - 1:
                ind += 1; curCross = CrossLineInfo[ind]; FixDistThres = diff_ratio*(curCross['p_x'] - curCross['n_x'])
            else:
                break
        curline += 1
        if curline >= len(mergelines):
            break
        
    # change curline in mergelines back to the next line in Df
    if curline < len(mergelines): curline = mergelines[curline][1]    
    else: curline = mergelines[-1][1]

    # check whether the last recorded line is the forward crossing to the last line in the paragraph
    question = False    
    if lines[0][0] == -1 or lines[-1][0] == -1 or lines[-1][2] != CrossLineInfo[-1]['n']:
        print 'Warning! crlFix start/end need check!'
        question = True
    
    return lines, curline, question


def _getFixLine(RegDF, crlSac, FixDF, classify_method, diff_ratio, frontrange_ratio, y_range):
    """
    add line information for each FixDF
    arguments:
        RegDF            : region file data frame (with line information)
        crlSac           : data frame storing identified 
                           cross line saccades
        FixDF            : fixation data of the trial
        classify_method  : fixation method: 'DIFF': based on difference in
                           x_axis; 'SAC': based on crosslineSac ('SAC' is 
                           preferred since saccade is kinda more accurate!);
                           default = 'DIFF'
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
    return:
        line : cross line fixations: previous fixation is in previous line, 
               current fixation is in next line
        FixDF as a data frame is mutable, no need to return    
    """
    CrossLineInfo = _getCrossLineInfo(RegDF)    # get cross line information
    question = False
    
    if len(_np.unique(FixDF.eye)) == 1 and (_np.unique(FixDF.eye)[0] == 'L' or _np.unique(FixDF.eye)[0] == 'R'):
        # single eye data
        if classify_method == 'DIFF':
            # method 1: based on difference in x_axis
            lines, curline, question = _getCrosslineFix(CrossLineInfo, 0, len(FixDF), FixDF, diff_ratio, frontrange_ratio)        
            endline = len(FixDF)        
            if curline < len(FixDF):
                # there are remaining lines, check whether there are backward cross-line fixation
                curCross = CrossLineInfo[-1]; FixDistThres = diff_ratio*(curCross['p_x'] - curCross['n_x'])
                nextline = curline + 1
                while nextline < len(FixDF) and abs(FixDF.x_pos[curline] - FixDF.x_pos[nextline]) <= FixDistThres and FixDF.y_pos[curline] - FixDF.y_pos[nextline] <= y_range:
                    curline = nextline; nextline = curline + 1
                if nextline < len(FixDF):
                    endline = nextline                
            # mark crossline saccade as prevline_nextline
            curlow = 0    
            for ind in range(len(lines)):
                curline = lines[ind]
                for line in range(curlow, curline[3]):
                    FixDF.loc[line,'line_no'] = curline[1]
                curlow = curline[3]
            for line in range(curlow, endline):
                FixDF.loc[line,'line_no'] = lines[-1][2]        
        elif classify_method == 'SAC':
            # method 2: based on crosslineSac
            lines = []            
            curlow = 0
            for ind in range(len(crlSac)):
                curup = curlow + 1
                while FixDF.end_time[curup] <= crlSac.start_time[ind]:
                    curup += 1
                start = crlSac.loc[ind,'startline']; end = crlSac.loc[ind,'endline']
                if start < end:
                    direction = 1
                else:
                    direction = -1
                lines.append([direction, start, end, curup])    
                for line in range(curlow, curup):
                    FixDF.loc[line,'line_no'] = crlSac.loc[ind,'startline']
                curlow = curup
            for line in range(curlow, len(FixDF)):
                FixDF.loc[line,'line_no'] = crlSac.loc[ind,'endline']        
    else:
        # double eye data
        numLeft = len(FixDF[FixDF.eye == 'L']); numRight = len(FixDF[FixDF.eye == 'R']) 
        if classify_method == 'DIFF':
            # method 1: based on differences in x_axis 
            # first, left eye data
            lines_Left, curline_Left, ques1 = _getCrosslineFix(CrossLineInfo, 0, numLeft, FixDF, diff_ratio, frontrange_ratio)        
            endline_Left = numLeft 
            if curline_Left < numLeft:
                # there are remaining lines, check whether there are backward cross-line fixation
                curCross = CrossLineInfo[-1]; FixDistThres = diff_ratio*(curCross['p_x'] - curCross['n_x'])
                nextline = curline_Left + 1
                while nextline < numLeft and abs(FixDF.x_pos[curline_Left] - FixDF.x_pos[nextline]) <= FixDistThres and FixDF.y_pos[curline_Left] - FixDF.y_pos[nextline] <= y_range:
                    curline_Left = nextline; nextline = curline_Left + 1
                if nextline < numLeft:
                    endline_Left = nextline
            # mark crossline saccade as prevline_nextline
            curlow = 0    
            for ind in range(len(lines_Left)):
                curline = lines_Left[ind]
                for line in range(curlow, curline[3]):
                    FixDF.loc[line,'line_no'] = curline[1]
                curlow = curline[3]
            for line in range(curlow, endline_Left):
                FixDF.loc[line,'line_no'] = lines_Left[-1][2]
            
            # second, right eye data
            lines_Right, curline_Right, ques2 = _getCrosslineFix(CrossLineInfo, numLeft, numLeft + numRight, FixDF, diff_ratio, frontrange_ratio)                
            endline_Right = numLeft + numRight
            if curline_Right < numLeft + numRight:
                # there are remaining lines, check whether there are backward cross-line fixation
                curCross = CrossLineInfo[-1]; FixDistThres = diff_ratio*(curCross['p_x'] - curCross['n_x'])
                nextline = curline_Right + 1
                while nextline < numLeft + numRight and abs(FixDF.x_pos[curline_Right] - FixDF.x_pos[nextline]) <= FixDistThres and FixDF.y_pos[curline_Right] - FixDF.y_pos[nextline] <= y_range:
                    curline_Right = nextline; nextline = curline_Right + 1
                if nextline < numLeft + numRight:
                    endline_Right = nextline                
            # mark crossline saccade as prevline_nextline        
            curlow = numLeft
            for ind in range(len(lines_Right)):
                curline = lines_Right[ind]
                for line in range(curlow, curline[3]):
                    FixDF.loc[line,'line_no'] = curline[1]
                curlow = curline[3]
            for line in range(curlow, endline_Right):
                FixDF.loc[line,'line_no'] = lines_Right[-1][2]
        
            lines = lines_Left + lines_Right
            if ques1 or ques2:
                question = True
        elif classify_method == 'SAC':
            # method 2: based on crosslineSac
            lines = []
            curlow = 0
            for ind in range(len(crlSac)):
                if crlSac.eye[ind] == 'L':
                    curup = curlow + 1
                    while FixDF.eye[curup] == 'L' and FixDF.end_time[curup] <= crlSac.start_time[ind]:
                        curup += 1
                    start = crlSac.loc[ind,'startline']; end = crlSac.loc[ind,'endline']
                    if start < end:
                        direction = 1
                    else:
                        direction = -1
                    lines.append([direction, start, end, curup])     
                    for line in range(curlow, curup):
                        FixDF.loc[line,'line_no'] = crlSac.loc[ind,'startline']
                    curlow = curup
            for line in range(curlow, numLeft):
                FixDF.loc[line,'line_no'] = crlSac.loc[ind,'endline']

            curlow = numLeft
            for ind in range(len(crlSac)):
                if crlSac.eye[ind] == 'R':
                    curup = curlow + 1
                    while FixDF.eye[curup] == 'R' and FixDF.end_time[curup] <= crlSac.start_time[ind]:
                        curup += 1
                    start = crlSac.loc[ind,'startline']; end = crlSac.loc[ind,'endline']
                    if start < end:
                        direction = 1
                    else:
                        direction = -1
                    lines.append([direction, start, end, curup])       
                    for line in range(curlow, curup):
                        FixDF.loc[line,'line_no'] = crlSac.loc[ind,'startline']
                    curlow = curup
            for line in range(curlow, numLeft + numRight):
                FixDF.loc[line,'line_no'] = crlSac.loc[ind,'endline']
    
    return lines, question
    
    
def _getcrlFix(RegDF, crlSac, FixDF, classify_method, diff_ratio, frontrange_ratio, y_range):
    """
    get crossline Fix
    arguments:
        RegDF            : region file data frame
        crlSac           : crossline saccades
        FixDF            : fixation data of the trial
        classify_method  : fixation method: 
                           'DIFF': based on difference in x_axis; 
                           'SAC': based on crosslineSac ('SAC' is preferred
                           since saccade is kinda more accurate!); 
                           default = 'DIFF'
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
    return:
        crlFix : crossline fixations of the trial
        FixDF is mutable, no need to return
    """                   
    # Second, get line information of each fixation
    lines, question = _getFixLine(RegDF, crlSac, FixDF, classify_method, diff_ratio, frontrange_ratio, y_range)
    
    crlFix = _pd.DataFrame(_np.zeros((len(lines), 13)))
    crlFix.columns = ['subj', 'trial_id', 'eye', 'startline', 'endline', 'FixlineIndex', 'start_time', 'end_time', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid']
    crlFix.subj = FixDF.subj[0]; crlFix.trial_id = FixDF.trial_id[0]
    cur = 0    
    for item in lines:
        curFix = FixDF.loc[item[3]]
        crlFix.loc[cur,'eye'] = curFix.eye
        crlFix.loc[cur,'startline'] = item[1]; crlFix.loc[cur,'endline'] = item[2]; crlFix.loc[cur,'FixlineIndex'] = item[3]
        crlFix.loc[cur,'start_time'] = curFix.start_time; crlFix.loc[cur,'end_time'] = curFix.end_time; crlFix.loc[cur,'duration'] = curFix.duration; 
        crlFix.loc[cur,'x_pos'] = curFix.x_pos; crlFix.loc[cur,'y_pos'] = curFix.y_pos
        crlFix.loc[cur,'pup_size'] = curFix.pup_size; crlFix.loc[cur,'valid'] = curFix['valid']        
        cur += 1
        
    return crlFix, question    
    

def _recTimeStamp(ExpType, trialID, blinklines, stamplines, sampfreq, eyerec, script, sessdate, srcfile, trial_type, trialstart, trialend, tdur, recstart, recend, error_free=1):
    """
    get fixation data from trials
    arguments:
        ExpType    : type of experiments: 'RAN', 'RP'        
        trailID    : trail ID of the data
        blinklines : blink lines of a trial
        stamplines : time stamped lines of a trial
        sampfreq   : sampling frequency (to calculate amending time for
                     duration)
        eyerec     : eye recorded ('R', 'L' or 'LR')
        script     : script file
        sessdate   : session date
        srcfile    : source file
        trial_type : type of trials
        trialstart : starting time of the trial
        trialend   : ending time of the trial
        tdur       : estimated trial duration
        recstart   : starting time of recording
        recend     : ending time of recording
        error_free : error_free of that trial; 
                     1, free of error; 0, error; default 1
    return:
        StampDF : stamp data of the trial
    """            
    blink_number, stamp_number = len(blinklines), len(stamplines)
        
    StampDF = _pd.DataFrame(_np.zeros((stamp_number, 26)))
    StampDF.columns = ['subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'trialstart', 'trialend', 'tdur', 'recstart', 'recend', 'blinks', 'eye', 'time', 'x_pos1', 'y_pos1', 'pup_size1', 'x_pos2', 'y_pos2', 'pup_size2', 'line_no', 'gaze_region_no', 'label', 'error_free', 'Fix_Sac']
    StampDF.subj = srcfile.split('.')[0]; StampDF.trial_id = int(trialID); StampDF.trial_type = trial_type
    StampDF.sampfreq = int(sampfreq); StampDF.script = script; StampDF.sessdate = sessdate; StampDF.srcfile = srcfile
    StampDF.trialstart = trialstart; StampDF.trialend = trialend; StampDF.tdur = tdur; StampDF.recstart = recstart; StampDF.recend = recend
    StampDF.blinks = int(blink_number)
        
    StampDF.eye = eyerec
    StampDF.time = [int(line[0]) for line in stamplines]
    if eyerec == 'L' or eyerec == 'R':
        StampDF.x_pos1 = [line[1] for line in stamplines]; StampDF.loc[StampDF.x_pos1 == '.', 'x_pos1'] = _np.nan; StampDF.x_pos1 = StampDF.x_pos1.astype(float)
        StampDF.y_pos1 = [line[2] for line in stamplines]; StampDF.loc[StampDF.y_pos1 == '.', 'y_pos1'] = _np.nan; StampDF.y_pos1 = StampDF.y_pos1.astype(float)
        StampDF.pup_size1 = [line[3] for line in stamplines]; StampDF.loc[StampDF.pup_size1 == '.', 'pup_size1'] = _np.nan; StampDF.pup_size1 = StampDF.pup_size1.astype(float)
        StampDF.x_pos2 = _np.nan; StampDF.y_pos2 = _np.nan 
        StampDF.pup_size2 = _np.nan
    elif eyerec == 'LR':
        StampDF.x_pos1 = [line[1] for line in stamplines]; StampDF.loc[StampDF.x_pos1 == '.', 'x_pos1'] = _np.nan; StampDF.x_pos1 = StampDF.x_pos1.astype(float)
        StampDF.y_pos1 = [line[2] for line in stamplines]; StampDF.loc[StampDF.y_pos1 == '.', 'y_pos1'] = _np.nan; StampDF.y_pos1 = StampDF.y_pos1.astype(float)
        StampDF.pup_size1 = [line[3] for line in stamplines]; StampDF.loc[StampDF.pup_size1 == '.', 'pup_size1'] = _np.nan; StampDF.pup_size1 = StampDF.pup_size1.astype(float)
        StampDF.x_pos2 = [line[4] for line in stamplines]; StampDF.loc[StampDF.x_pos2 == '.', 'x_pos2'] = _np.nan; StampDF.x_pos2 = StampDF.x_pos2.astype(float)
        StampDF.y_pos2 = [line[5] for line in stamplines]; StampDF.loc[StampDF.y_pos2 == '.', 'y_pos2'] = _np.nan; StampDF.y_pos2 = StampDF.y_pos2.astype(float)
        StampDF.pup_size2 = [line[6] for line in stamplines]; StampDF.loc[StampDF.pup_size2 == '.', 'pup_size2'] = _np.nan; StampDF.pup_size2 = StampDF.pup_size2.astype(float)
       
    StampDF.line_no = _np.nan; StampDF.gaze_region_no = _np.nan; StampDF.label = _np.nan; StampDF.error_free = error_free; StampDF.Fix_Sac = _np.nan
    
    return StampDF

        
def _recFix(ExpType, trialID, blinklines, fixlines, sampfreq, eyerec, script, sessdate, srcfile, trial_type, trialstart, trialend, tdur, recstart, recend, rec_lastFix, lump_Fix, ln, zn, mn):
    """
    get fixation data from trials
    arguments:
        ExpType     : type of experiments: 'RAN', 'RP'        
        trailID     : trail ID of the data
        blinklines  : blink lines of a trial
        fixlines    : fix lines of a trial
        sampfreq    : sampling frequency (to calculate amending time for 
                      duration)
        eyerec      : eye recorded ('R', 'L' or 'LR')
        script      : script file
        sessdate    : session date
        srcfile     : source file
        trial_type  : trial type
        trialstart  : starting time of the trial
        trialend    : ending time of the trial
        tdur        : estimated trial duration
        recstart    : starting time of recording
        recend      : ending time of recording
        rec_lastFix : whether (True)or not (False) include the last 
                      fixation of a trial and allow it to trigger 
                      regression; default = False
        lump_Fix    : whether (True) or not (False) lump short 
                      fixations; default = True
        ln          : in lumping, maximum duration of a fixation to
                      "lump"; default = 50. Fixation <= this value is
                      subject to lumping with adjacent and near enough
                      (determined by zN) fixations
        zn          : in lumping, maximum distance (in pixels) between
                      two fixations for "lumping"; default = 50, roughly
                      1.5 character (12/8s)
        mn          : in lumping, minimum legal fixation duration; default 
                      = 50 ms
    return:
        FixDF : fixation data of the trial
    """            
    blink_number, fix_number = len(blinklines), len(fixlines)
    addtime = 1/float(sampfreq) * 1000
    
    # First, record and lump fixations 
    if eyerec == 'L' or eyerec == 'R':
        # only left or right eye data are recorded
        FixDF = _pd.DataFrame(_np.zeros((fix_number, 23)))
        FixDF.columns = ['subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'trialstart', 'trialend', 'tdur', 'recstart', 'recend', 'blinks', 'eye', 'start_time', 'end_time', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid', 'line_no', 'region_no']
        FixDF.subj = srcfile.split('.')[0]; FixDF.trial_id = int(trialID); FixDF.trial_type = trial_type
        FixDF.sampfreq = int(sampfreq); FixDF.script = script; FixDF.sessdate = sessdate; FixDF.srcfile = srcfile
        FixDF.trialstart = trialstart; FixDF.trialend = trialend; FixDF.tdur = tdur; FixDF.recstart = recstart; FixDF.recend = recend
        FixDF.blinks = int(blink_number)
    
        FixDF.eye = [line[1] for line in fixlines]; FixDF.start_time = [float(line[2]) for line in fixlines]; FixDF.end_time = [float(line[3]) for line in fixlines]; FixDF.duration = [float(line[4]) for line in fixlines]
        FixDF.x_pos = [float(line[5]) for line in fixlines]; FixDF.y_pos = [float(line[6]) for line in fixlines]; FixDF.pup_size = [float(line[7]) for line in fixlines]
        
        FixDF['valid'] = 'yes'
        if not rec_lastFix:
            FixDF.loc[fix_number-1,'valid'] = 'no' 
        
        if lump_Fix:
            # lump fixations
            # get indices of candidate fixations for lumping, whose durations <= ln
            short_index = []
            for ind in range(fix_number):
                if FixDF.loc[ind,'duration'] <= ln and FixDF.loc[ind,'valid'] == 'yes':
                    short_index.append(ind)        
            # check each short fixation for lumping        
            if not rec_lastFix:
                endindex = fix_number - 2   # the upperbound of searching range, excluding the last one!
            else:
                endindex = fix_number - 1   # the upperbound of searching range
            # lump data    
            FixDF = _lumpFix(FixDF, endindex, short_index, addtime, ln, zn)       

    elif eyerec == 'LR':
        # both eyes data are recorded
        numLeft, numRight = 0, 0
        for line in fixlines:
            if line[1] == 'L':
                numLeft += 1
            if line[1] == 'R':
                numRight += 1
        # print some necessary warnings!            
        if numLeft == 0:
            print 'Warning! No left eye Fix under both eyes Fix!'
        if numRight == 0:
            print 'Warning! No right eye Fix under both eyes Fix!'
        # check which eye's fixation is the last fixation    
        if fixlines[-1][1] == 'L':
            lastLR = 'L'
        elif fixlines[-1][1] == 'R':
            lastLR = 'R'
        
        if numLeft != 0:
            FixDF1 = _pd.DataFrame(_np.zeros((numLeft, 23)))
            FixDF1.columns = ['subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'trialstart', 'trialend', 'tdur', 'recstart', 'recend', 'blinks', 'eye', 'start_time', 'end_time', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid', 'line_no', 'region_no']
            FixDF1.subj = srcfile.split('.')[0]; FixDF1.trial_id = int(trialID)
            FixDF1.trial_type = trial_type
            FixDF1.sampfreq = int(sampfreq); FixDF1.script = script; FixDF1.sessdate = sessdate; FixDF1.srcfile = srcfile
            FixDF1.trialstart = trialstart; FixDF1.trialend = trialend; FixDF1.tdur = tdur; FixDF1.recstart = recstart; FixDF1.recend = recend
            FixDF1.blinks = int(blink_number)
            
            cur = 0
            for line in fixlines:
                if line[1] == 'L':
                    FixDF1.loc[cur,'eye'] = line[1]; FixDF1.loc[cur,'start_time'] = float(line[2]); FixDF1.loc[cur,'end_time'] = float(line[3]); FixDF1.loc[cur,'duration'] = float(line[4])
                    FixDF1.loc[cur,'x_pos'] = float(line[5]); FixDF1.loc[cur,'y_pos'] = float(line[6]); FixDF1.loc[cur,'pup_size'] = float(line[7])
                    cur += 1
            
            FixDF1['valid'] = 'yes'
            if not rec_lastFix and lastLR == 'L':
                FixDF1.loc[numLeft-1,'valid'] = 'no'     
            
            if lump_Fix:
                # lump fixations
                short_index1 = []
                for ind in range(numLeft):
                    if FixDF1.loc[ind,'duration'] <= ln and FixDF1.loc[ind,'valid'] == 'yes':
                        short_index1.append(ind)
                # check each short fixation for lumping        
                if not rec_lastFix:
                    if numLeft == fix_number:
                        endindex1 = fix_number - 2   # all fixations are left eyes, the upperbound of searching range, excluding the last one!                    
                    else:                    
                        endindex1 = numLeft - 1  # the upperbound of searching range
                else:
                    endindex1 = numLeft - 1
                # lump data        
                FixDF1 = _lumpFix(FixDF1, endindex1, short_index1, addtime, ln, zn)               
        
        if numRight != 0:
            FixDF2 = _pd.DataFrame(_np.zeros((numRight, 23)))
            FixDF2.columns = ['subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'trialstart', 'trialend', 'tdur', 'recstart', 'recend', 'blinks', 'eye', 'start_time', 'end_time', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid', 'line_no', 'region_no']
            FixDF2.subj = srcfile.split('.')[0]; FixDF2.trial_id = int(trialID)
            FixDF2.trial_type = trial_type
            FixDF2.sampfreq = int(sampfreq); FixDF2.script = script; FixDF2.sessdate = sessdate; FixDF2.srcfile = srcfile
            FixDF2.trialstart = trialstart; FixDF2.trialend = trialend; FixDF2.tdur = tdur; FixDF2.recstart = recstart; FixDF2.recend = recend
            FixDF2.blinks = int(blink_number)

            cur = 0        
            for line in fixlines:
                if line[1] == 'R':
                    FixDF2.loc[cur,'eye'] = line[1]; FixDF2.loc[cur,'start_time'] = float(line[2]); FixDF2.loc[cur,'end_time'] = float(line[3]); FixDF2.loc[cur,'duration'] = float(line[4])
                    FixDF2.loc[cur,'x_pos'] = float(line[5]); FixDF2.loc[cur,'y_pos'] = float(line[6]); FixDF2.loc[cur,'pup_size'] = float(line[7])
                    cur += 1
            
            FixDF2['valid'] = 'yes'
            if not rec_lastFix and lastLR == 'R':
                FixDF2.loc[numRight-1,'valid'] = 'no'     
        
            if lump_Fix:            
                # lump fixation
                short_index2 = []
                for ind in range(numRight):
                    if FixDF2.loc[ind,'duration'] <= ln and FixDF2.loc[ind,'valid'] == 'yes':
                        short_index2.append(ind)
                # check each short fixation for lumping        
                if not rec_lastFix:
                    if numRight == fix_number:                     
                        endindex2 = fix_number - 2  # all fixations are right eyes, the upperbound of searching range, excluding the last one!
                    else:                
                        endindex2 = numRight - 1 # the upperbound of searching range
                else:
                    endindex2 = numRight - 1                
                # lump data        
                FixDF2 = _lumpFix(FixDF2, endindex2, short_index2, addtime, ln, zn) 
        
        # merge all data
        FixDF = _pd.DataFrame(columns=('subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'trialstart', 'trialend', 'tdur', 'recstart', 'recend', 'blinks', 'eye', 'start_time', 'end_time', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid', 'line_no', 'region_no'))
        if numLeft != 0:
            FixDF = FixDF.append(FixDF1, ignore_index=True)
        if numRight != 0:
            FixDF = FixDF.append(FixDF2, ignore_index=True)
    
    if lump_Fix:
        # check validity of fixations after possible lumping
        for ind in range(len(FixDF)):
            if FixDF.loc[ind,'duration'] < mn:
                FixDF.loc[ind,'valid'] = 'no'
    
    FixDF.line_no = _np.nan
    FixDF.region_no = _np.nan
    
    return FixDF


def _mergeSacLines(startline, endline, Df):
    """
    merge continuous rightward and leftward fixations
    arguments:
        startline : search starting line
        endline   : search ending line
        Df        : fixation data frame
    """
    mergelines = []
    ind = startline
    while ind < endline:
        if Df.loc[ind,'x2_pos'] - Df.loc[ind,'x1_pos'] > 0:
            # rightward fixations
            mergelines.append((ind, ind, Df.loc[ind,'x2_pos'] - Df.loc[ind,'x1_pos'], 0))  # rightward fixations
            nextl = ind + 1
        elif Df.loc[ind,'x2_pos'] - Df.loc[ind,'x1_pos'] <= 0:
            # leftward fixations
            # keep searching till it becomes a rightward fixations
            nextl = ind + 1; edl = nextl - 1
            while nextl < endline and Df.loc[nextl,'x2_pos'] - Df.loc[nextl,'x1_pos'] <= 0:
                edl = nextl; nextl += 1
            mergelines.append((ind, edl, Df.loc[edl,'x2_pos'] - Df.loc[ind,'x1_pos'], 1))  # leftward fixations
        ind = nextl
    return mergelines
    
    
def _getCrosslineSac(CrossLineInfo, startline, endline, Df, diff_ratio, frontrange_ratio):
    """
    collect all cross-line fixations in lines
    arguments:
        CrossLineInfo    : cross line information from region file
        startline        : search starting line
        endline          : search ending line
        Df               : fixation data frame
        diff_ratio       : for calculating crossline saccades(fixations),
                           the ratio of maximum distance between the center
                           of the last word and the center of the first 
                           word in a line; default = 0.6
        frontrange_ratio : for calculating crossline saccades(fixations),
                           the ratio to check backward crossline saccade
                           or fixation: such saccade or fixation usually
                           starts around the line beginning; default = 0.2
    return:
        lines   : list of turples storing cross-line fixations
        curline : the current line in Df
    """
    # merge rightward fixations and leftward fixations
    lines = []; mergelines = _mergeSacLines(startline, endline, Df)    
    curline, ind = 0, 0 # curline records the current mergeline Fix data, ind records the current CrossLineInfo
    while ind < len(CrossLineInfo):
        curCross = CrossLineInfo[ind]; FixDistThres = diff_ratio*(curCross['p_x'] - curCross['n_x'])    # set up the maximum fixation distance to be identified as a cross-line fixation
        if mergelines[curline][3] == 0 and mergelines[curline][2] >= FixDistThres and Df.loc[mergelines[curline][0],'x1_pos'] <= curCross['n_x'] + frontrange_ratio*(curCross['p_x'] - curCross['n_x']):
            if ind != 0:
                # rightward backward crossline fixation
                # move curCross to the back
                if ind > 0:
                    ind -= 1; curCross = CrossLineInfo[ind]; FixDistThres = diff_ratio*(curCross['p_x'] - curCross['n_x'])
                # record backward cross-line fixation using previous curCross
                lines.append((-1, curCross['n'], curCross['p'], mergelines[curline][1]))
        if mergelines[curline][3] == 1 and mergelines[curline][2] <= -FixDistThres:
            # leftward forward crossline fixation
            # further check which fixation is the start of the next line
            # two criteria:
            # first, if one saccade has a big jump in x value bigger than FixDistThres, that saccade is identified as the cross line saccade
            FindOne = False            
            stl1 = mergelines[curline][0]
            for nextl in range(mergelines[curline][0],mergelines[curline][1]+1):
                if Df.loc[nextl,'x2_pos'] - Df.loc[nextl,'x1_pos'] <= -FixDistThres:
                    stl1 = nextl; FindOne = True
                    break
            if FindOne:
                lines.append((1, curCross['p'], curCross['n'], stl1))
            else:
                # second, 1) find the first fixation having the biggest x value change 
                stl1 = mergelines[curline][0]; bigX = 0
                for nextl in range(mergelines[curline][0],mergelines[curline][1]+1):
                    if Df.loc[nextl,'x1_pos'] - Df.loc[nextl,'x2_pos'] > bigX:
                        bigX = Df.loc[nextl,'x1_pos'] - Df.loc[nextl,'x2_pos']; stl1 = nextl
                # 2) find the fixation having the biggest y value change     
                stl2 = mergelines[curline][0]; bigY = 0
                for nextl in range(mergelines[curline][0],mergelines[curline][1]+1):
                    if Df.loc[nextl,'y2_pos'] - Df.loc[nextl,'y1_pos'] > bigY:
                        bigY = Df.loc[nextl,'y2_pos'] - Df.loc[nextl,'y1_pos']; stl2 = nextl
                # compare stline1 and stline2
                lines.append((1, curCross['p'], curCross['n'], max(stl1,stl2)))
            # move curCross to the next
            if ind < len(CrossLineInfo) - 1:
                ind += 1; curCross = CrossLineInfo[ind]; FixDistThres = diff_ratio*(curCross['p_x'] - curCross['n_x'])
            else:
                break
        curline += 1
        if curline >= len(mergelines):
            break

    # change curline in mergelines back to the next line in Df
    if curline < len(mergelines):
        curline = mergelines[curline][1]    
    else:
        curline = mergelines[-1][1]
        
    # check whether the last recorded line is the forward crossing to the last line in the paragraph
    question = False    
    if lines[0][0] == -1 or lines[-1][0] == -1 or lines[-1][2] != CrossLineInfo[-1]['n']:
        print 'Warning! crlFix start/end need check!'
        question = True        

    return lines, curline, question

       
def _getSacLine(RegDF, SacDF, diff_ratio, frontrange_ratio, y_range):
    """
    add line information for each SacDF
    arguments:
        RegDF            : region file data frame
        SacDF            : saccade data of the trial
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
    return:
        lines : crossline information
        SacDF as a data frame is mutable, no need to return    
    """
    CrossLineInfo = _getCrossLineInfo(RegDF)    # get cross line information
    question = False
   
    if len(_np.unique(SacDF.eye)) == 1 and (_np.unique(SacDF.eye)[0] == 'L' or _np.unique(SacDF.eye)[0] == 'R'):
        # single eye data
        lines, curline, question = _getCrosslineSac(CrossLineInfo, 0, len(SacDF), SacDF, diff_ratio, frontrange_ratio)        
        endline = len(SacDF)        
        if curline < len(SacDF):
            # there are remaining lines, check whether there are backward cross-line saccade
            curCross = CrossLineInfo[-1]; FixDistThres = diff_ratio*(curCross['p_x'] - curCross['n_x'])
            curline += 1
            while curline < len(SacDF) and abs(SacDF.x2_pos[curline] - SacDF.x1_pos[curline]) <= FixDistThres and SacDF.y1_pos[curline] - SacDF.y2_pos[curline] <= y_range:
                curline += 1
            if curline < len(SacDF):
                endline = curline                
        # mark crossline saccade as prevline_nextline
        curlow = 0    
        for ind in range(len(lines)):
            curline = lines[ind]
            for line in range(curlow, curline[3]):
                SacDF.loc[line,'line_no'] = curline[1]
            SacDF.loc[curline[3],'line_no'] = str(curline[1])+'_'+str(curline[2])    
            curlow = curline[3]+1
        for line in range(curlow, endline):
            SacDF.loc[line,'line_no'] = lines[-1][2]
    else:
        # double eye saccade data
        numLeft = len(SacDF[SacDF.eye == 'L']); numRight = len(SacDF[SacDF.eye == 'R'])        
        # first, left eye saccade
        lines_Left, curline_Left, ques1 = _getCrosslineSac(CrossLineInfo, 0, numLeft, SacDF, diff_ratio, frontrange_ratio)
        endline_Left = numLeft 
        if curline_Left < numLeft:
            # there are remaining lines, check whether there are backward cross-line saccade
            curCross = CrossLineInfo[-1]; FixDistThres = diff_ratio*(curCross['p_x'] - curCross['n_x'])
            curline_Left += 1
            while curline_Left < numLeft and abs(SacDF.x2_pos[curline_Left] - SacDF.x1_pos[curline_Left]) <= FixDistThres and SacDF.y1_pos[curline_Left] - SacDF.y2_pos[curline_Left] <= y_range:
                curline_Left += 1
            if curline_Left < numLeft:
                endline_Left = curline_Left
        # mark crossline saccade as prevline_nextline
        curlow = 0    
        for ind in range(len(lines_Left)):
            curline = lines_Left[ind]
            for line in range(curlow, curline[3]):
                SacDF.loc[line,'line_no'] = curline[1]
            SacDF.loc[curline[3],'line_no'] = str(curline[1])+'_'+str(curline[2])    
            curlow = curline[3]+1
        for line in range(curlow, endline_Left):
            SacDF.loc[line,'line_no'] = lines_Left[-1][2]
        # mark crossline saccade as prevline_nextline    
        for ind in range(len(lines_Left)):
            curline = lines_Left[ind]
            crossline = str(curline[1])+'_'+str(curline[2])
            SacDF.loc[curline[3],'line_no'] = crossline
        
        # second, right eye saccade
        lines_Right, curline_Right, ques2 = _getCrosslineSac(CrossLineInfo, numLeft, numLeft + numRight, SacDF, diff_ratio, frontrange_ratio)
        endline_Right = numLeft + numRight
        if curline_Right < numLeft + numRight:
            # there are remaining lines, check whether there are backward cross-line fixation
            curCross = CrossLineInfo[-1]; FixDistThres = diff_ratio*(curCross['p_x'] - curCross['n_x'])
            curline_Right += 1
            while curline_Right < numLeft + numRight and abs(SacDF.x2_pos[curline_Right] - SacDF.x1_pos[curline_Right]) <= FixDistThres and SacDF.y1_pos[curline_Right] - SacDF.y2_pos[curline_Right] <= y_range:
                curline_Right += 1
            if curline_Right < numLeft + numRight:
                endline_Right = curline_Right                
        # mark crossline saccade as prevline_nextline        
        curlow = numLeft
        for ind in range(len(lines_Right)):
            curline = lines_Right[ind]
            for line in range(curlow, curline[3]):
                SacDF.loc[line,'line_no'] = curline[1]
            SacDF.loc[curline[3],'line_no'] = str(curline[1])+'_'+str(curline[2])    
            curlow = curline[3]+1
        for line in range(curlow, endline_Right):
            SacDF.loc[line,'line_no'] = lines_Right[-1][2]
        
        lines = lines_Left + lines_Right
        if ques1 or ques2:
            question = True
    
    return lines, question        


def _getcrlSac(RegDF, SacDF, diff_ratio, frontrange_ratio, y_range):
    """
    get crossline Sac
    arguments:
        RegDF            : region file data frame
        SacDFtemp        : saccade data of the trial
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
    return:
        crlSac : crossline saccades of the trial
        SacDF is mutable, no need to return
    """            
    lines, question = _getSacLine(RegDF, SacDF, diff_ratio, frontrange_ratio, y_range)   # get line information of each saccade
    
    crlSac = _pd.DataFrame(_np.zeros((len(lines), 15)))
    crlSac.columns = ['subj', 'trial_id', 'eye', 'startline', 'endline', 'SaclineIndex', 'start_time', 'end_time', 'duration', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos', 'ampl', 'pk']
    crlSac.subj = SacDF.subj[0]; crlSac.trial_id = SacDF.trial_id[0]
    cur = 0    
    for item in lines:
        curSac = SacDF.loc[item[3]]
        crlSac.loc[cur,'eye'] = curSac.eye
        crlSac.loc[cur,'startline'] = item[1]; crlSac.loc[cur,'endline'] = item[2]; crlSac.loc[cur,'SaclineIndex'] = item[3]
        crlSac.loc[cur,'start_time'] = curSac.start_time; crlSac.loc[cur,'end_time'] = curSac.end_time; crlSac.loc[cur,'duration'] = curSac.duration; 
        crlSac.loc[cur,'x1_pos'] = curSac.x1_pos; crlSac.loc[cur,'y1_pos'] = curSac.y1_pos
        crlSac.loc[cur,'x2_pos'] = curSac.x2_pos; crlSac.loc[cur,'y2_pos'] = curSac.y2_pos
        crlSac.loc[cur,'ampl'] = curSac.ampl; crlSac.loc[cur,'pk'] = curSac.pk        
        cur += 1 
    
    return crlSac, question    


def _recSac(ExpType, trialID, blinklines, saclines, sampfreq, eyerec, script, sessdate, srcfile, trial_type, trialstart, trialend, tdur, recstart, recend):
    """
    record saccade data from trials
    arguments:
        ExpType    : type of experiments: 'RAN', 'RP'
        trailID    : trail ID of the data
        blinklines : blink lines of a trial
        salines    : saccade lines of a trial
        sampfreq   : sampling frequency (to calculate amending time for
                     duration)
        eyerec     : eye recorded ('R', 'L' or 'LR')        
        script     : script file
        sessdate   : session date
        srcfile    : source file
        trial_type : trial type
        trialstart : starting time of the trial
        trialend   : ending time of the trial
        tdur       : estimated trial duration
        recstart   : starting time of recording
        recend     : ending time of recording
    return:
        SacDF : saccade data of the trial
    """    
    # calculate blinks
    blink_number, sac_number = len(blinklines), len(saclines)
    # remove saclines having '.' at start, end, duration, x1_pos, y1_pos, x2_pos, or y2_pos
    saclinestemp = saclines[:]    
    for line in saclinestemp:
        validData = True
        for ind in range(2,11):
            if line[ind] == '.':
                validData = False; break
        if validData == False:
            saclines.remove(line); sac_number -= 1
    
    SacDF = _pd.DataFrame(_np.zeros((sac_number, 24)))
    SacDF.columns = ['subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'trialstart', 'trialend', 'tdur', 'recstart', 'recend', 'blinks', 'eye', 'start_time', 'end_time', 'duration', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos', 'ampl', 'pk', 'line_no']
    SacDF.subj = srcfile.split('.')[0]; SacDF.trial_id = int(trialID); SacDF.trial_type = trial_type
    SacDF.sampfreq = int(sampfreq); SacDF.script = script; SacDF.sessdate = sessdate; SacDF.srcfile = srcfile
    SacDF.trialstart = trialstart; SacDF.trialend = trialend; SacDF.tdur = tdur; SacDF.recstart = recstart; SacDF.recend = recend
    SacDF.blinks = int(blink_number)

    if eyerec == 'L' or eyerec == 'R':
        # single eye saccade
        SacDF.eye = [line[1] for line in saclines]; SacDF.start_time = [float(line[2]) for line in saclines]; SacDF.end_time = [float(line[3]) for line in saclines]; SacDF.duration = [float(line[4]) for line in saclines]
        SacDF.x1_pos = [float(line[5]) for line in saclines]; SacDF.y1_pos = [float(line[6]) for line in saclines]
        SacDF.x2_pos = [float(line[7]) for line in saclines]; SacDF.y2_pos = [float(line[8]) for line in saclines]
        SacDF.ampl = [float(line[9]) for line in saclines]; SacDF.pk = [float(line[10]) for line in saclines]
    elif eyerec == 'LR':
        # double eye saccade
        numLeft, numRight = 0, 0
        for line in saclines:
            if line[1] == 'L':
                numLeft += 1
            elif line[1] == 'R':
                numRight += 1                
        # print some necessary warnings!            
        if numLeft == 0:
            print 'Warning! Both eyes" fixations are recorded, but no left eye fixation data!'
        if numRight == 0:
            print 'Warning! Both eyes" fixations are recorded, but no right eye fixation data!'
        # record data
        cur = 0    
        for line in saclines:
            if line[1] == 'L':
                SacDF.loc[cur,'eye'] = line[1]; SacDF.loc[cur,'start_time'] = float(line[2]); SacDF.loc[cur,'end_time'] = float(line[3]); SacDF.loc[cur,'duration'] = float(line[4])
                SacDF.loc[cur,'x1_pos'] = float(line[5]); SacDF.loc[cur,'y1_pos'] = float(line[6])
                SacDF.loc[cur,'x2_pos'] = float(line[7]); SacDF.loc[cur,'y2_pos'] = float(line[8])
                SacDF.loc[cur,'ampl'] = float(line[9]); SacDF.loc[cur,'pk'] = float(line[10])
                cur += 1
        for line in saclines:
            if line[1] == 'R':
                SacDF.loc[cur,'eye'] = line[1]; SacDF.loc[cur,'start_time'] = float(line[2]); SacDF.loc[cur,'end_time'] = float(line[3]); SacDF.loc[cur,'duration'] = float(line[4])
                SacDF.loc[cur,'x1_pos'] = float(line[5]); SacDF.loc[cur,'y1_pos'] = float(line[6])
                SacDF.loc[cur,'x2_pos'] = float(line[7]); SacDF.loc[cur,'y2_pos'] = float(line[8])
                SacDF.loc[cur,'ampl'] = float(line[9]); SacDF.loc[cur,'pk'] = float(line[10])
                cur += 1                   
    
    SacDF.line_no = _np.nan
    
    return SacDF            


def _modRegDF(RegDF, addCharSp):
    """
    modify RegDF's mod_x1 and mod_x2, add space to boundaries of line
    starting and ending words
    arguments:
        RegDF     : region file data frame
        addCharSp : number of single character space added to EMF for
                    catching overshoot fixations
        RegDF, as a data frame, is mutable, so no return is needed    
    """
    RegDF['mod_x1'] = RegDF.x1_pos; RegDF['mod_x2'] = RegDF.x2_pos
    addDist = addCharSp*(RegDF.loc[0,'x2_pos'] - RegDF.loc[0,'x1_pos'])/_np.float(RegDF.loc[0,'length'])
    for curEM in range(len(RegDF)):
        if curEM == 0:            
            RegDF.loc[curEM,'mod_x1'] -= addDist    # first word, add leftside!
        elif curEM == len(RegDF) - 1:            
            RegDF.loc[curEM,'mod_x2'] += addDist    # last word, add rightside!
        else:
            # check whether it is a line ending or line starting word
            if RegDF.loc[curEM-1,'line_no'] == RegDF.loc[curEM,'line_no'] - 1:
                RegDF.loc[curEM,'mod_x1'] -= addDist    # current region is a line starting, add leftside!
            elif RegDF.loc[curEM+1,'line_no'] == RegDF.loc[curEM,'line_no'] + 1:
                RegDF.loc[curEM,'mod_x2'] += addDist    # current region is a line ending, add rightside!


def _crtASC_dic(sit, direct, subjID):
    """
    create dictionary of ascii files (having the same name as subjID)
    arguments:
        sit    : situations: 0, subjID is given; 1, no subjID
        direct : root directory: all ascii files should be in level 
                 subfolder whose name is the same as the ascii file
        subjID : subject ID (for sit=0)
    output:
        ascfileExist : whether or not ascii file exists
        ascfileDic   : dictionary with key = subject ID, value = file with
                       directory
    """    
    ascfileExist = True
    ascfileDic = {}
    
    if sit == 0:
        fileName = _os.path.join(direct, subjID, subjID + '.asc')
        if _os.path.isfile(fileName):
            ascfileDic[subjID] = _os.path.join(direct, subjID, subjID + '.asc')
        else:            
            print subjID + '.asc' + ' does not exist!'
            ascfileExist = False            
    elif sit == 1:
        # search all subfolders for ascii file        
        for root, dirs, files in _os.walk(direct):
            for name in files:
                if name.endswith(".asc"):
                    ascfileDic[name.split('.')[0]] = _os.path.join(direct, name.split('.')[0], name)
        if len(ascfileDic) == 0:
            print 'No ascii files in subfolders!'
            ascfileExist = False                
    
    return ascfileExist, ascfileDic


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


def _crtFixRepDic(sit, direct, subjID):
    """
    create dictionary for fix report txt files
    arguments:
        sit    : situations 0: subjID is given; 1, no subjID
        direct : root directory: all txt files should be in level 
                 subfolder whose name is the same as the ascii file
        subjID : subject ID (for sit=0)
    output:
        FixRepExist : whether or not txt file exists
        FixRepDic   : dictionary with key = subject ID, value = txt file 
                      with directory
    """
    FixRepExist = True
    FixRepDic = {}
    
    FixRepNameEND = '-FixReportLines.txt'
    if sit == 0:
        fileName = _os.path.join(direct, subjID, subjID + FixRepNameEND)
        if _os.path.isfile(fileName):
            FixRepDic[subjID] = _os.path.join(direct, subjID, subjID + FixRepNameEND)
        else:            
            print subjID + FixRepNameEND + ' does not exist!'
            FixRepExist = False            
    elif sit == 1:
        # search all subfolders for txt file
        for root, dirs, files in _os.walk(direct):
            for name in files:
                if name.endswith(FixRepNameEND):
                    FixRepDic[name.split(FixRepNameEND)[0]] = _os.path.join(direct, name.split(FixRepNameEND)[0], name)
        if len(FixRepDic) == 0:
            print 'No fixation report txt files in subfolders!'
            FixRepExist = False    
    
    return FixRepExist, FixRepDic


def _calTimeStamp(align_method, trial_type, trialstart, RegDF, StampDFtemp, FixRepDF, SacDF, FixDF):
    """
    assign line_no based on FixRep or Fix_Sac
    arguments:
        align_method : 'FixRep': based on FixRepDF; 
                       'Fix_Sac': based on SacDF, FixDF
    """
    if align_method == 'FixRep':
        # use FixRepDF
        FixRep_cur = FixRepDF[FixRepDF.trial == trial_type].reset_index()          
        line_idx, line_time = _getLineInfo(FixRep_cur)            
        for curind in range(len(line_idx)):
            StampDFtemp.loc[(StampDFtemp.time >= line_time[curind][0] + trialstart) & (StampDFtemp.time <= line_time[curind][1] + trialstart), 'line_no'] = line_idx[curind]
            StampDFtemp.loc[(StampDFtemp.time >= line_time[curind][0] + trialstart) & (StampDFtemp.time <= line_time[curind][1] + trialstart), 'Fix_Sac'] = 'Fix'
    elif align_method == 'Fix_Sac':
        # use SacDF and FixDF
        SacDF_cur = SacDF[SacDF.trial_type == trial_type].reset_index()  
        FixDF_cur = FixDF[FixDF.trial_type == trial_type].reset_index()
        for curind in range(len(SacDF_cur)):
            starttime = SacDF_cur.start_time[curind]; endtime = SacDF_cur.end_time[curind]
            StampDFtemp.loc[(StampDFtemp.time >= starttime) & (StampDFtemp.time <= endtime), 'line_no'] = SacDF_cur.line_no[curind]
            StampDFtemp.loc[(StampDFtemp.time >= starttime) & (StampDFtemp.time <= endtime), 'Fix_Sac'] = 'Sac'
        for curind in range(len(FixDF_cur)):
            starttime = FixDF_cur.start_time[curind]; endtime = FixDF_cur.end_time[curind]
            StampDFtemp.loc[(StampDFtemp.time >= starttime) & (StampDFtemp.time <= endtime), 'line_no'] = FixDF_cur.line_no[curind]
            StampDFtemp.loc[(StampDFtemp.time >= starttime) & (StampDFtemp.time <= endtime), 'Fix_Sac'] = 'Fix'
        
    # assign region_no in StampDFtemp
    for curStamp in range(len(StampDFtemp)):
        if not _np.isnan(StampDFtemp.loc[curStamp, 'x_pos1']) and StampDFtemp.loc[curStamp, 'Fix_Sac'] == 'Fix' and not _np.isnan(StampDFtemp.loc[curStamp, 'line_no']):
            indlist = RegDF[(RegDF['line_no'] == StampDFtemp.loc[curStamp,'line_no']) & ((RegDF['mod_x1'] <= StampDFtemp.loc[curStamp,'x_pos1']) & (RegDF['mod_x2'] >= StampDFtemp.loc[curStamp,'x_pos1']))].index.tolist()
            if len(indlist) == 1:
                StampDFtemp.loc[curStamp,'gaze_region_no'] = int(RegDF.WordID[indlist[0]])
                StampDFtemp.loc[curStamp,'label'] = RegDF.Word[indlist[0]]
            else: StampDFtemp.loc[curStamp,'gaze_region_no'] = _np.nan
        else: StampDFtemp.loc[curStamp,'gaze_region_no'] = _np.nan


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


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# helper functions for calculating eye-movement measures
def _modEM(EMDF, addCharSp):
    """
    modify MFDF's mod_x1 and mod_x2, add space to boundaries of line
    starting and ending words
    arguments:
        EMDF      : result data frame
        addCharSp : number of single character space added to EMF for
                    catching overshoot fixations
        EMDF, as a data frame, is mutable, no need to return    
    """
    EMDF.mod_x1 = EMDF.x1_pos; EMDF.mod_x2 = EMDF.x2_pos
    addDist = addCharSp*(EMDF.loc[0,'x2_pos'] - EMDF.loc[0,'x1_pos'])/_np.float(EMDF.loc[0,'reglen'])
    for curEM in range(len(EMDF)):
        if curEM == 0:            
            EMDF.loc[curEM,'mod_x1'] -= addDist    # first word, add leftside!
        elif curEM == len(EMDF) - 1:            
            EMDF.loc[curEM,'mod_x2'] += addDist    # last word, add rightside!
        else:
            # check whether it is a line ending or line starting word
            if EMDF.loc[curEM-1,'line_no'] == EMDF.loc[curEM,'line_no'] - 1:
                EMDF.loc[curEM,'mod_x1'] -= addDist    # current region is a line starting, add leftside!
            elif EMDF.loc[curEM+1,'line_no'] == EMDF.loc[curEM,'line_no'] + 1:
                EMDF.loc[curEM,'mod_x2'] += addDist    # current region is a line ending, add rightside!


def _chk_fp_fix(FixDF, EMDF, curFix, curEM):
    """
    calculate fist-pass fixation measures:
        fpurt    : first-pass fixation time. It is the sum of the 
                   durations of one or more first-pass fixations 
                   falling into the word region. By default, we only
                   record fixations of 50 ms or longer; shorter fixations
                   are subject to the lumping operation. If there is no 
                   first-pass fixation laying within the word region, 
                   'fpurt' is 'NaN' (missing value)                   
        fpcount  : number of first-pass fixations falling into the word
                   region. If there is no first-pass fixation in the word
                   region, 'fpcount' is 'NaN'
        ffos     : offset in characters of the first first-pass fixation 
                   in the word region from the first character of the 
                   region. If there is no first-pass fixation in the word
                   region, 'ffos' is 'NaN'
        ffixurt  : duration of the first first-pass fixation in the word
                   region. If there is no first-pass fixation in the word
                   region, 'ffixurt' is 'NaN' 
        spilover : duration of the first fixation falling beyond (either 
                   left or right) the word region. If there is no 
                   first-pass fixation in the word region, 'spilover' is 
                   'NaN' 
    arguments:
        FixDF  : fixation data of the trial
        EMDF   : result data frame
        curFix : current fixation in the region
        curEM  : current region in the result data frame      
    returns:
        stFix, endFix : starting and ending fixation indices of the first reading
    """
    EMDF.loc[curEM,'fpurt'] += FixDF.loc[curFix,'duration']  # fpurt: first pass fixation time
    EMDF.loc[curEM,'fpcount'] += 1 # fpcount: number of first pass fixation
    EMDF.loc[curEM,'ffos'] = _np.ceil((FixDF.loc[curFix,'x_pos'] - EMDF.loc[curEM,'mod_x1'])/_np.float(EMDF.loc[curEM,'mod_x2'] - EMDF.loc[curEM,'mod_x1']) * EMDF.loc[curEM,'reglen']) - 1   # ffos: offset of the first first-pass fixation in a region from the first letter of the region, in characters (range of 0 to reglen-1)
    EMDF.loc[curEM,'ffixurt'] += FixDF.loc[curFix,'duration']   # ffixurt: first first-pass fixation duration for each region.
    # locate the starting and ending indices of the first pass fixation in the current region                    
    stFix, endFix = curFix, curFix + 1
    while endFix < len(FixDF)-1 and _np.isnan(FixDF.loc[endFix,'line_no']): endFix += 1
    # keep searching until leaving that word and use that as the ending index 
    while endFix < len(FixDF)-1 and FixDF.loc[endFix,'valid'] == 'yes' and FixDF.loc[endFix,'line_no'] == EMDF.loc[curEM,'line_no'] and EMDF.loc[curEM,'mod_x1'] <= FixDF.loc[endFix,'x_pos'] and FixDF.loc[endFix,'x_pos'] <= EMDF.loc[curEM,'mod_x2']:
        EMDF.loc[curEM,'fpurt'] += FixDF.loc[endFix,'duration']  # add fpurt: first pass fixation time
        EMDF.loc[curEM,'fpcount'] += 1  # add fpcount: number of first pass fixation
        endFix += 1
        while endFix < len(FixDF)-1 and _np.isnan(FixDF.loc[endFix,'line_no']): endFix += 1
    if endFix < len(FixDF) and FixDF.loc[endFix,'valid'] == 'yes' and not _np.isnan(FixDF.loc[endFix,'line_no']):
        EMDF.loc[curEM,'spilover'] += FixDF.loc[endFix,'duration']  # add spilover: Duration of the first fixation beyond a region/word.   
    return stFix, endFix


def _chk_fp_reg(FixDF, EMDF, stFix, endFix, curEM):
    """
    calculate first-pass regression measures:
        fpregres : whether there is a first-pass regression starting from
                   the current word region; if so, 'fpregres' is 1, 
                   otherwise, 'fpregres' is 0. If there is no first-pass 
                   fixation in the word region, ‘fpregres’ is ‘NaN’
        fpregreg : word region where the first-pass regression ends. If 
                   there is no first-pass regression ('fpregres' is 0),
                   'fpregreg' is 0. If there is no first-pass fixation in
                   the word region, 'fpregreg' is 'NaN'
        fpregchr : offset in characters in the word region where the
                   first-pass regression ends. If there is no first-pass 
                   regression ('fpregres' is 0), 'fpregchr' is set to a 
                   value large enough to be out of boundaries of any 
                   possible string (in the current version, it is set as
                   the total number of characters of the text). If there 
                   is no first-pass fixation in the word region, 
                   'fpregchr' is 'NaN'
    arguments:
        FixDF         : fixation data of the trial
        EMDF          : result data frame
        stFix, endFix : starting and ending fixation indices of the first
                        reading
        curEM         : current region in the result data frame              
    """
    if FixDF.loc[endFix,'line_no'] == EMDF.loc[curEM,'line_no']:
        # the fixation after the first pass reading is within the same line of the current word
        if FixDF.loc[endFix,'x_pos'] < EMDF.loc[curEM,'mod_x1']:
            # a regression fixation
            EMDF.loc[curEM,'fpregres'] = 1
            # search the region where regression fixation falls into
            for cur in range(len(EMDF)):
                if FixDF.loc[endFix,'region_no'] == EMDF.loc[cur,'region']:
                    EMDF.loc[curEM,'fpregreg'] = EMDF.loc[cur,'region']
                    if cur == 0: EMDF.loc[curEM,'fpregchr'] = _np.ceil((FixDF.loc[endFix,'x_pos'] - EMDF.loc[cur,'mod_x1'])/_np.float(EMDF.loc[cur,'mod_x2'] - EMDF.loc[cur,'mod_x1']) * EMDF.loc[cur,'reglen']) - 1
                    else: EMDF.loc[curEM,'fpregchr'] = sum(EMDF.reglen[0:cur-1]) + _np.ceil((FixDF.loc[endFix,'x_pos'] - EMDF.loc[cur,'mod_x1'])/_np.float(EMDF.loc[cur,'mod_x2'] - EMDF.loc[cur,'mod_x1']) * EMDF.loc[cur,'reglen']) - 1
                    break
        else:
            # a forward fixation
            EMDF.loc[curEM,'fpregres'] = 0; EMDF.loc[curEM,'fpregreg'] = 0; EMDF.loc[curEM,'fpregchr'] = sum(EMDF.reglen)                    
    else:
        # the fixation after the first pass reading is not in the same line of the current word
        if FixDF.loc[endFix,'line_no'] < EMDF.loc[curEM,'line_no']:
            # a regression fixation
            EMDF.loc[curEM,'fpregres'] = 1
            # search the region where regression fixation falls into
            for cur in range(len(EMDF)):
                if FixDF.loc[endFix,'region_no'] == EMDF.loc[cur,'region']:
                    EMDF.loc[curEM,'fpregreg'] = EMDF.loc[cur,'region']
                    if cur == 0: EMDF.loc[curEM,'fpregchr'] = _np.ceil((FixDF.loc[endFix,'x_pos'] - EMDF.loc[cur,'mod_x1'])/_np.float(EMDF.loc[cur,'mod_x2'] - EMDF.loc[cur,'mod_x1']) * EMDF.loc[cur,'reglen']) - 1
                    else: EMDF.loc[curEM,'fpregchr'] = sum(EMDF.reglen[0:cur-1]) + _np.ceil((FixDF.loc[endFix,'x_pos'] - EMDF.loc[cur,'mod_x1'])/_np.float(EMDF.loc[cur,'mod_x2'] - EMDF.loc[cur,'mod_x1']) * EMDF.loc[cur,'reglen']) - 1
                    break
        else:
            # a forward fixation
            EMDF.loc[curEM,'fpregres'] = 0; EMDF.loc[curEM,'fpregreg'] = 0; EMDF.loc[curEM,'fpregchr'] = sum(EMDF.reglen)

  
def _getReg(FixDF, curFix, EMDF):
    """
    search EMF to locate which region that FixDF.loc[curFix] falls into
    arguments:
        FixDF  : fixation data of the trial
        curFix : current fixation index
        EMDF   : result data frame containing all region information
    return: index in EMF    
    """
    if _np.isnan(FixDF.line_no[curFix]) or _np.isnan(FixDF.region_no[curFix]): return 0
    else:
        indlist = EMDF[(EMDF['line_no']==FixDF.line_no[curFix]) & (EMDF['region']==FixDF.region_no[curFix])].index.tolist()
        if len(indlist) == 1: return indlist[0]
        else: return 0


def _chk_rp_reg(FixDF, EMDF, stFix, endFix, curEM):
    """
    calculate regression path measures:
        rpurt    : sum of durations of all fixations in the regression 
                   path. A regression path starts from the first fixation
                   falling into the current word region and ends at the 
                   first fixation falling into the immediately next word
                   region. If there is a first-pass regression ('fpregres'
                   is 1), the regression path includes the fixations in 
                   the current region and those outside the current word 
                   region but falling into only the word regions before 
                   the current region. If there is no first-pass 
                   regression ('fpregres' is 0), 'rpurt' equals to 'fpurt'.
                   If there is no first-pass fixation in the word region, 
                   'rpurt' is 'NaN'
        rpcount  : number of fixations in the regression path. If there is
                   no first-pass fixation in the word region, 'rpcount' is
                   'NaN'
        rpregreg : the smallest index of the word region visited by the 
                   regression path. If there is no regression path 
                   ('fpregres' is 0), 'rpregreg' is 0. If there is no 
                   first-pass fixation in the word region, 'rpregreg' is 
                   'NaN'
        rpregchr : offset in characters in the smallest word region 
                   visited by the regression path. If there is no 
                   first-pass regression ('fpregres' is 'NA'), 'rpregchr' 
                   is set to a value large enough to be out of boundaries
                   of any possible string (in the current version, it is 
                   set as the total number of characters of the text). If
                   there is no first-pass fixation in the word region, 
                   'rpregreg' is 'NaN'
    arguments:
        FixDF         : fixation data of the trial
        EMDF          : result data frame
        stFix, endFix : starting and ending fixation indices of the first
                        reading
        curEM         : current region in the result data frame            
    """
    if EMDF.loc[curEM,'fpregres'] == 0:
        # there is no regression, so no regression path
        EMDF.loc[curEM,'rpurt'] = EMDF.loc[curEM,'fpurt']; EMDF.loc[curEM,'rpcount'] = 0; EMDF.loc[curEM,'rpregreg'] = 0; EMDF.loc[curEM,'rpregchr'] = sum(EMDF.reglen) 
    else:
        # there is a regression, find the regression path
        if curEM == 0:
            # the first region (word), treat it as the same as no regression
            EMDF.loc[curEM,'rpurt'] = EMDF.loc[curEM,'fpurt']; EMDF.loc[curEM,'rpcount'] = 0; EMDF.loc[curEM,'rpregreg'] = 0; EMDF.loc[curEM,'rpregchr'] = sum(EMDF.reglen) 
        elif curEM == len(EMDF) - 1:
            # the last region (word)            
            EMDF.loc[curEM,'rpurt'] = EMDF.loc[curEM,'fpurt'] + FixDF.loc[endFix,'duration']
            EMDF.loc[curEM,'rpcount'] += 1
            curFix = endFix + 1
            leftmostRegInd = _getReg(FixDF, endFix, EMDF)
            leftmostReg = EMDF.region[leftmostRegInd]
            leftmostCurFix = endFix            
            while curFix < len(FixDF) and FixDF.loc[curFix,'valid'] == 'yes' and not _np.isnan(FixDF.loc[curFix,'line_no']):
                # in the regression path                
                EMDF.loc[curEM,'rpurt'] += FixDF.loc[curFix,'duration']
                EMDF.loc[curEM,'rpcount'] += 1
                newleftInd = _getReg(FixDF, curFix, EMDF)
                newleft = EMDF.region[newleftInd]
                if leftmostReg > newleft:
                    leftmostRegInd = newleftInd
                    leftmostReg = newleft
                    leftmostCurFix = curFix                    
                curFix += 1
            EMDF.loc[curEM,'rpregreg'] = leftmostReg
            if leftmostRegInd == 0: EMDF.loc[curEM,'rpregchr'] = _np.ceil((FixDF.loc[leftmostCurFix,'x_pos'] - EMDF.loc[leftmostRegInd,'mod_x1'])/_np.float(EMDF.loc[leftmostRegInd,'mod_x2'] - EMDF.loc[leftmostRegInd,'mod_x1']) * EMDF.loc[leftmostRegInd,'reglen']) - 1
            else: EMDF.loc[curEM,'rpregchr'] = sum(EMDF.reglen[0:leftmostRegInd]) + _np.ceil((FixDF.loc[leftmostCurFix,'x_pos'] - EMDF.loc[leftmostRegInd,'mod_x1'])/_np.float(EMDF.loc[leftmostRegInd,'mod_x2'] - EMDF.loc[leftmostRegInd,'mod_x1']) * EMDF.loc[leftmostRegInd,'reglen']) - 1
        else:
            # the middle region (word)
            EMDF.loc[curEM,'rpurt'] = EMDF.loc[curEM,'fpurt']
            newendFix = endFix + 1
            while newendFix < len(FixDF) and FixDF.loc[newendFix,'valid'] == 'yes' and not _np.isnan(FixDF.loc[newendFix,'line_no']) and not _np.isnan(FixDF.loc[newendFix,'region_no']) and FixDF.loc[newendFix,'region_no'] <= FixDF.loc[stFix,'region_no']: newendFix += 1           
            leftmostRegInd = _getReg(FixDF, endFix, EMDF)
            leftmostReg = EMDF.region[leftmostRegInd]
            leftmostCurFix = endFix
            for indFix in range(endFix, newendFix):
                if not _np.isnan(FixDF.loc[indFix,'region_no']):               
                    EMDF.loc[curEM,'rpurt'] += FixDF.loc[indFix,'duration']
                    EMDF.loc[curEM,'rpcount'] += 1
                    newleftInd = _getReg(FixDF, indFix, EMDF)
                    newleft = EMDF.region[newleftInd]
                    if leftmostReg > newleft:
                        leftmostRegInd = newleftInd
                        leftmostReg = newleft
                        leftmostCurFix = indFix 
            EMDF.loc[curEM,'rpregreg'] = leftmostReg
            if leftmostRegInd == 0: EMDF.loc[curEM,'rpregchr'] = _np.ceil((FixDF.loc[leftmostCurFix,'x_pos'] - EMDF.loc[leftmostRegInd,'mod_x1'])/_np.float(EMDF.loc[leftmostRegInd,'mod_x2'] - EMDF.loc[leftmostRegInd,'mod_x1']) * EMDF.loc[leftmostRegInd,'reglen']) - 1
            else: EMDF.loc[curEM,'rpregchr'] = sum(EMDF.reglen[0:leftmostRegInd]) + _np.ceil((FixDF.loc[leftmostCurFix,'x_pos'] - EMDF.loc[leftmostRegInd,'mod_x1'])/_np.float(EMDF.loc[leftmostRegInd,'mod_x2'] - EMDF.loc[leftmostRegInd,'mod_x1']) * EMDF.loc[leftmostRegInd,'reglen']) - 1
            

def _chk_sp_fix(FixDF, EMDF, endFix, curEM):
    """
    calculate second-pass fixation measures:
        spurt   : second-pass fixation time. It is the sum of durations of
                  all fixations falling again into the current word region
                  after the first-pass reading. If there is no second-pass
                  fixation, 'spurt' is 'NaN'
        spcount : number of second-pass fixations. If there is no 
                  second-pass fixation, 'spcount' is 'NA'
    arguments:
        FixDF  : fixation data of the trial
        EMDF   : result data frame
        endFix : ending fixation index of the first reading
        curEM  : current region in the result data frame            
    """
    for curFix in range(endFix, len(FixDF)):
        if FixDF.loc[curFix,'region_no'] == EMDF.loc[curEM,'region']:
            EMDF.loc[curEM,'spurt'] += FixDF.loc[curFix,'duration'] # add spurt: second pass fixation time
            EMDF.loc[curEM,'spcount'] += 1  # add spcount: the number of second pass fixations            
    

def _chk_tffixos(EMDF):
    """
    calculate tffixos: offset of the first fixation in trial in 
    letters from the beginning of the sentence
    arguments:
        EMDF : result data frame
    """
    tffixos = 0
    for ind in range(len(EMDF)):
        if not _np.isnan(EMDF.loc[ind,'ffos']):
            if ind == 0: tffixos += EMDF.loc[ind,'ffos']
            else: tffixos += sum(EMDF.reglen[0:ind-1]) + EMDF.loc[ind,'ffos']
    
    return tffixos           

    
def _chk_tregrcnt(SacDF):
    """
    calculate tregrecnt: total number of regressive saccades in trial
    arguments:
        SacDF : saccade data of teh trial
    """
    totregr = 0
    for ind in range(len(SacDF)):
        crlinfo = str(SacDF.line_no[ind]).split('_')
        if len(crlinfo) == 1:
            if crlinfo != ['nan']:
                # not crossline saccade
                if SacDF.x1_pos[ind] > SacDF.x2_pos[ind]: totregr += 1
        else:
            # crossline saccade
            if int(float(crlinfo[0])) > int(float(crlinfo[1])): totregr += 1
                
    return totregr            


def _cal_EM(RegDF, FixDF, SacDF, EMDF):
    """
    calculate eye-movement measures of the trial
    arguments:
        RegDF : region file
        FixDF : fixation data of the trial
        SacDF : saccade data of the trial
        EMDF  : result data frame 
        EMDF, as a data frame, is mutable, no need to return
    eye-movement measures:
      whole trial measures:
        tffixos  : total offset of the first-pass fixation of each word 
                   from the beginning of the first sentence of the text
        tffixurt : total duration of the first pass fixation of each word
                   in the text
        tfixcnt  : total number of valid fixations in the trial
        tregrcnt : total number of regressive saccades (a saccade is a 
                   regressive saccade if it starts at one word region in
                   the text and ends at an earlier word region) in the 
                   trial region (each word) measures:  
        fpurt    : first-pass fixation time. It is the sum of the durations
                   of one or more first-pass fixations falling into the 
                   word region. By default, we only record fixations of 
                   50 ms or longer; shorter fixations are subject to the 
                   lumping operation. If there is no first-pass fixation 
                   laying within the word region, 'fpurt' is 'NaN' 
                   (missing value)
        fpcount  : number of first-pass fixations falling into the word 
                   region. If there is no first-pass fixation in the word
                   region, 'fpcount' is 'NaN' 
        fpregres : whether there is a first-pass regression starting from
                   the current word region; if so, 'fpregres' is 1, 
                   otherwise, 'fpregres' is 0. If there is no first-pass 
                   fixation in the word region, ‘fpregres’ is ‘NaN’
        fpregreg : word region where the first-pass regression ends. If 
                   there is no first-pass regression ('fpregres' is 0), 
                   'fpregreg' is 0. If there is no first-pass fixation in
                   the word region, 'fpregreg' is 'NaN'
        fpregchr : offset in characters in the word region where the
                   first-pass regression ends. If there is no first-pass 
                   regression ('fpregres' is 0), 'fpregchr' is set to a 
                   value large enough to be out of boundaries of any 
                   possible string (in the current version, it is set as
                   the total number of characters of the text). If there
                   is no first-pass fixation in the word region, 
                   'fpregchr' is 'NaN'
        ffos     : offset in characters of the first first-pass fixation 
                   in the word region from the first character of the 
                   region. If there is no first-pass fixation in the word
                   region, 'ffos' is 'NaN'
        ffixurt  : duration of the first first-pass fixation in the word 
                   region. If there is no first-pass fixation in the word 
                   region, 'ffixurt' is 'NaN'
        spilover : duration of the first fixation falling beyond (either 
                   left or right) the word region. If there is no 
                   first-pass fixation in the word region, 'spilover' is 
                   'NaN'
        rpurt    : sum of durations of all fixations in the regression
                   path. A regression path starts from the first fixation 
                   falling into the current word region and ends at the 
                   first fixation falling into the immediately next word 
                   region. If there is a first-pass regression ('fpregres'
                   is 1), the regression path includes the fixations in 
                   the current region and those outside the current word
                   region but falling into only the word regions before 
                   the current region. If there is no first-pass regression
                   ('fpregres' is 0), 'rpurt' equals to 'fpurt'. If there 
                   is no first-pass fixation in the word region, 'rpurt' 
                   is 'NaN'
        rpcount  : number of fixations in the regression path. If there is
                   no first-pass fixation in the word region, 'rpcount' is
                   'NaN'
        rpregreg : the smallest index of the word region visited by the
                   regression path. If there is no regression path 
                   ('fpregres' is 0), 'rpregreg' is 0. If there is no 
                   first-pass fixation in the word region, 'rpregreg' is
                   'NaN'
        rpregchr : offset in characters in the smallest word region 
                   visited by the regression path. If there is no 
                   first-pass regression ('fpregres' is 'NA'), 'rpregchr'
                   is set to a value large enough to be out of boundaries
                   of any possible string (in the current version, it is 
                   set as the total number of characters of the text). If
                   there is no first-pass fixation in the word region, 
                   'rpregreg' is 'NaN'
        spurt    : second-pass fixation time. It is the sum of durations
                   of all fixations falling again into the current word
                   region after the first-pass reading. If there is no 
                   second-pass fixation, 'spurt' is 'NaN'
        spcount  : number of second-pass fixations. If there is no 
                   second-pass fixation, 'spcount' is 'NA'
    """
    # default values
    EMDF.ffos = _np.nan  # for first pass fixation measures
    EMDF.fpregres = _np.nan; EMDF.fpregreg = _np.nan; EMDF.fpregchr = _np.nan   # for first regression measures
    EMDF.rpregres = _np.nan; EMDF.rpregreg = _np.nan; EMDF.rpregchr = _np.nan   # for regression path measures
    
    # region (each word) measures
    for curEM in range(len(EMDF)):
        for curFix in range(len(FixDF)):
            if FixDF.loc[curFix,'region_no'] == EMDF.loc[curEM,'region']:
                # find a first pass fixation on the current word!                    
                stFix, endFix = _chk_fp_fix(FixDF, EMDF, curFix, curEM) # calculate first pass fixation measures: fpurt, fpcount, ffos, ffixurt, spilover  
                _chk_fp_reg(FixDF, EMDF, stFix, endFix, curEM) # calculate first pass regression measures: fpregres, fpregreg, fpregchr
                _chk_rp_reg(FixDF, EMDF, stFix, endFix, curEM) # calculate regression path measures: rpurt, rpcount, rpregreg, rpregchr
                _chk_sp_fix(FixDF, EMDF, endFix, curEM) # calculate second pass fixation measures: spurt, spcount                                       
                # first pass reading of that word is finished, go to next word        
                break
                
    # change fpurt == 0, fpcount == 0, ffixurt == 0, spilover == 0 with NA
    EMDF.loc[EMDF[EMDF.fpurt==0].index,'fpurt'] = _np.nan
    EMDF.loc[EMDF[EMDF.fpcount==0].index,'fpcount'] = _np.nan
    EMDF.loc[EMDF[EMDF.ffixurt==0].index,'ffixurt'] = _np.nan
    EMDF.loc[EMDF[EMDF.spilover==0].index,'spilover'] = _np.nan
    EMDF.loc[EMDF[EMDF.spurt==0].index,'spurt'] = _np.nan
    EMDF.loc[EMDF[EMDF.spcount==0].index,'spcount'] = _np.nan
    EMDF.loc[EMDF[_np.isnan(EMDF.fpurt)].index,'rpurt'] = _np.nan
    EMDF.loc[EMDF[_np.isnan(EMDF.fpurt)].index,'rpcount'] = _np.nan          
    EMDF.loc[EMDF[_np.isnan(EMDF.fpurt)].index,'rpregreg'] = _np.nan
    # whole trial measures
    EMDF.tffixos = _chk_tffixos(EMDF)  # tffixos: offset of the first fixation in trial in letters from the beginning of the sentence       
    EMDF.ttfixurt = sum(x for x in EMDF.fpurt if not _np.isnan(x))     # tffixurt: duration of the first fixation in trial
    EMDF.tfixcnt = len(FixDF[FixDF.valid=='yes'])    # tfixcnt: total number of valid fixations in trial
    EMDF.tregrcnt = _chk_tregrcnt(SacDF)  # tregrcnt: total number of regressive saccades in trial

    