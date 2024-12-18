import os, sys, re
import subprocess
import unicodedata
from mutagen.mp4 import MP4
from pprint import pprint

# https://mutagen.readthedocs.io/en/latest/api/mp4.html
t4 = {
    "album": "\xa9alb",
    "albumartist": "aART",
    "albumartistsortorder": "soaa",
    "albumsortorder": "soal",
    "artist": "\xa9ART",
    "artistsortorder": "soar",
    "bpm": "tmpo",
    "comment": "\xa9cmt",
    "composer": "\xa9wrt",
    "composersortorder": "soco",
    "copyright": "cprt",
    "description": "desc",
    "encodedby": "\xa9too",
    "genre": "\xa9gen",
    "grouping": "\xa9grp",
    "lyrics": "\xa9lyr",
    "partofcompilation": "cpil",
    "partofgaplessalbum": "pgap",
    "podcast": "pcst",
    "podcastcategory": "catg",
    "podcastepisodeguid": "egid",
    "podcastkeywords": "keyw",
    "podcasturl": "purl",
    "purchasedate": "purd",
    "showname": "tvsh",
    "showsortorder": "sosn",
    "title": "\xa9nam",
    "titlesortorder": "sonm",
    "year": "\xa9day",
    "tracknum": "trkn", # Tuple of track number and total tracks, e.g. [(12, 15),]
}

def main():
    if len(sys.argv) > 1:
        path = os.path.abspath(sys.argv[1])
    else:
        path = os.path.abspath(".")
    print(path)
    os.chdir(path)
    # Remove this useless file
    if os.path.exists('.DS_Store'):
        os.remove('.DS_Store')
    # Load the files
    files = [filename for filename in os.listdir(".") if filename.endswith(".m4b")]
    files.sort()
    # Do all files have the same grouping name? Autodetect
    filename_grouping = None
    for file in files:
        match = re.search(r"^([^\-]+?)\s+(\d+(?:\.\d+)?)\s+-\s+", file)
        # print(f"  {match}")
        if match and match.group(1):
            if not filename_grouping:
                filename_grouping = match.group(1)
            elif filename_grouping != match.group(1):
                filename_grouping = None
                print(f'Multiple potential groupings found: "{filename_grouping}" != "{match.group(1)}"')
                break
    # Now process the files
    for file in files:
        print(f"{file}")
        m = MP4(file)
        change = {}
        # Track numbers don't make sense for books
        if m.get(t4["tracknum"], []) != []:
            change["tracknum"] = []
        # Don't want these taking up space
        for remove_tag in ["copyright", "encodedby"]:
            if m.get(t4[remove_tag], []) != [""]:
                change[remove_tag] = ""
        # Grouping in the filename
        groupnum = None
        match = re.search(r"^([^\-]+?)\s+(\d+(?:\.\d+)?)\s+-\s+", file)
        # pprint({"match": match})
        if match and match.group(2):
            groupnum = match.group(2)
        # Artist
        artist = m.get(t4["artist"], [""])[0].strip()
        split_artist = [a.strip() for a in re.split(r'\s*/\s*', artist) if a.strip()]
        # Composer
        composer = m.get(t4["composer"], [""])[0].strip()
        if composer:
            composer = re.sub(r'^(Read|Narrated) by\b *', 'read by ', composer, re.IGNORECASE)
            composer = re.sub(r'\s+', ' ', composer).strip()
            if not composer.startswith('read by '):
                composer = f'read by {composer}'
            if composer != m.get(t4["composer"], [""])[0]:
                change["composer"] = composer.strip()
        elif len(split_artist) == 2:
            change["artist"] = split_artist[0].strip()
            change["composer"] = f'read by {split_artist[1]}'.strip()
        # Comments
        # pprint({"comments": m.get(t4["comment"], [])})
        comments = m.get(t4["comment"], [""])[0].strip()
        if comments:
            comments = re.sub(r'<.+?>', ' ', comments)
            comments = re.sub(r'[“”]', '"', comments)
            comments = re.sub(r'[‘’]', '\'', comments)
            comments = re.sub(r'\bb estselling\b', 'bestselling', comments, re.IGNORECASE)
            comments = re.sub(r'\(Unabridged\)', '', comments, re.IGNORECASE)
            comments = re.sub(r'\.\.+$', '…', comments)
            comments = re.sub(r' *\w+$', '…', comments)
            comments = re.sub(r'\\n', ' ', comments)
            comments = re.sub(r'[, ]+…$', '…', comments)
            comments = re.sub(r'(\.["\']?)\W*?…$', r'\g<1>', comments)
            comments = re.sub(r'\s+', ' ', comments).strip()
            if comments != m.get(t4["comment"], [""])[0]:
                change["comment"] = comments
        # Grouping?
        if groupnum:
            grouping = m.get(t4["grouping"], [""])[0].strip()
            if filename_grouping and not grouping:
                grouping = filename_grouping
            # pprint({"grouping": grouping})
            # Can add an album sort order?
            if grouping:
                sortorder = "{0} {1} - {2}".format(
                    grouping, groupnum, m[t4["title"]][0].strip()
                )
                sortorder = re.sub(r'\(Unabridged\)', '', sortorder, re.IGNORECASE)
                sortorder = sortorder.strip()

                if m.get(t4["albumsortorder"], [""])[0] != sortorder:
                    change["albumsortorder"] = sortorder
                if m.get(t4["titlesortorder"], [""])[0] != sortorder:
                    change["titlesortorder"] = sortorder
        # Save?
        if len(change) > 0:
            # print(file)
            for prop, value in change.items():
                m[t4[prop]] = value
                print(f"  {prop}: {value}")
            m.save()
        # chmod (os.chmod() feels messy)
        subprocess.call(["chmod", "644", file])
        # Cover art?
        if os.path.exists(file[:-4] + ".jpg"):
            subprocess.call(["mp4art", "--remove", file])
            subprocess.call(["mp4art", "--add", file[:-4] + ".jpg", file])
