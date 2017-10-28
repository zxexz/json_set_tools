#! /usr/bin/env python3

import getopt
import sys
import json
from collections import deque
from functools import reduce


RNODE = '/'
LNODE = '[LIST]'
DNODE = '[DICT]'
LEAF = '[ITEM]'
REMAP = {RNODE: dict, LNODE: list, DNODE: dict, LEAF: lambda x: x}
SUMMARY=False

def usage():
    options = """    -i, --input-files=      - comma separated list of input JSON files (order is preserved)
    -o, --output=           - output file
    -l, --order-lists       - preserve order in lists in the diff (don't use of you don't care about order of list items in your diff)
    -p, --pretty            - you probably want this - if not it just dumps the internal structure of the diff set tuple
    -s, --summary           - reserved for future use
    -m, --output-map=       - comma separated list of functions to apply to input files. functions apply to the input json files in left to right order
                                a - additions across the files
                                s - subtractions across the files
                                u - union across the files
                                i - intersection across the files
                                e - each file
                                d - symmetric difference across the files"""
    print("USAGE: ",sys.argv[0],"[OPTIONS]")
    print(options)
    pass
def main():
    global SUMMARY
    try:
        opts, args = getopt.getopt(sys.argv[1:], "i:o:lpm:sh", ["input-files=", "second=", "output=", "order-lists", "pretty", "output-map", "summary", "help"])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(1)
    f_i = None
    f_o = None
    order_lists = False
    pretty = False
    output_map = []
    output_types = {
            'additions': additions_f,
            'subtractions': subtractions_f,
            'union':  union_f, 
            'intersection': intersection_f,
            'each': each_f,
            'symmetric_difference': symmetric_difference_f,
        }
    output_namemap = {'a': output_types['additions'], 's': output_types['subtractions'], 'u': output_types['union'], 'i': output_types['intersection'], 'e': output_types['each'], 'd': output_types['symmetric_difference']}
    for option, arg in opts:
        if option in ('-i', '--input-files'):
            f_i = arg.split(',')
        elif option in ('-h', '--help'):
            usage()
            exit(0)
        elif option in ('-o', '--output'):
            f_o = arg
        elif option in ('-l', '--order-lists'):
            order_lists = True
        elif option in ('-p', '--pretty'):
            pretty = True
        elif option in ('-s', '--summary'):
            SUMMARY=True
        elif option in ('-m', '--output-map'):
            for item in arg.split(','):
                output_map.append(output_types.setdefault(item, output_namemap[item]))
    loaded = list()
    for input_file in f_i:
        with open(input_file) as f:
            loaded.append({'file_name': input_file, 'processed': process_dict(json.load(f), order_lists)})
    with open(f_o, 'w') if f_o else sys.stdout as f_o:
        for o in output_map:
            o(loaded, f_o, pretty)
def process_dict(i, ordered_lists):
    t = set()
    process_q = deque()
    # path, parent_type, key, value
    for key, value in sorted(i.items()):
        process_q.appendleft((((RNODE,RNODE),), key, value))
    while process_q:
        path, key, value = process_q.pop()
        if isinstance(value, dict):
            path = path + ((DNODE,key),)
            t.add((path, DNODE, key))
            for inner_key, inner_value in value.items():
                process_q.appendleft((path, inner_key, inner_value))
        elif isinstance(value, list):
            path = path + ((LNODE, key),)
            t.add((path, LNODE, key))
            for index, item in enumerate(value):
                process_q.appendleft((path , index if ordered_lists else LNODE, item))
        else:
            # path, parent_type, value_type, value
            path = path
            path = path + ((LEAF,key),)
            t.add((path, LEAF, value))
    return t

def pp(i):
    _name_path = RNODE.join([ str(item[1]) for item in i[0]])# if SUMMARY else [item[1] for item in i[0]]
    _tree_path = RNODE.join([ str(item[0]) for item in i[0]])# if SUMMARY else [item[0] for item in i[0]]
    _type = i[1]
    _value = i[2]
    return {'name_path':_name_path,'tree_path': _tree_path, 'type':_type, 'value': _value}

# IN PROGRESS
def reassemble(i):
    assembly = dict()
    in_order = sorted(i, key=lambda x: len(x[0]))
    for item in in_order:
        print('-------')
        meta = [i[0] for i in item[0]]
        path = [i[1] for i in item[0]]
        i_meta = item[1]
        i_val = item[2]
        print('meta', meta)
        print('path', path)
        print('i_meta', i_meta)
        print('i_val', i_val)
        ptr = assembly
        for m, p in zip(meta, path):
            if m == RNODE:
                continue
            elif isinstance(ptr, list):
                pass
            elif isinstance(ptr, dict):
                pass
            else:
                pass
            print(m,p)
        print(item)

def prettify(i, p):
    return str(i) if not p else json.dumps(i, indent=2, sort_keys=True)

def additions_f(items, f, pretty):
    f.write('[additions]\n')
    f_path = ' > '.join([item['file_name'] for item in items])
    f.write(f_path + '\n')
    red = reduce(lambda x, y: x - y, map(lambda x: x['processed'], items[::-1])) if len(items) > 1 else items[0]['processed']
    for item in red:
        f.write(prettify(pp(item), pretty) + '\n')
    #reassemble(red)
def subtractions_f(items, f, pretty):
    f.write('[subtractions]\n')
    f_path = ' > '.join([item['file_name'] for item in items[::-1]])
    f.write(f_path + '\n')
    red = reduce(lambda x, y: x - y, map(lambda x: x['processed'], items)) if len(items) > 1 else items[0]['processed']
    for item in red:
        f.write(prettify(pp(item), pretty) + '\n')
def union_f(items, f, pretty):
    f.write('[union]\n')
    f_path = ' | '.join([item['file_name'] for item in items])
    f.write(f_path + '\n')
    red = reduce(lambda x, y: x | y, map(lambda x: x['processed'], items)) if len(items) > 1 else items[0]['processed']
    for item in red:
        f.write(prettify(pp(item), pretty) + '\n')
def intersection_f(items, f, pretty):
    f.write('[intersection]\n')
    f_path = ' & '.join([item['file_name'] for item in items])
    f.write(f_path + '\n')
    red = reduce(lambda x, y: x & y, map(lambda x: x['processed'], items)) if len(items) > 1 else items[0]['processed']
    for item in red:
        f.write(prettify(pp(item), pretty) + '\n')
def each_f(items, f, pretty):
    f.write('[each]\n')
    for item in items:
        f.write(item['file_name'] + '\n')
        for details in item['processed']:
            f.write(prettify(pp(details), pretty) + '\n')
def symmetric_difference_f(items, f, pretty):
    f.write('[symmetric_difference]\n')
    f_path = ' ^ '.join([item['file_name'] for item in items])
    f.write(f_path + '\n')
    items = reduce(lambda x, y: x['processed'] ^ y['processed'], items) if len(items) > 1 else set()
    for item in items:
        f.write(prettify(pp(item), pretty) + '\n')

if __name__ == '__main__':
    main()
