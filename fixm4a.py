#!/usr/bin/python
#
# Script used to clean up my music collection.  Most of the understanding I
# gained about mutagen comes thanks to puddletag.  I borrowed some of the
# tag name->field mappings, so this script might as well be licensed under
# the GPLv3, just like puddletag.
#

# Set to true for test mode
dryrun = True

import os, sys, re
import unicodedata
from mutagen.mp4 import MP4
import mutagen.id3 as id3

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

t3 = {
    'album':              'TALB',
    'bpm':                'TBPM',
    'composer':           'TCOM',
    'copyright':          'TCOP',
    'date':               'TDAT',
    'audiodelay':         'TDLY',
    'encodedby':          'TENC',
    'lyricist':           'TEXT',
    'filetype':           'TFLT',
    'time':               'TIME',
    'grouping':           'TIT1',
    'title':              'TIT2',
    'version':            'TIT3',
    'initialkey':         'TKEY',
    'language':           'TLAN',
    'audiolength':        'TLEN',
    'mediatype':          'TMED',
    'mood':               'TMOO',
    'originalalbum':      'TOAL',
    'filename':           'TOFN',
    'author':             'TOLY',
    'originalartist':     'TOPE',
    'originalyear':       'TORY',
    'fileowner':          'TOWN',
    'artist':             'TPE1',
    'albumartist':        'TPE2',
    'conductor':          'TPE3',
    'arranger':           'TPE4',
    'disk':               'TPOS',
    'producednotice':     'TPRO',
    'partofcompilation':  'TCMP',
    'organization':       'TPUB',
    'track':              'TRCK',
    'recordingdates':     'TRDA',
    'radiostationname':   'TRSN',
    'radioowner':         'TRSO',
    'audiosize':          'TSIZ',
    'albumsortorder':     'TSOA',
    'performersortorder': 'TSOP',
    'titlesortorder':     'TSOT',
    'isrc':               'TSRC',
    'encodingsettings':   'TSSE',
    'setsubtitle':        'TSST',
    'year':               'TYER',
    }

def strip_accents(s):
    return ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn'))

def _titlecase(m):
    return m.group(1).title()

def _lowercase(m):
    return m.group(1).lower()

def _uppercase(m):
    return m.group(1).upper()

def _musiccase(m):
    return m.group(1).title() + m.group(2).lower()

def fix_album(s):
    s = re.sub(r'\W+Dis[kc]\s+([AB]|\d+)\W*$', '', s)
    s = re.sub(r'\W+cd\s*\d+\W*$', '', s, flags=re.IGNORECASE)
    if re.search(r'Dis[kc]\b', s, flags=re.IGNORECASE) or re.search(r'cd\s*\d', s, flags=re.IGNORECASE):
        print "  WARNING, album with disk in name: {0}".format(s)
    return s

def fix_title(s):
    new = s.strip()
    new = new.replace(' MI ', ' Mi ') # typo
    new = re.sub(r'(?<= )(\w[a-z_-]*)(?=[ ,;.-])', _titlecase, new)
    for term in ('the', 'by', 'of', 'a', 'an', 'and', 'e', 'y', 'et', 'le', 'as', 'na', 'por', 'para', 'el', 'on', 'but', 'or', 'for', 'in', 'from', 'nor', 'to', 'at', 'de', 'la', 'los', 'les', 'las', 'und', 'del', 'von', 'in', 'des', 'dem', 'der', 'di', 'with'):
        new = re.sub(
            r'( {0} )'.format(term),
            _lowercase,
            new, flags=re.IGNORECASE
            )
        new = re.sub(
            r'([^a-z,1-9]+) {0} '.format(term),
            r'\1 {0} '.format(term.title()),
            new, flags=re.IGNORECASE
            )
    new = re.sub(r'(?<= )(\w)(?=[\w\.]+)$', _uppercase, new)
    new = re.sub(r'( \w(?: (?:flat|sharp))? )((?:major|minor))', _musiccase, new, flags=re.IGNORECASE)
    new = re.sub(r'(?:#|No\.?)(\d)', r'No. \1', new)
    new = new.replace(u'\u2019', "'") # smart apostrophe
    new = new.replace('`', "'")
    new = new.replace(u'\xb4', "'")   # some form of tilde meant to be apostrophe
    new = re.sub(r'\s+', ' ', new)
    new = re.sub(r'\s+,', ',', new)
    new = re.sub(r'^the', 'The', new, flags=re.IGNORECASE)
    new = re.sub(r'\b([xvi]+)\b', _uppercase, new, flags=re.IGNORECASE)
    new = re.sub(r'(\d(?:rd|st|nd|th))(?= )', _lowercase, new, flags=re.IGNORECASE)
    #new = new[0].upper() + new[1:]
    return new.strip()

def fix_name(s):
    new = strip_accents(s)
    new = new.replace(u'\xa1', '')    # upside down !
    new = new.replace(u'\xe6', 'ae')
    new = new.replace(u'\xdf', 'ss')  # eszet
    new = new.replace(u'\xa1', '')    # upside down !
    new = new.replace(u'\xbf', '')    # upside down ?
    new = fix_title(new)
    new = new.replace('"', '')
    new = re.sub('\s*&\s*', ' and ', new)
    new = re.sub(r'[\\/:*?<>|]+', '-', new) # characters unfriendly to win/mac
    new = re.sub(r' -(?! )', ' ', new)
    new = re.sub(r'\s+', ' ', new)
    new = re.sub(r'\W+;', ';', new)
    new = re.sub(r'^[^\w\(]+|[^\w\)]+$', '', new)
    new = re.sub(r'[^\w\)]*(\.\w\w+)$', _lowercase, new, flags=re.IGNORECASE)
    new = new.replace(' #!@-', ' Shit') # for one specific song
    new = re.sub(r'^(\d+)\. ', r'\1 ', new)
    new = re.sub(r'^([\d-]+ \w)', _uppercase, new)
    if new.endswith('.jpg'):
        new = new.lower()
    return new

def fix_name_full(new):
    new = re.sub('\(.+\)', '', new)
    new = re.sub('\[.+\]', '', new)
    new = fix_name(new)
    return new

def load_mp4(dir, file, _numtracks = None, _disk = None, _numdisks = None):
    m = MP4(os.path.join(dir, file))
    changed = []
    # Don't want this taking up space
    if m.get(t4['encodedby'], []) != ['']:
        m[t4['encodedby']] = ['']
        changed.append('encodedby')
    # Adjust num tracks
    try:
        (track, numtracks) = m['trkn'][0]
    except:
        track = numtracks = 0
    if numtracks == 0:
        if _numtracks:
            numtracks = _numtracks
            m['trkn'] = [(track,numtracks)]
            changed.append('trkn')
        else:
            print "  no numtracks for {0}".format(file)
            sys.exit(1)
    # Try to detect disk numbers
    try:
        (disk, numdisks) = m['disk'][0]
    except:
        disk = numdisks = 0
    # Use this bit to force num_disks
    # @todo detect numdisks
    #_disk = disk
    #_numdisks = 0
    if _disk and _numdisks and not disk and not numdisks:
        disk     = _disk
        numdisks = _numdisks
        m['disk'] = [(disk,numdisks)]
        changed.append('disk')
    elif str(_disk) != '0' and str(disk) != '0' and str(disk) != str(_disk):
        print "  Disknum mismatch {0} != {1} on {2}".format(disk, _disk, file)
        sys.exit(1)
    elif disk and not numdisks:
        print "  disknum but no numdisks on {0}".format(file)
        sys.exit(1)
    # Clean up the album name
    album = fix_album(m[t4['album']][0].strip())
    if album != m[t4['album']][0]:
        m[t4['album']] = [album]
        changed.append('album')
    # Clean up the title
    #print m[t4['title']][0]
    title = m[t4['title']][0].strip()
    title = title.replace(',,,', ';')  # catch some oddities left over from fixing nero's tag issues
    title = fix_title(title)
    if title != m[t4['title']][0]:
        m[t4['title']] = [title]
        changed.append('title')
    # Generate a new name
    new = fix_name_full(u"{0} {1}.m4a".format(
        str(track).zfill(max(2,len(str(numtracks)))),
        title
        ))
    if disk > 0 and numdisks > 1:
        new = "{0}-{1}".format(
            str(disk).zfill(len(str(numdisks))),
            new)
    try:
        if file.decode("utf-8") == new.decode("utf-8"):
            new = None
    except:
        print "  FILE:  "+os.path.join(dirname, file)
        raise
    # Return
    return (m, new, changed)

def load_mp3(dir, file, _numtracks = None, _disk = None, _numdisks = None):
    m = id3.ID3(os.path.join(dir, file))
    changed = []
    # Don't want this taking up space
    if t3['encodedby'] in m:
        del(m[t3['encodedby']])
        changed.append('encodedby')
    # Adjust num tracks
    try:
        numtracks = 0
        track = m[t3['track']].text[0]
        if '/' in track:
            (track, numtracks) = track.split('/')
    except:
        track = numtracks = 0
    if numtracks == 0:
        if _numtracks:
            numtracks = _numtracks
            m[t3['track']] = id3.TRCK(0, '{0}/{1}'.format(track,numtracks))
            changed.append('track')
        else:
            print "  no numtracks for {0}".format(file)
            sys.exit(1)
    # Try to detect disk numbers
    try:
        numdisks = 0
        disk = m[t3['disk']].text[0]
        if '/' in disk:
            (disk, numdisks) = disk.split('/')
    except:
        disk = numdisks = 0
    if _disk and _numdisks and not int(disk) and not int(numdisks):
        disk     = str(_disk).zfill(len(str(_numdisks)))
        numdisks = _numdisks
        m[t3['disk']] = id3.TPOS(0, '{0}/{1}'.format(disk,numdisks))
        changed.append('disk')
    elif str(_disk) != '0' and str(disk) != '0' and str(disk) != str(_disk):
        print "  Disknum mismatch {0} != {1} on {2}".format(disk, _disk, file)
        sys.exit(1)
    elif int(disk) and not int(numdisks):
        if _numdisks:
            disk     = str(disk).zfill(len(str(_numdisks)))
            numdisks = _numdisks
            m[t3['disk']] = id3.TPOS(0, '{0}/{1}'.format(disk,numdisks))
            changed.append('disk')
        else:
            print "  disknum but no numdisks on {0}".format(file)
            sys.exit(1)
    # Clean up the album name
    if t3['album'] in m:
        album = fix_album(m[t3['album']].text[0].strip())
        if album != m[t3['album']].text[0]:
            m[t3['album']].text[0] = album
            changed.append('album')
    # Clean up the title
    #print m[t3['title']].text[0]
    if t3['title'] in m:
        title = m[t3['title']].text[0].strip()
        title = fix_title(title)
        if title != m[t3['title']].text[0]:
            m[t3['title']].text = [title]
            changed.append('title')
    else:
        title = ''
        changed.append('title')
    # Generate a new name
    new = fix_name_full(u"{0} {1}.mp3".format(
        str(track).zfill(max(2,len(str(numtracks)))),
        title
        ))
    if int(disk) > 0 and int(numdisks) > 1:
        new = "{0}-{1}".format(
            str(disk).zfill(len(str(numdisks))),
            new)
    try:
        if file.decode("utf-8") == new.decode("utf-8"):
            new = None
    except:
        print "  FILE:  "+os.path.join(dirname, file)
        raise
    # Return
    return (m, new, changed)

def visit(arg, dirname, names):
    print dirname
    # Do some math/checking for disk number info
    parent = os.path.dirname(dirname)
    thisdir = os.path.basename(dirname)
    m = re.search(r'(?:cd|dis[ck])\s+([AB]|\d+)\b', thisdir, flags=re.IGNORECASE)
    disknum  = 0
    numdisks = 0
    if m:
        disknum = m.group(1)
        if disknum == 'A':
            disknum = 1
        elif disknum == 'B':
            disknum = 2
        else:
            disknum = int(disknum)
        for dir in os.listdir(parent):
            if not os.path.isdir(os.path.join(parent, dir)):
                continue
            m = re.search(r'(?:cd|dis[ck])\s+([AB]|\d+)\b', dir, flags=re.IGNORECASE)
            if m:
                d = m.group(1)
                if d == 'A':
                    d = 1
                elif d == 'B':
                    d = 2
                else:
                    d = int(d)
                numdisks = max(numdisks, d)
    # Parse the files
    mp3 = []
    m4a = []
    for file in names:
        if file.startswith('.'):
            continue
        elif file.endswith('.m4a'):
            m4a.append(file)
        elif file.endswith('.mp3'):
            mp3.append(file)
        else:
            try:
                # Clean up the name
                if os.path.isdir(os.path.join(dirname, file)):
                    new = fix_name(file.decode("utf-8"))
                else:
                    new = fix_name_full(file.decode("utf-8"))
                #print os.path.join(dirname, file)
                if file.decode("utf-8") != new.decode("utf-8"):
                    print '  {0}\n    {1}'.format(file, new)
                    if not dryrun:
                        os.rename(os.path.join(dirname, file), os.path.join(dirname, new))
            except:
                print "  FILE:  "+os.path.join(dirname, file)
                raise
    # Now, parse the music files
    music   = []
    artists = {}
    is_comp = False
    artist  = None
    for file in m4a:
        # Load some info about this mp4 for later comparison
        (mp4, name, changed) = load_mp4(dirname, file, len(m4a), int(disknum), int(numdisks))
        # Setup for compilation detection
        if not is_comp:
            if artist:
                if artist != mp4[t4['artist']][0]:
                    is_comp = True
            else:
                artist = mp4[t4['artist']][0]
                if artist.lower() == 'various':
                    is_comp = True
            a_artist = mp4.get(t4['albumartist'], [None])[0]
            if a_artist and artist and a_artist != artist:
                is_comp = True
        # Save music files for later
        music.append({
            'file':    file,
            'name':    name,
            'mp4':     mp4,
            'changed': changed,
            })
    for file in mp3:
        # Load some info about this mp4 for later comparison
        (mp3, name, changed) = load_mp3(dirname, file, len(mp3), disknum, numdisks)
        # Setup for compilation detection
        if not is_comp:
            if artist:
                if t3['artist'] in mp3 and artist != mp3[t3['artist']].text[0]:
                    is_comp = True
            elif t3['artist'] in mp3:
                artist = mp3[t3['artist']].text[0]
                if artist.lower() == 'various':
                    is_comp = True
            if t3['albumartist'] in mp3:
                a_artist = mp3[t3['albumartist']].text[0]
                if a_artist and artist and a_artist != artist:
                    is_comp = True
        # Save music files for later
        music.append({
            'file':    file,
            'name':    name,
            'mp3':     mp3,
            'changed': changed,
            })
    if len(artists) > 1:
        is_comp = True
    # Now parse the music files that we found
    for group in music:
        # Load the data from the group, for easier manipulation
        file    = group['file']
        name    = group['name']
        changed = group['changed']
        #print file
        if 'mp4' in group:
            m = group['mp4']
            # Compilation?
            compilation = m.get(t4['partofcompilation'])
            if is_comp and not compilation:
                compilation = True
                m[t4['partofcompilation']] = True
                changed.append('partofcompilation')
            a_artist = m.get(t4['albumartist'], [None])[0]
            if compilation and not a_artist:
                m[t4['albumartist']] = ['Various']
                changed.append('albumartist')
        elif 'mp3' in group:
            m = group['mp3']
            # Compilation?
            compilation = None
            if t3['partofcompilation'] in m:
                compilation = m[t3['partofcompilation']].text[0]
            if is_comp and not compilation:
                m[t3['partofcompilation']] = id3.TCMP(0, '1')
                changed.append('partofcompilation')
            if compilation and not (t3['albumartist'] in m and m[t3['albumartist']].text[0]):
                m[t3['albumartist']] = id3.TPE2(0, 'Various')
                changed.append('albumartist')
        # Save
        if changed and len(changed) > 0:
            print "  Save {0}\n    {1}".format(file, ','.join(changed))
            if not dryrun:
                m.save()
        if name:
            print '  {0}\n    {1}'.format(file, name)
            if not dryrun:
                os.rename(os.path.join(dirname, file), os.path.join(dirname, name))

if len(sys.argv) > 1:
    path = os.path.abspath(sys.argv[1])
else:
    path = os.path.abspath('.')
print path

os.path.walk(path, visit, None)
