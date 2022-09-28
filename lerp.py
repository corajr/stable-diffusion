import argparse
import itertools
import numpy as np
import os
import subprocess
from scripts import dream
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-A', '--sampler', help='Sampler type.', default='k_euler_a')
    parser.add_argument('-H', '--width', help='Width of video.', default=512)
    parser.add_argument('-W', '--height', help='Height of video.', default=512)
    parser.add_argument('-r', '--rate', help='Framerate of video.', default=12)
    parser.add_argument('-s', '--steps', help='Steps to sample.', default=30)
    parser.add_argument('-S', '--seed', help='Seed shared between images', default=1)
    parser.add_argument('--timestamps', help='File with floats of each line of infile.', default='')
    parser.add_argument('--audio', help='File with audio.', default='')
    parser.add_argument('-t', '--inbetweens', help='Number of frames to interpolate.', default=12)
    parser.add_argument('--style', help='Style appended to each prompt')
    parser.add_argument('infile')
    args = parser.parse_args()

    path, _ = os.path.splitext(args.infile)
    path = path + "_" + str(args.seed)
    prefix = os.path.basename(path)
    prompt_file = path + '_lerp.txt'

    with open(args.infile, 'r') as f:
        lines = f.readlines()
    
    inbetweens = list(gen_inbetweens(lines, args))
    if not os.path.exists(prompt_file):
        with open(prompt_file, 'w') as f:
            f.writelines(inbetweens)

    if not os.path.exists(path):
        dream.main(args=["--from_file", prompt_file, "--outdir", path])

    if os.path.exists(args.timestamps):
        with open(args.timestamps, 'r') as f:
            timestamps = [float(x.strip()) for x in f.readlines()]

        srtfile = f'{prefix}.srt'
        if not os.path.exists(srtfile):
            subtitles = []
            for i, (t_1, t_2)in enumerate(itertools.pairwise(timestamps)):
                t_1 = datetime.timedelta(seconds=t_1)
                t_2 = datetime.timedelta(seconds=t_2)
                subtitles.append(srt.Subtitle(i, t_1, t_2, lines[i]))
            with open(srtfile, 'w') as f:
                f.write(srt.compose(subtitles))
    else:
        timestamps = range(len(inbetweens))
    outfile = f"{prefix}.mp4"
    if not os.path.exists(outfile):
        img_glob = os.path.join(path, f"%06d.{args.seed}.png")
        maybe_audio = f"-i {args.audio}" if args.audio else ""
        FFMPEG_COMMAND = f"""
    ffmpeg {maybe_audio} -start_number 1 -i {img_glob} \
        -vf "settb=1/1000,setpts='{make_setpts(timestamps, args.inbetweens)}'" \
        -vsync vfr \
        -c:v libx264 \
        -enc_time_base 1/1000 \
        -pix_fmt yuv420p \
        {prefix}.mp4
    """
        print(FFMPEG_COMMAND)
        subprocess.run(FFMPEG_COMMAND, shell=True)


def gen_inbetweens(lines, args):
    style_suffix = (', ' + args.style) if args.style else ''
    for line1, line2 in itertools.pairwise(lines):
        line1 = line1.strip().replace(':', '') + style_suffix
        line2 = line2.strip().replace(':', '') + style_suffix
        for a in np.linspace(0.0, 1.0, endpoint=False, num=args.inbetweens):
            yield f"{line1}:{1.0-a} {line2}:{a} -A {args.sampler} -s {args.steps} -W {args.width} -H {args.height} -S {args.seed}\n"


def make_setpts(timestamps, inbetweens=12):
    """Return a setpts command from a series of timestamps.

    Args:
      timestamps: List of times in seconds.
      inbetweens: How many frames to interpolate.
    """
    fnum = 0
    clauses = 0
    tot = len(timestamps)
    setpts = 'if(eq(N,0),0,'
    for t_1, t_2 in itertools.pairwise(timestamps):
        duration = ((t_2 - t_1) * 1000.0) / (inbetweens - 0.5)
        clause = f'if(lte(N, {fnum}), PREV_OUTPTS + {duration},'
        setpts += clause
        fnum += inbetweens
        clauses += 1
    setpts += ')' * (clauses + 1)
    return setpts




if __name__ == '__main__':
    main()
