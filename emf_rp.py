# -*- coding: utf-8 -*-
"""
Created on Fri Mar 20 15:17:44 2015

Summary EMF ASCII file recording eye-movement data
@author: tg422
"""
# imported packages
import os 
import fnmatch
import re
import csv
import codecs
import pandas as pd
import numpy as np
# from scipy import spatial
from PIL import Image, ImageDraw, ImageFont
import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
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
    w = csv.writer(f)
    for key, val in dict_rap.items():
        w.writerow([key,eval(val)])
    f.close()
     

def readDict(fn):
    f = open(fn,'rb')
    dict_rap = Dictlist()
    for key, val in csv.reader(f):
        dict_rap[key] = eval(val)
    f.close()
    return(dict_rap)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# functions for generating bitmap used for paragraph reading
# global variables
# for PRaster
STANDARD_CHAR = u'n'


def InputDict(resDict, curKey, Name, Word, length, height, baseline, curline, x1_pos, y1_pos, x2_pos, y2_pos, b_x1, b_y1, b_x2, b_y2):
    """
    write result of each word into resDict: note that dictionary value may have a different sequence as in the final csv
    """
    resDict[curKey] = Name; resDict[curKey] = Word; resDict[curKey] = length; resDict[curKey] = height; resDict[curKey] = baseline; resDict[curKey] = curline
    resDict[curKey] = x1_pos; resDict[curKey] = y1_pos; resDict[curKey] = x2_pos; resDict[curKey] = y2_pos
    resDict[curKey] = b_x1; resDict[curKey] = b_y1; resDict[curKey] = b_x2; resDict[curKey] = b_y2    
    return(resDict)


def writeCSV(regFile, resDict):
    """
    write resDict to csv file: Name, WordID, Word, length, height, baseline, line, x1_pos, y1_pos, x2_pos, y2_pos, b_x1, b_y1, b_x2, b_y2
    """
    DF = pd.DataFrame(np.zeros((len(resDict), 15)))
    cur = 0    
    for key in resDict.keys():
        DF.loc[cur,0] = resDict[key][0]; DF.loc[cur,1] = key
        for i in np.arange(1,14):
            DF.loc[cur,i+1] = resDict[key][i]
        cur += 1
    DF.columns = ['Name', 'WordID', 'Word', 'length', 'height', 'baseline', 'line', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos', 'b_x1', 'b_y1', 'b_x2', 'b_y2']        
    DF.sort(column='WordID')
    DF.to_csv(regFile, index=False)


# class for PRaster (generating bitmap of pararaphs) and Draw_Fix_Sac 
class FontDict(dict):
    """ 
    Build a list of installed fonts with meta-data.
    FIXME: Look into using python bindings to fontconfig for this purpose.
    UPDATE: I tried to install python-fontconfig package under windows and 
            not able to do so. Did no troubleshooting.
    """
    def __init__(self):
        """
        This function returns a dict (fontdict) that includes a key for each font family,
        , with subkeys for each variant in the family (e.g., fontdict['Arial']['Regular']
        might contain u'c:\\windows\\fonts\\arial.ttf')
        Explore functionality in font_manager to see if this is really needed.
        Especially check into borrowing functionality from createFontList().
        fl=font_manager.createFontList(font_manager.findSystemFonts())
        """
        dict.__init__(self)
        fontpathlist = font_manager.findSystemFonts(); fontpathlist.sort() # Get paths to all installed font files (any system?).
        for fp in fontpathlist:
            fi = ImageFont.truetype(fp, 12)
            family = re.sub('[ -._]', '', fi.getname()[0])
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
        Given a font family name, return a dict containing all available styles in 
        the family (keys) and paths to relevant font files (values).
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
                

# functions for calculating descents and ascents of characters in words 
def getStrikeAscents(fontFileName, size):
    """
    Build and return a dictionary of ascents (in pixels) for a specific font/size:    
    group1: u'bdfhijkl|()\"\''
    group2: u't'
    group3: u'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    group4: u'0123456789'
    group5: u'?!'
    group6: u'%&@$'
    """
    ttf = ImageFont.truetype(fontFileName, size) # init the specified font resource
    (wd_o, ht_o) = ttf.getsize(u'o')    # used as the baseline character
    
    (wd_b, ht_b) = ttf.getsize(u'b')    # representative of group 1
    (wd_t, ht_t) = ttf.getsize(u't')    # representative of group 2
    (wd_A, ht_A) = ttf.getsize(u'A')    # representative of group 3
    (wd_0, ht_0) = ttf.getsize(u'0')    # representative of group 4
    (wd_ques, ht_ques) = ttf.getsize(u'?')  # representative of group 5
    (wd_and, ht_and) = ttf.getsize(u'&')    # representative of group 6
    
    ### FIXME: should also look at other punctuation chars, and digits.    
    return ({u'bdfhijkl|()\"\'': ht_b - ht_o,
             u't': ht_t - ht_o,
             u'ABCDEFGHIJKLMNOPQRSTUVWXYZ': ht_A - ht_o,
             u'0123456789': ht_0 - ht_o,
             u'?!': ht_ques - ht_o,
             u'%&@$': ht_and - ht_o})


def getStrikeCenters(fontFileName, size):  
    """
    Some fonts have no descents or ascents: u'acemnorsuvwxz'
    """    
    ttf = ImageFont.truetype(fontFileName, size) # init the specified font resource
    (wd_o, ht_o) = ttf.getsize(u'o')
    return (ht_o)


def getStrikeDescents(fontFileName, size):
    """
    Build and return a dictionary of descents (in pixels) for a specific font/size.
    group1: u'gpqy'; group2: u'j'; group3: u'Q@&$'; group4: u','; group5: u';'; group6: (u'|()_'
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

    ### FIXME: should also look at other punctuation chars, and digits.
    return ({u'gpqy': ht_o - ht_g, 
             u'j': ht_i - ht_j,
             u'Q@&$': ht_O - ht_Q,
             u',': ht_dot - ht_comma,
             u';': ht_colon - ht_semicolon,
             u'|()_': ht_l - ht_or})


def getKeyVal(char, desasc_dict):
    """
    get the value of the key that contains char    
    """
    val = 0
    for key in desasc_dict.keys():
        if key.find(char) != -1:
            val = desasc_dict[key]
            break            
    return (val)        


def getdesasc(w, descents, ascents):
    """
    calculate minimum descent and maximum ascent, note that if there is no descent, no need to calculate ascent!
    """
    mdes, masc = 0, 0
    for c in w:
        mdes, masc = min(mdes, getKeyVal(c, descents)), max(masc, getKeyVal(c, ascents))
    return ((mdes, masc))


def cAspect(imgfont, char=STANDARD_CHAR):
    """
    Determine the wd to ht ratio for the letter 'n' in the specified font.
    >>> fontdict = getfontdict()
    >>> sfont = fontdict['LucidaConsole']['Regular']
    >>> ssize = 12
    >>> sttf = ImageFont.truetype(sfont, ssize)
    >>> cAspect(sttf)
    """
    return (float(imgfont.getsize(char)[1])/imgfont.getsize(char)[0])


def Praster(fontpath, codeMethod='utf_8', text=[u'The quick brown fox jumps over the lazy dog.', u'The lazy tabby cat sleeps in the sun all afternoon.'],
            dim=(1280,1024), fg=(0,0,0), bg=(232,232,232), wfont=None, regfile=True, lmargin=86, tmargin=86, linespace=43, xsz=18, ysz=None, bbox=False, bbox_big=False, 
            ID='test', addspace=18, log=False):
    """
    Rasterize 'text' using 'font' according to the specified parameters. 
    Intended for single/multiple line texts.
    
    Arguments:
        fontpath        : fully qualified path to font file
        codeMethod      : for linux: utf_8; for Windows: cp1252
        text=[]         : text to be rasterized as a list of lines
        dim=(1280,1024) : (x,y) dimension of bitmap 
        fg=(0,0,0)      : RGB font color
        bg=(232,232,232): RGB background color
        wfont=None      : font used for watermark. Only relevant if watermark=True.
        regfile=True    : create word-wise regionfile by default
        lmargin=86      : left margin in pixels
        tmargin=86      : top margin in pixels  NOTE ORIGIN IS IN BOTTOM LEFT CORNER
        linespace=43    : linespacing in pixels
        xsz=18          : font height in pixels (max vertical distance between highest and lowest painted pixel
                        : considering every character in the font). Makes more sense to specify _width_,
                        : but ImageFont.truetype() wants a ht). Not every font obeys; see, e.g., "BrowalliaUPC Regular"
        ysz=None        : towards character width in pixels. Takes precedence over xsz. 
        bbox=False      : draw bounding box around each word.
        bbox_big=False  : draw bounding box around the whole line of word.        
        ID='test'       : unique ID for stim, used to build filenames for bitmap and regions. Also included in watermark.
        addspace        : the extra pixels you want to add above the top and below the bottom of each line of texts
        log             : log for recording intermediate result
    """
    if ysz: # Reset xsz if ysz is specified. This isn't working quite like I'd like. See full set of font species for details.
        ttf = ImageFont.truetype(fontpath, xsz) # init the specified font resource
        casp = cAspect(ttf)
        xsz= int(round(ysz*casp))
        ttf = ImageFont.truetype(fontpath, xsz) # re-init the specified font resource
        (wd, ht) = ttf.getsize(STANDARD_CHAR)  
    else:
        ttf = ImageFont.truetype(fontpath, xsz) # init the specified font resource
    
    # create descents and ascents dictionaries
    descents = getStrikeDescents(fontpath, xsz); ascents = getStrikeAscents(fontpath, xsz)

    if log: 
        import json
        logfileH = codecs.open("Praster.log", 'wb', encoding=codeMethod)
        logfileH.write('ascents\n'); json.dump(ascents, logfileH); logfileH.write('\n')
        logfileH.write('descents\n'); json.dump(descents, logfileH); logfileH.write('\n')

    ### FIXME: Should throw a warning if margins, font size and dim are such that 'text' will not fit on screen.
    ###        Look into using Pango for that purpose.
    ### FIXME: Add code to understand glyph size specification in either physical units like cm (given physical 
    ###        size of display screen) or degrees of physical angle given screen size plus nominal viewing distance.

    ### initialize the image
    img = Image.new('RGB', dim, bg) # 'RGB' specifies 8-bit per channel (32 bit color)
    draw = ImageDraw.Draw(img)

    ### open the region file: use codecs.open() to properly support writing unicode strings
    if regfile: 
        #regfileH = codecs.open(id+".region.txt", 'wb', encoding=codeMethod)
        #wo = '%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s' % ('Name', 'WordID', 'Word', 'length', 'height', 'baseline', 'line', 
        #                                                 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos', 'b_x1', 'b_y1', 'b_x2', 'b_y2') 
        #regfileH.write(wo+'\n')
        resDict = Dictlist(); curKey = 1
          
    # output file: 
    #       id: story id 
    #      len: length of each word, include ahead bracket or quotation, or behind punctuation, 
    #   height: getsize() for single character is fine! not for words!
    # baseline: base line of each line of words
    #     line: line number      
    # rec_x1, rec_y1, rec_x2, rec_y2: the rectangle bounding text of each word (not working properly due to error of getsize)
    # brec_x1, brec_y1, brec_x2, brec_y2: the rectangle bounding text based on the line (work properly!)      
    
    ### Paint each line onto the image a word at a time, including preceding space.
    if len(text) == 1: vpos = dim[1]/2 # single line! center 1st line of text in the middle
    else: vpos = tmargin  # multiple lines! initialize vertical position to the top margin!
    
    curline = 1
    for line in text:
        # break line into list of words and do some cleanup
        words = line.split(' ')
        if words.count(''): words.remove('')           # remove empty strings.
        words = [re.sub('^', ' ', w) for w in words]   # add a space to beginning of each word.
        if len(words) > 0: words[0] = words[0].strip() # remove space from beginning of first word in each line, guarding against empty wordlists.

        # paint the line into the image, one word at a time 
        # calculate the minimum descent and maximum height in all words on the same line
        mdes_all, mht_all = 0, 0
        for w in words:
            for c in w:
                mdes_all = min(mdes_all, getKeyVal(c, descents))    # get the biggest descent based on characters
            (wd, ht) = ttf.getsize(w)   # get the biggest height based on words (getsize function has offsets!)
            mht_all = max(mht_all, ht)
        aboveBase, belowBase = mht_all + mdes_all, mdes_all

        # paint the line into the image, one word at a time 
        xpos1 = lmargin # let edge of current word
        for w in words:
            wordlen = len(w) # should maybe trim leading space ?? punctuation ??    
            (wd, ht) = ttf.getsize(w)   # only wd is accurate
            xpos2 = xpos1 + wd    # right edge of current word
            
            (mdes, masc) = getdesasc(w, descents, ascents)  # calculate descent and ascent of each word
            ht = getStrikeCenters(fontpath, xsz) + masc - mdes  # calculate word height based on character
            # get the correct text position!
            vpos1 = vpos - ht - mdes
            vpos2 = vpos1 + ht            
            
            # outline the word region!
            if bbox: draw.rectangle([(xpos1, vpos1), (xpos2, vpos2)], outline=fg, fill=bg)
                
            # outline the line region!    
            vpos1_b, vpos2_b = vpos - aboveBase, vpos - belowBase    
            if bbox_big: draw.rectangle([(xpos1, vpos1_b - addspace), (xpos2, vpos2_b + addspace)], outline=fg, fill=bg)
            
            # draw current word
            vpos1_text = vpos1 + masc - xsz/4.5 - 1  # top edge of current word, masc - xsz/4.5 - 1 is offset!.
            draw.text((xpos1, vpos1_text), w, font=ttf, fill=fg) 
            
            # output word regions
            if regfile:
                #wo = '%s|%s|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d' % (id, w, wordlen, ht, vpos, curline,
                #                                                   xpos1, vpos1, xpos2, vpos2, xpos1, vpos1_b - addspace, xpos2, vpos2_b + addspace)
                #regfileH.write(wo+'\n')
                resDict = InputDict(resDict, curKey, ID, w, wordlen, ht, vpos, curline, xpos1, vpos1, xpos2, vpos2, xpos1, vpos1_b - addspace, xpos2, vpos2_b + addspace)
                curKey += 1
                
            xpos1 = xpos2   # shift to next word's left edge
        
        if vpos >= dim[1] + linespace: 
            raise ValueError("%d warning! %s has too many words! They cannot be shown within one screen!" % (vpos, id))
        else:
            vpos += linespace   # shift to next line
            curline += 1

    # ### apply a watermark
    # ### FIXME: watermark should (?) include more info. Maybe most arguments used in call to Sraster()
    # ### FIXME: need some error checking here.
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
    # ### FIXME: Add Functionality to include full set of arguments to Sraster() in meta data for bitmap files.
    # ### See PIL.ExifTags.TAGS
    
    ### Wrap up
    if regfile: 
        #regfileH.close() # close region file
        writeCSV(ID+".region.csv", resDict)
        
    if log: logfileH.close()  # close log file
    img.save(ID+".png",'PNG') # write bitmap file


def Gen_Bitmap_RegFile(direct, fontName, textFileNameList, genmethods=2, codeMethod='utf_8', dim=(1280,1024), fg=(0,0,0), bg=(232,232,232), 
    lmargin=215, tmargin=86, linespace=65, xsz=18, ysz=None, bbox=False, bbox_big=False, addspace=18, log=False):
    """
    generate the bitmaps (PNG) and region files of single/multiple line story from text file
    arguments:
        direct -- directory of for text files
        fontName -- name of a font, e.g. 'LiberationMono'
        textFileNameList -- a list of one or multiple text file for generating bitmaps
        genmethods -- methods to generate: 0: simple test (simple texts); 1: read from one text file; 2: read from many text files
     the following arguments are identical to Praster    
        codeMethod      : for linux: utf_8; for Windows: cp1252
        dim=(1280,1024) : (x,y) dimension of bitmap 
        fg=(0,0,0)      : RGB font color
        bg=(232,232,232): RGB background color
        lmargin=86      : left margin in pixels
        tmargin=86      : top margin in pixels NOTE ORIGIN IS IN BOTTOM LEFT CORNER
        linespace=43    : linespacing in pixels
        xsz=18          : font height in pixels (max vertical distance between highest and lowest painted pixel
                        : considering every character in the font). Makes more sense to specify _width_,
                        : but ImageFont.truetype() wants a ht). Not every font obeys; see, e.g., "BrowalliaUPC Regular"
        ysz=None        : towards character width in pixels. Takes precedence over xsz. 
        bbox=False      : draw bounding box around each word.
        bbox_big=False  : draw bounding box around the whole line of word.        
        addspace        : the extra pixels you want to add above the top and below the bottom of each line of texts
        log             : log for recording intermediate result
    output: for genmethods = 1, generate png and region files
    """
    fd = FontDict(); fontpath = fd.fontGet(fontName,'Regular')    
    # set up font related information
    fontpathlist = font_manager.findSystemFonts() # Get paths to all installed font files (any system?).
    fontpathlist.sort()
    
    if genmethods == 0:
        # Simple tests.
        Praster(fontpath, xsz=xsz, bbox=True, log=True)
        Praster(fontpath, text=["This is a test.", "This is another."], xsz=xsz)
        Praster(fontpath, text=["This is a one-liner."], xsz=xsz)

    elif genmethods == 1:
        # read from a single text file (containing many stories)
        txtfile = textFileNameList[0]; realtxtfile = direct + '/' + txtfile
    
        infileH = codecs.open(realtxtfile, mode="rb", encoding=codeMethod)
        print "Read text file: ", infileH.name; lines = infileH.readlines(); infileH.close()

        tmp0 = [ii for ii in lines if not re.match("^#", ii)] # Squeeze out comments: lines that start with '#'
        tmp1 = ''.join(tmp0)    # join list of strings into one long string
        tmp2 = re.split(u"\r\n\r\n", tmp1)  
               # Split string to lists by delimiter "\r\n\r\n", which corresponds to blank line in original text file (infileH).
               # At this point, each list item corresponds to 1, possibly multi-line, string.
               # Each list item is to be rendered as a single bitmap.
        tmp2[len(tmp2)-1] = re.sub(u"\r\n$", u"", tmp2[len(tmp2)-1])    # remove "\r\n" at the ending of the last line
        tmp3 = [re.split("\r\n", ii) for ii in tmp2]    # split each item into multiple lines, one string per line.

        for i, P in enumerate(tmp3): 
            s = "storyID = %02.d line = %d" % (i+1, len(P)); print(s)
            Praster(fontpath, codeMethod=codeMethod, text=P, dim=dim, fg=fg, bg=bg, lmargin=lmargin, tmargin=tmargin, linespace=linespace, 
                    xsz=xsz, ysz=ysz, bbox=bbox, bbox_big=bbox_big, addspace=addspace, ID=direct+'/'+'story%02.d' % (i+1), log=log)

    elif genmethods == 2:
        # read from multiple text files                        
        for txtfile in textFileNameList:
            ID = txtfile.split('.')[0]; realtxtfile = direct + '/' + txtfile
    
            infileH = codecs.open(realtxtfile, mode="rb", encoding=codeMethod)
            print "Read text file: ", infileH.name; lines = infileH.readlines(); infileH.close()

            tmp0 = [ii for ii in lines if not re.match("^#", ii)] # Squeeze out comments: lines that start with '#'
            tmp1 = ''.join(tmp0)    # join list of strings into one long string
            tmp2 = re.split(u"\r\n\r\n", tmp1)  
                        # Split string to lists by delimiter "\r\n\r\n", which corresponds to blank line in original text file (infileH).
                        # At this point, each list item corresponds to 1, possibly multi-line, string.
                        # Each list item is to be rendered as a single bitmap.
            tmp2[len(tmp2)-1] = re.sub(u"\r\n$", u"", tmp2[len(tmp2)-1])    # remove "\r\n" at the ending of the last line
            tmp3 = [re.split("\r\n", ii) for ii in tmp2]    # split each item into multiple lines, one string per line.

            Praster(fontpath, codeMethod=codeMethod, text=P, dim=dim, fg=fg, bg=bg, lmargin=lmargin, tmargin=tmargin, linespace=linespace, 
                    xsz=xsz, ysz=ysz, bbox=bbox, bbox_big=bbox_big, addspace=addspace, ID=direct+'/'+ID, log=log)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# functions obtaining basic information from data files
# global variables: 
# for updating old style region file
ADD_SPACE = 20
  

def getHeader(lines):
    """
    get header information
    argument:
        lines -- data lines
    return:
        script -- script file
        sessdate -- session date
        srcfile -- source file
    """
    header = [] 
    for line in lines:
        line = line.rstrip()
        if re.search('^[*][*] ', line):
            header.append(line)
       
    # get basic information from header lines       
    for line in header:
        if re.search('RECORDED BY', line):
            script = line.split(' ')[3]
        if re.search('DATE:', line):
            sessdate = line.split(': ')[1]
        if re.search('CONVERTED FROM', line):
            m = re.search(' FROM (.+?) using', line)
            if m:
                srcfile = os.path.basename(m.group(1))
    
    return script, sessdate, srcfile            


def getTrialReg(lines):
    """
    get the region (line range) of each trial
    argument:
        lines -- data lines
    return:
        T_idx -- trail start and ending lines
        T_lines -- trail start and ending line indices
    """
    trial_start = []; trial_start_lines = []
    trial_end = []; trial_end_lines = []
    cur = 0
    for line in lines:
        if re.search('TRIALID', line):
            trial_start.append(line); trial_start_lines.append(cur)
        if re.search('TRIAL_RESULT', line):
            trial_end.append(line); trial_end_lines.append(cur)
        cur += 1
    
    if len(trial_start) != len(trial_end):
        raise ValueError("Trial starting and ending mismatch!")

    T_idx = np.column_stack((trial_start, trial_end)); T_lines = np.column_stack((trial_start_lines, trial_end_lines))
    return T_idx, T_lines
    
    
def getBlink_Fix_Sac_SampFreq_EyeRec(triallines):
    """
    get split blink, fixation, and saccade data lines, and sampling frequency and eye recorded
    argument:
        triallines -- data lines of a trial
    return:
        blinklines; fixlines; saclines
        sampfreq; eyerec
    """
    blinklines = []; fixlines = []; saclines = []
    for line in triallines:
        if re.search('^EBLINK', line):
            blinklines.append(line.split())
        if re.search('^EFIX', line):
            fixlines.append(line.split())
        if re.search('^ESACC', line):
            saclines.append(line.split())
        if re.search('!MODE RECORD', line):
            sampfreq = int(line.split()[5])
            eyerec = line.split()[-1]
    return blinklines, fixlines, saclines, sampfreq, eyerec        


def gettdur(triallines):
    """
    get estimated trial duration
    argument:
        triallines -- data lines of a trial
    return:
        tdur -- estimated trial duration 
    """
    starttime, endtime = 0, 0
    for line in triallines:
        if re.search('START_RECORDING$', line):
            starttime = int(line.split()[1])
        if re.search('TIMER$', line):
            endtime = int(line.split()[1])
    return endtime - starttime        


def updateReg(regfileNameList):
    """
    update old style region file into new style and save
    """
    for trialID in range(len(regfileNameList)):
        RegDF = pd.read_csv(regfileNameList[trialID], sep=',', header=None)
        RegDF.columns = ['Name', 'Word', 'length', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos']
        # add WordID
        RegDF['WordID'] = range(1,len(RegDF)+1)        
        # add line        
        RegDF['line'] = 0
        lineInd = 1; lineReg_low = 0; cur_y = RegDF.y2_pos[0]
        for curind in range(len(RegDF)):
            if RegDF.y2_pos[curind] >= cur_y + 20:
                lineReg_up = curind
                for ind in range(lineReg_low, lineReg_up):
                    RegDF.loc[ind,'line'] = lineInd
                lineInd += 1; lineReg_low = lineReg_up; cur_y = RegDF.y2_pos[curind]
        if lineReg_up < len(RegDF):
            # add the remaining to another line
            for ind in range(lineReg_low, len(RegDF)):
                RegDF.loc[ind,'line'] = lineInd
        # add baseline
        RegDF['baseline'] = 0        
        for line in np.unique(RegDF.line):
            RegDF.loc[RegDF.line==line,'baseline'] = min(RegDF.loc[RegDF.line==line,'y2_pos'])
        # add height
        RegDF['height'] = 0
        for line in range(len(RegDF)):
            RegDF.loc[line,'height'] = RegDF.loc[line,'y2_pos'] - RegDF.loc[line,'y1_pos']        
        # add b_x1, b_y1, b_x2, b_y2    
        RegDF['b_x1'] = RegDF.x1_pos; RegDF['b_y1'] = 0; RegDF['b_x2'] = RegDF.x2_pos; RegDF['b_y2'] = 0
        for line in np.unique(RegDF.line):
            RegDF.loc[RegDF.line==line,'b_y1'] = max(RegDF.loc[RegDF.line==line,'y1_pos']) - ADD_SPACE
            RegDF.loc[RegDF.line==line,'b_y2'] = min(RegDF.loc[RegDF.line==line,'y2_pos']) + ADD_SPACE
        RegDF = RegDF[['Name', 'WordID', 'Word', 'length', 'height', 'baseline', 'line', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos', 'b_x1', 'b_y1', 'b_x2', 'b_y2']]     
        RegDF.to_csv(regfileNameList[trialID], index=False)            

    
def getRegDF(regfileNameList, trialID):
    """
    get the region file data frame from regfileNameList based on trialID
    arguments:
        regfileNameList -- a list of region file names
        trialID -- current trial ID
    return:
        RegDF -- region file data frame
    """
    if trialID < 0 or trialID >= len(regfileNameList):
        raise ValueError("invalid trialID! must be within [0, " + str(len(regfileNameList)) + ")")
    RegDF = pd.read_csv(regfileNameList[trialID], sep=',')
    return RegDF


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# functions geting crossline information based on region files, 
# used for checking crossline saccades and fixations.
# global variables
# for recording and lumping short fixations
LN = 50 # maximum duration of a fixation to "lump". Fixation <= this value is subject to lumping with adjacent and near enough (determined by zN) fixations
ZN = 50 # maximum distance (in pixels) between two fixations for "lumping"; default = 1.5 character (12/8s)
MN = 50 # minimum legal fixation duration; default = 50 ms
RECFINAL = False # whether or not include the final fixation of a trial and allow it to trigger regression; default = False

# for tracing log file recording questionable trials
RECSTATUS = True # record whether the datafile has some problem needing hand check    

# for extracting crossline saccade
# Basic assumption: crossline saccade or concatenate fixation tend to jump a large range of distance
FIXDIFF_RATIO = 0.6    # the ratio of maximum distance between the center of the last word and the center of the first word in a line, for checking cross-line fixations
FRONT_RANGE_RATIO = 0.2 # the ratio to check backward crossline saccade or fixation: such saccade or fixation usually starts around the line beginning
COSDIF_THRES = 0.99 # threshold for identifying forward crossline saccades or fixations based on cosine difference
Y_RANGE = 60   # the biggest y difference indicating the eyes are crossing lines or moving away from that line (this must be similar to the distance between two lines)
#Y_RANGE_RATIO = 1.3 # if y axis change too big, it is not a crossline
FIX_METHOD = 'DIFF' # fixation method: 'DIFF': based on difference in x_axis; 'SAC': based on crosslineSac ('SAC' is preferred since saccade is kinda more accurate!)


def getCrossLineInfo(RegDF, ExpType):
    """
    get cross line information from region file
    arguments:
        RegDF -- region file data frame (with line information)
        ExpType -- type of experiments: 'RAN', 'RP'
    return:
        CrossLineInfo -- list of dictionaries marking the cross line information: 
                        center of the last word of the previous line and center of the first word of the next line) 
    """
    CrossLineInfo = []
    if ExpType == 'RAN':
        CrossLineInfo = [
        {'p': 1, 'p_x': 1048, 'p_y': 287, 'n': 2, 'n_x': 232, 'n_y': 437},
        {'p': 2, 'p_x': 1048, 'p_y': 437, 'n': 3, 'n_x': 232, 'n_y': 587},
        {'p': 3, 'p_x': 1048, 'p_y': 587, 'n': 4, 'n_x': 232, 'n_y': 737}
        ]        
    elif ExpType == 'RP':
        for ind in range(len(RegDF)-1):
            if RegDF.line[ind]+1 == RegDF.line[ind+1]:
                # line crossing! record
                dic = {}
                # center of the last word of the previous line
                dic['p'] = RegDF.loc[ind,'line'];
                dic['p_x'] = (RegDF.loc[ind,'x1_pos'] + RegDF.loc[ind,'x2_pos'])/2.0; dic['p_y'] = (RegDF.loc[ind,'y1_pos'] + RegDF.loc[ind,'y2_pos'])/2.0
                # center of the first word of the next line
                dic['n'] = RegDF.loc[ind+1,'line'];
                dic['n_x'] = (RegDF.loc[ind+1,'x1_pos'] + RegDF.loc[ind+1,'x2_pos'])/2.0; dic['n_y'] = (RegDF.loc[ind+1,'y1_pos'] + RegDF.loc[ind+1,'y2_pos'])/2.0
                CrossLineInfo.append(dic)
    return CrossLineInfo 


# functions for lumping short fixations (< 50ms)
def lumpTwoFix(Df, ind1, ind2, direc, addtime):
    """
    lump two adjacent fixation data line (ind1 and ind2)
    direc = 1: next (ind1 < ind2); -1: previous (ind1 > ind2)
    Df as a data frame is mutable, no need to return Df
    """
    if direc == 1:
        if ind1 >= ind2:
            raise ValueError('Warning! Wrong direction in lumping!')
        # lump
        Df.loc[ind1,'end'] = Df.loc[ind2,'end']
        Df.loc[ind1,'duration'] = Df.loc[ind1,'end'] - Df.loc[ind1,'start'] + addtime # new duration
        Df.loc[ind1,'x_pos'] = (Df.loc[ind1,'x_pos'] + Df.loc[ind2,'x_pos'])/2.0; Df.loc[ind1,'y_pos'] = (Df.loc[ind1,'y_pos'] + Df.loc[ind2,'y_pos'])/2.0   # mean x_pos, mean y_pos
        Df.loc[ind1,'pup_size'] = (Df.loc[ind1,'pup_size'] + Df.loc[ind2,'pup_size'])/2.0  # mean pup_size
    elif direc == -1:
        if ind1 <= ind2:
            raise ValueError('Warning! Wrong direction in lumping!')
        # lump
        Df.loc[ind1,'start'] = Df.loc[ind2,'start']
        Df.loc[ind1,'duration'] = Df.loc[ind1,'end'] - Df.loc[ind1,'start'] + addtime # new duration
        Df.loc[ind1,'x_pos'] = (Df.loc[ind1,'x_pos'] + Df.loc[ind2,'x_pos'])/2.0; Df.loc[ind1,'y_pos'] = (Df.loc[ind1,'y_pos'] + Df.loc[ind2,'y_pos'])/2.0    # mean x_pos, mean y_pos
        Df.loc[ind1,'pup_size'] = (Df.loc[ind1,'pup_size'] + Df.loc[ind2,'pup_size'])/2.0   # mean pup_size
    

def lumpMoreFix(Df, ind, ind_list, addtime):
    """
    lump ind with inds in ind_list
    Df as a data frame is mutable, no need to return Df
    """
    Df.loc[ind,'end'] = Df.loc[ind_list[-1],'end']  # use the last one's ending time for the lumped ending time
    Df.loc[ind,'duration'] = Df.loc[ind,'end'] - Df.loc[ind,'start'] + addtime # new duration
    for item in ind_list:           
        Df.loc[ind,'x_pos'] += Df.loc[item,'x_pos']; Df.loc[ind,'y_pos'] += Df.loc[item,'y_pos']
        Df.loc[ind,'pup_size'] += Df.loc[item,'pup_size']
    Df.loc[ind,'x_pos'] /= float(len(ind_list)+1); Df.loc[ind,'y_pos'] /= float(len(ind_list)+1)  # mean x_pos, mean y_pos
    Df.loc[ind,'pup_size'] /= float(len(ind_list)+1)   # mean pup_size                    

    
def lumpFix(Df, endindex, short_index, addtime):
    """
    lump fixation
    arguments:
        Df -- fixation data for lumping 
        short_index -- list of index of fixation having short duration
        addtime -- adjusting time for duration, calculated based on sampling frequency
    return:
        Df -- although Df as a data frame is mutable, due to possible dropping and reindexing, we need to return Df
    """
    droplist = []; cur = 0
    while cur < len(short_index):
        if short_index[cur] == 0:
            # the first fixation
            # check the next one
            next_list = []; ind = cur + 1
            while ind < len(short_index) and short_index[ind] == short_index[ind-1]+1 and abs(Df.x_pos[short_index[ind]]-Df.x_pos[short_index[cur]]) <= ZN:
                # the next fixation is also a short fixation and within the zN distance                    
                next_list.append(short_index[ind]); ind += 1                
            
            if len(next_list) != 0:                
                lumpMoreFix(Df, short_index[cur], next_list, addtime)   # lump short_index[cur] and items in next_list
                # mark items in next_list for dropping
                for item in next_list:
                    droplist.append(item)                        
                # further check the next fixation!
                if Df.duration[short_index[cur]] <= LN:
                    if next_list[-1]+1 <= endindex and abs(Df.x_pos[short_index[cur]]-Df.x_pos[next_list[-1]+1]) <= ZN:
                        lumpTwoFix(Df, short_index[cur], next_list[-1]+1, 1, addtime)   # there are next item in Df and it can be further lumped together
                        droplist.append(next_list[-1]+1)    # mark next_list[-1]+1 for dropping
                # jump over these lumped ones
                cur += len(next_list)                
            else:
                # no consecutive short fixation for lumping, check the next one
                if short_index[cur]+1 <= endindex and abs(Df.x_pos[short_index[cur]]-Df.x_pos[short_index[cur]+1]) <= ZN:
                    lumpTwoFix(Df, short_index[cur], short_index[cur]+1, 1, addtime)    # lump short_index[cur] and short_index[cur]+1
                    droplist.append(short_index[cur]+1) # mark short_index[cur]+1 for dropping
                    
        elif short_index[cur] == endindex:
            # the last fixation, only check the previous one
            if not (short_index[cur]-1 in droplist) and abs(Df.x_pos[short_index[cur]]-Df.x_pos[short_index[cur]-1]) <= ZN:
                lumpTwoFix(Df, short_index[cur], short_index[cur]-1, -1, addtime)   # lump short_index[cur] and short_index[cur]-1
                droplist.append(short_index[cur]-1) # mark short_index[cur]-1 for dropping
                
        else:
            # check both next and previous fixation
            # check the next one
            next_list = []; ind = cur + 1
            while ind < len(short_index) and short_index[ind] == short_index[ind-1]+1 and abs(Df.x_pos[short_index[ind]]-Df.x_pos[short_index[cur]]) <= ZN:
                # the next fixation is also a short fixation and can be lumped together!                    
                next_list.append(short_index[ind]); ind += 1                
            if len(next_list) != 0:
                # lump short_index[cur] and items in next_list
                lumpMoreFix(Df, short_index[cur], next_list, addtime)# mark items in next_list for dropping
                for item in next_list:
                    droplist.append(item)
                    
                # further check the previous and next fixation!
                if Df.duration[short_index[cur]] <= LN:
                    dist_next, dist_prev = 0.0, 0.0
                    if next_list[-1]+1 <= endindex and not (next_list[-1]+1 in droplist) and abs(Df.x_pos[short_index[cur]]-Df.x_pos[next_list[-1]+1]) <= ZN:
                        dist_next = abs(Df.x_pos[short_index[cur]] - Df.x_pos[next_list[-1]+1])
                    if not (short_index[cur]-1 in droplist) and abs(Df.x_pos[short_index[cur]]-Df.x_pos[short_index[cur]-1]) <= ZN:
                        dist_prev = abs(Df.x_pos[short_index[cur]] - Df.x_pos[short_index[cur]-1])
                    
                    if dist_next != 0.0 and dist_prev == 0.0:                        
                        lumpTwoFix(Df, short_index[cur], next_list[-1]+1, 1, addtime)   # lump next                  
                        droplist.append(next_list[-1]+1)    # mark next_list[-1]+1 for dropping
                    elif dist_next == 0.0 and dist_prev != 0.0:                        
                        lumpTwoFix(Df, short_index[cur], short_index[cur]-1, -1, addtime)   # lump previous                       
                        droplist.append(short_index[cur]-1) # mark short_index[cur]-1 for dropping 
                    elif dist_next != 0.0 and dist_prev != 0.0:
                        if dist_next < dist_prev:
                            lumpTwoFix(Df, short_index[cur], next_list[-1]+1, 1, addtime)   # lump next first!
                            droplist.append(next_list[-1]+1)    # mark next_list[-1]+1 for dropping
                            # further check previous
                            if Df.duration[short_index[cur]] <= LN and abs(Df.x_pos[short_index[cur]]-Df.x_pos[short_index[cur]-1]) <= ZN:
                                lumpTwoFix(Df, short_index[cur], short_index[cur]-1, -1, addtime)   # lump previous                        
                                droplist.append(short_index[cur]-1)# mark short_index[cur]-1 for dropping
                        else:
                            lumpTwoFix(Df, short_index[cur], short_index[cur]-1, -1, addtime)   # lump previous first!                       
                            droplist.append(short_index[cur]-1) # mark short_index[cur]-1 for dropping
                            # further check next
                            if Df.duration[short_index[cur]] <= LN and abs(Df.x_pos[short_index[cur]]-Df.x_pos[next_list[-1]+1]) <= ZN:
                                lumpTwoFix(Df, short_index[cur], next_list[-1]+1, 1, addtime)   # lump next                    
                                droplist.append(next_list[-1]+1)    # mark next_list[-1]+1 for dropping            

                # jump over these lumped ones    
                cur += len(next_list)
            else:
                # check the previous and next fixation!
                dist_next, dist_prev = 0.0, 0.0
                if short_index[cur]+1 <= endindex and abs(Df.x_pos[short_index[cur]]-Df.x_pos[short_index[cur]+1]) <= ZN:
                    dist_next = abs(Df.x_pos[short_index[cur]] - Df.x_pos[short_index[cur]+1])
                if not (short_index[cur]-1 in droplist) and abs(Df.x_pos[short_index[cur]]-Df.x_pos[short_index[cur]-1]) <= ZN:
                    dist_prev = abs(Df.x_pos[short_index[cur]] - Df.x_pos[short_index[cur]-1])
                    
                if dist_next != 0.0 and dist_prev == 0.0:
                    lumpTwoFix(Df, short_index[cur], short_index[cur]+1, 1, addtime)    # lump next                    
                    droplist.append(short_index[cur]+1) # mark short_index[cur]+1 for dropping
                elif dist_next == 0.0 and dist_prev != 0.0:                    
                    lumpTwoFix(Df, short_index[cur], short_index[cur]-1, -1, addtime)   # lump previous
                    droplist.append(short_index[cur]-1) # mark short_index[cur]-1 for dropping
                elif dist_next != 0.0 and dist_prev != 0.0:
                    if dist_next < dist_prev:
                        lumpTwoFix(Df, short_index[cur], short_index[cur]+1, 1, addtime)    # lump next first!                   
                        droplist.append(short_index[cur]+1) # mark short_index[cur]+1 for dropping
                        # further check previous
                        if Df.duration[short_index[cur]] <= LN and abs(Df.x_pos[short_index[cur]] - Df.x_pos[short_index[cur]-1]) <= ZN:
                            lumpTwoFix(Df, short_index[cur], short_index[cur]-1, -1, addtime)   # lump previous
                            droplist.append(short_index[cur]-1)# mark short_index[cur]-1 for dropping
                    else:                        
                        lumpTwoFix(Df, short_index[cur], short_index[cur]-1, -1, addtime)   # lump previous first!                        
                        droplist.append(short_index[cur]-1) # mark short_index[cur]-1 for dropping
                        # further check next
                        if Df.duration[short_index[cur]] <= LN and abs(Df.x_pos[short_index[cur]] - Df.x_pos[short_index[cur]+1]) <= ZN:
                            lumpTwoFix(Df, short_index[cur], short_index[cur]+1, 1, addtime)    # lump next                  
                            droplist.append(short_index[cur]+1) # mark short_index[cur]+1 for dropping
        
        # after lumping or not, if short_index[cur]'s duration is still less than lN, delete it! 
        if Df.loc[short_index[cur],'duration'] <= LN:
            droplist.append(short_index[cur])            
        # move to next short fixation
        cur += 1    
    
    if droplist != []:
        # drop ind lumped to other inds, and reindex rows
        Df = Df.drop(droplist)                
        Df = Df.reset_index(drop=True)
    return Df


# functions for getting normal and crossline fixations
#def calCosDif(vect1, vect2):
#    """
#    calculate cosine differences of two vectors
#    arguments:
#        vect1, vect2 -- each is a list of two points' coordinates
#    """
#    return 1 - spatial.distance.cosine(vect1, vect2)
#
#
#def change2vect(data1, data2, cases):
#    """
#    change data into vector for calculating cosine difference
#    arguments:
#        data1, data2 -- dataframe or list
#        cases -- change methods:
#            1, data1 is crossline information
#            2, data1 is one row of Saccade data frame
#            3, data1 and data2 are two rows of Fixation data
#    """
#    if cases < 1 or cases > 3:
#        raise ValueError("change2Vect wrong cases option!")
#    if cases == 1:
#        # crossline information
#        return [data1['p_x'], data1['p_y'], data1['n_x'], data1['n_y']]        
#    elif cases == 2:
#        # Saccade data frame
#        return [data1['x2_pos'], data1['y2_pos'], data1['x1_pos'], data1['x1_pos']]    
#    elif cases == 3:
#        # Fixation data
#        return [data1['x_pos'], data1['y_pos'], data2['x_pos'], data2['y_pos']]


#def getCrosslineFix(CrossLineInfo, startline, endline, Df):
#    """
#    collect all cross-line fixations in lines
#    arguments:
#        CrossLineInfo -- cross line information from region file
#        startline -- search starting line
#        endline -- search ending line
#        Df -- fixation data frame
#    return:
#        lines -- list of turples storing cross-line fixations
#        curline -- the current line in Df
#    """
#    lines = []; curline = startline; ind = 0    # curline records the current Fix data, ind records the current CrossLineInfo
#    while ind < len(CrossLineInfo):
#        curCross = CrossLineInfo[ind]
#        FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])    # set up the maximum fixation distance to be identified as a cross-line fixation
#        nextline = curline + 1
#        while nextline < endline-1 and np.absolute(Df.x_pos[curline] - Df.x_pos[nextline]) < FixDistThres and np.absolute(Df.y_pos[curline] - Df.y_pos[nextline]) < Y_RANGE:
#            curline = nextline; nextline = curline + 1
#        if nextline < endline:
#            # find a possible cross-line fixation
#            if Df.x_pos[curline] - Df.x_pos[nextline] >= FixDistThres:
#                # record forward cross-line fixation
#                lines.append((1, curCross['p'], curCross['n'], nextline))
#                # move curCross to the next
#                if ind < len(CrossLineInfo) - 1:
#                    ind += 1; curCross = CrossLineInfo[ind]; FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])
#                else:
#                    break
#            elif Df.x_pos[curline] - Df.x_pos[nextline] <= -FixDistThres:
#                # move curCross to the back
#                if ind > 0:
#                    ind -= 1; curCross = CrossLineInfo[ind]; FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])
#                # record backward cross-line fixation using previous curCross
#                lines.append((-1, curCross['n'], curCross['p'], nextline))
#            elif Df.x_pos[nextline] - Df.x_pos[curline] < 0 and Df.y_pos[nextline] - Df.y_pos[curline] >= Y_RANGE and Df.y_pos[nextline] - Df.y_pos[curline] <= Y_RANGE_RATIO*Y_RANGE:
#                # record forward cross-line fixation
#                lines.append((1, curCross['p'], curCross['n'], nextline))
#                # move curCross to the next
#                if ind < len(CrossLineInfo) - 1:
#                    ind += 1; curCross = CrossLineInfo[ind]; FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])
#                else:
#                    break
#                # keep moving ahead curline until finding a forward fixation
#                curline += 1; nextline = curline + 1
#                while nextline < endline-1 and Df.x_pos[nextline] - Df.x_pos[curline] < 0:
#                    curline += 1; nextline = curline + 1
#                curline -= 1            
#        curline += 1
#        if curline >= endline - 1:
#            break
#    # check whether the last recorded line is the forward crossing to the last line in the paragraph
#    question = False    
#    if lines[-1][0] == -1 or lines[-1][2] != CrossLineInfo[-1]['n']:
#        print 'Warning! crlFix do not cover all lines!'
#        question = True
#    
#    return lines, curline, question


def mergeFixLines(startline, endline, Df):
    """
    merge continuous rightward and leftward fixations
    arguments:
        startline -- search starting line
        endline -- search ending line
        Df -- fixation data frame
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
    
    
def getCrosslineFix(CrossLineInfo, startline, endline, Df):
    """
    collect all cross-line fixations in lines
    arguments:
        CrossLineInfo -- cross line information from region file
        startline -- search starting line
        endline -- search ending line
        Df -- fixation data frame
    return:
        lines -- list of turples storing cross-line fixations
        curline -- the current line in Df
    """
    # merge rightward fixations and leftward fixations
    lines = []; mergelines = mergeFixLines(startline, endline, Df)    
    curline, ind = 0, 0 # curline records the current mergeline Fix data, ind records the current CrossLineInfo
    while ind < len(CrossLineInfo):
        curCross = CrossLineInfo[ind]; FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])    # set up the maximum fixation distance to be identified as a cross-line fixation
        if mergelines[curline][3] == 0 and mergelines[curline][2] >= FixDistThres and Df.loc[mergelines[curline][0],'x_pos'] <= curCross['n_x'] + FRONT_RANGE_RATIO*(curCross['p_x'] - curCross['n_x']):
            if ind != 0:
                # rightward backward crossline fixation
                # move curCross to the back
                if ind > 0:
                    ind -= 1; curCross = CrossLineInfo[ind]; FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])
                # record backward cross-line fixation using previous curCross
                lines.append((-1, curCross['n'], curCross['p'], mergelines[curline][1]))
        if mergelines[curline][3] == 1 and mergelines[curline][2] <= -FixDistThres:
            # leftward forward crossline fixation
            # further check which fixation is the start of the next line
            # two criteria: 1) find the first fixation having a big x value change 
            stl1 = mergelines[curline][1]
            for nextl in range(mergelines[curline][0]+1,mergelines[curline][1]+1):
                if Df.loc[nextl,'x_pos'] - Df.loc[nextl-1,'x_pos'] <=- FixDistThres:
                    stl1 = nextl
                    break
            # 2) find the fixation having the biggest y value change     
            stl2 = mergelines[curline][1]; bigY = 0
            for nextl in range(mergelines[curline][0]+1,mergelines[curline][1]+1):
                if Df.loc[nextl,'y_pos'] - Df.loc[nextl-1,'y_pos'] > bigY:
                    bigY = Df.loc[nextl,'y_pos'] - Df.loc[nextl-1,'y_pos']; stl2 = nextl
            # compare stline1 and stline2
            lines.append((1, curCross['p'], curCross['n'], min(stl1,stl2)))
            # move curCross to the next
            if ind < len(CrossLineInfo) - 1:
                ind += 1; curCross = CrossLineInfo[ind]; FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])
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


def getFixLine(RegDF, crlSac, FixDF):
    """
    add line information for each FixDF
    arguments:
        RegDF -- region file data frame (with line information)
        crlSac -- data frame storing identified cross line saccades
        FixDF -- saccade data of the trial
    return:
        newlineFix -- cross line fixations: previous fixation is in previous line, current fixation is in next line
    FixDF as a data frame is mutable, no need to return    
    """
    CrossLineInfo = getCrossLineInfo(RegDF, FixDF.trial_type[0].split('_')[0])    # get cross line information
    question = False
    
    if len(np.unique(FixDF.eye)) == 1 and (np.unique(FixDF.eye)[0] == 'L' or np.unique(FixDF.eye)[0] == 'R'):
        # single eye data
        if FIX_METHOD == 'DIFF':
            # method 1: based on difference in x_axis
            lines, curline, question = getCrosslineFix(CrossLineInfo, 0, len(FixDF), FixDF)        
            endline = len(FixDF)        
            if curline < len(FixDF):
                # there are remaining lines, check whether there are backward cross-line fixation
                curCross = CrossLineInfo[-1]; FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])
                nextline = curline + 1
                while nextline < len(FixDF) and FixDF.x_pos[curline] - FixDF.x_pos[nextline] > -FixDistThres and FixDF.y_pos[curline] - FixDF.y_pos[nextline] <= Y_RANGE:
                    curline = nextline; nextline = curline + 1
                if nextline < len(FixDF):
                    endline = nextline                
            # mark crossline saccade as prevline_nextline
            curlow = 0    
            for ind in range(len(lines)):
                curline = lines[ind]
                for line in range(curlow, curline[3]):
                    FixDF.loc[line,'line'] = curline[1]
                curlow = curline[3]
            for line in range(curlow, endline):
                FixDF.loc[line,'line'] = lines[-1][2]        
        elif FIX_METHOD == 'SAC':
            # method 2: based on crosslineSac
            lines = []            
            curlow = 0
            for ind in range(len(crlSac)):
                curup = curlow + 1
                while FixDF.end[curup] <= crlSac.start[ind]:
                    curup += 1
                start = crlSac.loc[ind,'startline']; end = crlSac.loc[ind,'endline']
                if start < end:
                    direction = 1
                else:
                    direction = -1
                lines.append([direction, start, end, curup])    
                for line in range(curlow, curup):
                    FixDF.loc[line,'line'] = crlSac.loc[ind,'startline']
                curlow = curup
            for line in range(curlow, len(FixDF)):
                FixDF.loc[line,'line'] = crlSac.loc[ind,'endline']        
    else:
        # double eye data
        numLeft = len(FixDF[FixDF.eye == 'L']); numRight = len(FixDF[FixDF.eye == 'R']) 
        if FIX_METHOD == 'DIFF':
            # method 1: based on differences in x_axis 
            # first, left eye data
            lines_Left, curline_Left, ques1 = getCrosslineFix(CrossLineInfo, 0, numLeft, FixDF)        
            endline_Left = numLeft 
            if curline_Left < numLeft:
                # there are remaining lines, check whether there are backward cross-line fixation
                curCross = CrossLineInfo[-1]; FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])
                nextline = curline_Left + 1
                while nextline < numLeft and (FixDF.loc[curline_Left, 'x_pos'] - FixDF.loc[nextline,'x_pos']) > -FixDistThres and FixDF.loc[curline_Left,'y_pos'] - FixDF.loc[nextline,'y_pos'] <= Y_RANGE:
                    curline_Left = nextline; nextline = curline_Left + 1
                if nextline < numLeft:
                    endline_Left = nextline
            # mark crossline saccade as prevline_nextline
            curlow = 0    
            for ind in range(len(lines_Left)):
                curline = lines_Left[ind]
                for line in range(curlow, curline[3]):
                    FixDF.loc[line,'line'] = curline[1]
                curlow = curline[3]
            for line in range(curlow, endline_Left):
                FixDF.loc[line,'line'] = lines_Left[ind-1][2]
            # second, right eye data
            lines_Right, curline_Right, ques2 = getCrosslineFix(CrossLineInfo, numLeft, numLeft + numRight, FixDF)                
            endline_Right = numLeft + numRight
            if curline_Right < numLeft + numRight:
                # there are remaining lines, check whether there are backward cross-line fixation
                curCross = CrossLineInfo[-1]; FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])
                nextline = curline_Right + 1
                while nextline < numLeft + numRight and (FixDF.loc[curline_Right,'x_pos'] - FixDF.loc[nextline,'x_pos']) > -FixDistThres and FixDF.loc[curline_Right,'y_pos'] - FixDF.loc[nextline,'y_pos'] <= Y_RANGE:
                    curline_Right = nextline; nextline = curline_Right + 1
                if nextline < numLeft + numRight:
                    endline_Right = nextline                
            # mark crossline saccade as prevline_nextline        
            curlow = numLeft
            for ind in range(len(lines_Right)):
                curline = lines_Right[ind]
                for line in range(curlow, curline[3]):
                    FixDF.loc[line,'line'] = curline[1]
                curlow = curline[3]
            for line in range(curlow, endline_Right):
                FixDF.loc[line,'line'] = lines_Right[-1][2]
        
            lines = lines_Left + lines_Right
            if ques1 or ques2:
                question = True
        elif FIX_METHOD == 'SAC':
            # method 2: based on crosslineSac
            lines = []
            curlow = 0
            for ind in range(len(crlSac)):
                if crlSac.eye[ind] == 'L':
                    curup = curlow + 1
                    while FixDF.loc[curup,'eye'] == 'L' and FixDF.loc[curup,'end'] <= crlSac.loc[ind,'start']:
                        curup += 1
                    start = crlSac.loc[ind,'startline']; end = crlSac.loc[ind,'endline']
                    if start < end:
                        direction = 1
                    else:
                        direction = -1
                    lines.append([direction, start, end, curup])     
                    for line in range(curlow, curup):
                        FixDF.loc[line,'line'] = crlSac.loc[ind,'startline']
                    curlow = curup
            for line in range(curlow, numLeft):
                FixDF.loc[line,'line'] = crlSac.loc[ind,'endline']

            curlow = numLeft
            for ind in range(len(crlSac)):
                if crlSac.eye[ind] == 'R':
                    curup = curlow + 1
                    while FixDF.loc[curup,'eye'] == 'R' and FixDF.loc[curup,'end'] <= crlSac.loc[ind,'start']:
                        curup += 1
                    start = crlSac.loc[ind,'startline']; end = crlSac.loc[ind,'endline']
                    if start < end:
                        direction = 1
                    else:
                        direction = -1
                    lines.append([direction, start, end, curup])       
                    for line in range(curlow, curup):
                        FixDF.loc[line,'line'] = crlSac.loc[ind,'startline']
                    curlow = curup
            for line in range(curlow, numLeft + numRight):
                FixDF.loc[line,'line'] = crlSac.loc[ind,'endline']
    
    return lines, question
         

def getcrlFix(RegDF, crlSac, FixDF):
    """
    get crossline Fix
    arguments:
        RegDF -- region file data frame
        crlSac -- crossline saccades
        FixDF -- fixation data of the trial
    return:
        crlFix -- crossline fixations of the trial
    FixDF is mutable, no need to return
    """                   
    # Second, get line information of each fixation
    lines, question = getFixLine(RegDF, crlSac, FixDF)
    
    crlFix = pd.DataFrame(np.zeros((len(lines), 13)))
    crlFix.columns = ['subj', 'trial_id', 'eye', 'startline', 'endline', 'FixlineIndex', 'start', 'end', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid']
    crlFix.subj = FixDF.subj[0]; crlFix.trial_id = FixDF.trial_id[0]
    cur = 0    
    for item in lines:
        curFix = FixDF.loc[item[3]]
        crlFix.loc[cur,'eye'] = curFix.eye
        crlFix.loc[cur,'startline'] = item[1]; crlFix.loc[cur,'endline'] = item[2]; crlFix.loc[cur,'FixlineIndex'] = item[3]
        crlFix.loc[cur,'start'] = curFix.start; crlFix.loc[cur,'end'] = curFix.end; crlFix.loc[cur,'duration'] = curFix.duration; 
        crlFix.loc[cur,'x_pos'] = curFix.x_pos; crlFix.loc[cur,'y_pos'] = curFix.y_pos
        crlFix.loc[cur,'pup_size'] = curFix.pup_size; crlFix.loc[cur,'valid'] = curFix['valid']        
        cur += 1
        
    return crlFix, question    


def recFix(RegDF, ExpType, trialID, blinklines, fixlines, sampfreq, eyerec, script, sessdate, srcfile, tdur):
    """
    get fixation data from trials
    arguments:
        RegDF -- region file data frame
        ExpType -- type of experiments: 'RAN', 'RP'        
        trailID -- trail ID of the data
        blinklines -- blink lines of a trial
        fixlines -- fix lines of a trial
        sampfreq -- sampling frequency (to calculate amending time for duration)
        eyerec -- eye recorded ('R', 'L' or 'LR')
        script -- script file
        sessdate -- session date
        srcfile -- source file
        tdur -- estimated trial duration        
    return:
        FixDF -- fixation data of the trial
    """            
    blink_number, fix_number = len(blinklines), len(fixlines)
    addtime = 1/float(sampfreq) * 1000
    
    # First, record and lump fixations 
    if eyerec == 'L' or eyerec == 'R':
        # only left or right eye data are recorded
        FixDF = pd.DataFrame(np.zeros((fix_number, 18)))
        FixDF.columns = ['subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'tdur', 'blinks', 'eye', 'start', 'end', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid', 'line']
        FixDF.subj = srcfile.split('.')[0]; FixDF.trial_id = int(trialID)
        FixDF.trial_type = ExpType + '_' + RegDF.Name[0]; FixDF.sampfreq = int(sampfreq); FixDF.script = script; FixDF.sessdate = sessdate; FixDF.srcfile = srcfile; FixDF.tdur = tdur; FixDF.blinks = int(blink_number)
    
        FixDF.eye = [line[1] for line in fixlines]; FixDF.start = [float(line[2]) for line in fixlines]; FixDF.end = [float(line[3]) for line in fixlines]; FixDF.duration = [float(line[4]) for line in fixlines]
        FixDF.x_pos = [float(line[5]) for line in fixlines]; FixDF.y_pos = [float(line[6]) for line in fixlines]; FixDF.pup_size = [float(line[7]) for line in fixlines]
        
        FixDF['valid'] = 'yes'
        if not RECFINAL:
            FixDF.loc[fix_number-1,'valid'] = 'no' 

        # lump fixations        
        # get indices of candidate fixations for lumping, whose durations <= lN
        short_index = []
        for ind in range(fix_number):
            if FixDF.loc[ind,'duration'] <= LN and FixDF.loc[ind,'valid'] == 'yes':
                short_index.append(ind)        
        # check each short fixation for lumping        
        if not RECFINAL:
            endindex = fix_number - 2   # the upperbound of searching range, excluding the last one!
        else:            
            endindex = fix_number - 1   # the upperbound of searching range
        # lump data    
        FixDF = lumpFix(FixDF, endindex, short_index, addtime)       

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
            FixDF1 = pd.DataFrame(np.zeros((numLeft, 17)))
            FixDF1.columns = ['subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'blinks', 'eye', 'start', 'end', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid', 'line']
            FixDF1.subj = srcfile.split('.')[0]; FixDF1.trial_id = int(trialID)
            FixDF1.trial_type = ExpType + '_' + RegDF.Name[0]; FixDF1.sampfreq = int(sampfreq); FixDF1.script = script; FixDF1.sessdate = sessdate; FixDF1.srcfile = srcfile; FixDF1.blinks = int(blink_number)
            
            cur = 0
            for line in fixlines:
                if line[1] == 'L':
                    FixDF1.loc[cur,'eye'] = line[1]; FixDF1.loc[cur,'start'] = float(line[2]); FixDF1.loc[cur,'end'] = float(line[3]); FixDF1.loc[cur,'duration'] = float(line[4])
                    FixDF1.loc[cur,'x_pos'] = float(line[5]); FixDF1.loc[cur,'y_pos'] = float(line[6]); FixDF1.loc[cur,'pup_size'] = float(line[7])
                    cur += 1
            
            FixDF1['valid'] = 'yes'
            if not RECFINAL and lastLR == 'L':
                FixDF1.loc[numLeft-1,'valid'] = 'no'     
            
            # lump fixations
            short_index1 = []
            for ind in range(numLeft):
                if FixDF1.loc[ind,'duration'] <= LN and FixDF1.loc[ind,'valid'] == 'yes':
                    short_index1.append(ind)
            # check each short fixation for lumping        
            if not RECFINAL:
                if numLeft == fix_number:
                    endindex1 = fix_number - 2   # all fixations are left eyes, the upperbound of searching range, excluding the last one!                    
                else:                    
                    endindex1 = numLeft - 1  # the upperbound of searching range
            else:
                endindex1 = numLeft - 1
            # lump data        
            FixDF1 = lumpFix(FixDF1, endindex1, short_index1, addtime)               
        
        if numRight != 0:
            FixDF2 = pd.DataFrame(np.zeros((numRight, 17)))
            FixDF2.columns = ['subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'blinks', 'eye', 'start', 'end', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid', 'line']
            FixDF2.subj = srcfile.split('.')[0]; FixDF2.trial_id = int(trialID)
            FixDF2.trial_type = ExpType + '_' + RegDF.Name[0]; FixDF2.sampfreq = int(sampfreq); FixDF2.script = script; FixDF2.sessdate = sessdate; FixDF2.srcfile = srcfile; FixDF2.blinks = int(blink_number)

            cur = 0        
            for line in fixlines:
                if line[1] == 'R':
                    FixDF2.loc[cur,'eye'] = line[1]; FixDF2.loc[cur,'start'] = float(line[2]); FixDF2.loc[cur,'end'] = float(line[3]); FixDF2.loc[cur,'duration'] = float(line[4])
                    FixDF2.loc[cur,'x_pos'] = float(line[5]); FixDF2.loc[cur,'y_pos'] = float(line[6]); FixDF2.loc[cur,'pup_size'] = float(line[7])
                    cur += 1
            
            FixDF2['valid'] = 'yes'
            if not RECFINAL and lastLR == 'R':
                FixDF2.loc[numRight-1,'valid'] = 'no'     
        
            # lump fixation
            short_index2 = []
            for ind in range(numRight):
                if FixDF2.loc[ind,'duration'] <= LN and FixDF2.loc[ind,'valid'] == 'yes':
                    short_index2.append(ind)
            # check each short fixation for lumping        
            if not RECFINAL:
                if numRight == fix_number:                     
                    endindex2 = fix_number - 2  # all fixations are right eyes, the upperbound of searching range, excluding the last one!
                else:                
                    endindex2 = numRight - 1 # the upperbound of searching range
            else:
                endindex2 = numRight - 1                
            # lump data        
            FixDF2 = lumpFix(FixDF2, endindex2, short_index2, addtime) 
        
        # merge all data
        FixDF = pd.DataFrame(columns=('trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'blinks', 'eye', 'start', 'end', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid'))        
        if numLeft != 0:
            FixDF = FixDF.append(FixDF1, ignore_index=True)
        if numRight != 0:
            FixDF = FixDF.append(FixDF2, ignore_index=True)
    
    # check validity of fixations after possible lumping
    for ind in range(len(FixDF)):
        if FixDF.loc[ind,'duration'] < MN:
            FixDF.loc[ind,'valid'] = 'no'
    
    return FixDF
           

# functions for getting normal and crossline saccades    
#def getCrosslineSac(CrossLineInfo, startline, endline, Df):
#    """
#    collect all cross-line saccades in lines
#    arguments:
#        CrossLineInfo -- cross line information from region file
#        startline -- search starting line
#        endline -- search ending line
#        Df -- saccade data frame
#    return:
#        lines -- list of turples storing cross-line fixations
#        curline -- last line after searching crossline saccade
#        question -- whether there is a problem in the data
#    """
#    lines = []; curline = startline; ind = 0    # curline records the current Fix data, ind records the current CrossLineInfo
#    while ind < len(CrossLineInfo):
#        curCross = CrossLineInfo[ind]
#        FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])    # set up the maximum fixation distance to be identified as a cross-line fixation
#        while curline < endline-1 and np.absolute(Df.x1_pos[curline] - Df.x2_pos[curline]) < FixDistThres and np.absolute(Df.y1_pos[curline] - Df.y2_pos[curline]) < Y_RANGE:
#            curline += 1
#        if curline < endline:
#            # find a cross-line fixation
#            if Df.x1_pos[curline] - Df.x2_pos[curline] >= FixDistThres:
#                # record forward cross-line fixation
#                lines.append((1, curCross['p'], curCross['n'], curline))
#                # move curCross to the next
#                if ind < len(CrossLineInfo) - 1:
#                    ind += 1; curCross = CrossLineInfo[ind]; FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])
#                else:
#                    break
#            elif Df.x1_pos[curline] - Df.x2_pos[curline] <= -FixDistThres:
#                # move curCross to the back
#                if ind > 0:
#                    ind -= 1; curCross = CrossLineInfo[ind]; FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])
#                # record backward cross-line fixation using previous curCross
#                lines.append((-1, curCross['n'], curCross['p'], curline))
#            elif Df.x2_pos[curline] - Df.x1_pos[curline] < 0 and Df.y2_pos[curline] - Df.y1_pos[curline] >= Y_RANGE and Df.y2_pos[curline] - Df.y1_pos[curline] <= Y_RANGE_RATIO*Y_RANGE:
#                # record forward cross-line fixation
#                lines.append((1, curCross['p'], curCross['n'], curline))
#                # move curCross to the next
#                if ind < len(CrossLineInfo) - 1:
#                    ind += 1; curCross = CrossLineInfo[ind]; FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])
#                else:
#                    break
#                # keep moving ahead curline until finding a non-crossline fixation
#                curline += 1
#                while curline < endline-1 and Df.x2_pos[curline] - Df.x1_pos[curline] < 0:
#                    curline += 1
#                curline -= 1
#        curline += 1
#        if curline >= endline:
#            break
#        
#    # check whether the last recorded line is the forward crossing to the last line in the paragraph
#    question = False
#    if lines[-1][0] == -1 or lines[-1][2] != CrossLineInfo[-1]['n']:
#        print 'Warning! crlSac do not cover all lines!'
#        question = True
#        
#    return lines, curline, question

def mergeSacLines(startline, endline, Df):
    """
    merge continuous rightward and leftward fixations
    arguments:
        startline -- search starting line
        endline -- search ending line
        Df -- fixation data frame
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
    
    
def getCrosslineSac(CrossLineInfo, startline, endline, Df):
    """
    collect all cross-line fixations in lines
    arguments:
        CrossLineInfo -- cross line information from region file
        startline -- search starting line
        endline -- search ending line
        Df -- fixation data frame
    return:
        lines -- list of turples storing cross-line fixations
        curline -- the current line in Df
    """
    # merge rightward fixations and leftward fixations
    lines = []; mergelines = mergeSacLines(startline, endline, Df)    
    curline, ind = 0, 0 # curline records the current mergeline Fix data, ind records the current CrossLineInfo
    while ind < len(CrossLineInfo):
        curCross = CrossLineInfo[ind]; FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])    # set up the maximum fixation distance to be identified as a cross-line fixation
        if mergelines[curline][3] == 0 and mergelines[curline][2] >= FixDistThres and Df.loc[mergelines[curline][0],'x1_pos'] <= curCross['n_x'] + FRONT_RANGE_RATIO*(curCross['p_x'] - curCross['n_x']):
            if ind != 0:
                # rightward backward crossline fixation
                # move curCross to the back
                if ind > 0:
                    ind -= 1; curCross = CrossLineInfo[ind]; FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])
                # record backward cross-line fixation using previous curCross
                lines.append((-1, curCross['n'], curCross['p'], mergelines[curline][1]))
        if mergelines[curline][3] == 1 and mergelines[curline][2] <= -FixDistThres:
            # leftward forward crossline fixation
            # further check which fixation is the start of the next line
            # two criteria: 1) find the first fixation having a big x value change 
            stl1 = mergelines[curline][1]
            for nextl in range(mergelines[curline][0]+1,mergelines[curline][1]+1):
                if Df.loc[nextl,'x2_pos'] - Df.loc[nextl,'x1_pos'] <=- FixDistThres:
                    stl1 = nextl
                    break
            # 2) find the fixation having the biggest y value change     
            stl2 = mergelines[curline][1]; bigY = 0
            for nextl in range(mergelines[curline][0]+1,mergelines[curline][1]+1):
                if Df.loc[nextl,'y2_pos'] - Df.loc[nextl,'y1_pos'] > bigY:
                    bigY = Df.loc[nextl,'y2_pos'] - Df.loc[nextl,'y1_pos']; stl2 = nextl
            # compare stline1 and stline2
            lines.append((1, curCross['p'], curCross['n'], min(stl1,stl2)))
            # move curCross to the next
            if ind < len(CrossLineInfo) - 1:
                ind += 1; curCross = CrossLineInfo[ind]; FixDistThres = FIXDIFF_RATIO*(curCross['p_x'] - curCross['n_x'])
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

       
def getSacLine(RegDF, SacDF):
    """
    add line information for each SacDF
    arguments:
        RegDF -- region file data frame
        SacDF -- saccade data of the trial
    return:
        lines -- crossline information
    SacDF as a data frame is mutable, no need to return    
    """
    CrossLineInfo = getCrossLineInfo(RegDF, SacDF.trial_type[0].split('_')[0])    # get cross line information
    question = False
   
    if len(np.unique(SacDF.eye)) == 1 and (np.unique(SacDF.eye)[0] == 'L' or np.unique(SacDF.eye)[0] == 'R'):
        # single eye data
        lines, curline, question = getCrosslineSac(CrossLineInfo, 0, len(SacDF), SacDF)        
        # mark crossline saccade as prevline_nextline    
        for ind in range(len(lines)):
            curline = lines[ind]
            crossline = str(curline[1])+'_'+str(curline[2])
            SacDF.loc[curline[3],'line'] = crossline
    else:
        # double eye saccade data
        numLeft = len(SacDF[SacDF.eye == 'L']); numRight = len(SacDF[SacDF.eye == 'R'])        
        # first, left eye saccade
        lines_Left, curline, ques1 = getCrosslineSac(CrossLineInfo, 0, numLeft, SacDF)
        # mark crossline saccade as prevline_nextline    
        for ind in range(len(lines_Left)):
            curline = lines_Left[ind]
            crossline = str(curline[1])+'_'+str(curline[2])
            SacDF.loc[curline[3],'line'] = crossline
        # second, right eye saccade
        lines_Right, curline, ques2 = getCrosslineSac(CrossLineInfo, numLeft, numLeft + numRight, SacDF)
        # mark crossline saccade as prevline_nextline    
        for ind in range(len(lines_Right)):
            curline = lines_Right[ind]
            crossline = str(curline[1])+'_'+str(curline[2])
            SacDF.loc[curline[3],'line'] = crossline            
        lines = lines_Left + lines_Right
        if ques1 or ques2:
            question = True
    
    return lines, question        


def getcrlSac(RegDF, SacDF):
    """
    get crossline Sac
    arguments:
        RegDF -- region file data frame
        SacDFtemp -- saccade data of the trial
    return:
        crlSac -- crossline saccades of the trial
    SacDF is mutable, no need to return
    """            
    lines, question = getSacLine(RegDF, SacDF)   # get line information of each saccade
    
    crlSac = pd.DataFrame(np.zeros((len(lines), 15)))
    crlSac.columns = ['subj', 'trial_id', 'eye', 'startline', 'endline', 'SaclineIndex', 'start', 'end', 'duration', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos', 'ampl', 'pk']
    crlSac.subj = SacDF.subj[0]; crlSac.trial_id = SacDF.trial_id[0]
    cur = 0    
    for item in lines:
        curSac = SacDF.loc[item[3]]
        crlSac.loc[cur,'eye'] = curSac.eye
        crlSac.loc[cur,'startline'] = item[1]; crlSac.loc[cur,'endline'] = item[2]; crlSac.loc[cur,'SaclineIndex'] = item[3]
        crlSac.loc[cur,'start'] = curSac.start; crlSac.loc[cur,'end'] = curSac.end; crlSac.loc[cur,'duration'] = curSac.duration; 
        crlSac.loc[cur,'x1_pos'] = curSac.x1_pos; crlSac.loc[cur,'y1_pos'] = curSac.y1_pos
        crlSac.loc[cur,'x2_pos'] = curSac.x2_pos; crlSac.loc[cur,'y2_pos'] = curSac.y2_pos
        crlSac.loc[cur,'ampl'] = curSac.ampl; crlSac.loc[cur,'pk'] = curSac.pk        
        cur += 1 
    
    return crlSac, question    


def recSac(RegDF, ExpType, trialID, blinklines, saclines, sampfreq, eyerec, script, sessdate, srcfile, tdur):
    """
    record saccade data from trials
    arguments:
        RegDF -- region file dataframe
        ExpType -- type of experiments: 'RAN', 'RP'
        trailID -- trail ID of the data
        blinklines -- blink lines of a trial
        salines -- saccade lines of a trial
        sampfreq -- sampling frequency (to calculate amending time for duration)
        eyerec -- eye recorded ('R', 'L' or 'LR')        
        script -- script file
        sessdate -- session date
        srcfile -- source file
        tdur -- estimated trial duration
    return:
        SacDF -- saccade data of the trial
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
    
    SacDF = pd.DataFrame(np.zeros((sac_number, 20)))
    SacDF.columns = ['subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'tdur', 'blinks', 'eye', 'start', 'end', 'duration', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos', 'ampl', 'pk', 'line']
    SacDF.subj = srcfile.split('.')[0]; SacDF.trial_id = int(trialID); 
    SacDF.trial_type = ExpType + '_' + RegDF.Name[0]; SacDF.sampfreq = int(sampfreq); SacDF.script = script; SacDF.sessdate = sessdate; SacDF.srcfile = srcfile; SacDF.tdur = tdur; SacDF.blinks = int(blink_number)

    if eyerec == 'L' or eyerec == 'R':
        # single eye saccade
        SacDF.eye = [line[1] for line in saclines]; SacDF.start = [float(line[2]) for line in saclines]; SacDF.end = [float(line[3]) for line in saclines]; SacDF.duration = [float(line[4]) for line in saclines]
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
                SacDF.loc[cur,'eye'] = line[1]; SacDF.loc[cur,'start'] = float(line[2]); SacDF.loc[cur,'end'] = float(line[3]); SacDF.loc[cur,'duration'] = float(line[4])
                SacDF.loc[cur,'x1_pos'] = float(line[5]); SacDF.loc[cur,'y1_pos'] = float(line[6])
                SacDF.loc[cur,'x2_pos'] = float(line[7]); SacDF.loc[cur,'y2_pos'] = float(line[8])
                SacDF.loc[cur,'ampl'] = float(line[9]); SacDF.loc[cur,'pk'] = float(line[10])
                cur += 1
        for line in saclines:
            if line[1] == 'R':
                SacDF.loc[cur,'eye'] = line[1]; SacDF.loc[cur,'start'] = float(line[2]); SacDF.loc[cur,'end'] = float(line[3]); SacDF.loc[cur,'duration'] = float(line[4])
                SacDF.loc[cur,'x1_pos'] = float(line[5]); SacDF.loc[cur,'y1_pos'] = float(line[6])
                SacDF.loc[cur,'x2_pos'] = float(line[7]); SacDF.loc[cur,'y2_pos'] = float(line[8])
                SacDF.loc[cur,'ampl'] = float(line[9]); SacDF.loc[cur,'pk'] = float(line[10])
                cur += 1                   
    
    return SacDF            
   

# main function for getting saccades and fixations
def rec_Sac_Fix(direct, datafile, regfileNameList, ExpType):
    """
    read EMF file and extract the saccade and fixation data
    arguments:
        direct -- directory for storing output files
        datafile -- EMF ascii file name
        regionfileNameList -- a list of region file names (trial_id will help select corresponding region files)
        ExpType -- type of experiments: 'RAN', 'RP'
    output:
        SacDF -- saccade data in different trials
        FixDF -- fixation data in different trials
    """    
    f = open(datafile, 'r'); print "Read ASC: ", f.name; lines = f.readlines(); f.close()   # read EMF file    
    script, sessdate, srcfile = getHeader(lines)    # get header lines    
    T_idx, T_lines = getTrialReg(lines) # get trial regions
    
    SacDF = pd.DataFrame(columns=('subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'tdur', 'blinks', 'eye', 'start', 'end', 'duration', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos', 'ampl', 'pk', 'line'))
    FixDF = pd.DataFrame(columns=('subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'tdur', 'blinks', 'eye', 'start', 'end', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid', 'line'))        
    
    for ind in range(len(T_lines)):
        triallines = lines[T_lines[ind,0]+1:T_lines[ind,1]]; trialID = int(T_idx[ind,0].split(' ')[-1])
        blinklines, fixlines, saclines, sampfreq, eyerec = getBlink_Fix_Sac_SampFreq_EyeRec(triallines); tdur = gettdur(triallines)
        RegDF = getRegDF(regfileNameList, trialID)  # get region file
        # read saccade data
        print "Read Sac: Trial ", str(trialID)
        SacDFtemp = recSac(RegDF, ExpType, trialID, blinklines, saclines, sampfreq, eyerec, script, sessdate, srcfile, tdur)
        SacDF = SacDF.append(SacDFtemp, ignore_index=True)
        # read fixation data
        print "Read Fix: Trial ", str(trialID)
        FixDFtemp = recFix(RegDF, ExpType, trialID, blinklines, fixlines, sampfreq, eyerec, script, sessdate, srcfile, tdur)        
        FixDF = FixDF.append(FixDFtemp, ignore_index=True)
    
    resName = direct + '/' + srcfile.split('.')[0]
    SacDF.to_csv(resName + '_Sac.csv', index=False); FixDF.to_csv(resName + '_Fix.csv', index=False)


def rec_Sac_Fix_Batch(direct, regfileNameList, ExpType):
    """
    batch processing of all subjects' fixation and saccade data
    arguments:
        direct -- directory containing all asc files
        regfileNameList -- a list of region file names (trial_id will help select corresponding region files)
        ExpType -- type of experiments: 'RAN', 'RP'
    output:
        FixDF -- fixation data in different trials of different subjects
        SacDF -- saccade data in different trials of different subjects
    """
    ascfiles = []
    for file in os.listdir(direct):
        if fnmatch.fnmatch(file, '*.asc'):
            ascfiles.append(direct+'/'+file)
    for asc in ascfiles:
        rec_Sac_Fix(direct, asc, regfileNameList, ExpType)


def crl_Sac_Fix(direct, subj, regfileNameList, ExpType):
    """
    read csv data file of subj and extract crossline saccades and fixations
    arguments:
        direct -- directory for storing csv and output files
        subj -- subject ID
        regionfileNameList -- a list of region file names (trial_id will help select corresponding region files)
        ExpType -- type of experiments: 'RAN', 'RP'    
    output:
        SacDF -- saccade data in different trials with updated line numbers
        crlSac -- crossline saccade data in different trials
        FixDF -- fixation data in different trials with updated line numbers
        crlFix -- crossline fixation data in different trials
    """
    nameSac = direct + '/' + subj + '_Sac.csv'; nameFix = direct + '/' + subj + '_Fix.csv'
    SacDF = pd.read_csv(nameSac, sep=','); FixDF = pd.read_csv(nameFix, sep=',')    
    newSacDF = pd.DataFrame(); newFixDF = pd.DataFrame()        
    crlSac = pd.DataFrame(columns=('subj', 'trial_id', 'eye', 'startline', 'endline', 'SaclineIndex', 'start', 'end', 'duration', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos', 'ampl', 'pk'))
    crlFix = pd.DataFrame(columns=('subj', 'trial_id', 'eye', 'startline', 'endline', 'FixlineIndex', 'start', 'end', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid'))
    print "Subj: ", subj
    
    for trialID in np.unique(map(int,SacDF.trial_id)):
        RegDF = getRegDF(regfileNameList, trialID)  # get region file
        # get saccade data
        print "Get crlSac: Trial ", str(trialID)
        SacDFtemp = SacDF[SacDF.trial_id==trialID].reset_index(); crlSactemp, question = getcrlSac(RegDF, SacDFtemp)
        newSacDF = newSacDF.append(SacDFtemp, ignore_index=True); crlSac = crlSac.append(crlSactemp, ignore_index=True)
        if RECSTATUS and question:
            logfile = open(direct + '/log.txt', 'a+')
            logfile.write('Subj: ' + subj + ' Trial ' + str(trialID) + ' crlSac start/end need check!\n')
            logfile.close()
        
        # get fixation data
        print "Get Fix: Trial ", str(trialID)
        FixDFtemp = FixDF[FixDF.trial_id==trialID].reset_index(); crlFixtemp, question = getcrlFix(RegDF, crlSactemp, FixDFtemp)
        newFixDF = newFixDF.append(FixDFtemp, ignore_index=True); crlFix = crlFix.append(crlFixtemp, ignore_index=True)
        if RECSTATUS and question:
            logfile = open(direct + '/log.txt', 'a+')
            logfile.write('Subj: ' + subj + ' Trial ' + str(trialID) + ' crlFix start/end need check!\n')  
            logfile.close()
            
    newSacDF.to_csv(nameSac, index=False); newFixDF.to_csv(nameFix, index=False)
    
    namecrlSac = direct + '/' + subj + '_crlSac.csv'; namecrlFix = direct + '/' + subj + '_crlFix.csv'
    crlSac.to_csv(namecrlSac, index=False); crlFix.to_csv(namecrlFix, index=False)


def crl_Sac_Fix_Batch(direct, regfileNameList, ExpType):
    """
    batch processing of all subjects' fixation and saccade data
    arguments:
        direct -- directory containing all asc files
        regfileNameList -- a list of region file names (trial_id will help select corresponding region files)
        ExpType -- type of experiments: 'RAN', 'RP'
    output:
        SacDF -- saccade data in different trials with updated line numbers of different subjects
        crlSac -- crossline saccade data in different trials of different subjects
        FixDF -- fixation data in different trials with updated line numbers of different subjects
        crlFix -- crossline fixation data in different trials of different subjects
    """
    subjlist = []
    for file in os.listdir(direct):
        if fnmatch.fnmatch(file, '*.asc'):
            subjlist.append(str(file).split('.')[0])
    for subj in subjlist:
        crl_Sac_Fix(direct, subj, regfileNameList, ExpType)
        

def reccrl_Sac_Fix(direct, datafile, regfileNameList, ExpType):
    """
    read ASC file and extract the fixation and saccade data
    arguments:
        direct -- directory for storing output files
        datafile -- EMF ascii file name
        regionfileNameList -- a list of region file names (trial_id will help select corresponding region files)
        ExpType -- type of experiments: 'RAN', 'RP'
    output:
        SacDF -- saccade data in different trials
        crlSacDF -- crossline saccade data in different trials
        FixDF -- fixation data in different trials
        crlFixDF -- crossline fixation data in different trials
    """
    # read EMF file
    f = open(datafile, 'r'); print "Read ASC: ", f.name; lines = f.readlines(); f.close()   # read EMF file    
    script, sessdate, srcfile = getHeader(lines)    # get header lines    
    T_idx, T_lines = getTrialReg(lines) # get trial regions
    
    SacDF = pd.DataFrame(columns=('subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'tdur', 'blinks', 'eye', 'start', 'end', 'duration', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos', 'ampl', 'pk', 'line'))
    FixDF = pd.DataFrame(columns=('subj', 'trial_id', 'trial_type', 'sampfreq', 'script', 'sessdate', 'srcfile', 'tdur', 'blinks', 'eye', 'start', 'end', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid', 'line'))        
    crlSac = pd.DataFrame(columns=('subj', 'trial_id', 'eye', 'startline', 'endline', 'SaclineIndex', 'start', 'end', 'duration', 'x1_pos', 'y1_pos', 'x2_pos', 'y2_pos', 'ampl', 'pk'))
    crlFix = pd.DataFrame(columns=('subj', 'trial_id', 'eye', 'startline', 'endline', 'FixlineIndex', 'start', 'end', 'duration', 'x_pos', 'y_pos', 'pup_size', 'valid'))
    
    for ind in range(len(T_lines)):
        triallines = lines[T_lines[ind,0]+1:T_lines[ind,1]]; trialID = int(T_idx[ind,0].split(' ')[-1])
        blinklines, fixlines, saclines, sampfreq, eyerec = getBlink_Fix_Sac_SampFreq_EyeRec(triallines); tdur = gettdur(triallines)
        RegDF = getRegDF(regfileNameList, trialID)  # get region file
        # read saccade data and get crossline saccade
        print "Read Sac and Get crlSac: Trial ", str(trialID)
        SacDFtemp = recSac(RegDF, ExpType, trialID, blinklines, saclines, sampfreq, eyerec, script, sessdate, srcfile, tdur)
        crlSactemp, question = getcrlSac(RegDF, SacDFtemp)
        SacDF = SacDF.append(SacDFtemp, ignore_index=True); crlSac = crlSac.append(crlSactemp, ignore_index=True)
        if RECSTATUS and question:
            logfile = open(direct + '/log.txt', 'a+')
            logfile.write('Subj: ' + SacDFtemp.subj[0] + ' Trial ' + str(trialID) + ' crlSac start/end need check!\n')
            logfile.close()

        # read fixation data and get crossline fixation
        print "Read Fix and Get crlFix: Trial ", str(trialID)
        FixDFtemp = recFix(RegDF, ExpType, trialID, blinklines, fixlines, sampfreq, eyerec, script, sessdate, srcfile, tdur)        
        crlFixtemp, question = getcrlFix(RegDF, crlSactemp, FixDFtemp)
        FixDF = FixDF.append(FixDFtemp, ignore_index=True); crlFix = crlFix.append(crlFixtemp, ignore_index=True)
        if RECSTATUS and question:
            logfile = open(direct + '/log.txt', 'a+')
            logfile.write('Subj: ' + FixDFtemp.subj[0] + ' Trial ' + str(trialID) + ' crlFix start/end need check!\n')
            logfile.close()
    
    # store fixation and saccade data
    resName = direct + './' + srcfile.split('.')[0]   
    SacDF.to_csv(resName + '_Sac.csv', index=False); crlSac.to_csv(resName + '_crlSac.csv')
    FixDF.to_csv(resName + '_Fix.csv', index=False); crlFix.to_csv(resName + '_crlFix.csv')
        
    
def reccrl_Sac_Fix_Batch(direct, regfileNameList, ExpType):
    """
    batch processing of all subjects' fixation and saccade data
    arguments:
        direct -- directory containing all asc files
        regfileNameList -- a list of region file names (trial_id will help select corresponding region files)
        ExpType -- type of experiments: 'RAN', 'RP'
    output:
        SacDF -- saccade data in different trials of different subjects
        crlSacDF -- crossline saccade data in different trials of different subjects
        FixDF -- fixation data in different trials of different subjects
        crlFixDF -- crossline fixation data in different trials of different subjects
    """
    ascfiles = []
    for file in os.listdir(direct):
        if fnmatch.fnmatch(file, '*.asc'):
            ascfiles.append(direct+'/'+file)
    for asc in ascfiles:
        reccrl_Sac_Fix(direct, asc, regfileNameList, ExpType)

    
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# functions for drawing saccades and fixations    
# gloabl variables
# for drawing
MAX_FIXATION_RADIUS = 30 # maximum radius of fixation circles for showing 


def rgb2gray(rgb):
    """
    convert a rgb turple to gray scale
    """
    return str(0.2989*rgb[0]/256.0 + 0.5870*rgb[1]/256.0 + 0.1140*rgb[2]/256.0)


def image_Sac_Fix(direct, subj, bitmapNameList, Sac, crlSac, Fix, crlFix, RegDF, trialID, method, PNGmethod = 0):
    """
    draw saccade and fixation data of a trial
    arguments:
        direct -- directory to store drawn figures
        subj -- subject ID
        bitmapNameList -- list of the bitmap files as backgrounds
        Sac -- saccade data of the trail
        crlSac -- cross line saccade data of the trial
        Fix -- fixation data of the trial
        crlFix -- cross line fixation data of the trial
        RegDF -- region file of the trail
        trialID -- trial ID
        method -- drawing method:
            'ALL': draw all results (mixing saccade with fixation, and mixing crossline saccade with crossline fixation)
            'SAC': draw saccade results (saccades and crossline saccades)
            'FIX': draw fixation results (fixation and crossline fixations)
        PNGmethod -- whether use png file as background (0) or draw texts from region file (1)    
    the results are saved in png file    
    """
    fd = FontDict(); fontpath = fd.fontGet('LiberationMono','Regular')
    xsz = 18; ttf = ImageFont.truetype(fontpath, xsz)
    if PNGmethod == 1:
        descents = getStrikeDescents(fontpath, xsz); ascents = getStrikeAscents(fontpath, xsz)   
        fg = (0,0,0); bg = (232,232,232); dim = (1280,1024)
    
    # draw
    if method == 'ALL':
        if PNGmethod == 0:
            # open the bitmap of the paragraph
            img1 = Image.open(bitmapNameList[trialID]); draw1 = ImageDraw.Draw(img1)      
        elif PNGmethod == 1:        
            # initialize the image
            img1 = Image.new('RGB', dim, bg) # 'RGB' specifies 8-bit per channel (32 bit color)
            draw1 = ImageDraw.Draw(img1)        
            # draw texts and rectangles
            for curline in pd.unique(RegDF.line):
                line = RegDF[RegDF.line==curline]; line.index = range(len(line))            
                # draw word one by one    
                for ind in range(len(line)):
                    (mdes, masc) = getdesasc(line.Word[ind], descents, ascents)  # calculate descent and ascent of each word
                    # draw current word
                    vpos_text = line.y1_pos[ind] + masc - xsz/4.5 - 1  # top edge of current word, masc - xsz/4.5 - 1 is offset!.
                    draw1.text((line.x1_pos[ind], vpos_text), line.Word[ind], font=ttf, fill=fg) 
                    # outline the word region!
                    # draw1.rectangle([(line.x1_pos[ind], line.y1_pos[ind]), (line.x2_pos[ind], line.y2_pos[ind])], outline=fg, fill=None)
        # draw fixations
        radius_ratio = MAX_FIXATION_RADIUS/max(Fix.duration)
        for ind in range(len(Fix)):
            if Fix.line[ind] != 0 and Fix.valid[ind] != 'no':
                r = Fix.duration[ind]*radius_ratio            
                draw1.ellipse((Fix.x_pos[ind]-r, Fix.y_pos[ind]-r, Fix.x_pos[ind]+r, Fix.y_pos[ind]+r), outline='blue', fill='blue')
                draw1.text((Fix.x_pos[ind], Fix.y_pos[ind]), str(Fix.duration[ind]), font=ttf, fill='green')
        # draw saccades
        for ind in range(len(Sac)):
            if Sac.x1_pos[ind] < Sac.x2_pos[ind]:
                draw1.line((Sac.x1_pos[ind], Sac.y1_pos[ind], Sac.x2_pos[ind], Sac.y2_pos[ind]), fill='green', width=2)
            else:
                draw1.line((Sac.x1_pos[ind], Sac.y1_pos[ind], Sac.x2_pos[ind], Sac.y2_pos[ind]), fill='red', width=2)
        # save image
        img1.save(direct + '/' + subj + '_FixSac_trial' + str(trialID) + '.png', 'PNG')
        
        if PNGmethod == 0:        
            # open the bitmap of the paragraph
            img2 = Image.open(bitmapNameList[trialID]); draw2 = ImageDraw.Draw(img2)
        elif PNGmethod == 1:
            # initialize the image
            img2 = Image.new('RGB', dim, bg) # 'RGB' specifies 8-bit per channel (32 bit color)
            draw2 = ImageDraw.Draw(img2)
            # draw texts and rectangles
            for curline in pd.unique(RegDF.line):
                line = RegDF[RegDF.line==curline]; line.index = range(len(line))            
                # draw word one by one    
                for ind in range(len(line)):
                    (mdes, masc) = getdesasc(line.Word[ind], descents, ascents)  # calculate descent and ascent of each word
                    # draw current word
                    vpos_text = line.y1_pos[ind] + masc - xsz/4.5 - 1  # top edge of current word, masc - xsz/4.5 - 1 is offset!.
                    draw2.text((line.x1_pos[ind], vpos_text), line.Word[ind], font=ttf, fill=fg) 
                    # outline the word region!
                    # draw2.rectangle([(line.x1_pos[ind], line.y1_pos[ind]), (line.x2_pos[ind], line.y2_pos[ind])], outline=fg, fill=None)
        # draw crossline fixations
        radius_ratio = MAX_FIXATION_RADIUS/max(Fix.duration)
        for ind in range(len(crlFix)):
            r = crlFix.duration[ind]*radius_ratio            
            draw2.ellipse((crlFix.x_pos[ind]-r, crlFix.y_pos[ind]-r, crlFix.x_pos[ind]+r, crlFix.y_pos[ind]+r), outline='blue', fill='blue')
            draw2.text((crlFix.x_pos[ind], crlFix.y_pos[ind]), str(crlFix.duration[ind]), font=ttf, fill='green')
        # draw crossline saccades
        for ind in range(len(crlSac)):
            if crlSac.x1_pos[ind] < crlSac.x2_pos[ind]:
                draw2.line((crlSac.x1_pos[ind], crlSac.y1_pos[ind], crlSac.x2_pos[ind], crlSac.y2_pos[ind]), fill='green', width=2)
            else:
                draw2.line((crlSac.x1_pos[ind], crlSac.y1_pos[ind], crlSac.x2_pos[ind], crlSac.y2_pos[ind]), fill='red', width=2)
        # save image
        img2.save(direct + '/' + subj + '_crlFixSac_trial' + str(trialID) + '.png', 'PNG')                
    elif method == 'SAC':
        if PNGmethod == 0:
            # open the bitmap of the paragraph        
            img = Image.open(bitmapNameList[trialID]); draw = ImageDraw.Draw(img)
        elif PNGmethod == 1:        
            # initialize the image
            img = Image.new('RGB', dim, bg) # 'RGB' specifies 8-bit per channel (32 bit color)
            draw = ImageDraw.Draw(img1)
            # draw texts and rectangles
            for curline in pd.unique(RegDF.line):
                line = RegDF[RegDF.line==curline]; line.index = range(len(line))            
                # draw word one by one    
                for ind in range(len(line)):
                    (mdes, masc) = getdesasc(line.Word[ind], descents, ascents)  # calculate descent and ascent of each word
                    # draw current word
                    vpos_text = line.y1_pos[ind] + masc - xsz/4.5 - 1  # top edge of current word, masc - xsz/4.5 - 1 is offset!.
                    draw.text((line.x1_pos[ind], vpos_text), line.Word[ind], font=ttf, fill=fg) 
                    # outline the word region!
                    # draw.rectangle([(line.x1_pos[ind], line.y1_pos[ind]), (line.x2_pos[ind], line.y2_pos[ind])], outline=fg, fill=None)
        # draw saccades
        for ind in range(len(Sac)):
            if Sac.x1_pos[ind] < Sac.x2_pos[ind]:
                draw.line((Sac.x1_pos[ind], Sac.y1_pos[ind], Sac.x2_pos[ind], Sac.y2_pos[ind]), fill='green', width=2)
            else:
                draw.line((Sac.x1_pos[ind], Sac.y1_pos[ind], Sac.x2_pos[ind], Sac.y2_pos[ind]), fill='red', width=2)
        # save image
        img.save(direct + '/' + subj + '_Sac_trial' + str(trialID) + '.png', 'PNG')
    elif method == 'FIX':
        if PNGmethod == 0:
            # open the bitmap of the paragraph        
            img = Image.open(bitmapNameList[trialID]); draw = ImageDraw.Draw(img)
        elif PNGmethod == 1:    
            # initialize the image
            img = Image.new('RGB', dim, bg) # 'RGB' specifies 8-bit per channel (32 bit color)
            draw = ImageDraw.Draw(img1)
            # draw texts and rectangles
            for curline in pd.unique(RegDF.line):
                line = RegDF[RegDF.line==curline]; line.index = range(len(line))            
                # draw word one by one    
                for ind in range(len(line)):
                    (mdes, masc) = getdesasc(line.Word[ind], descents, ascents)  # calculate descent and ascent of each word
                    # draw current word
                    vpos_text = line.y1_pos[ind] + masc - xsz/4.5 - 1  # top edge of current word, masc - xsz/4.5 - 1 is offset!.
                    draw.text((line.x1_pos[ind], vpos_text), line.Word[ind], font=ttf, fill=fg) 
                    # outline the word region!
                    # draw.rectangle([(line.x1_pos[ind], line.y1_pos[ind]), (line.x2_pos[ind], line.y2_pos[ind])], outline=fg, fill=None)
        # draw fixations
        radius_ratio = MAX_FIXATION_RADIUS/max(Fix.duration)
        for ind in range(len(Fix)):
            if Fix.line[ind] != 0 and Fix.valid[ind] != 'no':
                r = Fix.duration[ind]*radius_ratio            
                draw.ellipse((Fix.x_pos[ind]-r, Fix.y_pos[ind]-r, Fix.x_pos[ind]+r, Fix.y_pos[ind]+r), outline='blue', fill='blue')
                draw.text((Fix.x_pos[ind], Fix.y_pos[ind]), str(Fix.duration[ind]), font=ttf, fill='green')
        # save image
        img.save(direct + '/' + subj + '_Fix_trial' + str(trialID) + '.png', 'PNG') 


# main functions for drawing saccades and fixations
def draw_Sac_Fix(direct, subj, regfileNameList, bitmapNameList, method, PNGmethod = 0):    
    """
    read and draw saccade and fixation data
    arguments:
        direct -- directory storing csv and region files
        subj -- subject ID
        regfileNameList -- a list of region files (trial_id will help select corresponding region files)
        bitmapNameList -- a list of png bitmaps showing the paragraphs shown to the subject
        method -- drawing method:
            'ALL': draw all results (mixing saccade with fixation, and mixing crossline saccade with crossline fixation)
            'SAC': draw saccade results (saccades and crossline saccades)
            'FIX': draw fixation results (fixation and crossline fixations)
        PNGmethod -- whether use png file as background (0) or draw texts from region file (1) 
    output:
        when method == 'ALL'
            subj_FixSac_trial*.png -- showing the fixations and saccades of subj in different trials
            subj_crlFixSac_trial*.png -- showing the crossline fixations and saccades of subj in different trials
        when method == 'SAC':
            subj_Sac_trial*.png
            subj_crlSac_trial*.png
        when method == 'FIX':    
            subj_Fix_trial*.png
            subj_crlFix_trial*.png        
    """
    # read files
    nameSac = direct + '/' + subj + '_Sac.csv'; nameFix = direct + '/' + subj + '_Fix.csv' 
    namecrlSac = direct + '/' + subj + '_crlSac.csv'; namecrlFix = direct + '/' + subj + '_crlFix.csv'
    SacDF = pd.read_csv(nameSac, sep=','); FixDF = pd.read_csv(nameFix, sep=',')
    crlSacDF = pd.read_csv(namecrlSac, sep=','); crlFixDF = pd.read_csv(namecrlFix, sep=',')
    
    # draw fixation and saccade data on a picture
    for trialID in range(len(regfileNameList)):
        RegDF = getRegDF(regfileNameList, trialID)  # get region file
        print "Draw Sac and Fix: Subj: " + subj + ", Trial: " + str(trialID)
        Sac = SacDF[SacDF.trial_id == trialID].reset_index(); crlSac = crlSacDF[crlSacDF.trial_id == trialID].reset_index()
        Fix = FixDF[FixDF.trial_id == trialID].reset_index(); crlFix = crlFixDF[crlFixDF.trial_id == trialID].reset_index()    
        image_Sac_Fix(direct, subj, bitmapNameList, Sac, crlSac, Fix, crlFix, RegDF, trialID, method, PNGmethod)


def draw_Sac_Fix_Batch(direct, regfileNameList, bitmapNameList, method, PNGmethod = 0):
    """
    batch drawing of all subjects' fixation and saccade data figures
    arguments:
        direct -- directory containing all csv files
        regfileNameList -- a list of region file names (trial_id will help select corresponding region files)
        bitmapNameList -- a list of png bitmaps showing the paragraphs shown to the subject
        method -- drawing method:
            'ALL': draw all results (mixing saccade with fixation, and mixing crossline saccade with crossline fixation)
            'SAC': draw saccade results (saccades and crossline saccades)
            'FIX': draw fixation results (fixation and crossline fixations)
    output:
        when method == 'ALL'
            *_FixSac_trial*.png -- showing the fixations and saccades of all subjects in different trials
            *_crlFixSac_trial*.png -- showing the crossline fixations and saccades of all subjects in different trials
        when method == 'SAC':
            *_Sac_trial*.png
            *_crlSac_trial*.png
        when method == 'FIX':    
            *_Fix_trial*.png
            *_crlFix_trial*.png            
    """
    subjlist = []
    for file in os.listdir(direct):
        if fnmatch.fnmatch(file, '*.asc'):
            subjlist.append(file.split('.')[0])
    for subj in subjlist:
        draw_Sac_Fix(direct, subj, regfileNameList, bitmapNameList, method, PNGmethod)


def draw_blinks(direct, trialNum):
    """
    draw histogram of individual blinks
    arguments: 
        direct -- directory storing csv files
        trialNum -- number of trials in each subject's data
    output: histogram    
    """
    subjlist = []
    for file in os.listdir(direct):
        if fnmatch.fnmatch(file, '*.asc'):
            subjlist.append(file.split('.')[0])
            
    for trialID in range(trialNum):
        blinksdata = []
        for subj in subjlist:
            FixDF = pd.read_csv(direct + '/' + subj + '_Fix.csv', sep=',')
            FixDFtemp = FixDF[FixDF.trial_id==trialID].reset_index(); blinksdata.append(FixDFtemp.blinks[0])
        # draw histogram    
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.hist(blinksdata, bins=20, normed=True)
        ax.set_title('Histogram of Blinks (trial = ' + str(trialID) + '; n= ' + str(len(blinksdata)) + ')')
        ax.set_xlabel('No. Blinks')
        ax.set_ylabel('Frequency')
        plt.show()
        plt.savefig(direct + '/Hist_blinks_trial' + str(trialID) + '.png')
    
    
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# functions for calculating eye-movement measures
# global variables
ADD_TIMES = 1   # the times of single character length added to EMF for catching overshoot fixations

def modEMF(EMF):
    """
    modify EMF's mod_x1 and mod_x2, add space to boundaries of line starting and ending words
    arguments:
        EMF -- result data frame
    EMF, as a data frame, is mutable, no need to return    
    """
    EMF.mod_x1 = EMF.x1_pos; EMF.mod_x2 = EMF.x2_pos
    addDist = ADD_TIMES * (EMF.loc[0,'x2_pos']-EMF.loc[0,'x1_pos'])/np.float(EMF.loc[0,'reglen'])
    for curEMF in range(len(EMF)):
        if curEMF == 0:            
            EMF.loc[curEMF,'mod_x1'] -= addDist    # first word, add leftside!
        elif curEMF == len(EMF) - 1:            
            EMF.loc[curEMF,'mod_x2'] += addDist    # last word, add rightside!
        else:
            # check whether it is a line ending or line starting word
            if EMF.loc[curEMF-1,'line'] == EMF.loc[curEMF,'line']-1:
                EMF.loc[curEMF,'mod_x1'] -= addDist    # current region is a line starting, add leftside!
            elif EMF.loc[curEMF+1,'line'] == EMF.loc[curEMF,'line'] + 1:
                EMF.loc[curEMF,'mod_x2'] += addDist    # current region is a line ending, add rightside!


def chk_fp_fix(FixDF, EMF, curFix, curEMF):
    """
    calculate fist pass fixation measures:
        fpurt: first pass fixation time. Only includes fixations of 50 ms or longer by default (but see option --minfixdur). 
               If fpcount == 0 then fpurt = 0 (but see option --conditionalize).
        fpcount: The number of first pass fixations
        ffos: offset of the first first-pass fixation in a region from the first letter of the region, in characters (range of 0 to reglen-1).
        ffixurt: first first-pass fixation duration for each region.
        spilover: Duration of the first fixation beyond a region/word.
    arguments:
        FixDF -- fixation data of the trial
        EMF -- result data frame
        curFix -- current fixation in the region
        curEMF -- current region in the result data frame      
    returns:
        stFix, endFix -- starting and ending fixation indices of the first reading
    """
    EMF.loc[curEMF,'fpurt'] += FixDF.loc[curFix,'duration']  # fpurt: first pass fixation time
    EMF.loc[curEMF,'fpcount'] += 1 # fpcount: number of first pass fixation
    EMF.loc[curEMF,'ffos'] = np.ceil((FixDF.loc[curFix,'x_pos']-EMF.loc[curEMF,'mod_x1'])/np.float(EMF.loc[curEMF,'mod_x2']-EMF.loc[curEMF,'mod_x1'])*EMF.loc[curEMF,'reglen']) - 1   # ffos: offset of the first first-pass fixation in a region from the first letter of the region, in characters (range of 0 to reglen-1)
    EMF.loc[curEMF,'ffixurt'] += FixDF.loc[curFix,'duration']   # ffixurt: first first-pass fixation duration for each region.
    # locate the starting and ending indices of the first pass fixation in the current region                    
    stFix, endFix = curFix, curFix + 1
    # keep searching until leaving that word and use that as the ending index 
    while endFix < len(FixDF) and FixDF.loc[endFix,'valid'] == 'yes' and FixDF.loc[endFix,'line'] == EMF.loc[curEMF,'line'] and EMF.loc[curEMF,'mod_x1'] <= FixDF.loc[endFix,'x_pos'] and FixDF.loc[endFix,'x_pos'] <= EMF.loc[curEMF,'mod_x2']:
        EMF.loc[curEMF,'fpurt'] += FixDF.loc[endFix,'duration']  # add fpurt: first pass fixation time
        EMF.loc[curEMF,'fpcount'] += 1  # add fpcount: number of first pass fixation
        endFix += 1
    if endFix < len(FixDF) and FixDF.loc[endFix,'valid'] == 'yes':
        EMF.loc[curEMF,'spilover'] += FixDF.loc[endFix,'duration']  # add spilover: Duration of the first fixation beyond a region/word.   
    return stFix, endFix


def chk_fp_reg(FixDF, EMF, stFix, endFix, curEMF):
    """
    calculate first pass regression measures:
        fpregres: whether or not there was a first-pass regression from this region, yes=1, no=0.
        fpregreg: region targeted by first pass regression. If fpregres == 0 then fpregreg = 0.
        fpregchr: character position targeted by first pass regression (offset from first letter of the sentence). 
                 If fpregres == 0 then fpregchr will have a large value (high enough to be out of bounds for any possible stimulus string).
    arguments:
        FixDF -- fixation data of the trial
        EMF -- result data frame
        stFix, endFix -- starting and ending fixation indices of the first reading
        curEMF -- current region in the result data frame              
    """
    if FixDF.loc[endFix,'line'] == EMF.loc[curEMF,'line']:
        # the fixation after the first pass reading is within the same line of the current word
        if FixDF.loc[endFix,'x_pos'] < EMF.loc[curEMF,'mod_x1']:
            # a regression fixation
            EMF.loc[curEMF,'fpregres'] = 1
            # search the region where regression fixation falls into
            for cur in range(len(EMF)):
                if FixDF.loc[endFix,'valid'] == 'yes' and FixDF.loc[endFix,'line'] == EMF.loc[cur,'line'] and EMF.loc[cur,'mod_x1'] <= FixDF.loc[endFix,'x_pos'] and FixDF.loc[endFix,'x_pos'] <= EMF.loc[cur,'mod_x2']:
                    EMF.loc[curEMF,'fpregreg'] = EMF.loc[cur,'region']
                    if cur == 0:
                        EMF.loc[curEMF,'fpregchr'] = np.ceil((FixDF.loc[endFix,'x_pos']-EMF.loc[cur,'mod_x1'])/np.float(EMF.loc[cur,'mod_x2']-EMF.loc[cur,'mod_x1'])*EMF.loc[cur,'reglen']) - 1
                    else:    
                        EMF.loc[curEMF,'fpregchr'] = sum(EMF.reglen[0:cur-1]) + np.ceil((FixDF.loc[endFix,'x_pos']-EMF.loc[cur,'mod_x1'])/np.float(EMF.loc[cur,'mod_x2']-EMF.loc[cur,'mod_x1'])*EMF.loc[cur,'reglen']) - 1
                    break
        else:
            # a forward fixation
            EMF.loc[curEMF,'fpregres'] = 0; EMF.loc[curEMF,'fpregreg'] = 0; EMF.loc[curEMF,'fpregchr'] = sum(EMF.reglen)                    
    else:
        # the fixation after the first pass reading is not in the same line of the current word
        if FixDF.loc[endFix,'line'] < EMF.loc[curEMF,'line']:
            # a regression fixation
            EMF.loc[curEMF,'fpregres'] = 1
            # search the region where regression fixation falls into
            for cur in range(len(EMF)):
                if FixDF.loc[endFix,'valid'] == 'yes' and FixDF.loc[endFix,'line'] == EMF.loc[cur,'line'] and EMF.loc[cur,'mod_x1'] <= FixDF.loc[endFix,'x_pos'] and FixDF.loc[endFix,'x_pos'] <= EMF.loc[cur,'mod_x2']:
                    EMF.loc[curEMF,'fpregreg'] = EMF.loc[cur,'region']
                    if cur == 0:
                        EMF.loc[curEMF,'fpregchr'] = np.ceil((FixDF.loc[endFix,'x_pos']-EMF.loc[cur,'mod_x1'])/np.float(EMF.loc[cur,'mod_x2']-EMF.loc[cur,'mod_x1'])*EMF.loc[cur,'reglen']) - 1
                    else:    
                        EMF.loc[curEMF,'fpregchr'] = sum(EMF.reglen[0:cur-1]) + np.ceil((FixDF.loc[endFix,'x_pos']-EMF.loc[cur,'mod_x1'])/np.float(EMF.loc[cur,'mod_x2']-EMF.loc[cur,'mod_x1'])*EMF.loc[cur,'reglen']) - 1
                    break
        else:
            # a forward fixation
            EMF.loc[curEMF,'fpregres'] = 0; EMF.loc[curEMF,'fpregreg'] = 0; EMF.loc[curEMF,'fpregchr'] = sum(EMF.reglen)


def getReg(FixDF, curFix, EMF):
    """
    search EMF to locate which region that FixDF.loc[curFix] falls into
    arguments:
        FixDF -- fixation data of the trial
        curFix -- current fixation index
        EMF -- result data frame containing all region information
    return: index in EMF    
    """
    for curEMF in range(len(EMF)):
        if FixDF.loc[curFix,'line'] == EMF.loc[curEMF,'line'] and EMF.loc[curEMF,'mod_x1'] <= FixDF.loc[curFix,'x_pos'] and FixDF.loc[curFix,'x_pos'] <= EMF.loc[curEMF,'mod_x2']:
            break
    return curEMF
   

def chk_rp_reg(FixDF, EMF, stFix, endFix, curEMF):
    """
    calculate regression path measures:
        rpurt: regression path fixation time: The sum of all fixations from the time a region is entered until the first fixation to the right of that region. 
               This will include fixations outside, but to the left of the region in the case that fpregres=1. It is not the same as 'go-past time' (AKA 'quasi-first pass time), in which fixations outside the
               region are not counted. If fpregres == 0 then rpurt == fpurt.
        rpcount: The number of fixations in the regression path
        rpregreg: most upstream region visited in regression path. If fpcount == 0 then rpregreg = 0.
        rpregchr: must upstream letter visited in regression path (offset from the first letter of the sentence). 
                  If fpcount = 0 then rpregchr will have a large value (high enough to be out of bounds for any possible stimulus string).
    arguments:
        FixDF -- fixation data of the trial
        EMF -- result data frame
        stFix, endFix -- starting and ending fixation indices of the first reading
        curEMF -- current region in the result data frame            
    """
    if EMF.loc[curEMF,'fpregres'] == 0:
        # there is no regression, so no regression path
        EMF.loc[curEMF,'rpurt'] = EMF.loc[curEMF,'fpurt']; EMF.loc[curEMF,'rpcount'] = 0; EMF.loc[curEMF,'rpregreg'] = 0; EMF.loc[curEMF,'rpregchr'] = sum(EMF.reglen) 
    else:
        # there is a regression, find the regression path
        if curEMF == 0:
            # the first region (word), treat it as the same as no regression
            EMF.loc[curEMF,'rpurt'] = EMF.loc[curEMF,'fpurt']; EMF.loc[curEMF,'rpcount'] = 0; EMF.loc[curEMF,'rpregreg'] = 0; EMF.loc[curEMF,'rpregchr'] = sum(EMF.reglen) 
        elif curEMF == len(EMF) - 1:
            # the last region (word)            
            EMF.loc[curEMF,'rpurt'] = EMF.loc[curEMF,'fpurt'] + FixDF.loc[endFix,'duration']
            EMF.loc[curEMF,'rpcount'] += 1
            curFix = endFix + 1
            leftmostReg = getReg(FixDF, endFix, EMF); leftmostCurFix = endFix            
            while curFix < len(FixDF) and FixDF.loc[curFix,'valid'] == 'yes':
                # in the regression path                
                EMF.loc[curEMF,'rpurt'] += FixDF.loc[curFix,'duration']
                EMF.loc[curEMF,'rpcount'] += 1
                newleft = getReg(FixDF, curFix, EMF)
                if leftmostReg > newleft:
                    leftmostReg = newleft; leftmostCurFix = curFix                    
                curFix += 1
            EMF.loc[curEMF,'rpregreg'] = leftmostReg
            if leftmostReg == 0:
                EMF.loc[curEMF,'rpregchr'] = np.ceil((FixDF.loc[leftmostCurFix,'x_pos']-EMF.loc[leftmostReg,'mod_x1'])/np.float(EMF.loc[leftmostReg,'mod_x2']-EMF.loc[leftmostReg,'mod_x1'])*EMF.loc[leftmostReg,'reglen']) - 1
            else:    
                EMF.loc[curEMF,'rpregchr'] = sum(EMF.reglen[0:leftmostReg-1]) + np.ceil((FixDF.loc[leftmostCurFix,'x_pos']-EMF.loc[leftmostReg,'mod_x1'])/np.float(EMF.loc[leftmostReg,'mod_x2']-EMF.loc[leftmostReg,'mod_x1'])*EMF.loc[leftmostReg,'reglen']) - 1
        else:
            # the middle region (word)
            EMF.loc[curEMF,'rpurt'] = EMF.loc[curEMF,'fpurt'] + FixDF.loc[endFix,'duration']
            EMF.loc[curEMF,'rpcount'] += 1
            leftmostReg = getReg(FixDF, endFix, EMF); leftmostCurFix = endFix
            curFix = endFix + 1
            while curFix < len(FixDF) and FixDF.loc[curFix,'valid'] == 'yes' and not (FixDF.loc[curFix,'line'] == EMF.loc[curEMF+1,'line'] and EMF.loc[curEMF+1,'mod_x1'] <= FixDF.loc[curFix,'x_pos'] and FixDF.loc[curFix,'x_pos'] <= EMF.loc[curEMF+1,'mod_x2']):
                # in the regression path                
                EMF.loc[curEMF,'rpurt'] += FixDF.loc[curFix,'duration']
                EMF.loc[curEMF,'rpcount'] += 1
                newleft = getReg(FixDF, curFix, EMF)
                if leftmostReg > newleft:
                    leftmostReg = newleft; leftmostCurFix = curFix                    
                curFix += 1
            EMF.loc[curEMF,'rpregreg'] = leftmostReg
            if leftmostReg == 0:
                EMF.loc[curEMF,'rpregchr'] = np.ceil((FixDF.loc[leftmostCurFix,'x_pos']-EMF.loc[leftmostReg,'mod_x1'])/np.float(EMF.loc[leftmostReg,'mod_x2']-EMF.loc[leftmostReg,'mod_x1'])*EMF.loc[leftmostReg,'reglen']) - 1
            else:
                EMF.loc[curEMF,'rpregchr'] = sum(EMF.reglen[0:leftmostReg-1]) + np.ceil((FixDF.loc[leftmostCurFix,'x_pos']-EMF.loc[leftmostReg,'mod_x1'])/np.float(EMF.loc[leftmostReg,'mod_x2']-EMF.loc[leftmostReg,'mod_x1'])*EMF.loc[leftmostReg,'reglen']) - 1
            

def chk_sp_fix(FixDF, EMF, endFix, curEMF):
    """
    calculate second pass fixation measures:
        spurt: second pass fixation time
        spcount: The number of second pass fixations
    arguments:
        FixDF -- fixation data of the trial
        EMF -- result data frame
        endFix -- ending fixation index of the first reading
        curEMF -- current region in the result data frame            
    """
    for curFix in range(endFix, len(FixDF)):
        if FixDF.loc[curFix,'valid'] == 'yes' and FixDF.loc[curFix,'line'] == EMF.loc[curEMF,'line'] and EMF.loc[curEMF,'mod_x1'] <= FixDF.loc[curFix,'x_pos'] and FixDF.loc[curFix,'x_pos'] <= EMF.loc[curEMF,'mod_x2']:
            EMF.loc[curEMF,'spurt'] += FixDF.loc[curFix,'duration'] # add spurt: second pass fixation time
            EMF.loc[curEMF,'spcount'] += 1  # add spcount: the number of second pass fixations            
    

def chk_tffixos(EMF):
    """
    calculate tffixos: offset of the first fixation in trial in letters from the beginning of the sentence
    arguments:
        EMF -- result data frame
    """
    tffixos = 0
    for ind in range(len(EMF)):
        if not np.isnan(EMF.loc[ind,'ffos']):
            if ind == 0:
                tffixos += EMF.loc[ind,'ffos']
            else:
                tffixos += sum(EMF.reglen[0:ind-1]) + EMF.loc[ind,'ffos']
    
    return tffixos           

    
def chk_tregrcnt(SacDF):
    """
    calculate tregrecnt: total number of regressive saccades in trial
    arguments:
        SacDF -- saccade data of teh trial
    """
    totregr = 0
    for ind in range(len(SacDF)):
        crlinfo = SacDF.line[ind].split('_')
        if len(crlinfo) == 1:
            # not crossline saccade
            if SacDF.x1_pos[ind] > SacDF.x2_pos[ind]:
                totregr += 1
        else:
            # crossline saccade
            if crlinfo[0] > crlinfo[1]:
                totregr += 1
                
    return totregr            


def cal_EM_measures(RegDF, FixDF, SacDF, EMF):
    """
    calculate eye-movement measures of the trial
    arguments:
        RegDF -- region file
        FixDF -- fixation data of the trial
        SacDF -- saccade data of the trial
        EMF -- result data frame 
    EMF, as a data frame, is mutable, no need to return
    eye-movement measures:
      whole trial measures:
        tffixos -- offset of the first fixation in trial in letters from the beginning of the sentence.
        tffixurt -- duration of the first fixation in trial.
        tfixcnt -- total number of valid fixations in trial.
        tregrcnt -- total number of regressive saccades in trial.
      region (each word) measures:  
        fpurt -- first pass fixation time. Only includes fixations of 50 ms or longer by default (but see option --minfixdur). 
                If fpcount == 0 then fpurt = 0 (but see option --conditionalize).
        fpcount -- The number of first pass fixations
        fpregres -- whether or not there was a first-pass regression from this region, yes=1, no=0.
        fpregreg -- region targeted by first pass regression. If fpregres == 0 then fpregreg = 0.
        fpregchr -- character position targeted by first pass regression (offset from first letter of the sentence). 
                    If fpregres = 0 then fpregchr will have a large value (high enough to be out of bounds for any possible stimulus string).
        ffos -- offset of the first first-pass fixation in a region from the first letter of the region, in characters (range of 0 to reglen-1).
        ffixurt -- first first-pass fixation duration for each region.
        spilover -- Duration of the first fixation beyond a region/word.
        rpurt -- regression path fixation time: The sum of all fixations from the time a region is entered until the first fixation to the right of that region. 
                This will include fixations outside, but to the left of the region in the case that fpregres=1. It is not the same as 'go-past time' (AKA 'quasi-first pass time), in which fixations outside the
                region are not counted. If fpregres == 0 then rpurt = fpurt.
        rpcount -- The number of fixations in the regression path
        rpregreg -- most upstream region visited in regression path. If fpcount == 0 then rpregreg = 0.
        rpregchr -- must upstream letter visited in regression path (offset from the first letter of the sentence). 
                    If fpcount == 0 then rpregchr will have a large value (high enough to be out of bounds for any possible stimulus string).
        spurt -- second pass fixation time
        spcount -- The number of second pass fixations
    """
    # default values
    EMF.ffos = np.nan  # for first pass fixation measures
    EMF.fpregres = np.nan; EMF.fpregreg = np.nan; EMF.fpregchr = np.nan   # for first regression measures
    EMF.rpregres = np.nan; EMF.rpregreg = np.nan; EMF.rpregchr = np.nan   # for regression path measures
    
    # region (each word) measures
    for curEMF in range(len(EMF)):
        for curFix in range(len(FixDF)):
            if FixDF.loc[curFix,'valid'] == 'yes' and FixDF.loc[curFix,'line'] == EMF.loc[curEMF,'line'] and EMF.loc[curEMF,'mod_x1'] <= FixDF.loc[curFix,'x_pos'] and FixDF.loc[curFix,'x_pos'] <= EMF.loc[curEMF,'mod_x2']:
                # find a first pass fixation on the current word!                    
                stFix, endFix = chk_fp_fix(FixDF, EMF, curFix, curEMF) # calculate first pass fixation measures: fpurt, fpcount, ffos, ffixurt, spilover  
                chk_fp_reg(FixDF, EMF, stFix, endFix, curEMF) # calculate first pass regression measures: fpregres, fpregreg, fpregchr
                chk_rp_reg(FixDF, EMF, stFix, endFix, curEMF) # calculate regression path measures: rpurt, rpcount, rpregreg, rpregchr
                chk_sp_fix(FixDF, EMF, endFix, curEMF) # calculate second pass fixation measures: spurt, spcount                                       
                # first pass reading of that word is finished, go to next word        
                break
                
    # change fpurt == 0, fpcount == 0, ffixurt == 0, spilover == 0 with NA
    for curEMF in range(len(EMF)):
        if EMF.loc[curEMF,'fpurt'] == 0:
            EMF.loc[curEMF,'fpurt'] = np.nan
        if EMF.loc[curEMF,'fpcount'] == 0:
            EMF.loc[curEMF,'fpcount'] = np.nan
        if EMF.loc[curEMF,'ffixurt'] == 0:
            EMF.loc[curEMF,'ffixurt'] = np.nan
        if EMF.loc[curEMF,'spilover'] == 0:
            EMF.loc[curEMF,'spilover'] = np.nan
    
    # whole trial measures
    EMF.tffixos = chk_tffixos(EMF)  # tffixos: offset of the first fixation in trial in letters from the beginning of the sentence       
    EMF.ttfixurt = sum(x for x in EMF.fpurt if not np.isnan(x))     # tffixurt: duration of the first fixation in trial
    EMF.tfixcnt = len(FixDF[FixDF.valid=='yes'])    # tfixcnt: total number of valid fixations in trial
    EMF.tregrcnt = chk_tregrcnt(SacDF)  # tregrcnt: total number of regressive saccades in trial
    

def cal_EMF(direct, subj, regfileNameList):
    """
    read fixation and saccade data of subj and calculate eye-movement measures
    arguments:
        direct -- directory for storing csv and output files
        subj -- subject ID
        regionfileNameList -- a list of region file names (trial_id will help select corresponding region files)
    output:
        EMF -- data frame storing eye-movement measures
    """
    nameFix = direct + '/' + subj + '_Fix.csv'; FixDF = pd.read_csv(nameFix, sep=',')   # read fixation data 
    nameSac = direct + '/' + subj + '_Sac.csv'; SacDF = pd.read_csv(nameSac, sep=',')   # read saccade data
    for trialID in range(len(regfileNameList)):
        RegDF = getRegDF(regfileNameList, trialID) # get region file 
        FixDFtemp = FixDF[FixDF.trial_id==trialID].reset_index()  # get fixation of the trial
        SacDFtemp = SacDF[SacDF.trial_id==trialID].reset_index()  # get saccade of the trial
        # create result data frame
        EMF = pd.DataFrame(np.zeros((len(RegDF), 32)))
        EMF.columns = ['subj', 'trial_id', 'trial_type', 'tdur', 'blinks', 'eye', 'tffixos', 'tffixurt', 'tfixcnt', 'tregrcnt', 'region', 'reglen', 'word', 'line', 'x1_pos', 'x2_pos', 'mod_x1', 'mod_x2',
                       'fpurt', 'fpcount', 'fpregres', 'fpregreg', 'fpregchr', 'ffos', 'ffixurt', 'spilover', 'rpurt', 'rpcount', 'rpregreg', 'rpregchr', 'spurt', 'spcount']
        # copy values from FixDF about the whole trial               
        EMF.subj = subj; EMF.trial_id = FixDF.trial_id[0]; EMF.trial_type = FixDF.trial_type[0]; EMF.tdur = FixDF.tdur[0]; EMF.blinks = FixDF.blinks[0]; EMF.eye = FixDF.eye[0]
        # copy values from RegDF about region        
        EMF.region = RegDF.WordID; EMF.reglen = RegDF.length; EMF.word = RegDF.Word; EMF.line = RegDF.line; EMF.x1_pos = RegDF.x1_pos; EMF.x2_pos = RegDF.x2_pos
        modEMF(EMF) # modify EMF's mod_x1 and mod_x2
        print "Cal EM measures: Subj: " + subj + ", Trial: " + str(trialID)
        cal_EM_measures(RegDF, FixDFtemp, SacDFtemp, EMF)        
        nameEMF = direct + '/' + subj + '_EMF_trial' + str(trialID) + '.csv'; EMF.to_csv(nameEMF, index=False) # store results
        

def cal_EMF_Batch(direct, regfileNameList):
    """
    batch calculating all subjects' EMF measures
    arguments:
        direct -- directory containing all csv files
        regfileNameList -- a list of region file names (trial_id will help select corresponding region files)
    output:
        EMF -- data frame storing eye-movement measures of different subjects        
    """
    subjlist = []
    for file in os.listdir(direct):
        if fnmatch.fnmatch(file, '*.asc'):
            subjlist.append(file.split('.')[0])
    for subj in subjlist:
        cal_EMF(direct, subj, regfileNameList)      