#! /usr/bin/python

import sys
import re
from itertools import product
import xml.etree.ElementTree as ET
import numpy as np


#########################
##### FDS arguments #####
#########################

global_args = {}
global_args['fds_reac'] = ['heat_of_combustion', 'soot_yield', 'C', 'H', 'fuel', 'ideal']
global_args['fds_matl'] = ['specific_heat', 'conductivity', 'density', 'heat_of_combustion',
                       'n_reactions', 'heat_of_reaction', 'nu_spec', 'reference_temperature',
                       'a', 'e', 'n_s', 'spec_id', 'emissivity', 'heating_rate', 'pyrolysis_range', 'matl_id',
                       'nu_matl']
global_args['fds_surf'] = ['rgb', 'color', 'vel', 'hrrpua', 'heat_of_vaporization',
                       'ignition_temperature', 'burn_away', 'matl_id', 'matl_mass_fraction',
                       'thickness', 'external_flux', 'backing', 'hrrupa', 'stretch_factor', 'cell_size_factor',
                       'ramp_q', 'mlrpua', 'tmp_front', 'transparency']
global_args['fds_obst'] = ['xb', 'surf_ids', 'surf_id', 'color', 'bulk_density', 'bndf_obst']
global_args['fds_hole'] = ['xb', 'color']
global_args['fds_vent'] = ['xb', 'surf_id', 'color', 'dynamic_pressure', 'tmp_exterior', 'mb', 'transparency']
global_args['fds_slcf'] = ['pbx', 'pby', 'pbz', 'quantity', 'vector', 'evacuation']
global_args['fds_pers'] = ['avatar_color', 'color_method', 'default_properties', 'det_mean', 'pre_mean', 'dens_init',
                       'l_non_sp']
global_args['fds_exit'] = ['ior', 'xyz', 'xb']
global_args['fds_evac'] = ['number_initial_persons', 'xb', 'agent_type', 'pers_id']
global_args['fds_ramp'] = ['t', 'f']
global_args['fds_mesh'] = ['ijk', 'xb']


#########################
##### FDS key words #####
#########################

global_keys = {}
global_keys['fds_reac'] = 'REAC'
global_keys['fds_matl'] = 'MATL'
global_keys['fds_surf'] = 'SURF'
global_keys['fds_obst'] = 'OBST'
global_keys['fds_hole'] = 'HOLE'
global_keys['fds_vent'] = 'VENT'
global_keys['fds_slcf'] = 'SLCF'
global_keys['fds_pers'] = 'PERS'
global_keys['fds_exit'] = 'EXIT'
global_keys['fds_evac'] = 'EVAC'
global_keys['fds_ramp'] = 'RAMP'
global_keys['fds_mesh'] = 'MESH'


# accepted deviation when dealing with float arithmetic
epsilon = 0.0001


###############################
##### VARIABLE MANAGEMENT #####
###############################

def add_var(key, value):
    # DESCRIPTION:
    #  adds a new variable
    # INPUT:
    #  key          - name of the new variable (required)
    #  value        - value assigned to the new variable (required)
    global vars
    vars[key] = value


def del_var(key):
    # DESCRIPTION:
    #  deletes a variable
    # INPUT:
    #  key      - name of the variable to delete (required)
    global vars
    del vars[key]


def var(node):
    # DESCRIPTION:
    #  adds new global variables either passed as node arguments or from file via add_var
    # INPUT (arguments of node):
    #  from_file    - file that contains variable keys and values
    global vars
    for key in node.attrib:
        if key != 'from_file':
            add_var(key, eval(node.attrib[key], globals(), vars))
            # print "added variable: %s = %s"%(key, str(vars[key]))

    if check_val(node, 'from_file'):
        print "adding variables from file: "
        in_file = open(node.attrib["from_file"], 'r')
        for line in in_file:
            if line.isspace(): continue
            contents = line.split()
            key = contents[0]
            val = eval(contents[1], globals(), vars)
            print "  found variable name:  ", key
            print "  found variable value: ", val
            add_var(key, val)


###########################
##### NODE EVALUATION #####
###########################

def check_get_val(node, name, default):
    # DESCRIPTION:
    #  checks via check_val if name is an attribute of node
    #  returns the value of name via get_val if possible, returns the specified default value otherwise
    # INPUT:
    #  node     - current node (required)
    #  name     - name of the attribute to return the value for (required)
    #  default  - value that should be returned if no value for name can be determined (required)
    if check_val(node, name):
        return get_val(node, name)
    else:
        return default


def check_val(node, lst, opt=True):
    # DESCRIPTION:
    #  checks whether the items in lst are attributes of node and exits the program with an error message to
    #  standard output if a required attribute cannot be found
    # INPUT:
    #  node     - current node (required)
    #  lst      - list of attributes to search for (required)
    #  opt      - determines if the program should be exited if an attribute cannot be found (default: True)
    if type(lst) is not list:
        lst = [lst]
    for item in lst:
        if not item in node.attrib:
            if not opt:
                print "required attribute %s not found in node %s" % (item, node)
                sys.exit()
            return False
    return True


def get_val(node, name, opt=False):
    # DESCRIPTION:
    #  gets value of an named attribute of node if possible,
    #  if no value for the attribute can be retrieved but the attribute appears in vars and is marked as optional
    #  the value from vars will be returned otherwise the program exits with an error message to standard output
    # INPUT:
    #  node     - current node (required)
    #  name     - name of the attribute to return the value for (required)
    #  opt      - determines if the program should be exited if no value for name can be found (default: False)
    if name in node.attrib:
        return eval(node.attrib[name], {}, vars)
    elif (opt) and (name in vars):
        return vars[name]
    else:
        print "error reading attribute %s from node %s" % (name, node)
        sys.exit()


def cond(node):
    # DESCRIPTION:
    #  checks if the requirements passed as node arguments are fulfilled and exits the program with an error message
    #  to standard output otherwise
    for att in node.attrib:
        if not get_val(node, att):
            print "condition was not met: ", node.attrib[att]
            sys.exit()


def traverse(root):
    # DESCRIPTION:
    #  traverses through the tree and processes the child nodes of root
    #  uses process_node if the tag is included in global_keys (marking it as a keyword of FDS)
    #  looks for a method named like the tag otherwise
    for node in root:
        if node.tag.lower() in global_keys:
            process_node(node)
        else:
            globals()[node.tag](node)


def process_node(node):
    # DESCRIPTION:
    #  processes node with a tag/key found in global_keys and writes it as a FDS statement to the FDS file via write_to_fds
    # INPUT (arguments of node):
    #  id       - identifier of the statement
    #  comment  - comment to be written after the statement
    global vars
    line = ''
    line += "ID='%s'" % check_get_val(node, 'id', 'none')
    args = global_args[node.tag.lower()]
    for arg in args:
        # checks if the argument is a vector in order to treat vectors correctly
        if check_val(node, arg):
            vec_post = ''
            if node.attrib[arg].find(';') != -1:
                vec_post = '(' + node.attrib[arg].split(';')[0] + ')'
                val = eval(node.attrib[arg].split(';')[1], globals(), vars)
            else:
                val = get_val(node, arg)
            if isinstance(val, tuple):
                line += ", %s%s=" % (arg.upper(), vec_post)
                first = True
                for el in val:
                    if not first:
                        line += ", "
                    first = False

                    if isinstance(el, basestring):
                        line += "'%s'" % (el)
                    elif isinstance(el, int):
                        line += "%d" % (el)
                    else:
                        line += "%f" % (el)
            else:
                if isinstance(val, basestring):
                    line += ", %s='%s'" % (arg.upper(), val)
                elif isinstance(val, bool):
                    if val == True:
                        line += ", %s=%s" % (arg.upper(), '.TRUE.')
                    else:
                        line += ", %s=%s" % (arg.upper(), '.FALSE.')
                else:
                    line += ", %s=%f" % (arg.upper(), val)
    all_args = args[:]
    all_args.extend(['id', 'comment'])
    # checks if the arguments given are consistent with global_args for the given key
    for att in node.attrib:
        #print "checking attribute %s"%att
        if att not in all_args:
            print "WARNING: unknown argument %s" % att
    # writes the statement to the FDS file
    write_to_fds("&%s %s/ %s\n" % (global_keys[node.tag.lower()], line, check_get_val(node, 'comment', "")))


###############################
##### FDS FILE MANAGEMENT #####
###############################

def open_fds_file():
    # DESCRIPTION:
    #  checks if an FDS file is already open, closes it if necessary and opens a new one
    #  as specified by the outfile variable, writes a HEAD statement via write_to_fds
    if type(vars['fds_file']) == file:
        close_fds_file()
    vars['fds_file'] = open(vars['outfile'], 'w')
    write_to_fds("&HEAD CHID='%s', TITLE='%s' /\n" % (vars['chid'], vars['title']))


def close_fds_file():
    # DESCRIPTION:
    #  writes a TAIL statement via write_to_fds and closes the FDS file
    write_to_fds("&TAIL/\n")
    vars['fds_file'].close()


###############################
##### FDS CODE GENERATION #####
###############################

def write_to_fds(text):
    # DESCRIPTION:
    #  checks if the FDS file specified by the fds_file variable exists, opens a new one
    #  via open_fds_file if necessary and writes a given text into the FDS file
    # INPUT:
    #  text     - text to write into the FDS file
    if type(vars['fds_file']) != file:
        open_fds_file()
    vars['fds_file'].write(text)


def dump(node):
    # DESCRIPTION:
    #  writes a given string or the content of a given file via write_to_fds
    # INPUT (arguments of node):
    #  text          - raw text to be written to the FDS file
    #  str           - text to be interpreted and written to the FDS file
    #  file          - file whose content is to be written to the FDS File
    if check_val(node, 'text'):
        write_to_fds("%s\n" % (node.attrib["text"]))
    if check_val(node, 'str'):
        write_to_fds("%s\n" % (get_val(node, "str")))
    if check_val(node, 'file'):
        f = open(node.attrib["file"], 'r')
        for line in f:
            write_to_fds("%s\n" % line.rstrip('\n'))
        f.close()


def input(node):
    # DESCRIPTION:
    #  writes FDS given as a string or file via write_to_fds
    #  excluding and including FDS keywords at the same time is not supported and will cause the program to exit with
    #  an error message to standard output
    # INPUT (arguments of node):
    #  text         - raw text to be written to the FDS file, will be preceded by a '&'
    #  str          - text to be interpreted and written to the FDS file, will be preceded by a '&'
    #  from_file    - file that includes FDS commands to be inserted into the FDS file
    #  incl         - list of FDS keywords to exclude
    #  excl         - list of FDS keywords to include
    # given as a string
    if check_val(node, 'text'):
        write_to_fds("&%s /\n" % (node.attrib["text"]))
    if check_val(node, 'str'):
        write_to_fds("&%s /\n" % (get_val(node, "str")))
    # given as a file
    #  check for included and excluded keywords
    if check_val(node, "from_file"):
        excl = []
        excl_tmp = check_get_val(node, 'excl', None)
        if excl_tmp:
            if type(excl_tmp) == type('str'):
                excl.append(excl_tmp)
            else:
                for e in excl_tmp: excl.append(e)
        incl = []
        incl_tmp = check_get_val(node, 'incl', None)
        if incl_tmp:
            if type(incl_tmp) == type('str'):
                incl.append(incl_tmp)
            else:
                for e in incl_tmp: incl.append(e)
        # capitalize keywords
        if incl != []: incl = [e.upper() for e in incl]
        if excl != []: excl = [e.upper() for e in excl]
        # ensure that keywords are not included and excluded at the same time
        if incl != [] and excl != []:
            print "!! exclusion and inclusion of FDS key words at the same time is not possible "
            sys.exit()
        # open and read input file
        in_file_name = get_val(node, "from_file")
        in_file = open(in_file_name, 'r')
        in_file_raw = in_file.read()
        in_file.close()
        # look for lines starting with '&' which marks FDS commands
        in_file_contents = re.findall('&.*?/', in_file_raw.replace('\n', ' '))
        # insert the found commands into the FDS file
        write_to_fds("\n == insertion from file: %s == \n" % in_file_name)
        for line in in_file_contents:
            # looking for the FDS keyword in each line
            m = re.search('\A\s*&\D{4}', line)
            fds_key = m.group(0).strip().strip('&').upper()
            print " -- found FDS key: ", fds_key
            # write the command into the FDS file if it is included or not excluded else ignore it
            if (incl != [] and fds_key in incl) or (incl == [] and not fds_key in excl):
                write_to_fds("%s\n" % line)
            else:
                print "  - ignoring key ", fds_key
        write_to_fds("== end of insertion == \n\n")


def loop(node):
    # DESCRIPTION:
    #  loops via traverse over the values passed by a given start and stop value and/or a list of values
    # INPUT (arguments of node):
    #  var      - variable of the loop
    #  start    - start value of the loop, interpreted as an integer
    #  stop     - end value of the loop, interpreted as an integer
    #  list     - comma-separated list to loop over
    # integer iteration from start to stop
    if 'start' in node.attrib and 'stop' in node.attrib:
        start = int(get_val(node, 'start'))
        stop = int(get_val(node, 'stop'))
        for loop_i in range(start, stop+1):
            add_var(node.attrib['var'], loop_i)
            traverse(node)
            del_var(node.attrib['var'])
    # iteration over a list
    if 'list' in node.attrib:
        llist = node.attrib['list'].split(',')
        for loop_i in llist:
            add_var(node.attrib['var'], loop_i.strip())
            traverse(node)
            del_var(node.attrib['var'])


def mesh(node):
    # DESCRIPTION:
    #  creates a mesh with the given parameters and writes the MESH statement via write_to_fds
    # INPUT (arguments of node):
    #  px, py, pz           - number of meshes in x,y or z direction (default: 1)
    #  nx, ny, nz           - number of cells in x, y and z direction
    #  xmin, ymin, zmin     - starting coordinates of the mesh
    #  xmax, ymax, zmax     - end coordinates of the mesh
    # calculating the number of meshes
    px = 1
    py = 1
    pz = 1
    if check_val(node, ["px", "py", "pz"]):
        px = get_val(node, "px", opt=True)
        py = get_val(node, "py", opt=True)
        pz = get_val(node, "pz", opt=True)
    # calculating the number of cells
    gnx = get_val(node, "nx", opt=True)
    gny = get_val(node, "ny", opt=True)
    gnz = get_val(node, "nz", opt=True)
    lnx = gnx / px
    lny = gny / py
    lnz = gnz / pz
    gxmin = get_val(node, "xmin", opt=True)
    gxmax = get_val(node, "xmax", opt=True)
    gymin = get_val(node, "ymin", opt=True)
    gymax = get_val(node, "ymax", opt=True)
    gzmin = get_val(node, "zmin", opt=True)
    gzmax = get_val(node, "zmax", opt=True)
    dx = (gxmax - gxmin) / px
    dy = (gymax - gymin) / py
    dz = (gzmax - gzmin) / pz
    # writing the MESH statements
    for ix in range(px):
        for iy in range(py):
            for iz in range(pz):
                xmin = gxmin + ix * dx
                xmax = gxmin + (ix + 1) * dx
                ymin = gymin + iy * dy
                ymax = gymin + (iy + 1) * dy
                zmin = gzmin + iz * dz
                zmax = gzmin + (iz + 1) * dz
                write_to_fds("&MESH IJK=%d,%d,%d, XB=%f,%f,%f,%f,%f,%f /\n" % (
                    lnx, lny, lnz,
                    xmin, xmax, ymin, ymax, zmin, zmax))


def evac_mesh(node):
    # DESCRIPTION:
    #  creates a single mesh for evacuation simulations with the given parameters and writes the MESH statement
    #  via write_to_fds
    # INPUT (arguments of node):
    #  px, py, pz           - number of meshes in x,y or z direction (default: 1)
    #  xmin, ymin, zmin     - starting coordinates of the mesh
    #  xmax, ymax, zmax     - end coordinates of the mesh
    #  nx, ny               - number of cells in x and y direction
    xmin = get_val(node, "xmin", opt=True)
    xmax = get_val(node, "xmax", opt=True)
    ymin = get_val(node, "ymin", opt=True)
    ymax = get_val(node, "ymax", opt=True)
    zmin = get_val(node, "zmin", opt=True)
    zmax = get_val(node, "zmax", opt=True)

    nx = get_val(node, "nx", opt=True)
    ny = get_val(node, "ny", opt=True)

    evac_zmin = 0.25 * (zmax - zmin)
    evac_zmax = 0.75 * (zmax - zmin)

    write_to_fds(
        "&MESH ID='evac_mesh' IJK=%d,%d,%d, XB=%f,%f,%f,%f,%f,%f, EVACUATION=.TRUE., EVAC_HUMANS=.TRUE. /\n" % (
            nx, ny, 1, xmin, xmax, ymin, ymax, evac_zmin, evac_zmax))


def obst(node):
    # DESCRIPTION:
    #  defines an rectangular obstruction and writes the OBST statement via write_to_fds
    # INPUT (arguments of node):
    #  x1, y1, z1       - coordinates of one corner of the obstacle (required)
    #  x2, y2, z2       - coordinates of the opposing corner of the obstacle (required)
    #  color            - color of the obstacle (default: "WHITE")
    #  transparency     - transparency of the obstacle (default: 1.0)
    #  surf_id          - surface of the obstacle
    #  comment          - comment to be written after the OBST statement
    line = "XB=%f,%f,%f,%f,%f,%f, COLOR='%s', TRANSPARENCY=%f" % (get_val(node, "x1"),
                                                                  get_val(node, "x2"),
                                                                get_val(node, "y1"),
                                                                get_val(node, "y2"),
                                                                get_val(node, "z1"),
                                                                get_val(node, "z2"),
                                                                check_get_val(node, "color", "WHITE"),
                                                                check_get_val(node, "transparency", 1.))
    if check_val(node, 'surf_id'):
        line += ", SURF_ID='%s'" % get_val(node, "surf_id")
    write_to_fds("&OBST %s / %s\n" % (line, check_get_val(node, 'comment', "")))


def hole(node):
    # DESCRIPTION:
    #  defines an rectangular void in an obstruction and writes the HOLE statement via write_to_fds
    # INPUT (arguments of node):
    #  x1, y1, z1       - coordinates of one corner of the hole (required)
    #  x2, y2, z2       - coordinates of the opposing corner of the hole (required)
    # comment          - comment to be written after the HOLE statement
    write_to_fds("&HOLE XB=%f,%f,%f,%f,%f,%f / %s\n" % (get_val(node, "x1"),
                                                        get_val(node, "x2"),
                                                        get_val(node, "y1"),
                                                        get_val(node, "y2"),
                                                        get_val(node, "z1"),
                                                        get_val(node, "z2"),
                                                        check_get_val(node, 'comment', "")))


def boundary(node):
    # DESCRIPTION:
    #  defines open surfaces as boundary conditions and writes the VENT statements via write_to_fds
    # INPUT (arguments of node):
    #  x, y, z                              - boundary conditions for the corresponding direction, effecting both surfaces
    #  xmin, xmax, ymin, ymax, zmin, zmax   - boundary condition for only one surface
    if check_get_val(node, "x", "") == "open":
        write_to_fds("&VENT MB='XMIN' ,SURF_ID='OPEN' /\n")
        write_to_fds("&VENT MB='XMAX' ,SURF_ID='OPEN' /\n")
    else:
        if check_get_val(node, "xmin", "") == "open":
            write_to_fds("&VENT MB='XMIN' ,SURF_ID='OPEN' /\n")
        if check_get_val(node, "xmax", "") == "open":
            write_to_fds("&VENT MB='XMAX' ,SURF_ID='OPEN' /\n")

    if check_get_val(node, "y", "") == "open":
        write_to_fds("&VENT MB='YMIN' ,SURF_ID='OPEN' /\n")
        write_to_fds("&VENT MB='YMAX' ,SURF_ID='OPEN' /\n")
    else:
        if check_get_val(node, "ymin", "") == "open":
            write_to_fds("&VENT MB='YMIN' ,SURF_ID='OPEN' /\n")
        if check_get_val(node, "ymax", "") == "open":
            write_to_fds("&VENT MB='YMAX' ,SURF_ID='OPEN' /\n")

    if check_get_val(node, "z", "") == " open":
        write_to_fds("&VENT MB='ZMIN' ,SURF_ID='OPEN' /\n")
        write_to_fds("&VENT MB='ZMAX' ,SURF_ID='OPEN' /\n")
    else:
        if check_get_val(node, "zmin", "") == "open":
            write_to_fds("&VENT MB='ZMIN' ,SURF_ID='OPEN' /\n")
        if check_get_val(node, "zmax", "") == "open":
            write_to_fds("&VENT MB='ZMAX' ,SURF_ID='OPEN' /\n")


def init(node):
    # DESCRIPTION:
    #  initializes temperature in a defined area and writes the INIT statement via write_to_fds
    # INPUT (arguments of node):
    #  temperature      - temperature in the defined area (required)
    #  x1, y1, z1       - coordinates of one corner of the defined area (required)
    #  x2, y2, z2       - coordinates of the opposing corner of the defined area (required)
    #  comment          - comment to be written after the INIT statement
    write_to_fds("&INIT TEMPERATURE=%f XB=%f,%f,%f,%f,%f,%f / %s" % (get_val(node, "temperature"),
                                                                     get_val(node, "x1"),
                                                                     get_val(node, "x2"),
                                                                     get_val(node, "y1"),
                                                                     get_val(node, "y2"),
                                                                     get_val(node, "z1"),
                                                                     get_val(node, "z2"),
                                                                     check_get_val(node, 'comment', "")))


def ramp(node):
    # DESCRIPTION:
    #  reads ramp data from a given file and writes the RAMP statements via write_to_fds
    # INPUT (arguments of node):
    #  id       - identifier of the ramp (default: name of the passed file)
    #  file     - file with the ramp data (required)
    id = check_get_val(node, 'id', node.attrib["file"].split(".")[0])
    if check_val(node, 'file'):
        file_values = open(get_val(node, "file"), 'r')
        for line in file_values:
            write_to_fds("&RAMP ID='%s' T=%f, F=%f / \n" % (id, float(line.split(",")[0]), float(line.split(",")[1])))


def radi(node):
    # DESCRIPTION:
    #  writes a RADI statement with the given radiative fraction via write_to_fds
    # INPUT (arguments of node):
    #  radiative_fraction   - radiative fraction (required)
    #  comment              - comment to be written after the INIT statement
    if check_val(node, 'radiative_fraction'):
        write_to_fds("&RADI RADIATIVE_FRACTION = %f /\n" % (get_val(node, 'radiative_fraction'),
                                                            check_get_val(node, 'comment', "")))


def devc(node):
    # DESCRIPTION:
    #  defines devices in an area or a single point and writes the DEVC statement via write_to_fds
    # INPUT (arguments of node):
    #  id           - identifier of the device (required)
    #  q            - quantity of the devices (required)
    #  x1, y1, z1   - coordinates of one corner of the defined area where the devices are to be placed
    #  x2, y2, z2   - coordinates of the opposing corner of the defined area where the devices are to be placed
    # OR
    #  x, y, z      - coordinates of the point where the devices are to be placed
    #  ior          - ?
    check_val(node, ["q", "id"], opt=False)
    if check_val(node, ["x1", "x2", "y1", "y2", "z1", "z2"]):
        write_to_fds("&DEVC ID='%s' XB=%f,%f,%f,%f,%f,%f QUANTITY='%s'/\n" % (get_val(node, "id"),
                                                                              get_val(node, "x1"),
                                                                              get_val(node, "x2"),
                                                                              get_val(node, "y1"),
                                                                              get_val(node, "y2"),
                                                                              get_val(node, "z1"),
                                                                              get_val(node, "z2"),
                                                                              get_val(node, "q")))
        return True
    if check_val(node, ["x", "y", "z"]):
        ior_s = ''
        if check_val(node, ["ior"], opt=True):
            ior_s = ", IOR=%s" % get_val(node, "ior")
        write_to_fds("&DEVC ID='%s', XYZ=%f,%f,%f, QUANTITY='%s'%s/\n" % (get_val(node, "id"),
                                                                          get_val(node, "x"),
                                                                          get_val(node, "y"),
                                                                          get_val(node, "z"),
                                                                          get_val(node, "q"),
                                                                          ior_s))
        return True
    return False


def slcf(node):
    # DESCRIPTION:
    #  defines slice files and writes the SLCF statements via write_to_fds
    # INPUT (arguments of node):
    #  q        - quantity of slices
    #  v        - determines that a vector is used
    #  x, y, z  - dimension to record as slice file
    q = "QUANTITY='%s'" % get_val(node, 'q')
    v = ""
    if check_get_val(node, 'v', "") == '1':
        v = "VECTOR=.TRUE."
    if check_val(node, 'x'):
        write_to_fds("&SLCF PBX=%e, %s %s /\n" % (get_val(node, 'x'), q, v))
    if check_val(node, 'y'):
        write_to_fds("&SLCF PBY=%e, %s %s /\n" % (get_val(node, 'y'), q, v))
    if check_val(node, 'z'):
        write_to_fds("&SLCF PBZ=%e, %s %s /\n" % (get_val(node, 'z'), q, v))


#############################
##### COMBINED COMMANDS #####
#############################

def info(node):
    # DESCRIPTION:
    #  writes a short info about the job to standard output and creates a new FDS file via open_fds_file
    # INPUT (arguments of node):
    #  chid     - job identifier (required)
    #  title    - short description of the job
    #  outfile  - name of the FDS file, should match with chid (required)
    if check_val(node, ['chid', 'outfile'], opt=False):
        vars['chid'] = get_val(node, "chid")
        vars['title'] = get_val(node, "title", opt=True)
        vars['outfile'] = get_val(node, "outfile")
        print "chid    : %s" % vars['chid']
        print "title   : %s" % vars['title']
        print "outfile : %s" % vars['outfile']
        open_fds_file()


def fire(node):
    # DESCRIPTION:
    #  defines a box and writes the OBST statement via write_to_fds
    #  defines a fire fueled by methane on the box and writes the REAC, SURF and VENT statements via write_to_fds
    # INPUT (arguments of node):
    #  type     - must be "burningbox" in order for the method to have an effect (required)
    #  cx, cy   - x & y coordinates of the center of the box (required)
    #  lz       - z coordinate of the bottom of the box (required)
    #  width    - width of the box (required)
    #  height   - height of the box (required)
    # hrr      - heat release rate (required)
    if node.attrib['type'] == "burningbox":
        # define the box
        cx = get_val(node, 'cx')
        cy = get_val(node, 'cy')
        lz = get_val(node, 'lz')
        w2 = get_val(node, 'width') / 2.0
        h = get_val(node, 'height')
        box_obst = "&OBST "
        box_obst += "XB=%f, %f, %f, %f, %f, %f" % (cx - w2, cx + w2, cy - w2, cy + w2, lz, lz + h)
        box_obst += "/\n"
        write_to_fds(box_obst)

        # define the fire
        write_to_fds("&REAC FUEL = 'METHANE' /\n")
        hrrpua = get_val(node, 'hrr') / (2.0 * w2) ** 2
        write_to_fds("&SURF ID='burningbox', HRRPUA=%f /\n" % hrrpua)
        write_to_fds("&VENT XB=%f,%f,%f,%f,%f,%f SURF_ID='burningbox' color='RED'/\n" % (
            cx - w2, cx + w2, cy - w2, cy + w2, lz + h, lz + h))


def bounded_room(node):
    # DESCRIPTION:
    #  creates a simple rectangular room with walls and a fitting mesh created via mesh
    # INPUT (arguments of node):
    #  x1, y1, z1                       - coordinates of one corner of the room
    #  x2, y2, z2                       - coordinates of the opposing corner of the room
    #  bx1, bx2, by1, by2, bz1, bz2     - wall thickness in relation to wt (default: 0)
    #  wt                               - reference value for wall thickness (default: 0.0)
    #  ax, ay, az                       - number of meshes in the x, y or z direction (default: 1)
    #  delta                            - cell width of the mesh
    #  wall_color                       - color of room walls (default: "FIREBRICK")
    #  wall_transparency                - transparency of walls (default: 0.5)
    # get input values from node
    x1 = get_val(node, "x1", opt=True)
    x2 = get_val(node, "x2", opt=True)
    y1 = get_val(node, "y1", opt=True)
    y2 = get_val(node, "y2", opt=True)
    z1 = get_val(node, "z1", opt=True)
    z2 = get_val(node, "z2", opt=True)

    bx1 = check_get_val(node, "bx1", 0)
    bx2 = check_get_val(node, "bx2", 0)
    by1 = check_get_val(node, "by1", 0)
    by2 = check_get_val(node, "by2", 0)
    bz1 = check_get_val(node, "bz1", 0)
    bz2 = check_get_val(node, "bz2", 0)
    wt = check_get_val(node, "wt", 0.0)

    ax = check_get_val(node, "ax", 1)
    ay = check_get_val(node, "ay", 1)
    az = check_get_val(node, "az", 1)

    delta = get_val(node, "delta", opt=True)

    # compute the minimum mesh size (room + walls)
    dxmin = x1 - bx1 * wt
    dxmax = x2 + bx2 * wt
    dymin = y1 - by1 * wt
    dymax = y2 + by2 * wt
    dzmin = z1 - bz1 * wt
    dzmax = z2 + bz2 * wt

    # compute required number of mesh cells
    nx = int(div235((dxmax - dxmin) / delta))
    ny = int(div235((dymax - dymin) / delta))
    nz = int(div235((dzmax - dzmin) / delta))
    if ax == 1:
        dxmax = dxmin + nx * delta
    else:
        dxmin = dxmax - nx * delta
    if ay == 1:
        dymax = dymin + ny * delta
    else:
        dymin = dymax - ny * delta
    if az == 1:
        dzmax = dzmin + nz * delta
    else:
        dzmin = dzmax - nz * delta

    # save the computed values as global variables (for further usage)
    add_var("xmin", dxmin)
    add_var("xmax", dxmax)
    add_var("ymin", dymin)
    add_var("ymax", dymax)
    add_var("zmin", dzmin)
    add_var("zmax", dzmax)
    add_var("nx", nx)
    add_var("ny", ny)
    add_var("nz", nz)

    # call the mesh method
    mesh(node)

    # draw the walls if the wall is thicker than 0
    wall_color = check_get_val(node, "wall_color", "FIREBRICK")
    wall_transparency = check_get_val(node, "wall_transparency", 0.5)
    if wt * bx1 > epsilon:
        write_to_fds("&OBST XB=%f,%f,%f,%f,%f,%f, COLOR='%s', TRANSPARENCY=%f /\n" % (
            x1 - wt * bx1, x1, y1 - wt * by1, y2 + wt * by2, z1 - wt * bz1, z2 + wt * bz2, wall_color,
            wall_transparency))
    if wt * bx2 > epsilon:
        write_to_fds("&OBST XB=%f,%f,%f,%f,%f,%f, COLOR='%s', TRANSPARENCY=%f /\n" % (
            x2, x2 + wt * bx2, y1 - wt * by1, y2 + wt * by2, z1 - wt * bz1, z2 + wt * bz2, wall_color,
            wall_transparency))
    if wt * by1 > epsilon:
        write_to_fds("&OBST XB=%f,%f,%f,%f,%f,%f, COLOR='%s', TRANSPARENCY=%f /\n" % (
            x1 - wt * bx1, x2 + wt * bx2, y1 - wt * by1, y1, z1 - wt * bz1, z2 + wt * bz2, wall_color,
            wall_transparency))
    if wt * by2 > epsilon:
        write_to_fds("&OBST XB=%f,%f,%f,%f,%f,%f, COLOR='%s', TRANSPARENCY=%f /\n" % (
            x1 - wt * bx1, x2 + wt * bx2, y2, y2 + wt * by2, z1 - wt * bz1, z2 + wt * bz2, wall_color,
            wall_transparency))
    if wt * bz1 > epsilon:
        write_to_fds("&OBST XB=%f,%f,%f,%f,%f,%f, COLOR='%s', TRANSPARENCY=%f /\n" % (
            x1 - wt * bx1, x2 + wt * bx2, y1 - wt * by1, y2 + wt * by2, z1 - wt * bz1, z1, wall_color,
            wall_transparency))
    if wt * bz2 > epsilon:
        write_to_fds("&OBST XB=%f,%f,%f,%f,%f,%f, COLOR='%s', TRANSPARENCY=%f /\n" % (
            x1 - wt * bx1, x2 + wt * bx2, y1 - wt * by1, y2 + wt * by2, z2, z2 + wt * bz2, wall_color,
            wall_transparency))


def my_room(node):
    # DESCRIPTION:
    #  subset of bounded_room
    #  determines mesh parameters for simple rectangular room with walls but does neither create the mesh nor the walls
    # INPUT (arguments of node):
    #  x1, y1, z1                       - coordinates of one corner of the room
    #  x2, y2, z2                       - coordinates of the opposing corner of the room
    #  bx1, bx2, by1, by2, bz1, bz2     - wall thickness in relation to wt (default: 0)
    #  wt                               - reference value for wall thickness (default: 0.0)
    #  ax, ay, az                       - number of meshes in the x, y or z direction (default: 1)
    #  delta                            - cell width of the mesh
    # get input values from node
    x1 = get_val(node, "x1")
    x2 = get_val(node, "x2")
    y1 = get_val(node, "y1")
    y2 = get_val(node, "y2")
    z1 = get_val(node, "z1")
    z2 = get_val(node, "z2")

    bx1 = check_get_val(node, "bx1", 0)
    bx2 = check_get_val(node, "bx2", 0)
    by1 = check_get_val(node, "by1", 0)
    by2 = check_get_val(node, "by2", 0)
    bz1 = check_get_val(node, "bz1", 0)
    bz2 = check_get_val(node, "bz2", 0)

    wt = check_get_val(node, "wt", 0.0)

    ax = check_get_val(node, "ax", 1)
    ay = check_get_val(node, "ay", 1)
    az = check_get_val(node, "az", 1)

    delta = get_val(node, "delta", opt=True)

    # compute the minimum mesh size (room + walls)
    dxmin = x1 - bx1 * wt
    dxmax = x2 + bx2 * wt
    dymin = y1 - by1 * wt
    dymax = y2 + by2 * wt
    dzmin = z1 - bz1 * wt
    dzmax = z2 + bz2 * wt

    # compute required number of mesh cells
    nx = int(div235((dxmax - dxmin) / delta))
    ny = int(div235((dymax - dymin) / delta))
    nz = int(div235((dzmax - dzmin) / delta))
    if ax == 1:
        dxmax = dxmin + nx * delta
    else:
        dxmin = dxmax - nx * delta
    if ay == 1:
        dymax = dymin + ny * delta
    else:
        dymin = dymax - ny * delta
    if az == 1:
        dzmax = dzmin + nz * delta
    else:
        dzmin = dzmax - nz * delta

    # save the computed values as global variables (for further usage)
    add_var("xmin", dxmin)
    add_var("xmax", dxmax)
    add_var("ymin", dymin)
    add_var("ymax", dymax)
    add_var("zmin", dzmin)
    add_var("zmax", dzmax)
    add_var("nx", nx)
    add_var("ny", ny)
    add_var("nz", nz)


##########
# OTHERS #
##########

def section(node):
    # DESCRIPTION:
    #  no functionality itself, used for structuring the XML file
    traverse(node)


def dbg(node):
    # DESCRIPTION:
    #  writes the value of the node argument print to standard output
    print get_val(node, "print")


def div235(n):
    # DESCRIPTION:
    #  increases a given integer value until its factors only consist of 2, 3 and 5
    # INPUT:
    #  n        - integer value to increase (required)
    r_init = int(n)
    while True:
        r = r_init
        while r % 2 == 0 and r != 0: r /= 2
        while r % 3 == 0 and r != 0: r /= 3
        while r % 5 == 0 and r != 0: r /= 5
        if r == 1: break
        r_init += 1
    return r_init


def para(node):
    # DESCRIPTION:
    #  the tag defines parameters that are used for creating a parameter space in the main loop
    #  the node has no functionality when the tree is traversed
    pass


def paradim(node, dirlist):
    # DESCRIPTION:
    #  evaluates nodes with the para tag and creates a list of parameters
    # INPUT (arguments of node):
    #  var      - name of the attribute (required)
    #  list     - list of parameters
    #  file     - file with a list of comma-separated parameters, passing a file deletes the parameters of list!
    #  col      - number of the first column with content
    check_val(node, ["var"], opt=False)
    paralist = check_get_val(node, 'list', [])

    if check_val(node, ["file"]):
        col = int(check_get_val(node, "col", 0))
        paralist = np.loadtxt(node.attrib["file"], usecols=(col,), delimiter=',')

    nump = len(paralist)
    if len(dirlist) == 0:
        for ip in paralist: dirlist.append({})
    if len(dirlist) != nump:
        print "wrong number of parameter!!"
        sys.exit()
    for ip in range(nump):
        dirlist[ip][node.attrib['var']] = paralist[ip]


######################
##### MAIN LOOP ######
######################

tree = ET.parse(str(sys.argv[1]))
root = tree.getroot()

params = {}
vars = {}

# looking for parameters
for node in root:
    if node.tag == 'para':
        if 'dim' not in node.attrib:
            node.attrib['dim'] = 'default_dim'
        if node.attrib['dim'] not in params:
            params[node.attrib['dim']] = []
        paradim(node, params[node.attrib['dim']])

# generating a parameter space and traversing the tree for each set of parameters
para_id = 0
for items in product(*[params[pd] for pd in params]):
    vars = {'outfile': "output.fds", 'chid': "chid", 'title': "title", 'fds_file_open': False, 'fds_file': 0,
            'para_id': para_id}
    para_id += 1
    for v in items:
        vars = dict(vars.items() + v.items())
        print v

    traverse(root)

    close_fds_file()
