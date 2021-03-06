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
import pysftp
import log_checker
import shutil

def parse_config(config_file_pth):
    with open(config_file_pth, 'r') as f:
        config_file = json.loads(f.read(), object_pairs_hook=OrderedDict)

        machine_ip = config_file["machine_ip"]
        e2e_script_to_follow = config_file["e2e_script_to_follow"]
        corresponding_local_directory = config_file["corresponding_local_directory"]
        remote_server_key = config_file["remote_server_key"]
        user = config_file["user"]

    return machine_ip, e2e_script_to_follow, corresponding_local_directory, remote_server_key, user

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
        print "subdir", subdir #, subdir[-1]
        cur_dir = "/mydata/mimir_v2/experiment_coordinator/experimental_data/" + subdir.split('/')[-1]
        create_dir_cmd = "mkdir " + cur_dir
        print "create_dir_cmd", create_dir_cmd
        sendline_and_wait_responses(sh, create_dir_cmd)

        for file in files:
            cur_file = os.path.join(subdir, file)
            print cur_file
            # we want to upload every file in this directory (but NOT the subdirectories!)
            print "cur_file (local)",cur_file, "cur remote file ", cur_dir + '/' + file
            #s.upload(cur_file, remote=cur_dir + '/' + file)

            #sftp_upload_cmd = 'put ' + cur_file + ' ' + cur_dir + '/' + file
            #sendline_and_wait_responses(sftp, sftp_upload_cmd)

            with sftp.cd(cur_dir + '/'):  # temporarily chdir to public
                sftp.put(cur_file)  # upload file to public/ on remote

            '''
            # TODO: let's add some code with zipping and unzipping the file in question...
            # first let's compress the file
            tar_cmds = ['tar', '-czvf', cur_file + '.gz', cur_file]
            print "tar-ing the file...", tar_cmds
            # if tar-ed file does NOT already exist, then create it...
            if not os.path.exists(cur_file + '.gz') and '.gz' not in cur_file:
                tar_out = subprocess.check_output(tar_cmds)
                print "tar_out", tar_out

            # then let's send the zipped file
            print "uploading tar-ed file..."
            with sftp.cd(cur_dir + '/'):  # temporarily chdir to public
                sftp.put(cur_file + '.gz')  # upload file to public/ on remote

            # finally, let's unzip the zipped file
            unzip_cmd = 'tar -xvf ' + cur_dir + '/' + cur_file.split('/')[-1] + '.gz'
            print "unzip_cmd", unzip_cmd
            sendline_and_wait_responses(sh, unzip_cmd)
            '''

    print "all done uploading files! (hopefully it worked, because I haven't actually tested this function!)"

def retrieve_relevant_files_from_cloud(sh, s, sftp, local_directory, data_was_uploaded=False, machine_ip=None,
                                       only_retrieve_multilooper=False):
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
        print "line_rec", line_rec
        listed_subdirs = line_rec.replace('\t', ' ').split(' ')
        print "listed_subdirs",listed_subdirs
        listed_subdirs = [potential_subdir.rstrip().lstrip() for potential_subdir in listed_subdirs if potential_subdir != '' and \
                          potential_subdir != '/mydata/mimir_v2/experiment_coordinator/experimental_data/' and \
                          potential_subdir != '$']
        subdirs.extend(listed_subdirs)

    # step (1.5): if local directory doesn't exist, then make it!
    if not os.path.exists(local_directory):
        os.makedirs(local_directory)

    print "subdirs", subdirs

    subdirs = [subdir for subdir in subdirs if has_pcap_file(sh, subdir)]

    print "subdirs_with_pcap_files", subdirs

    # stop uploading all those stupid dirs

    # then, step (2): recover the relevant files from each subdirectory
    if not only_retrieve_multilooper:
        for subdir in subdirs:
            cur_subdir = subdir #"/mydata/mimir_v2/experiment_coordinator/experimental_data/" + subdir
            print "cur_subdir",cur_subdir
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
                    ######s.download(file_or_directory=cur_file, local=cur_local_file)
                    #sendline_and_wait_responses(sftp, "get " + cur_file + " " + cur_local_file)
                    #print "cur_subdir", cur_subdir, "file_in_subdir", file_in_subdir
                    print "recover file via sftp...", "remote_file", cur_file, "localpath", cur_local_file
                    sftp.get(cur_file,localpath=cur_local_file)

            # need to recover the debug directory too...
            try:
                retrieve_files_in_directory(sh, s, sftp, cur_subdir, cur_local_subdir, 'debug')
            except:
                print "debug not present for " + subdir + ' on ' + str(machine_ip)

            # we should always recover the actual results...
            # step (4): make sure there's a nested results subdirectory
            try:
                retrieve_files_in_directory(sh, s, sftp, cur_subdir, cur_local_subdir, 'results')
                pass
                '''
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
                    s.download(file_or_directory=cur_file, local=cur_local_subdir + file_in_subdir)
                    #sendline_and_wait_responses(sftp, "get " + cur_file + " " + cur_local_subdir + file_in_subdir)
                '''
            except:
                print "results are not present for " + subdir + ' on ' + str(machine_ip)

            # TODO: also need to bring the alerts file back too... TODO: need to test this whole thing!!!!!!!
            # step 1: make the relevant exp-containing dir (if it does not already exist) # TODO: might want to look at directories and loop this for all directories with exp name in it...
            print "----downloading alerts-----"
            print "local_directory.split('/')[-1]", local_directory.split('/'), local_directory
            experiment_analysis_files =  cur_subdir.split('/')[-2]  + '/' + cur_subdir.split('/')[-2] .split('/')[-1] + 'dropInfra'
            cur_local_directory = local_directory + experiment_analysis_files
            print "cur_local_directory",cur_local_directory
            if not os.path.exists(cur_local_directory):
                os.makedirs(cur_local_directory)
            # step 2: bring the remote files in the alert dir to the local remote dir (TODO TODO TODO)
            print cur_subdir[:-1], cur_subdir.split('/')[-2]
            cur_subdir = cur_subdir[:-1]  + '/' + cur_subdir.split('/')[-2] + 'dropInfra' + '/' # remote
            print "cur_subdir",cur_subdir
            print "cur_local_directory", cur_local_directory
            try:
                retrieve_files_in_directory(sh, s, sftp, cur_subdir, cur_local_directory, 'alerts')
            except Exception as E:
                print cur_subdir, " had this problem", E
            print "---done downloading alerts---"
            print "EEEE"


    # (okay, we need to actually test this tho...)
    dir_with_exp_graphs_dir = '/mydata/mimir_v2/analysis_pipeline/'
    exp_graphs_dir = 'multilooper_outs/'
    #s.download(file_or_directory=dir_with_exp_graphs, local=local_directory)
    print "------------------------"
    cur_local_directory = local_directory + '/'  + exp_graphs_dir
    print "cur_local_directory",cur_local_directory
    if os.path.exists(cur_local_directory):
        shutil.rmtree(cur_local_directory)
    #os.makedirs(cur_local_directory)
    with sftp.cd(dir_with_exp_graphs_dir):
        try:
            print "retrieving multilooper directory now..."
            print "exp_graphs_dir", exp_graphs_dir
            print "cur_local_directory", cur_local_directory
            sftp.get_r(exp_graphs_dir, localdir=local_directory + '/')  # upload file to public/ on remote
        except Exception as e:
            print "retrieving the multilooper_outs failed with this exception:", e

def has_pcap_file(sh, subdir):
    sh.sendline('ls ' + subdir)

    files_in_subdir = []
    line_rec = 'blahblahblah'
    while line_rec != '':
        line_rec = sh.recvline(timeout=2)
        if line_rec != '':
            files_in_subdir.append(line_rec.replace('$', '').strip())  # step (5): retrieve all the generated results

    for file in files_in_subdir:
        if '.pcap' in file:
            return True

    return False


def printTotals(already_transfered, total_to_transfer):
    print "Transferred: {0}\tOut of: {1}".format( already_transfered, total_to_transfer),
    #sys.stdout.flush()

#def progressBar(value, endvalue, bar_length=20):
#    percent = float(value) / endvalue
#    arrow = '-' * int(round(percent * bar_length) - 1) + '>'
#    spaces = ' ' * (bar_length - len(arrow))
#    sys.stdout.write("\rPercent: [{0}] {1}%".format(arrow + spaces, int(round(percent * 100))))
#    sys.stdout.flush()


def retrieve_files_in_directory(sh, s, sftp, cur_subdir, cur_local_subdir, subdir_name, recursive_dir=False):
    cur_subdir += subdir_name + '/'
    cur_local_subdir = cur_local_subdir + '/' + subdir_name + '/'
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
            files_in_subdir.append(line_rec.replace('$', '').strip())  # step (5): retrieve all the generated results
    for file_in_subdir in files_in_subdir:
        cur_file = cur_subdir + file_in_subdir
        ######s.download(file_or_directory=cur_file, local=cur_local_subdir + file_in_subdir)
        # sendline_and_wait_responses(sftp, "get " + cur_file + " " + cur_local_subdir + file_in_subdir)
        print "cur_file", cur_file, "localpath", cur_local_subdir + file_in_subdir
        if recursive_dir:
            sftp.get_r(cur_file, localpath=cur_local_subdir + file_in_subdir)  # retreive file from remote
        else:
            sftp.get(cur_file, localpath=cur_local_subdir + file_in_subdir)  # retreive file from remote

def run_experiment(config_file_pth, only_retrieve, upload_data, only_process, run_only_log_checker, use_k3s_cluster,
                   only_retrieve_multilooper, machine_ip, remote_server_key, user):
    # step 1: parse the config file
    #machine_ip, e2e_script_to_follow, corresponding_local_directory, remote_server_key, user = parse_config(config_file_pth)

    if not run_only_log_checker:
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
        sftp =  pysftp.Connection(machine_ip, username=user, private_key=remote_server_key)

        if not only_retrieve:
            # step 4: call the actual e2e script
            # if necessary, bypass pcap/data collection in the e2e script
            sh_screen = s.run('nice -11 screen -U')
            clone_command = "git clone https://github.com/fretbuzz/mimir_v2.git"
            sendline_and_wait_responses(sh_screen, clone_command, timeout=5)
            script_one_start_cmd = 'bash ~/mimir_v2/configs_to_reproduce_results/full_cluster_scripts/first_part_of_setup.sh'
            sendline_and_wait_responses(sh_screen, script_one_start_cmd, timeout=5)
            # TODO: setup keys
            script_two_start_cmd = 'bash ~/mimir_v2/configs_to_reproduce_results/full_cluster_scripts/second_part_of_setup.sh'
            sendline_and_wait_responses(sh_screen, script_two_start_cmd, timeout=5)
            # TODO: Setup the InfluxDB and Prometheus
            script_tree_start_cmd = 'bash ~/mimir_v2/configs_to_reproduce_results/full_cluster_scripts/third_part_of_setup.sh'
            sendline_and_wait_responses(sh_screen, script_tree_start_cmd, timeout=5)
            # TODO: get the data

            '''
            e2e_script_start_cmd = ". ../configs_to_reproduce_results/e2e_repro_scripts/" + e2e_script_to_follow
            if upload_data and not only_process:
                print "uploading_data...."
                upload_data_to_remote_machine(sh, s, sftp, corresponding_local_directory)
            if upload_data or only_process:
                e2e_script_start_cmd += ' --skip_pcap'
                #sftp.write('exit')
            print "e2e_script_start_cmd", e2e_script_start_cmd
            e2e_script_start_cmd += '; exit'
            #exit(2)
            sh_screen = s.run('nice -11 screen -U')
            sendline_and_wait_responses(sh_screen, prelim_commands, timeout=5)
            try:
                sendline_and_wait_responses(sh_screen, e2e_script_start_cmd, timeout=5400)
            except EOFError as e:
                print "e2e_script_start_cmd command resulted in EOFError, probably because the command timed out when finished. "
                print "therefore, the file will just keep running. Here's the error: ", e
            '''

        # Step 5: Pull the relevant data to store locally
        # NOTE: what should be pulled depends on what (if anything) was uploaded
        #print "start sftp..."
        #sftp = pwnlib.tubes.ssh.process(['sftp', '-i', '~/Dropbox/cloudlab.pem', 'jsev@c240g5-110215.wisc.cloudlab.us'])
        ''' # TODO: fix this
        retrieve_relevant_files_from_cloud(sh, s, sftp, corresponding_local_directory,
                                           data_was_uploaded=(upload_data and not only_process), machine_ip=machine_ip,
                                           only_retrieve_multilooper=only_retrieve_multilooper)
        '''
        #sftp.write('exit')

    # Step 6: maybe run the log file checker to make sure everything is legit?
    # TODO: I think I never actually fulled tested this function... might want to do that before scaling up experimental data\
    # collectio too high...
    # PLAN: (1) call log checker [done]
    # (2) add flag for only log checker [done]
    # (3) beef up log checker [done]
    log_checker.main(exp_parent_directory=corresponding_local_directory)

if __name__=="__main__":
    print "RUNNING"

    # # only_retrieve, run_only_log_checker,  machine_ip, remote_server_key, user

    parser = argparse.ArgumentParser(description='v0.1 of automating MIMIR collection on a kubespray cluster')
    parser.add_argument('--config_json', dest='config_json', default=None,
                        help='this is the configuration file used to run to loop through several experiments')
    parser.add_argument('--only_retrieve', dest='only_retrieve',
                        default=False, action='store_true',
                        help='Does no computing activities on the remote host-- only downloads files')
    parser.add_argument('--upload_data', dest='upload_data',
                        default=False, action='store_true',
                        help='Should it upload the pcaps instead of generating them')
    parser.add_argument('--only_process', dest='only_process',
                        default=False, action='store_true',
                        help='Do not generate or upload pcaps-- start at processing pcaps *already* on the device')
    parser.add_argument('--run_only_log_checker', dest='run_only_log_checker',
                        default=False, action='store_true',
                        help='Do not generator pcaps, upload pcaps, process pcaps, or retrieve pcaps -- only run the '
                             'log checker on the data already on the local device')
    parser.add_argument('--only_retrieve_multilooper', dest='only_retrieve_multilooper',
                        default=False, action='store_true',
                        help='Instead of retrieving all the data, only recover the multilooper directory (will still perform'
                             'other steps (e.g., data generation) unless the other appropriate flags are used)')
    parser.add_argument('--use_k3s_cluster', dest='use_k3s_cluster',
                        default=False, action='store_true',
                        help='Instead of using the minikube k8s cluster, use the k3s k8s cluster instead (in development ATM)')

    parser.add_argument('--machine_ip', dest='machine_ip', default=None,
                        help='ip of node1')
    parser.add_argument('--remote_server_key', dest='remote_server_key', default=None,
                        help='private cloudlab key location')
    parser.add_argument('--user', dest='user', default=None,
                        help='cloudlab username')

    args = parser.parse_args()

    machine_ip, remote_server_key, user = args.machine_ip, args.remote_server_key, args.user

    if not  machine_ip or not remote_server_key or not user:
        exit('missing a key attribute (machine_ip, remote_server_key or user)')

    if not args.config_json:
        #config_file_pth = "./remote_experiment_configs/sockshop_scale_trial_1.json"
        #config_file_pth = "./remote_experiment_configs/sockshop_scale_take1.json"
        ####config_file_pth = "./remote_experiment_configs/hipsterStore_scale_take1.json"

        #config_file_pth = "./remote_experiment_configs/trials/sockshop_scale_trial_1_rep1.json"
        config_file_pth = "./remote_experiment_configs/trials/sockshop_scale_trial_1_rep2.json"
        #config_file_pth = "./remote_experiment_configs/trials/sockshop_scale_trial_1_rep3.json"

        #config_file_pth = "./remote_experiment_configs/sockshop_scale_newRepro.json"

        #config_file_pth = "./remote_experiment_configs/wordpress_scale_trial_1.json"
        #config_file_pth = "./remote_experiment_configs/wordpress_scale_trial_2.json"
        #config_file_pth = "./remote_experiment_configs/wordpress_scale_trial_3.json"
        #config_file_pth = './remote_experiment_configs/sockshop_scale_test1.json'

    else:
        config_file_pth = args.config_json

    run_experiment(config_file_pth, args.only_retrieve, args.upload_data, args.only_process, args.run_only_log_checker,
                   args.use_k3s_cluster, args.only_retrieve_multilooper, machine_ip, remote_server_key, user)