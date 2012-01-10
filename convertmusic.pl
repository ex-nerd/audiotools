#!/usr/bin/perl -w
#
# Convert music files from one format (ogg/mp3) to another (aac)
#
# Get the Nero stuff from http://www.nero.com/eng/downloads-nerodigital-nero-aac-codec.php
#

# We need some extra libraries
    use Cwd 'abs_path';
    use Encode;
    use File::Basename;
    use File::Copy;
    use File::Find;
    use File::Temp qw/ tempfile /;
    use Getopt::Long;
    use MP3::Tag;

# Define the global genre variable, and load the genres
    my %mp3_genres;
    load_mp3_genres();

# Load in the commandline arguments
    my ($destdir, $format, $aac_bitrate, $mp3_min_bitrate, $mp3_max_bitrate, $filter);
    GetOptions('dest|path=s'               => \$destdir,
               'format|out|type=s'         => \$format,
               'aac_bitrate=i'             => \$aac_bitrate,
               'mp3_min_bitrate|mp3_min=i' => \$mp3_min_bitrate,
               'mp3_max_bitrate|mp3_max=i' => \$mp3_max_bitrate,
               'filter=s' => \$filter
              );

# Defaults
    $format          ||= 'm4a';
    $destdir         ||= $format.'_out';
    $aac_bitrate     ||= 192;
    $mp3_min_bitrate ||= 96;
    $mp3_max_bitrate ||= 320;

# Checks
    $destdir = abs_path($destdir);
    $format  = lc($format);
    $format  = 'm4a' if ($format eq 'aac');
    die "output format must be m4a, ogg or mp3\n" unless ($format =~ /^(m4a|mp3|ogg)$/);

    die "$destdir exists but is not a directory" if (-e $destdir && ! -d $destdir);

# Program checks
# @todo make this smarter so it only cares about what we'll actually use
    foreach my $prog ('mpg321', 'lame',
                      'ogg123', 'oggenc', 'vorbiscomment',
                      'flac',
                      'neroAacEnc', 'neroAacTag') {
        my $test = find_program($prog);
        die "You need $prog to continue.\n" unless ($test);
    }

# Make the destination directory
    if (!-d $destdir) {
        mkdir $destdir or die "Can't create $destdir:  $!\n";
    }

# Default to scan the current directory
    @ARGV = ('.') unless (@ARGV);

# Prep
    $filter = qr/$filter/ if ($filter);

# Process the directories passed in
    foreach my $path (@ARGV) {
        next unless (-e $path);
    # In order to get proper access to parent directory names, we have to do the chdir ourselves
        finddepth({wanted => \&process, no_chdir => 1}, $path);
    }

# Done
    exit;

###############################################################################

# Process a found file
    sub process {
        my $path = $File::Find::name;
    # Not a file
        return unless (-f $path);
    # Ignore files that we've created ourselves
        return if (substr(abs_path($path), 0, length $destdir) eq $destdir);
    # Not the kind of file we want
        return if ($filter && $path !~ /$filter/i);
        return unless ($path =~ /\.(ogg|mp3|flac)$/i);
    # Initialize some variables
        my (%info,
            $ignore,
            $command);
    # Get some info about the file
        my $type      = lc($1);
        my $dir       = dirname($path);
        my $file      = basename($path);
        my $safe_path = shell_safe($path);
    # Extract the comments and build the decoder command
        if ($type eq 'ogg') {
            $command = 'ogg123 -d wav -f - '.$safe_path;
            my $out = `vorbiscomment $safe_path`;
            ($info{'track'})     = $out =~ /^TRACKNUMBER=(.+)$/mi;
            ($info{'numtracks'}) = $out =~ /^TRACKTOTAL=(.+)$/mi;
            ($info{'disknum'})   = $out =~ /^DISCNUMBER=(.+)$/mi;
            ($info{'title'})     = $out =~ /^TITLE=(.+)$/mi;
            ($info{'artist'})    = $out =~ /^ARTIST=(.+)$/mi;
            ($info{'album'})     = $out =~ /^ALBUM=(.+)$/mi;
            ($info{'genre'})     = $out =~ /^GENRE=(.+)$/mi;
            ($info{'year'})      = $out =~ /^DATE=(\d+)$/mi;
            ($info{'composer'})  = $out =~ /^COMPOSER=(\d+)$/mi;
        }
        elsif ($type eq 'm4a' || $type eq 'aac') {
            $command = 'faad -o /dev/stdout '.$safe_path;
            my $out = `neroAacTag -list-meta $safe_path`;
            ($info{'track'})     = $out =~ /^\s+track = (.+)$/mi;
            ($info{'numtracks'}) = $out =~ /^\s+totaltracks = (.+)$/mi;
            ($info{'disknum'})   = $out =~ /^\s+disc = (.+)$/mi;
            ($info{'numdisks'})  = $out =~ /^\s+totaldiscs = (.+)$/mi;
            ($info{'title'})     = $out =~ /^\s+title = (.+)$/mi;
            ($info{'artist'})    = $out =~ /^\s+artist = (.+)$/mi;
            ($info{'album'})     = $out =~ /^\s+album = (.+)$/mi;
            ($info{'genre'})     = $out =~ /^\s+genre = (.+)$/mi;
            ($info{'year'})      = $out =~ /^\s+year = (\d+)$/mi;
            ($info{'composer'})  = $out =~ /^\s+writer = (\d+)$/mi;
        }
        elsif ($type eq 'flac') {
            $command = 'flac -d -c '.$safe_path;
            my $out = `metaflac --export-tags-to=- $safe_path`;
            ($info{'track'})       = $out =~ /^\s*tracknumber=(.+)$/mi;
            ($info{'disknum'})     = $out =~ /^\s*discnumber=(.+)$/mi;
            ($info{'numdisks'})    = $out =~ /^\s*totaldiscs=(.+)$/mi;
            ($info{'title'})       = $out =~ /^\s*title=(.+)$/mi;
            ($info{'artist'})      = $out =~ /^\s*artist=(.+)$/mi;
            ($info{'album'})       = $out =~ /^\s*album=(.+)$/mi;
            ($info{'genre'})       = $out =~ /^\s*genre=(.+)$/mi;
            ($info{'year'})        = $out =~ /^\s*date=(\d+)$/mi;
        }
        else {
            $command = 'mpg321 --wav /dev/stdout '.$safe_path;
            my $mp3 = MP3::Tag->new($path);
            $mp3->get_tags;
            if ($mp3->{'ID3v2'}) {
                ($info{'track'},    $ignore) = $mp3->{'ID3v2'}->get_frame('TRCK');
                ($info{'title'},    $ignore) = $mp3->{'ID3v2'}->get_frame('TIT2');
                ($info{'artist'},   $ignore) = $mp3->{'ID3v2'}->get_frame('TPE1');
                ($info{'album'},    $ignore) = $mp3->{'ID3v2'}->get_frame('TALB');
                ($info{'genre'},    $ignore) = $mp3->{'ID3v2'}->get_frame('TCON');
                ($info{'year'},     $ignore) = $mp3->{'ID3v2'}->get_frame('TYER');
                ($info{'composer'}, $ignore) = $mp3->{'ID3v2'}->get_frame('TCOM');
                ($info{'url'},      $ignore) = $mp3->{'ID3v2'}->get_frame('WXXX');
                ($info{'disknum'},  $ignore) = $mp3->{'ID3v2'}->get_frame('TPOS');
            }
            if ($mp3->{'ID3v1'}) {
                $info{'track'}  ||= $mp3->{'ID3v1'}->track;
                $info{'title'}  ||= $mp3->{'ID3v1'}->song;
                $info{'artist'} ||= $mp3->{'ID3v1'}->artist;
                $info{'album'}  ||= $mp3->{'ID3v1'}->album;
                $info{'genre'}  ||= $mp3->{'ID3v1'}->genre;
                $info{'year'}   ||= $mp3->{'ID3v1'}->year;
            }
        }
    # Clean up the info
        $info{'track'}    = fix_utf8($info{'track'}    or '');
        $info{'title'}    = fix_utf8($info{'title'}    or '');
        $info{'artist'}   = fix_utf8($info{'artist'}   or '');
        $info{'album'}    = fix_utf8($info{'album'}    or '');
        $info{'genre'}    = fix_utf8($info{'genre'}    or '');
        $info{'year'}     = fix_utf8($info{'year'}     or '');
        $info{'composer'} = fix_utf8($info{'composer'} or '');
        $info{'disknum'}  = fix_utf8($info{'disknum'}  or '');
        if ($info{'track'} && $info{'track'} =~ /^(\d+)\/(\d*)$/) {
            $info{'track'}     = $1;
            $info{'numtracks'} = $2;
        }
        $info{'numdisks'} ||= 0;
        if ($info{'disknum'} && $info{'disknum'} =~ /^(\d+)\/(\d*)$/) {
            $info{'disknum'}  = $1;
            $info{'numdisks'} = $2;
        }
        $info{'numdisks'} ||= 0;
    # Create the destination directory
        my $thisdir = clean_filename("$info{'artist'} - $info{'album'}");
        if (!-d "$destdir/$thisdir") {
            mkdir "$destdir/$thisdir" or die "Can't create $destdir/$thisdir:  $!\n";
        }
        if ($info{'numdisks'} && $info{'numdisks'} > 1 && $info{'disknum'}) {
            $thisdir .= "/Disk $info{'disknum'}";
            if (!-d "$destdir/$thisdir") {
                mkdir "$destdir/$thisdir" or die "Can't create $destdir/$thisdir:  $!\n";
            }
        }
    # Get a new name
        my $dest = "$destdir/$thisdir/".clean_filename($file);
        $dest =~ s/\.$type$/.$format/i;
    # Find cover art
        opendir(DIR, $dir) or die "Can't open $dir:  $!\n";
        my @files = sort grep(/cover|front/, grep(/\.(jpe?g|gif|png)$/, readdir(DIR)));
        closedir(DIR);
        my $cover = shift @files;
    # Pipe
        $command .= ' | ';
    # Output m4a?
        if ($format eq 'm4a') {
            my $tmp = "/tmp/m4a_enc.$$.wav";
            $command =~ s/ \| $/ > $tmp/;
            print "COMMAND1:  $command\n";
            system($command);
        # Finish the command
            $command = "neroAacEnc -br ${aac_bitrate}000 -2pass -if $tmp -of ".shell_safe($dest);
            print "COMMAND2:  $command\n";
            system($command);
            unlink $tmp;
        # Tag the file
            $command = 'neroAacTag '.shell_safe($dest)
                .' -meta:track='.shell_safe($info{'track'})
                .' -meta:totaltracks='.shell_safe($info{'numtracks'})
                .' -meta:disc='.shell_safe($info{'disknum'})
                .' -meta:totaldiscs='.shell_safe($info{'numdisks'})
                .' -meta:title='.shell_safe($info{'title'})
                .' -meta:artist='.shell_safe($info{'artist'})
                .' -meta:album='.shell_safe($info{'album'})
                .' -meta:genre='.shell_safe($info{'genre'})
                .' -meta:year='.shell_safe($info{'year'})
                .' -meta:composer='.shell_safe($info{'composer'})
                ;
        # Found cover art?
            if ($cover) {
                $command .= ' -add-cover:front:'.shell_safe(resize_cover_art("$dir/$cover", "$destdir/$thisdir"));
            }
        # Execute the command
            #$command .= ' /dev/stdin';
            print "COMMAND3:  $command\n";
            system($command);
        # Touch
            open DATA, ">$destdir/$thisdir/please_rerip";
            close DATA;
        }
    # Output mp3?
        elsif ($format eq 'mp3') {
            $command .= "lame -k -m j --vbr-new -V 0 -b $mp3_min_bitrate "
                       ." -B $mp3_max_bitrate /dev/stdin ".shell_safe($dest);
        # Execute the command
            system($command);
        # Guess the v1 genre?
            my $v1_genre = -1;
            foreach my $mp3_genre (reverse sort by_length keys %mp3_genres) {
                next unless ($mp3_genre && $info{'genre'} =~ /\b$mp3_genre\b/i);
                $v1_genre = $mp3_genres{$mp3_genre};
                last;
            }
        # open the mp3 and grab the tags
            my $mp3 = MP3::Tag->new($dest);
            $mp3->get_tags;
        # wipe out the existing ID3 tags
            $mp3->{ID3v1}->remove_tag if (exists $mp3->{ID3v1});
            $mp3->{ID3v2}->remove_tag if (exists $mp3->{ID3v2});
        # Build a new ID3v1 tag
            $mp3->new_tag('ID3v1');
            $mp3->{ID3v1}->track($info{'numtracks'} ? "$info{'track'}/$info{'numtracks'}" : $info{'track'});
            $mp3->{ID3v1}->song(fix_utf8($info{'title'},    1));
            $mp3->{ID3v1}->artist(fix_utf8($info{'artist'}, 1));
            $mp3->{ID3v1}->album( fix_utf8($info{'album'},  1));
            $mp3->{ID3v1}->genre($v1_genre)    if ($v1_genre >= 0);
            $mp3->{ID3v1}->year($info{'year'}) if ($info{'year'});
        # Build a new ID3v2 tag
            $mp3->new_tag('ID3v2');
            $mp3->{ID3v2}->add_frame('TRCK', $info{'numtracks'} ? "$info{'track'}/$info{'numtracks'}" : $info{'track'});
            $mp3->{ID3v2}->add_frame('TIT2', fix_utf8($info{'title'},  1));
            $mp3->{ID3v2}->add_frame('TPE1', fix_utf8($info{'artist'}, 1));
            $mp3->{ID3v2}->add_frame('TALB', fix_utf8($info{'album'},  1));
            $mp3->{ID3v2}->add_frame('TCON', fix_utf8($info{'genre'},  1));
            $mp3->{ID3v2}->add_frame('TYER', $info{'year'}) if ($info{'year'});
        # Cover art
        # This doesn't work...
        #    if ($cover) {
        #    # Read in the resized cover data
        #        my $tmp = resize_cover_art("$dir/$cover", "$destdir/$thisdir");
        #        open(DATA, $tmp) or die "Can't read cover art tempfile $tmp:  $!\n";
        #        my $data = '';
        #        $data .= $_ while (<DATA>);
        #        close DATA;
        #    # Set the tag
        #        $mp3->{ID3v2}->add_frame('APIC',
        #                                 (chr(0x0), 'image/png', chr(0x3), 'Cover Image'),
        #                                 $data);
        #    }
        # Save the tags
            $mp3->{ID3v2}->write_tag;
            $mp3->{ID3v1}->write_tag;
            $mp3->close();
        }
    # Output ogg?
        elsif ($format eq 'ogg') {
        # Execute the command
            $command .= 'oggenc -q 6 -o '.shell_safe($dest).' /dev/stdin';
            system($command);
        # Save the tags
            my $data = '';
            $data .= "TITLE=$info{'title'}\n"          if ($info{'title'});
            $data .= "ARTIST=$info{'artist'}\n"        if ($info{'artist'});
            $data .= "ALBUM=$info{'album'}\n"          if ($info{'album'});
            $data .= "DISCNUMBER=$info{'disknum'}\n"   if ($info{'disknum'});
            $data .= "DATE=$info{'year'}\n"            if ($info{'year'});
            $data .= "TRACKNUMBER=$info{'track'}\n"    if ($info{'track'});
            $data .= "TRACKTOTAL=$info{'numtracks'}\n" if ($info{'numtracks'});
            $data .= "GENRE=$info{'genre'}\n"          if ($info{'genre'});
            $data .= "COMPOSER=$info{'composer'}\n"    if ($info{'composer'});
            #$data .= "DESCRIPTION=$info{'title'}\n"    if ($info{'title'});
            #$data .= "COMMENT=$info{'title'}\n"        if ($info{'title'});
            #$data .= "PERFORMER=$info{'title'}\n"      if ($info{'title'});
            #$data .= "COPYRIGHT=$info{'copyright'}\n"  if ($info{'copyright'});
            #$data .= "LICENSE=$info{'url'}\n"          if ($info{'url'});
            open(OGG, '| vorbiscomment -w '.shell_safe($dest)) or die "Can't open pipe to vorbiscomment:  $!\n\n";
            print OGG $data;
            close OGG;
        }
    # Size check
        if (-s $path < -s $dest) {
            #die "Bitrate needs adjustment downward:  ".(-s $path).' < '.(-s $dest)."\n";
        }
    }

# Done!
    exit;

################################################################################


# This converts a string from UTF-8 or Latin1 character set to proper UTF-8
# Set $undo to true, and it will undo the process, returning a latin1 string
# (which is needed for mp3 files because they can't handle UTF-8)
    sub fix_utf8 {
        my $str  = shift;
        my $undo = shift;
    # Return Early?
        return '' unless ($str && length($str));
    # Get a temp var so we don't actually modify $str
        my $tmp = $str;
    # Decode the string to UTF-8 and check for malformed characters - if there are some, this isn't already UTF-8
        Encode::_utf8_on($tmp);
        my $is_utf8 = Encode::is_utf8($tmp, Encode::FB_QUIET);
    # Undoing utf-8?
        if ($undo) {
        # Malformed utf-8 characters, this is probably NOT utf-8
            return $str if (!$is_utf8);
        # Now we convert back to iso-8859-1
            Encode::from_to($str, 'utf-8', 'iso-8859-1');
            return $str;
        }
    # No malformed characters - this is already UTF-8 - convert it back to latin1 check again to make sure that it's encoded properly
        if ($is_utf8) {
            Encode::from_to($str, 'utf-8', 'iso-8859-1');
        # Check again to see if it wasn't just a malformed string
            $tmp = $str;
            Encode::_utf8_on($tmp);
            $is_utf8 = Encode::is_utf8($tmp, Encode::FB_QUIET);
            if ($is_utf8) {
                Encode::from_to($str, 'utf-8', 'iso-8859-1');
            }
        }
    # Now we decode from iso-8859-1
        Encode::from_to($str, 'iso-8859-1', 'utf-8');
        return $str;
    }

# Clean up a filename so that it's safe for use in Windows or MacOS
    sub clean_filename {
        my $file = (shift or '');
        $file =~ s/^(\d+)\W+/$1 /;
        $file =~ s/(?:[\-\/\\:*?<>|]+\s*)+(?=[^\d\s])/- /sg;
        $file =~ tr/!?//d;
        $file =~ tr/\/\\:*<>|/-/;
        $file =~ s/^[\-\ ]+//s;
        $file =~ s/[\-\ ]+$//s;
        return $file;
    }

# Return an escaped string that's safe for use on the commandline
    sub shell_safe {
        my $str = (shift or '');
        $str =~ s/'/'\\''/sg;
        return "'$str'";
    }

# Return the path to the resized cover artwork
    sub resize_cover_art {
        my $path = shift;
        my $dest = shift;
    # Not created
        unless (-e "$dest/cover.jpg") {
            my $safe_path = shell_safe($path);
            my $safe_dest = shell_safe("$dest/cover.jpg");
            system("convert -geometry '1024x1024>' -quality 6 $safe_path jpg:$safe_dest");
        }
    # Return
        return "$dest/cover.jpg";
    }

# Sort based on the length of the string
    sub by_length {
        return $a cmp $b if (length $a == length $b);
        return length $a <=> length $b;
    }

# Load the mp4 genres into a hash (here so it doesn't have to live at the top
# of the file).
    sub load_mp3_genres {
        %mp3_genres = (
            'Blues'                  => 0,
            'Classic Rock'           => 1,
            'Country'                => 2,
            'Dance'                  => 3,
            'Disco'                  => 4,
            'Funk'                   => 5,
            'Grunge'                 => 6,
            'Hip-Hop'                => 7,
            'Jazz'                   => 8,
            'Metal'                  => 9,
            'New Age'                => 10,
            'Oldies'                 => 11,
            'Other'                  => 12,
            'Pop'                    => 13,
            'R&B'                    => 14,
            'Rap'                    => 15,
            'Reggae'                 => 16,
            'Rock'                   => 17,
            'Techno'                 => 18,
            'Industrial'             => 19,
            'Alternative'            => 20,
            'Ska'                    => 21,
            'Death Metal'            => 22,
            'Pranks'                 => 23,
            'Soundtrack'             => 24,
            'Euro-Techno'            => 25,
            'Ambient'                => 26,
            'Trip-Hop'               => 27,
            'Vocal'                  => 28,
            'Jazz+Funk'              => 29,
            'Fusion'                 => 30,
            'Trance'                 => 31,
            'Classical'              => 32,
            'Instrumental'           => 33,
            'Acid'                   => 34,
            'House'                  => 35,
            'Game'                   => 36,
            'Sound Clip'             => 37,
            'Gospel'                 => 38,
            'Noise'                  => 39,
            'Alt. Rock'              => 40,
            'Bass'                   => 41,
            'Soul'                   => 42,
            'Punk'                   => 43,
            'Space'                  => 44,
            'Meditative'             => 45,
            'Instrumental Pop'       => 46,
            'Instrumental Rock'      => 47,
            'Ethnic'                 => 48,
            'Gothic'                 => 49,
            'Darkwave'               => 50,
            'Techno-Industrial'      => 51,
            'Electronic'             => 52,
            'Pop-Folk'               => 53,
            'Eurodance'              => 54,
            'Dream'                  => 55,
            'Southern Rock'          => 56,
            'Comedy'                 => 57,
            'Cult'                   => 58,
            'Gangsta Rap'            => 59,
            'Top 40'                 => 60,
            'Christian Rap'          => 61,
            'Pop/Funk'               => 62,
            'Jungle'                 => 63,
            'Native American'        => 64,
            'Cabaret'                => 65,
            'New Wave'               => 66,
            'Psychedelic'            => 67,
            'Rave'                   => 68,
            'Showtunes'              => 69,
            'Trailer'                => 70,
            'Lo-Fi'                  => 71,
            'Tribal'                 => 72,
            'Acid Punk'              => 73,
            'Acid Jazz'              => 74,
            'Polka'                  => 75,
            'Retro'                  => 76,
            'Musical'                => 77,
            'Rock & Roll'            => 78,
            'Hard Rock'              => 79,
            'Folk'                   => 80,
            'Folk Rock'              => 81,
            'National Folk'          => 82,
            'Swing'                  => 83,
            'Fast-Fusion'            => 84,
            'Bebob'                  => 85,
            'Latin'                  => 86,
            'Revival'                => 87,
            'Celtic'                 => 88,
            'Bluegrass'              => 89,
            'Avantgarde'             => 90,
            'Gothic Rock'            => 91,
            'Progressive Rock'       => 92,
            'Psychedelic Rock'       => 93,
            'Symphonic Rock'         => 94,
            'Slow Rock'              => 95,
            'Big Band'               => 96,
            'Chorus'                 => 97,
            'Easy Listening'         => 98,
            'Acoustic'               => 99,
            'Humour'                 => 100,
            'Speech'                 => 101,
            'Chanson'                => 102,
            'Opera'                  => 103,
            'Chamber Music'          => 104,
            'Sonata'                 => 105,
            'Symphony'               => 106,
            'Booty Bass'             => 107,
            'Primus'                 => 108,
            'Porn Groove'            => 109,
            'Satire'                 => 110,
            'Slow Jam'               => 111,
            'Club'                   => 112,
            'Tango'                  => 113,
            'Samba'                  => 114,
            'Folklore'               => 115,
            'Ballad'                 => 116,
            'Power Ballad'           => 117,
            'Rhythmic Soul'          => 118,
            'Freestyle'              => 119,
            'Duet'                   => 120,
            'Punk Rock'              => 121,
            'Drum Solo'              => 122,
            'A Cappella'             => 123,
            'Euro-House'             => 124,
            'Dance Hall'             => 125,
            'Goa'                    => 126,
            'Drum & Bass'            => 127,
            'Club-House'             => 128,
            'Hardcore'               => 129,
            'Terror'                 => 130,
            'Indie'                  => 131,
            'BritPop'                => 132,
            'Negerpunk'              => 133,
            'Polsk Punk'             => 134,
            'Beat'                   => 135,
            'Christian Gangsta Rap'  => 136,
            'Heavy Metal'            => 137,
            'Black Metal'            => 138,
            'Crossover'              => 139,
            'Contemporary Christian' => 140,
            'Christian Rock'         => 141,
            'Merengue'               => 142,
            'Salsa'                  => 143,
            'Thrash Metal'           => 144,
            'Anime'                  => 145,
            'JPop'                   => 146,
            'Synthpop'               => 147
        );
    }

# This searches the path for the specified programs, and returns the
#   lowest-index-value program found, caching the results
BEGIN {
    my %find_program_cache;
    sub find_program {
    # Get the hash id
        my $hash_id = join("\n", @_);
    # No cache?
        if (!defined($find_program_cache{$hash_id})) {
        # Load the programs, and get a count of the priorities
            my (%programs, $num_programs);
            foreach my $program (@_) {
                $programs{$program} = ++$num_programs;
            }
        # No programs requested?
            return undef unless ($num_programs > 0);
        # Search for the program(s)
            my %found;
            foreach my $path (split(/:/, $ENV{'PATH'}), '.') {
                foreach my $program (keys %programs) {
                    if (-e "$path/$program" && (!$found{'name'} || $programs{$program} < $programs{$found{'name'}})) {
                        $found{'name'} = $program;
                        $found{'path'} = $path;
                    }
                    elsif ($^O eq "darwin" && -e "$path/$program.app" && (!$found{'name'} || $programs{$program} < $programs{$found{'name'}})) {
                        $found{'name'} = $program;
                        $found{'path'} = "$path/$program.app/Contents/MacOS";
                    }
                # Leave early if we found the highest priority program
                    last if ($found{'name'} && $programs{$found{'name'}} == 1);
                }
            }
        # Set the cache
            $find_program_cache{$hash_id} = ($found{'path'} && $found{'name'})
                                               ? $found{'path'}.'/'.$found{'name'}
                                               : '';
        }
    # Return
        return $find_program_cache{$hash_id};
    }
}
