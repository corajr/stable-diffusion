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
    parser.add_argument('-t', '--tweens', help='Number of frames to interpolate.', default=12)
    parser.add_argument('--style', help='Style appended to each prompt')
    parser.add_argument('infile')
    args = parser.parse_args()

    path, _ = os.path.splitext(args.infile)
    path = path + "_" + str(args.seed)
    prefix = os.path.basename(path)
    prompt_file = path + '_lerp.txt'

    with open(args.infile, 'r') as f:
        lines = f.readlines()

    style_suffix = (', ' + args.style) if args.style else ''
    if not os.path.exists(prompt_file):
        write_prompt_file(prompt_file, lines, style_suffix)

    if not os.path.exists(path):
        dream.main(args=["--from_file", prompt_file, "--outdir", path])

    outfile = f"{prefix}.mp4"
    if not os.path.exists(outfile):
        img_glob = os.path.join(path, f"%06d.{args.seed}.png")
        with open("chess_ts.txt", 'r') as f:
            timestamps = [float(x.strip()) for x in f.readlines()]
        FFMPEG_COMMAND = f"""
    ffmpeg -i chess.wav -start_number 1 -i {img_glob} \
        -vf "settb=1/1000,setpts='{make_setpts(timestamps, args.tweens)}'" \
        -vsync vfr \
        -c:v libx264 \
        -enc_time_base 1/1000 \
        -pix_fmt yuv420p \
        {prefix}.mp4
    """
        print(FFMPEG_COMMAND)
        subprocess.run(FFMPEG_COMMAND, shell=True)


def write_prompt_file(prompt_file, lines, style_suffix, args):
    with open(prompt_file, 'w') as f:
        for line1, line2 in itertools.pairwise(lines):
            line1 = line1.strip().replace(':', '') + style_suffix
            line2 = line2.strip().replace(':', '') + style_suffix
            for a in np.linspace(0.0, 1.0, endpoint=False, num=args.tweens):
                f.write(f"{line1}:{1.0-a} {line2}:{a} -A {args.sampler} -s {args.steps} -W {args.width} -H {args.height} -S {args.seed}\n")


def make_setpts(timestamps, tweens=12):
    """Return a setpts command from a series of timestamps.

    Args:
      timestamps: List of times in seconds.
    """
    fnum = 0
    clauses = 0
    tot = len(timestamps)
    setpts = 'if(eq(N,0),0,'
    for t_1, t_2 in itertools.pairwise(timestamps):
        duration = ((t_2 - t_1) * 1000.0) / (tweens - 0.5)
        clause = f'if(lte(N, {fnum}), PREV_OUTPTS + {duration},'
        setpts += clause
        fnum += tweens
        clauses += 1
    setpts += ')' * (clauses + 1)
    return setpts




if __name__ == '__main__':
    main()
