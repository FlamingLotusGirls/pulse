import csv
import sys
import os.path
import json

infiletype = 'stl'
outfiletype = 'json'

def parse_cad_points_to_json(file, region):
    output_string = ""
    with open(file, 'rb') as f:
        for line in f:
            arr = line.strip().split(' ')
            if arr[0] != 'vertex':
                continue
            arr = map(lambda v: float(v), arr[1:])
            output_string += '{"point": ' + str(arr) + ', "region": "' + region + '"},\n'

    # output_string = output_string[:-2]
    return output_string

def create_json(filename, *arg):
    arg_length = len(arg)
    print arg_length
    if (arg_length > 1) and (arg_length % 2 != 0):
        print "Incorrect number of arguments"
        return        
    output_string = "[\n"

    if arg_length == 1:
        output_string += parse_cad_points_to_json(arg[0], "main region")
    else:
        for i in range(arg_length):
            if i % 2 != 0:
                continue
            else:
                output_string += parse_cad_points_to_json(arg[i], arg[i+1])
                output_string += ",\n"

    json_file_name = arg[0].replace('.' + infiletype, '.' + outfiletype)
    output_string = output_string[:-2]
    output_string += "\n]"
    print output_string
    print json.loads(output_string)

    write_to_file = open(json_file_name, 'w')
    write_to_file.write(output_string)
    write_to_file.close()

    return json_file_name

if len(sys.argv) > 1:
    if sys.argv[1].find('.' + infiletype) == -1:
        print "Gimme a ." + infiletype + " file"
    else:
        json_file = create_json(*sys.argv)
        print "Created " + json_file
else:
    print "Booooo-urns"



