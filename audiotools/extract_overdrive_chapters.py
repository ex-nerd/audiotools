#!/usr/bin/env python3
#
# Recursively scans current or specified directory for all subdirectories
# containing mp3 files. If these mp3 files contain overdrive chapter markers
# (id3 tag), writes overdrive_chapters.txt to the same directory.
#
# Usage:
#
# extract_overdrive_chapters.py [optional directory path]
#
# Use with build_m4b from https://github.com/ex-nerd/audiotools
#
# Note: Due to overdrive low quality, there is no point in encoding aac files
# with better than: 64kbps stereo, HE, optimize for voice
#

import os, sys, re
import mutagen.id3 as id3
from mutagen.mp3 import MP3
from mutagen import File

from collections import OrderedDict


def timestr(secs):
    (secs, ms) = str(secs).split(".")
    ms = float(ms[0:3] + "." + ms[3:])
    secs = int(secs)
    hours = int(secs // 3600)
    secs = secs % 3600
    mins = int(secs // 60)
    secs = secs % 60
    return f"{hours:02}:{mins:02}:{secs:02}.{ms:03.0f}"


def load_mp3(total, dir, file):
    path = os.path.join(dir, file)
    audio = MP3(path)
    # print(audio.info.length)  # , audio.info.bitrate
    m = id3.ID3(path)

    data = m.get("TXXX:OverDrive MediaMarkers")
    if not data:
        print("Can't find TXXX data point for {0}".format(file))
        print(m.keys())
        return
    info = data.text[0]
    file_chapters = re.findall(
        r"<Name>\s*([^>]+?)\s*</Name><Time>\s*([\d:.]+)\s*</Time>", info, re.MULTILINE
    )
    chapters = []
    for chapter in file_chapters:
        (name, length) = chapter
        name = re.sub(r'^"(.+)"$', r"\1", name)
        name = re.sub(r"^\*(.+)\*$", r"\1", name)
        name = re.sub(
            r"\s*\([^)]*\)$", "", name
        )  # ignore any sub-chapter markers from Overdrive
        name = re.sub(
            r"\s+\(?continued\)?$", "", name
        )  # ignore any sub-chapter markers from Overdrive
        name = re.sub(
            r"\s+-\s*$", "", name
        )  # ignore any sub-chapter markers from Overdrive
        name = re.sub(
            r"^Dis[kc]\s+\d+\W*$", "", name
        )  # ignore any disk markers from Overdrive
        name = name.strip()
        t_parts = list(length.split(":"))
        t_parts.reverse()
        seconds = total + float(t_parts[0])
        if len(t_parts) > 1:
            seconds += int(t_parts[1]) * 60
        if len(t_parts) > 2:
            seconds += int(t_parts[2]) * 60 * 60
        chapters.append([name, seconds])
        # print(name, seconds)
    return (total + audio.info.length, chapters)


def visit(dirname, filenames):
    print(dirname)
    os.chdir(dirname)
    # Parse the files
    total = 0
    all_chapters = OrderedDict()
    for file in sorted(filenames):
        if file.endswith(".mp3"):
            (total, chapters) = load_mp3(total, dirname, file)
            # print(repr(chapters))
            for chapter in chapters:
                if chapter[0] in all_chapters.keys():
                    continue
                all_chapters[chapter[0]] = chapter[1]
    if len(all_chapters) > 0:
        with open("overdrive_chapters.txt", "w") as file:
            for name, length in all_chapters.items():
                chapstr = f"{timestr(length)} {name}"
                print(chapstr)
                file.write(chapstr + "\n")
    # print(repr(all_chapters))


def main():

    if len(sys.argv) > 1:
        path = os.path.abspath(sys.argv[1])
    else:
        path = os.path.abspath(".")

    for dirname, dirs, files in os.walk(path, topdown=True):
        dirs[:] = [d for d in dirs if d not in {".git", ".direnv"}]
        visit(dirname, files)
