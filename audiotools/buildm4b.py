"""
@todo Put these variables into CLI config?
"""

# Force build, regardless of meta data
force = True

# Group by disk numbers?
group_by_disk = False

# Max length (in seconds) for each segment
# max_length = 60 * 60 * 20
max_length = None

# Maximum size (in megabytes) for each segment
max_size = 300
max_size = None

###############################################################################

import os, sys, re
import shutil
import subprocess
from mutagen.mp4 import MP4

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
}


def newburn():
    return {
        "chapters": "",
        "tracks": [],
        "tlen": 0.0,
        "tsize": 0.0,
        "disknum": 0,
        "tmin": None,
        "tmax": None,
    }


def timestr(secs):
    (secs, ms) = str(secs).split(".")
    ms = float(ms[0:3] + "." + ms[3:])
    secs = int(secs)
    hours = int(secs // 3600)
    secs = secs % 3600
    mins = int(secs // 60)
    secs = secs % 60
    return "{0:02}:{1:02}:{2:02}.{3:03.0f}".format(hours, mins, secs, ms)


def pick_file(*paths) -> str:
    for file in paths:
        if os.path.exists(file):
            return file
    raise Exception(f"no file found from paths: {paths}")


def encode(title, burn, meta):
    safe_title = title.replace("/", "-")
    chapterfile = f"{safe_title}.chapters.txt"
    outfile = "{0}.m4b".format(safe_title)
    # Run mp4box
    # Some versions (0.4.5 and below?) limit to 20 files per run
    # numruns = (len(burn['tracks']) + 19) / 20
    # for i in range(numruns):
    #    index = i * 20
    if True:
        i = 0
        call = ["MP4Box", "-force-cat"]
        # for tpath in burn['tracks'][index:index+20]:
        for tpath in burn["tracks"]:
            call += ["-cat", str(tpath)]
        if i == 0:
            call += ["-new"]
        call += [str(outfile)]
        print(call)
        subprocess.call(call)
    # Add the appropriate meta tags
    m = MP4(outfile)
    m[t4["genre"]] = ["Audiobook"]
    m[t4["title"]] = [title]
    for key in (
        "artist",
        "album",
        "comment",
        "year",
        "grouping",
        "composer",
        "comment",
        "description",
    ):
        if key in meta and meta[key]:
            m[t4[key]] = [meta[key]]
    #'numtracks': numtracks,
    m.save()
    # Create the chapters file, chapterize, cleanup
    if os.path.exists("overdrive_chapters.txt"):
        shutil.copyfile("overdrive_chapters.txt", chapterfile)
    else:
        with open(chapterfile, "w") as file:
            file.write(burn["chapters"])
    subprocess.call(["mp4chaps", "--import", outfile])
    # os.unlink(chapterfile)
    # Add a cover image?
    if os.path.exists(burn["cover"]):
        subprocess.call(["mp4art", "--remove", outfile])
        subprocess.call(["mp4art", "--add", burn["cover"], outfile])
    # chmod (os.chmod() feels messy)
    subprocess.call(["chmod", "644", outfile])


def main():
    if len(sys.argv) > 1:
        path = os.path.abspath(sys.argv[1])
    else:
        path = os.path.abspath(".")
    print(path)
    os.chdir(path)
    # Load the files
    files = [
        filename
        for filename in os.listdir(".")
        if filename.endswith(".m4a") or filename.endswith(".m4b")
    ]
    files.sort()
    # Init
    burns = []
    burn = newburn()
    meta = {}
    chapters = ""
    num_tracks = 0
    for file in files:
        # Preload the file size (something about MP4() can cause issues with stat)
        filesize = os.path.getsize(file) / (1024 * 1024)
        # Load the m4a info
        m = MP4(file)
        # Title, for the chapter name
        # print file
        try:
            title = m[t4["title"]][0].strip()
        except Exception as e:
            print(f"No title in file {file}")
            raise e
        # Disk number
        try:
            (disknum, numdisks) = m["disk"][0]
        except:
            disknum = numdisks = 0
        if group_by_disk and burn["disknum"] and burn["disknum"] != disknum:
            burns.append(burn)
            burn = newburn()
        burn["disknum"] = disknum
        # Need cover art?
        cover_name = "cover_{0}.jpg".format(disknum)
        if not os.path.exists(cover_name) and m.get("covr"):
            if len(m["covr"][0]) > 0:
                with open(cover_name, "wb") as covrfile:
                    covrfile.write(m["covr"][0])
        if os.path.exists(cover_name) and not os.path.exists("cover.jpg"):
            burn["cover"] = cover_name
        if os.path.exists("folder.jpg") and not os.path.exists("cover.jpg"):
            burn["cover"] = "folder.jpg"
        else:
            burn["cover"] = "cover.jpg"
        # Track number
        try:
            (tracknum, numtracks) = m["trkn"][0]
        except:
            tracknum = numtracks = 0
        if burn["tmin"] == None or int(tracknum) <= int(burn["tmin"]):
            burn["tmin"] = tracknum
        if burn["tmax"] == None or int(tracknum) >= int(burn["tmax"]):
            burn["tmax"] = tracknum
        if numtracks > num_tracks:
            num_tracks = numtracks
        # Other info
        track = {
            "artist": m.get(t4["artist"], [""])[0].strip(),
            "album": m.get(t4["album"], [""])[0].strip(),
            "comment": m.get(t4["comment"], [""])[0].strip(),
            "grouping": m.get(t4["grouping"], [""])[0].strip(),
            "year": m.get(t4["year"], [""])[0].strip(),
            "disknum": disknum,
            "numdisks": numdisks,
            "numtracks": numtracks,
        }
        # Compare with all-album meta
        for key in (
            "artist",
            "album",
            "comment",
            "grouping",
            "year",
            "numdisks",
            "numtracks",
        ):
            if not force and key in meta:
                if track[key] != meta[key]:
                    raise ValueError(
                        "{0} Mismatch:  {1} != {2}".format(key, track[key], meta[key])
                    )
            else:
                meta[key] = track[key]
        # Length and chapter info
        print(title)
        burn["chapters"] += f"{timestr(burn['tlen'])} {title}\n"
        burn["tlen"] += m.info.length
        # Keep track of file size
        burn["tsize"] += filesize
        # Add the file
        burn["tracks"].append(file)
        # Long enough to break out a chunk?
        if (max_length and burn["tlen"] >= max_length) or (
            max_size and burn["tsize"] >= max_size
        ):
            burns.append(burn)
            burn = newburn()
    if len(burn["tracks"]) > 0:
        burns.append(burn)

    for burn in burns:
        if len(burns) == 1:
            title = meta["album"]
        elif group_by_disk and meta["numdisks"]:
            title = "{0} - Disk {1} of {2}".format(
                meta["album"],
                str(burn["disknum"]).zfill(len(str(meta["numdisks"]))),
                meta["numdisks"],
            )
        else:
            title = "{0} - {1}-{2} of {3}".format(
                meta["album"],
                str(burn["tmin"]).zfill(max(2, len(str(num_tracks)))),
                str(burn["tmax"]).zfill(max(2, len(str(num_tracks)))),
                meta["numtracks"],
            )
        encode(title, burn, meta)
