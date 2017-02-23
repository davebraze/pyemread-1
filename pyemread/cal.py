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

This is a set of functions designed for calculating regional summaries of
widely-adopted EM measures used in reading research.

For usage, 
In python code, use: from pyemread import cal
Then, one can call all functions in the package using the namespace cal.
Or, one can use: import pyemread as pr, 
and then use pr.cal to call functions in cal.
"""

# import helper functions from _helperfunc_.py
import os as _os
import sys as _sys
import fnmatch as _fnmatch
import pandas as _pd
import numpy as _np


# make the system default codeing as "utf-8"
reload(_sys); _sys.setdefaultencoding("utf-8")


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
        mergeDF = mergeDF.sort_values(by=['trial_id','time'], ascending=True)
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

