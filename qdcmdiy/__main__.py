import sys
import argparse

def info(filename):
    import qdcmdiy.store
    db = qdcmdiy.store.load(filename)
    print("Modes:")
    for mode in db.get_mode_names():
        print(mode)

def patch(filename, mode, input_shaper, lut3d, output_shaper):
    import qdcmdiy.store
    import qdcmdiy.pipeline
    import qdcmdiy.data
    db = qdcmdiy.store.load(filename)
    mode = db.get_mode(mode)
    pipeline = qdcmdiy.pipeline.ColorPipeline()
    if input_shaper is not None:
        pipeline.degamma = qdcmdiy.data.load_lut3x1d(input_shaper)
    if lut3d is not None:
        pipeline.gamut = qdcmdiy.data.load_lut3d(lut3d)
    if output_shaper is not None:
        pipeline.gamma = qdcmdiy.data.load_lut3x1d(output_shaper)
    mode.set_color_pipeline(pipeline)
    with open(filename, 'w', encoding='utf-8') as f:
        db.dump(f)

def merge_lut(lut1_filename, lut2_filename, out_filename):
    import qdcmdiy.data
    import colour
    lut1 = qdcmdiy.data.load_anylut(lut1_filename)
    lut2 = qdcmdiy.data.load_anylut(lut2_filename)
    merged = type(lut1)(lut2.apply(lut1.table))
    colour.io.write_LUT_IridasCube(merged, out_filename)

def main():
    parser = argparse.ArgumentParser()

    commands = parser.add_subparsers(dest='command', metavar='command', )

    parser_info = commands.add_parser('info', help='show info of specified qdcm database file')
    parser_info.add_argument('filename', help='qdcm database file')

    parser_patch = commands.add_parser('patch', help='replace calibration pipeline in qdcm database file', formatter_class=argparse.RawTextHelpFormatter)
    parser_patch.add_argument('filename', help='qdcm database file')
    parser_patch.add_argument('--mode', help='the mode to be patched')
    parser_patch.add_argument('--input-shaper', help='3x1D LUT file for input shaper (8-bit input / 12-bit output)', metavar='FILE')
    parser_patch.add_argument('--3dlut', help='3D LUT file applied after input shaper (17x17x17 / 12-bit output)', dest='lut3d', metavar='FILE')
    parser_patch.add_argument('--output-shaper', help='3x1D LUT file applied after 3D LUT (10-bit input / output)', metavar='FILE')
    parser_patch.epilog = "Unspecified stages will be disabled. Other settings (e.g. game enhancement) is remain unchanged.\n\nSupported file formats:\n    IRIDAS/Resolve .cube\n    ArgyllCMS/DisplayCAL .cal"


    parser_merge_lut = commands.add_parser('merge-lut', help='merge two LUT files', formatter_class=argparse.RawTextHelpFormatter)
    parser_merge_lut.add_argument('lut1', help='first LUT file')
    parser_merge_lut.add_argument('lut2', help='second LUT file')
    parser_merge_lut.add_argument('out', help='output LUT file')
    parser_merge_lut.epilog = "out(input) = lut2(lut1(input))\n\nmerged LUT will have the same type and size as lut1\n\nSupported file formats:\n    IRIDAS/Resolve .cube\n    ArgyllCMS/DisplayCAL .cal"


    args = parser.parse_args()
    # print(args)
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    elif args.command == 'info':
        info(args.filename)
    elif args.command == 'patch':
        patch(args.filename, args.mode, args.input_shaper, args.lut3d, args.output_shaper)
    elif args.command == 'merge-lut':
        merge_lut(args.lut1, args.lut2, args.out)

if __name__ == '__main__':
    main()
