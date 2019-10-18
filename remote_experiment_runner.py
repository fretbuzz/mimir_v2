'''
This file differs from multi_experiment_looper.py in that multi_experiment_looper.py has a bunch of custom instructions
and stuff for running the experiments, while this file literally just calls the e2e scripts and recovers data, etc.

All of this could be done by hand fairly easily, but I'm automating it because it's easier that way
'''
import argparse
import json
from collections import OrderedDict
import pwnlib.tubes.ssh
from pwn import *
import time

def parse_config(config_file_pth):
    with open(config_file_pth, 'r') as f:
        config_file = json.loads(f.read(), object_pairs_hook=OrderedDict)

        machine_ip = config_file["machine_ip"]
        generate_pcaps_p = config_file["generate_pcaps_p"]
        e2e_script_to_follow = config_file["e2e_script_to_follow"]
        corresponding_local_directory = config_file["corresponding_local_directory"]
        remote_server_key = config_file["remote_server_key"]
        user = config_file["user"]

    return machine_ip, generate_pcaps_p, e2e_script_to_follow, corresponding_local_directory, remote_server_key, user

def sendline_and_wait_responses(sh, cmd_str, timeout=5, extra_rec=False):
    sh.sendline(cmd_str)
    if extra_rec:
        sh.recvline()
    line_rec = 'start'
    while line_rec != '':
        line_rec = sh.recvline(timeout=timeout)
        print("recieved line", line_rec)

def upload_data_to_remote_machine(sh, s, sftp, local_directory):
    # okay, what do I want to do here?
    # just upload each file in the local directory to the remote device
    # (is going to be kinda hard to test at the moment, because the data isn't setup like this...)

    sendline_and_wait_responses(sh, 'ls')
    clear_dir_cmd = "sudo rm -rf /mydata/mimir_v2/experiment_coordinator/experimental_data/;"
    #0clear_dir_cmd = "rm -rf /mydata/mimir_v2/experiment_coordinator/experimental_data/;"
    print "clear_dir_cmd", clear_dir_cmd
    sendline_and_wait_responses(sh, clear_dir_cmd, timeout=5)

    create_dir_cmd = "mkdir /mydata/mimir_v2/experiment_coordinator/experimental_data/"
    print "create_dir_cmd", create_dir_cmd
    sendline_and_wait_responses(sh, create_dir_cmd)

    #exit(1)

    for subdir, dirs, files in os.walk(local_directory):
        cur_dir = "/mydata/mimir_v2/experiment_coordinator/experimental_data/" + subdir[-1]
        create_dir_cmd = "mkdir " + cur_dir
        sendline_and_wait_responses(sh, create_dir_cmd)

        for file in files:
            cur_file = os.path.join(subdir, file)
            print cur_file
            # we want to upload every file in this directory (but NOT the subdirectories!)
            # TODO: need to upload the pcaps via a binary transfer method (not ascii- this causes problems! -- testing solution now...)
            s.upload(cur_file, remote=cur_dir + '/' + file)
            ###sendline_and_wait_responses(sftp, 'put ' + cur_dir + '/' + file + ' ' + cur_file)

    print "all done uploading files! (hopefully it worked, because I haven't actually tested this function!)"

def retrieve_relevant_files_from_cloud(sh, s, sftp, local_directory, data_was_uploaded=False):
    # this function needs to grab the relevant files that were generated on the remote device and download them
    # so that they are available locally...

    # okay, so the easiest way to do this is to grab everything in the blahblahblah/experimental_data folder
    # however, then I'm grabbing all kinds of things that I don't want/need...

    # okay, step (1): get the subdirectories...
    get_subdirs_cmd = 'ls -d /mydata/mimir_v2/experiment_coordinator/experimental_data/*'
    print "get_subdirs_cmd", get_subdirs_cmd
    sh.sendline(get_subdirs_cmd)
    subdirs = []
    line_rec = 'blahblahblah'
    while line_rec != '':
        line_rec = sh.recvline(timeout=2)
        #print "line_rec", line_rec
        listed_subdirs = line_rec.split(' ')[1:]
        listed_subdirs = [potential_subdir.rstrip().lstrip() for potential_subdir in listed_subdirs if potential_subdir != '' and \
                          potential_subdir != '/mydata/mimir_v2/experiment_coordinator/experimental_data/']
        subdirs.extend(listed_subdirs)

    # step (1.5): if local directory doesn't exist, then make it!
    if not os.path.exists(local_directory):
        os.makedirs(local_directory)

    print "subdirs", subdirs

    # then, step (2): recover the relevant files from each subdirectory
    for subdir in subdirs:
        cur_subdir = subdir #"/mydata/mimir_v2/experiment_coordinator/experimental_data/" + subdir
        get_files_in_subdir = "ls -p " + cur_subdir + " | grep -v /"

        sh.sendline(get_files_in_subdir)
        files_in_subdir = []
        line_rec = 'blahblahblah'
        while line_rec != '':
            line_rec = sh.recvline(timeout=2)
            if line_rec != '':
                files_in_subdir.append(line_rec.replace('$','').strip())
        print "files_in_subdir", files_in_subdir

        # step (2.5): if local directory for the current experiment does not exist, make it!
        if cur_subdir[-1] != '/':
            cur_subdir += '/'
        if local_directory[-1] != '/':
            local_directory += '/'
        cur_local_subdir = local_directory + subdir.split('/')[-1]
        print "cur_local_subdir",cur_local_subdir
        if not os.path.exists(cur_local_subdir):
            os.makedirs(cur_local_subdir)

        # Step (3): grab the files generated during the processing
        # note: if data was uploaded, then we don't need to recover the pcap/config files
        if not data_was_uploaded:
            for file_in_subdir in files_in_subdir:
                cur_file = cur_subdir + file_in_subdir
                print "cur_file", cur_file
                cur_local_file = cur_local_subdir + '/' + file_in_subdir
                print "cur_local_file", cur_local_file
                # TODO: PROBLEM: pulls in ASCII mode... needs to be in binary mode (testing solution now...)
                s.download(file_or_directory=cur_file, local=cur_local_file)
                #sendline_and_wait_responses(sftp, "get " + cur_file + " " + cur_local_file)
        # we should always recover the actual results...
        # step (4): make sure there's a nested results subdirectory
        cur_subdir += 'results/'
        cur_local_subdir = cur_local_subdir + '/results/'
        if not os.path.exists(cur_local_subdir):
            os.makedirs(cur_local_subdir)
        # step (4.5): get a list of all the generated results files
        get_files_in_subdir = "ls -p " + cur_subdir + " | grep -v /"
        sh.sendline(get_files_in_subdir)
        files_in_subdir = []
        line_rec = 'blahblahblah'
        while line_rec != '':
            line_rec = sh.recvline(timeout=2)
            if line_rec != '':
                files_in_subdir.append(line_rec.replace('$', '').strip())        # step (5): retrieve all the generated results
        for file_in_subdir in files_in_subdir:
            cur_file = cur_subdir + file_in_subdir
            # TODO: PROBLEM: pulls in ASCII mode... needs to be in binary mode (testing solution now...)
            s.download(file_or_directory=cur_file, local=cur_local_subdir + file_in_subdir)
            #sendline_and_wait_responses(sftp, "get " + cur_file + " " + cur_local_subdir + file_in_subdir)


def run_experiment(config_file_pth, only_retrieve):
    # step 1: parse the config file
    machine_ip, generate_pcaps_p, e2e_script_to_follow, corresponding_local_directory, remote_server_key, user = parse_config(config_file_pth)
    print "generate_pcaps_p",generate_pcaps_p, not generate_pcaps_p

    # step 2: create ssh session on the remote device
    s = None
    while s == None:
        try:
            s = pwnlib.tubes.ssh.ssh(host=machine_ip,
                keyfile=remote_server_key,
                user=user)
        except:
            time.sleep(60)
    sh = s.run('sh')
    print "shell on the remote device is started..."

    # step 3: call the preliminary commands that sets up the shell correctly
    prelim_commands = "cd /mydata; export MINIKUBE_HOME=/mydata; " \
    "sudo chown jsev /mydata; " \
    "git clone https://github.com/fretbuzz/mimir_v2.git; "\
    "cd ./mimir_v2/experiment_coordinator/; " \
    "PATH=$PATH:/opt/bro/bin/; " \
    "sudo chown -R $USER $MINIKUBE_HOME/.minikube; \
    sudo chown -R $USER $HOME/.config; ls"

    sendline_and_wait_responses(sh, prelim_commands, timeout=5)

    if not only_retrieve:
        # step 4: call the actual e2e script
        # if necessary, bypass pcap/data collection in the e2e script
        e2e_script_start_cmd = ". ../configs_to_reproduce_results/e2e_repro_scripts/" + e2e_script_to_follow
        if not generate_pcaps_p:
            print "uploading_data...."
            sftp = pwnlib.tubes.ssh.process(['sftp', '-i', '~/Dropbox/cloudlab.pem', 'jsev@c240g5-110215.wisc.cloudlab.us'])
            upload_data_to_remote_machine(sh, s, sftp, corresponding_local_directory)
            e2e_script_start_cmd += ' --skip_pcap'
            sftp.write('exit')
        print "calling_e2e_script_now....", "not generate_pcaps_p", not generate_pcaps_p
        print "e2e_script_start_cmd",e2e_script_start_cmd
        #exit(2)
        sendline_and_wait_responses(sh, e2e_script_start_cmd, timeout=600)

    #return ## TODO<--- remove this in the future!!!

    # Step 5: Pull the relevant data to store locally
    # NOTE: what should be pulled depends on what (if anything) was uploaded
    print "start sftp..."
    sftp = pwnlib.tubes.ssh.process(['sftp', '-i', '~/Dropbox/cloudlab.pem', 'jsev@c240g5-110215.wisc.cloudlab.us'])
    retrieve_relevant_files_from_cloud(sh, s, sftp, corresponding_local_directory, data_was_uploaded=(not generate_pcaps_p))
    sftp.write('exit')

    # Step 6: maybe run the log file checker to make sure everything is legit?
    # TODO (what it says above): do this at a later point in time (there's already a ticket on the kanban board)
if __name__=="__main__":
    print "RUNNING"

    parser = argparse.ArgumentParser(description='This can run multiple experiments in a row on MIMIR. Also makes graphs')
    parser.add_argument('--config_json', dest='config_json', default=None,
                        help='this is the configuration file used to run to loop through several experiments')
    parser.add_argument('--only_retrieve', dest='only_retrieve',
                        default=False, action='store_true')
    args = parser.parse_args()

    if not args.config_json:
        config_file_pth = "./remote_experiment_configs/sockshop_scale_trial_1.json"
        #config_file_pth = "./remote_experiment_configs/sockshop_scale_take1.json"
        ##config_file_pth = "./remote_experiment_configs/hipsterStore_scale_take1.json"
    else:
        config_file_pth = args.config_json

    run_experiment(config_file_pth, args.only_retrieve)