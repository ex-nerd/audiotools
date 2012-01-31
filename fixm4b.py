#!/usr/bin/python
#

###############################################################################

import os, sys, re
import subprocess
import unicodedata
from mutagen.mp4 import MP4

t4 = {
    'album':                '\xa9alb',
    'albumartist':          'aART',
    'albumartistsortorder': 'soaa',
    'albumsortorder':       'soal',
    'artist':               '\xa9ART',
    'artistsortorder':      'soar',
    'bpm':                  'tmpo',
    'comment':              '\xa9cmt',
    'composer':             '\xa9wrt',
    'composersortorder':    'soco',
    'copyright':            'cprt',
    'description':          'desc',
    'encodedby':            '\xa9too',
    'genre':                '\xa9gen',
    'grouping':             '\xa9grp',
    'lyrics':               '\xa9lyr',
    'partofcompilation':    'cpil',
    'partofgaplessalbum':   'pgap',
    'podcast':              'pcst',
    'podcastcategory':      'catg',
    'podcastepisodeguid':   'egid',
    'podcastkeywords':      'keyw',
    'podcasturl':           'purl',
    'purchasedate':         'purd',
    'showname':             'tvsh',
    'showsortorder':        'sosn',
    'title':                '\xa9nam',
    'titlesortorder':       'sonm',
    'year':                 '\xa9day',
    }

if __name__ == '__main__':
    if len(sys.argv) > 1:
        path = os.path.abspath(sys.argv[1])
    else:
        path = os.path.abspath('.')
    print path
    os.chdir(path)
    # Load the files
    files = [filename for filename in os.listdir(".") if filename.endswith(".m4b")]
    files.sort()
    # Init
    for file in files:
        m = MP4(file)
        changed = []
        # Don't want this taking up space
        if m.get(t4['encodedby'], []) != ['']:
            m[t4['encodedby']] = ['']
            changed.append('encodedby')
        # Grouping in the filename
        groupnum = None
        match = re.search(r'^([^\-]+?)\s+(\d+)\s-\s', file)
        if match and match.group(2):
            groupnum = match.group(2)
        # Grouping?
        grouping = m.get(t4['grouping'], [''])[0].strip()
        # Can add an album sort order?
        if groupnum and grouping:
            sortorder = '{0} {1} - {2}'.format(grouping, groupnum, m[t4['album']][0].strip())
            if m.get(t4['albumsortorder'], [''])[0] != sortorder:
                m[t4['albumsortorder']] = sortorder
                changed.append('albumsortorder')
        # Save?
        if len(changed) > 0:
            print file
            print '  ' + ', '.join(changed)
            m.save()
        # Cover art?
        if os.path.exists(file[:-4] + '.jpg'):
            subprocess.call(['mp4art', '--remove', file])
            subprocess.call(['mp4art', '--add', file[:-4] + '.jpg', file])
        # chmod (os.chmod() feels messy)
        subprocess.call(['chmod', '644', file])
