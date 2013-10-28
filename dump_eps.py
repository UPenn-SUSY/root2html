#!/usr/bin/env python
"""
NAME
    root2html.py - generates html and images for displaying TCanvases

SYNOPSIS
    root2html.py [OPTIONS] file.root [file2.root ...]

DESCRIPTION
    root2html is a script for generating an html page for displaying plots.
    root2html expects you to pass a root file, filled with TCanvases,
    possibly organized in TDirectories.  The canvases presumably have plots
    that you have pre-made and styled however you like.  root2html inspects
    the root file and walks its directories.  Then, for each canvas, it
    inspects  all objects that have been drawn to the canvas, and gets
    statistics depending on the object's type.  These stats are displayed in
    the caption when you click on a figure.  Then, root2html creates eps and
    gif/png images for each of the plots, and generates an html page
    containing and linking all the information.

    When viewing the output html, note that you can click-up more than one
    figure at a time, and drag them around the screen.  That javascript magic
    is done with the help of this library: http://highslide.com/.

INSTALLATION
    Assuming you have a working ROOT installation with PyROOT, the only other
    requirement is that you download the highslide javascript library at
    http://highslide.com/, unzip it, and set the highslide_path variable to
    point to the path: highslide-<version>/highslide (see below).

OPTIONS
    -h, --help
        Prints this manual and exits.
        
    -p PATTERN, --pattern=PATTERN
        Regex pattern for filtering the TCanvas paths processed.  The pattern
        is matched against the full paths of the TCanvases in the root file.

    -j PATH, --highslide=PATH
        Overrides the default path to highslide.

AUTHORS
    Ryan Reece  <ryan.reece@cern.ch>
    Tae Min Hong  <tmhong@cern.ch>

COPYRIGHT
    Copyright 2011 The authors
    License: GPL <http://www.gnu.org/licenses/gpl.html>

SEE ALSO
    ROOT <http://root.cern.ch>
    Highslide <http://highslide.com/>

2011-02-16
"""
#------------------------------------------------------------------------------

import os, sys, getopt
import time
import re
import math

import ROOT
ROOT.gROOT.SetBatch(True)
import rootlogon # your custom ROOT options, comment-out this if you don't have one
ROOT.gErrorIgnoreLevel = 1001

#------------------------------------------------------------------------------

## global options
img_height = 450 # pixels
quiet = True

#______________________________________________________________________________
def main(argv):
    ## option defaults
    pattern = ''

    ## parse options
    _short_options = 'hp:j:'
    _long_options = ['help', 'pattern=', 'highslide=']
    try:
        opts, args = getopt.gnu_getopt(argv, _short_options, _long_options)
    except getopt.GetoptError:
        print 'getopt.GetoptError\n'
        print __doc__
        sys.exit(2)
    for opt, val in opts:
        if opt in ('-h', '--help'):
            print __doc__
            sys.exit()
        if opt in ('-p', '--pattern'):
            pattern = val
        if opt in ('-j', '--highslide'):
            highslide_path = val

    assert len(args) > 0

    t_start = time.time()
    n_plots = 0

    ## make indexes
    for path in args:
        path_wo_ext = strip_root_ext(path)
        name = os.path.join(path_wo_ext, 'index.html')
        index = HighSlideRootFileIndex(name)
        n_plots += index.write_root_file(path, pattern)

    t_stop = time.time()
    print '  # plots    = %i' % n_plots
    print '  time spent = %i s' % round(t_stop-t_start)
    print '  avg rate   = %.2f Hz' % (float(n_plots)/(t_stop-t_start))
    print '  Done.'

#------------------------------------------------------------------------------
class HighSlideRootFileIndex(file):
    #__________________________________________________________________________
    def __init__(self, name=''):
        make_dir_if_needed(name)
        self.dirname = os.path.dirname(name)
        self.previous_level = 0
        self.pwd = None
    #__________________________________________________________________________
    def write_root_file(self, path, pattern=''):
        n_plots = 0
        rootfile = ROOT.TFile(path)
        for dirpath, dirnames, filenames, tdirectory in walk(rootfile):
            for key in filenames:
                obj = tdirectory.Get(key)
                if isinstance(obj, ROOT.TCanvas):
                    root_dir_path = dirpath.split(':/')[1]
                    root_key_path = os.path.join(root_dir_path, key)
                    if pattern and not re.match(pattern, root_key_path):
                        continue
                    print os.path.join(dirpath, key)
                    full_path = os.path.join(self.dirname, root_key_path)
                    self.write_canvas(obj, full_path)
                    n_plots += 1
        rootfile.Close()
        return n_plots

    #__________________________________________________________________________
    def write_canvas(self, canvas, basepath):
        name = canvas.GetName()
        make_dir_if_needed(basepath)
        ## save eps
        eps = basepath + '.eps'
        png = basepath + '.png'
        canvas.SaveAs(eps)
        # canvas.SaveAs(png)


#------------------------------------------------------------------------------
# free functions
#------------------------------------------------------------------------------

#__________________________________________________________________________
#______________________________________________________________________________
def walk(top, topdown=True):
    """
    os.path.walk like function for TDirectories.
    Return 4-tuple: (dirpath, dirnames, filenames, top)
        dirpath = 'file_name.root:/some/path' # may end in a '/'?
        dirnames = ['list', 'of' 'TDirectory', 'keys']
        filenames = ['list', 'of' 'object', 'keys']
        top = this level's TDirectory
    """
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    assert isinstance(top, ROOT.TDirectory)
    names = [k.GetName() for k in top.GetListOfKeys()]
    dirpath = top.GetPath()
    dirnames = []
    filenames = []
    ## filter names for directories
    for k in names:
        d = top.Get(k)
        if isinstance(d, ROOT.TDirectory):
            dirnames.append(k)
        else:
            filenames.append(k)
    ## sort
    dirnames.sort()
    filenames.sort()
    ## yield
    if topdown:
        yield dirpath, dirnames, filenames, top
    for dn in dirnames:
        d = top.Get(dn)
        for x in walk(d, topdown):
            yield x
    if not topdown:
        yield dirpath, dirnames, filenames, top

#______________________________________________________________________________
def strip_root_ext(path):
    reo = re.match('(\S*?)(\.canv)?(\.root)(\.\d*)?', path)
    assert reo
    return reo.group(1)

#______________________________________________________________________________
def make_dir_if_needed(path):
    if path.count('/'):
        dirname = os.path.split(path)[0]
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

#______________________________________________________________________________
def relpath(path, start='.'):
    """
    Return a relative version of a path
    Stolen implementation from Python 2.6.5 so I can use it in 2.5
    http://svn.python.org/view/python/tags/r265/Lib/posixpath.py?revision=79064&view=markup
    """
    # strings representing various path-related bits and pieces
    curdir = '.'
    pardir = '..'
    extsep = '.'
    sep = '/'
    pathsep = ':'
    defpath = ':/bin:/usr/bin'
    altsep = None
    devnull = '/dev/null'

    if not path:
        raise ValueError("no path specified")

    start_list = os.path.abspath(start).split(sep)
    path_list = os.path.abspath(path).split(sep)

    # Work out how much of the filepath is shared by start and path.
    i = len(os.path.commonprefix([start_list, path_list]))

    rel_list = [pardir] * (len(start_list)-i) + path_list[i:]
    if not rel_list:
        return '.'
    return os.path.join(*rel_list)


#______________________________________________________________________________
if __name__ == '__main__': main(sys.argv[1:])

