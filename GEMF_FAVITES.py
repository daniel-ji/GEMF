#! /usr/bin/env python3
'''
User-friendly GEMF wrapper for use in FAVITES (or elsewhere).
Niema Moshiri 2022
'''

# imports
from os import chdir, getcwd, makedirs
from os.path import abspath, expanduser, isdir, isfile
from sys import argv
import argparse

# useful variables
C_UINT_MAX = 4294967295

# defaults
DEFAULT_FN_GEMF_NETWORK = 'network.txt'
DEFAULT_FN_GEMF_NODE2NUM = 'node2num.txt'
DEFAULT_FN_GEMF_OUT = 'output.txt'
DEFAULT_FN_GEMF_PARA = 'para.txt'
DEFAULT_FN_GEMF_STATE2NUM = 'state2num.txt'
DEFAULT_FN_GEMF_STATUS = 'status.txt'

def parse_args():
    '''
    Parse user arguments

    Returns:
        `argparse.ArgumentParser`: Parsed user arguments
    '''
    # user runs with no args (place-holder if I want to add GUI in future)
    if len(argv) == 1:
        pass

    # parse user args
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-c', '--contact_network', required=True, type=str, help="Contact Network (TSV)")
    parser.add_argument('-s', '--initial_states', required=True, type=str, help="Initial States (TSV)")
    parser.add_argument('-r', '--rates', required=True, type=str, help="State Transition Rates (TSV)")
    parser.add_argument('-t', '--end_time', required=True, type=float, help="End Time")
    parser.add_argument('-o', '--output', required=True, type=str, help="Output Directory")
    parser.add_argument('--max_events', required=False, type=int, default=C_UINT_MAX, help="Max Number of Events")
    parser.add_argument('--gemf_path', required=False, type=str, default='GEMF', help="Path to GEMF Executable")
    args = parser.parse_args()

    # convert local paths to absolute
    args.contact_network = abspath(expanduser(args.contact_network))
    args.initial_states = abspath(expanduser(args.initial_states))
    args.rates = abspath(expanduser(args.rates))
    args.output = abspath(expanduser(args.output))
    return args

def check_args(args):
    '''
    Check user argumentss for validity

    Args:
        `args` (`argparse.ArgumentParser`): Parsed user arguments
    '''
    # check that input files exist
    for fn in [args.contact_network, args.initial_states, args.rates]:
        if not isfile(fn):
            raise ValueError("File not found: %s" % fn)

    # check that end time is positive
    if args.end_time <= 0:
        raise ValueError("End time must be positive: %s" % args.end_time)

    # check that output directory doesn't already exist
    if isdir(args.output) or isfile(args.output):
        raise ValueError("Output directory exists: %s" % args.output)

def prepare_outdir(outdir, para_fn=DEFAULT_FN_GEMF_PARA, network_fn=DEFAULT_FN_GEMF_NETWORK, node2num_fn=DEFAULT_FN_GEMF_NODE2NUM, status_fn=DEFAULT_FN_GEMF_STATUS, state2num_fn=DEFAULT_FN_GEMF_STATE2NUM, out_fn=DEFAULT_FN_GEMF_OUT):
    '''
    Prepare GEMF output directory

    Args:
        `outdir` (`str`): Path to output directory

        `para_fn` (`str`): File name of GEMF parameter file

        `network_fn` (`str`): File name of GEMF network file

        `node2num_fn` (`str`): File name of "node label to GEMF number" mapping file

        `status_fn` (`str`): File name of GEMF status file

        `state2num_fn` (`str`): File name of "state label to GEMF number" mapping file

        `out_fn` (`str`): File name of GEMF output file

    Returns:
        `file`: Write-mode file object to GEMF parameter file

        `file`: Write-mode file object to GEMF network file

        `file`: Write-mode file object to "GEMF to original node label" mapping file

        `file`: Write-mode file object to GEMF status file

        `file`: Write-mode file object to "state label to GEMF number" mapping file

        `file`: Write-mode file object to GEMF output file
    '''
    makedirs(outdir)
    para_f = open('%s/%s' % (outdir, para_fn), 'w')
    network_f = open('%s/%s' % (outdir, network_fn), 'w')
    node2num_f = open('%s/%s' % (outdir, node2num_fn), 'w')
    status_f = open('%s/%s' % (outdir, status_fn), 'w')
    state2num_f = open('%s/%s' % (outdir, state2num_fn), 'w')
    out_f = open('%s/%s' % (outdir, out_fn), 'w')
    return para_f, network_f, node2num_f, status_f, state2num_f, out_f

def create_gemf_network(contact_network_fn, network_f, node2num_f):
    '''
    Load contact network and convert to GEMF network format

    Args:
        `contact_network_fn` (`str`): Path to input contact network (FAVITES format)

        `network_f` (`file`): Write-mode file object to GEMF network file

        `node2num_f` (`file`): Write-mode file object to "node label to GEMF number" mapping file

    Returns:
        `dict`: A mapping from node label to node number

        `list`: A mapping from node number to node label
    '''
    node2num = dict(); num2node = [None] # None is dummy (GEMF starts node numbers at 1)
    for l in open(contact_network_fn):
        # skip empty and header lines
        if len(l) == 0 or l[0] == '#' or l[0] == '\n':
            continue

        # parse NODE line
        if l.startswith('NODE'):
            dummy, u, a = l.split('\t'); u = u.strip()
            if u in node2num:
                raise ValueError("Duplicate node encountered in contact network file: %s" % u)
            node2num[u] = len(num2node); num2node.append(u)

        # parse EDGE line
        elif l.startswith('EDGE'):
            dummy, u, v, a, d_or_u = l.split('\t'); u = u.strip(); v = v.strip(); d_or_u = d_or_u.strip()
            if d_or_u != 'd' and d_or_u != 'u':
                raise ValueError("Last column of contact network EDGE row must be exactly d or u")
            try:
                u_num = node2num[u]
            except KeyError:
                raise ValueError("Node found in EDGE section but not in NODE section: %s" % u)
            try:
                v_num = node2num[v]
            except KeyError:
                raise ValueError("Node found in EDGE section but not in NODE section: %s" % v)
            network_f.write('%d\t%d\n' % (u_num, v_num))
            if d_or_u == 'u':
                network_f.write('%d\t%d\n' % (v_num, u_num))

        # non-comment and non-empty lines must start with NODE or EDGE
        else:
            raise ValueError("Invalid contact network file: %s" % contact_network_fn)

    # finish up and return
    node2num_f.write(str(node2num)); node2num_f.write('\n'); node2num_f.close(); network_f.close()
    return node2num, num2node

def create_gemf_status(initial_states_fn, status_f, state2num_f, node2num):
    '''
    Load initial states and convert to GEMF status format

    Args:
        `initial_states_fn` (`str`): Path to initial states file (FAVITES format)

        `status_f` (`file`): Write-mode file object to GEMF status file

        `state2num_f` (`file`): Write-mode file object to "state label to GEMF number" mapping file

        `node2num` (`dict`): A mapping from node label to node number (for validity checking)

    Returns:
        `dict`: A mapping from state label to state number

        `list`: A mapping from state number to state label
    '''
    state2num = dict(); num2state = list()
    for l in open(initial_states_fn):
        # skip empty and header lines
        if len(l) == 0 or l[0] == '#' or l[0] == '\n':
            continue
        u, s = l.split('\t'); u = u.strip(); s = s.strip()
        try:
            u_num = node2num[u]
        except KeyError:
            raise ValueError("Encountered node in inital states file that is not in contact network file: %s" % u)
        try:
            s_num = state2num[s]
        except KeyError:
            s_num = len(num2state); state2num[s] = s_num; num2state.append(s)
        status_f.write('%d\n' % s_num)

    # finish up and return
    status_f.close()
    return state2num, num2state

def create_gemf_para(rates_fn, para_f, state2num_f, state2num, num2state):
    '''
    Load transition rates and convert to GEMF para format

    Args:
        TODO
    '''
    # load transition rates
    RATE = dict() # RATE[by_state][from_state][to_state] = transition rate (by_state == None means nodal transition)
    INDUCERS = set() # state numbers of inducer states
    for l in open(rates_fn):
        if len(l) == 0 or l[0] == '#' or l[0] == '\n':
            continue
        from_s, to_s, by_s, r = l.split('\t'); from_s = from_s.strip(); to_s = to_s.strip(); by_s = by_s.strip(); r = float(r)
        try:
            from_s_num = state2num[from_s]
        except KeyError:
            from_s_num = len(num2state); state2num[from_s] = from_s_num; num2state.append(from_s)
        try:
            to_s_num = state2num[to_s]
        except KeyError:
            to_s_num = len(num2state); state2num[to_s] = to_s_num; num2state.append(to_s)
        if by_s.lower() == 'none':
            by_s = None; by_s_num = None
        else:
            try:
                by_s_num = state2num[by_s]
            except KeyError:
                by_s_num = len(num2state); state2num[by_s] = by_s_num; num2state.append(by_s)
            INDUCERS.add(by_s_num)
        if by_s_num not in RATE:
            RATE[by_s_num] = dict()
        if from_s_num not in RATE[by_s_num]:
            RATE[by_s_num][from_s_num] = dict()
        if to_s_num in RATE[by_s_num][from_s_num]:
            raise ValueError("Duplicate transition encountered: from '%s' to '%s' by '%s'" % (from_s, to_s, by_s))
        RATE[by_s_num][from_s_num][to_s_num] = r
    state2num_f.write(str(state2num)); state2num_f.write('\n'); state2num_f.close(); NUM_STATES = len(state2num)

    # write nodal transition matrix (by_state == None)
    para_f.write("[NODAL_TRAN_MATRIX]\n")
    for s in range(NUM_STATES):
        if s in RATE[None]:
            rates = [str(RATE[None][s][s_to]) if s_to in RATE[None][s] else '0' for s_to in range(NUM_STATES)]
        else:
            rates = ['0']*NUM_STATES
        para_f.write("%s\n" % '\t'.join(rates))
    para_f.write('\n')

    # write edged transition matrix (by_state != None)
    para_f.write("[EDGED_TRAN_MATRIX]\n")
    for s_by in sorted(INDUCERS):
        for s_from in range(NUM_STATES):
            if s_from in RATE[s_by]:
                rates = [str(RATE[s_by][s_from][s_to]) if s_to in RATE[s_by][s_from] else '0' for s_to in range(NUM_STATES)]
            else:
                rates = ['0']*NUM_STATES
            para_f.write("%s\n" % '\t'.join(rates))
        para_f.write('\n')
    para_f.write('\n')

def main():
    '''
    Main function
    '''
    args = parse_args(); check_args(args)
    para_f, network_f, node2num_f, status_f, state2num_f, out_f = prepare_outdir(args.output)
    node2num, num2node = create_gemf_network(args.contact_network, network_f, node2num_f) # closes network_f and node2num_f
    state2num, num2state = create_gemf_status(args.initial_states, status_f, state2num_f, node2num) # closes status_f
    create_gemf_para(args.rates, para_f, state2num_f, state2num, num2state) # closes para_f and state2num_f

# execute main function
if __name__ == "__main__":
    main()
