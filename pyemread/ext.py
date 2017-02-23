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

This is a set of functions designed for extracting saccades and fixations
detected by eye trackers (SRR eyelink devices) during reading and 
classifying them into different text lines.

For usage, 
In python code, use: from pyemread import ext
Then, one can call all functions in the package using the namespace ext.
Or, one can use: import pyemread as pr, 
and then use pr.ext to call functions in ext.
"""

# import helper functions from _helperfunc_.py
import os as _os
import sys as _sys
import fnmatch as _fnmatch
import re as _re
import pandas as _pd
import numpy as _np


# make the system default codeing as "utf-8"
reload(_sys); _sys.setdefaultencoding("utf-8")


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

