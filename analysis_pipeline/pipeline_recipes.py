import json
import time

import pyximport
pyximport.install() # am I sure that I want this???

import sys
import gc
import functools
import numpy as np

import matplotlib
matplotlib.use('Agg',warn=False, force=True)

from analysis_pipeline.pipeline_coordinator import multi_experiment_pipeline
from analysis_pipeline.single_experiment_pipeline import data_anylsis_pipline

'''
This file is essentially just sets of parameters for the run_data_analysis_pipeline function in pipeline_coordinator.py
There are a lot of parameters, and some of them are rather long, so I decided to make a function to store them in
'''

# these lists are only need for processing the k8s pod info
#microservices_sockshop = ['carts-db', 'carts', 'catalogue-db', 'catalogue', 'front-end', 'orders-db', 'orders',
#                         'payment', 'queue-master', 'rabbitmq', 'session-db', 'shipping', 'user-db', 'user',
#                          'load-test']
# NOTE: useed to be carts, not cart
microservices_sockshop = ['carts-db', 'cart', 'catalogue-db', 'catalogue', 'front-end', 'orders-db', 'orders',
                         'payment', 'queue-master', 'rabbitmq', 'shipping', 'user-db', 'user']
minikube_infrastructure = ['etcd', 'kube-addon-manager', 'kube-apiserver', 'kube-controller-manager',
                           'kube-dns', 'kube-proxy', 'kube-scheduler', 'kubernetes-dashboard', 'metrics-server',
                           'storage-provisioner']
microservices_wordpress = ['mariadb-master', 'mariadb-slave', 'wordpress']

def run_analysis_pipeline_recipes_json(json_file, path_to_experimental_data):
    with open(path_to_experimental_data + json_file) as f:
        data = json.load(f)
        pcap_paths = [path_to_experimental_data + i for i in data["pcap_paths"]]
        is_swarm = int(data["is_swarm"])
        basefile_name = path_to_experimental_data + data["basefile_name"]
        basegraph_name = path_to_experimental_data + data["basegraph_name"]
        container_info_path =  path_to_experimental_data + data["container_info_path"]
        cilium_config_path = (path_to_experimental_data + data["cilium_config_path"])[0] if (data["cilium_config_path"] and data["cilium_config_path"] != "None") else None
        kubernetes_svc_info = path_to_experimental_data + data["kubernetes_svc_info"]
        kubernetes_pod_info = path_to_experimental_data + data["kubernetes_pod_info"]
        time_interval_lengths = data["time_interval_lengths"]
        ms_s = data["ms_s"]
        make_edgefiles =  data["make_edgefiles"]
        start_time = data["start_time"]
        end_time = data["end_time"]
        exfil_start_time = data["exfil_start_time"]
        exfil_end_time = data["exfil_end_time"]
        calc_vals = data["calc_vals"]
        window_size = data["window_size"]
        graph_p = data["graph_p"]
        colors = data["colors"]
        wiggle_room = data["wiggle_room"] # the number of seconds to extend the start / end of exfil time (to account for imperfect synchronization)
        #percentile_thresholds = data["percentile_thresholds"]
        #anomaly_window = data["anomaly_window"]
        #anom_num_outlier_vals_in_window = data["anom_num_outlier_vals_in_window"]
        alert_file = path_to_experimental_data + data["alert_file"]
        ROC_curve_p =  data["ROC_curve_p"]
        calc_tpr_fpr_p =  data["calc_tpr_fpr_p"]
        sec_between_exfil_events = data['sec_between_exfil_events']

        run_data_anaylsis_pipeline(pcap_paths, is_swarm, basefile_name, container_info_path, time_interval_lengths,
                                   ms_s, make_edgefiles, basegraph_name, window_size, colors, exfil_start_time,
                                   exfil_end_time, wiggle_room, start_time=start_time, end_time=end_time,
                                   calc_vals=calc_vals, graph_p=graph_p, kubernetes_svc_info=kubernetes_svc_info,
                                   cilium_config_path=cilium_config_path, rdpcap_p=False,
                                   kubernetes_pod_info=kubernetes_pod_info, alert_file=alert_file,
                                   ROC_curve_p=ROC_curve_p, calc_zscore_p=calc_tpr_fpr_p,
                                   sec_between_exfil_events=sec_between_exfil_events)



def wordpress_thirteen_t2(time_of_synethic_exfil=None, only_exp_info=False, initiator_info_for_paths=None,
                            portion_for_training=None, training_window_size=None, size_of_neighbor_training_window=None,
                            synthetic_exfil_paths_train=None,
                            synthetic_exfil_paths_test=None, calc_vals=False,
                            skip_model_part=False,max_number_of_paths=None,
                            time_interval_lengths=None,
                            window_size=6, minimum_training_window=6,
                          startup_time=200):

    basefile_name = '/Volumes/exM2/experimental_data/wordpress_info/wordpress_thirteen_t2/edgefiles/wordpress_thirteen_t2_'
    basegraph_name = '/Volumes/exM2/experimental_data/wordpress_info/wordpress_thirteen_t2/graphs/wordpress_thirteen_t2_'
    alert_file = '/Volumes/exM2/experimental_data/wordpress_info/wordpress_thirteen_t2/alerts/wordpress_thirteen_t2_'

    container_info_path = "/Volumes/exM2/experimental_data/wordpress_info/wordpress_thirteen_t2/wordpress_thirteen_t2_docker_0_network_configs.txt"
    cilium_config_path = None # does NOT use cilium on reps 2-4
    kubernetes_svc_info = '/Volumes/exM2/experimental_data/wordpress_info/wordpress_thirteen_t2/wordpress_thirteen_t2_svc_config_0.txt'
    kubernetes_pod_info = '/Volumes/exM2/experimental_data/wordpress_info/wordpress_thirteen_t2/wordpress_thirteen_t2_pod_config_0.txt'
    pcap_paths = [
        "/Volumes/exM2/experimental_data/wordpress_info/wordpress_thirteen_t2/wordpress_thirteen_t2_default_bridge_0any.pcap"]

    is_swarm = 0
    ms_s = ["my-release-pxc", "wwwppp-wordpress"]
    start_time = False
    end_time = None
    exfil_start_time = 6090
    exfil_end_time = 6090
    graph_p = False  # should I make graphs?
    colors = ['b', 'r']
    wiggle_room = 2  # the number of seconds to extend the start / end of exfil time (to account for imperfect synchronization)
    sec_between_exfil_events = 15
    physical_exfil_path = []


    make_edgefiles = False ## already done!
    wordpress_thirteen_t2_object = data_anylsis_pipline(pcap_paths, is_swarm, basefile_name, container_info_path, time_interval_lengths, ms_s,
                                   make_edgefiles, basegraph_name, window_size, colors, exfil_start_time, exfil_end_time,
                                   wiggle_room, start_time=start_time, end_time=end_time, calc_vals=calc_vals,
                                   graph_p=graph_p, kubernetes_svc_info=kubernetes_svc_info,
                                   cilium_config_path=cilium_config_path, rdpcap_p=False,
                                   kubernetes_pod_info=kubernetes_pod_info, alert_file=alert_file, ROC_curve_p=True,
                                   calc_zscore_p=True, sec_between_exfil_events=sec_between_exfil_events,
                                   injected_exfil_path = physical_exfil_path, only_exp_info=only_exp_info,
                                   time_of_synethic_exfil=time_of_synethic_exfil,
                                   initiator_info_for_paths=initiator_info_for_paths,
                                   end_of_training=portion_for_training,
                                   training_window_size=training_window_size, size_of_neighbor_training_window=size_of_neighbor_training_window,
                                   synthetic_exfil_paths_train=synthetic_exfil_paths_train, synthetic_exfil_paths_test=synthetic_exfil_paths_test,
                                   skip_model_part=skip_model_part,
                                   max_number_of_paths=max_number_of_paths,
                                   minimum_training_window=minimum_training_window,
                                   startup_time=startup_time)

    return wordpress_thirteen_t2_object

def sockshop_thirteen_NOautoscale_mark1(time_of_synethic_exfil=None, only_exp_info=False, initiator_info_for_paths=None,
                            portion_for_training=None, training_window_size=None, size_of_neighbor_training_window=None,
                            synthetic_exfil_paths_train=None,
                            synthetic_exfil_paths_test=None, calc_vals=False,
                            skip_model_part=False,max_number_of_paths=None,
                            time_interval_lengths=None,
                            window_size=6, minimum_training_window=6,
                            startup_time=200):

    basefile_name = '/Volumes/exM2/experimental_data/sockshop_info/sockshop_thirteen_NOautoscale_mark1/edgefiles/sockshop_thirteen_NOautoscale_mark1_'
    basegraph_name = '/Volumes/exM2/experimental_data/sockshop_info/sockshop_thirteen_NOautoscale_mark1/graphs/sockshop_thirteen_NOautoscale_mark1_'
    alert_file = '/Volumes/exM2/experimental_data/sockshop_info/sockshop_thirteen_NOautoscale_mark1/alerts/sockshop_thirteen_NOautoscale_mark1_'

    pod_creation_log = None
    container_info_path = "/Volumes/exM2/experimental_data/sockshop_info/sockshop_thirteen_NOautoscale_mark1/sockshop_thirteen_NOautoscale_mark1_docker_0_network_configs.txt"
    cilium_config_path = None # does NOT use cilium on reps 2-4
    kubernetes_svc_info = '/Volumes/exM2/experimental_data/sockshop_info/sockshop_thirteen_NOautoscale_mark1/sockshop_thirteen_NOautoscale_mark1_svc_config_0.txt'
    kubernetes_pod_info = '/Volumes/exM2/experimental_data/sockshop_info/sockshop_thirteen_NOautoscale_mark1/sockshop_thirteen_NOautoscale_mark1_pod_config_0.txt'
    pcap_paths = [
        "/Volumes/exM2/experimental_data/sockshop_info/sockshop_thirteen_NOautoscale_mark1/sockshop_thirteen_NOautoscale_mark1_default_bridge_0any.pcap"
    ]
    netsec_policy = '/Volumes/exM2/experimental_data/sockshop_info/sockshop_nine_better_exfil_netsec_seg.txt'
    is_swarm = 0
    ms_s = microservices_sockshop
    start_time = False
    end_time = None
    exfil_start_time = 8000
    exfil_end_time = 8000
    graph_p = False  # should I make graphs?
    colors = ['b', 'r']
    wiggle_room = 2  # the number of seconds to extend the start / end of exfil time (to account for imperfect synchronization)
    sec_between_exfil_events = 15
    physical_exfil_path = []


    make_edgefiles = False ## already done!
    sockshop_thirteen_NOautoscale_mark1_object = data_anylsis_pipline(pcap_paths, is_swarm, basefile_name, container_info_path, time_interval_lengths, ms_s,
                                   make_edgefiles, basegraph_name, window_size, colors, exfil_start_time, exfil_end_time,
                                   wiggle_room, start_time=start_time, end_time=end_time, calc_vals=calc_vals,
                                   graph_p=graph_p, kubernetes_svc_info=kubernetes_svc_info,
                                   cilium_config_path=cilium_config_path, rdpcap_p=False,
                                   kubernetes_pod_info=kubernetes_pod_info, alert_file=alert_file, ROC_curve_p=True,
                                   calc_zscore_p=True, sec_between_exfil_events=sec_between_exfil_events,
                                   injected_exfil_path = physical_exfil_path, only_exp_info=only_exp_info,
                                   time_of_synethic_exfil=time_of_synethic_exfil,
                                   initiator_info_for_paths=initiator_info_for_paths,
                                   end_of_training=portion_for_training,
                                   training_window_size=training_window_size, size_of_neighbor_training_window=size_of_neighbor_training_window,
                                   synthetic_exfil_paths_train=synthetic_exfil_paths_train, synthetic_exfil_paths_test=synthetic_exfil_paths_test,
                                   skip_model_part=skip_model_part,
                                   max_number_of_paths=max_number_of_paths,
                                   minimum_training_window=minimum_training_window,
                                   startup_time=startup_time,
                                   pod_creation_log=pod_creation_log,
                                   netsec_policy=netsec_policy)

    return sockshop_thirteen_NOautoscale_mark1_object


def wordpress_fourteen_mark7(time_of_synethic_exfil=None, only_exp_info=False, calc_vals=False,
                                      time_interval_lengths=None, ide_window_size=10):

    basefile_name = '/Volumes/exM2/experimental_data/wordpress_info/wordpress_fourteen_mark7_final/edgefiles/wordpress_fourteen_mark7_final_'
    basegraph_name = '/Volumes/exM2/experimental_data/wordpress_info/wordpress_fourteen_mark7_final/graphs/wordpress_fourteen_mark7_final_'
    alert_file = '/Volumes/exM2/experimental_data/wordpress_info/wordpress_fourteen_mark7_final/alerts/wordpress_fourteen_mark7_final_'

    container_info_path = "/Volumes/exM2/experimental_data/wordpress_info/wordpress_fourteen_mark7_final/wordpress_fourteen_mark7_final_docker_0_network_configs.txt"
    cilium_config_path = None # does NOT use cilium on reps 2-4
    kubernetes_svc_info = '/Volumes/exM2/experimental_data/wordpress_info/wordpress_fourteen_mark7_final/wordpress_fourteen_mark7_final_svc_config_0.txt'
    kubernetes_pod_info = '/Volumes/exM2/experimental_data/wordpress_info/wordpress_fourteen_mark7_final/wordpress_fourteen_mark7_final_pod_config_0.txt'

    # eventaully these should be the only files that actually exist.
    pod_creation_log = "/Volumes/exM2/experimental_data/wordpress_info/wordpress_fourteen_mark7_final/wordpress_fourteen_mark7_final_pod_creation_log.txt"
    pcap_paths = [
        "/Volumes/exM2/experimental_data/wordpress_info/wordpress_fourteen_mark7_final/wordpress_fourteen_mark7_final_default_bridge_0any.pcap"]

    ms_s = ["my-release-pxc", "wwwppp-wordpress"]
    exfil_start_time = 8000
    exfil_end_time = 8000
    sec_between_exfil_events = 15
    physical_exfil_path = []

    make_edgefiles = False ## already done!
    wordpress_fourteen_mark7_object = data_anylsis_pipline(pcap_paths=pcap_paths,
                                                                    basefile_name=basefile_name, container_info_path=container_info_path,
                                                                    time_interval_lengths=time_interval_lengths,
                                                                    ms_s=ms_s, make_edgefiles_p=make_edgefiles,
                                                                    basegraph_name=basegraph_name,
                                                                    ide_window_size = ide_window_size,
                                                                    exfil_start_time=exfil_start_time,
                                                                    exfil_end_time=exfil_end_time,
                                                                    calc_vals=calc_vals,
                                                                    kubernetes_svc_info=kubernetes_svc_info,
                                                                    cilium_config_path=cilium_config_path,
                                                                    kubernetes_pod_info=kubernetes_pod_info,
                                                                    alert_file=alert_file,
                                                                    sec_between_exfil_events=sec_between_exfil_events,
                                                                    injected_exfil_path = physical_exfil_path,
                                                                    only_exp_info=only_exp_info,
                                                                    time_of_synethic_exfil=time_of_synethic_exfil,
                                                                    pod_creation_log=pod_creation_log,
                                                                    netsec_policy=None)

    return wordpress_fourteen_mark7_object


def sockshop_thirteen_autoscale_mark4(time_of_synethic_exfil=None, only_exp_info=False, calc_vals=False,
                                      time_interval_lengths=None, ide_window_size=10):

    experiment_folder = '/Volumes/exM2/experimental_data/sockshop_info/sockshop_thirteen_autoscale_mark4/'

    basefile_name = experiment_folder + 'edgefiles/sockshop_thirteen_autoscale_mark4_'
    basegraph_name = experiment_folder + 'graphs/sockshop_thirteen_autoscale_mark4_'
    alert_file = experiment_folder + 'alerts/sockshop_thirteen_autoscale_mark4_'

    pod_creation_log = experiment_folder + "sockshop_thirteen_autoscale_mark4_pod_creation_log.txt"
    container_info_path = experiment_folder + "sockshop_thirteen_autoscale_mark4_docker_0_network_configs.txt"
    kubernetes_svc_info = experiment_folder + 'sockshop_thirteen_autoscale_mark4_svc_config_0.txt'
    kubernetes_pod_info = experiment_folder + 'sockshop_thirteen_autoscale_mark4_pod_config_0.txt'
    pcap_paths = [ experiment_folder + "sockshop_thirteen_autoscale_mark4_default_bridge_0any.pcap"]

    netsec_policy = '/Volumes/exM2/experimental_data/sockshop_info/sockshop_nine_better_exfil_netsec_seg.txt'

    cilium_config_path = None # does NOT use cilium on reps 2-4
    ms_s = microservices_sockshop
    exfil_start_time = 8000
    exfil_end_time = 8000
    physical_exfil_path = []
    sec_between_exfil_events = 15

    make_edgefiles = False ## already done!

    sockshop_thirteen_autoscale_mark4_object = data_anylsis_pipline(pcap_paths=pcap_paths,
                                                                    basefile_name=basefile_name, container_info_path=container_info_path,
                                                                    time_interval_lengths=time_interval_lengths,
                                                                    ms_s=ms_s, make_edgefiles_p=make_edgefiles,
                                                                    basegraph_name=basegraph_name,
                                                                    ide_window_size = ide_window_size,
                                                                    exfil_start_time=exfil_start_time,
                                                                    exfil_end_time=exfil_end_time,
                                                                    calc_vals=calc_vals,
                                                                    kubernetes_svc_info=kubernetes_svc_info,
                                                                    cilium_config_path=cilium_config_path,
                                                                    kubernetes_pod_info=kubernetes_pod_info,
                                                                    alert_file=alert_file,
                                                                    sec_between_exfil_events=sec_between_exfil_events,
                                                                    injected_exfil_path = physical_exfil_path,
                                                                    only_exp_info=only_exp_info,
                                                                    time_of_synethic_exfil=time_of_synethic_exfil,
                                                                    pod_creation_log=pod_creation_log,
                                                                    netsec_policy=netsec_policy)

    return sockshop_thirteen_autoscale_mark4_object

def nonauto_sockshop_recipe():
    skip_model_part = False
    ignore_physical_attacks_p = True

    time_of_synethic_exfil = 30 # sec
    goal_train_test_split_training = 0.5
    goal_attack_NoAttack_split_training = 0.6
    goal_attack_NoAttack_split_testing = 0.2

    time_interval_lengths = [30, 10]#, 10] #[30, 10, 1] #[30, 10, 1] #[30, 10, 1]#,

    # this doesn't actually do anything
    size_of_neighbor_training_window = 0
    # window size is for ide_angles and the other things that use the angle between the principal
    # eigenvectors
    window_size = 10
    # these are for the moz-z-score-calculation
    training_window_size = 400
    minimum_training_window = 12
    # note: attack injection doesn't start until startup_time has elapsed
    startup_time = 25 * np.max(time_interval_lengths)
    ###

    #####
    # IN MEGABYTES / MINUTE
    avg_exfil_per_min = [10.0, 2.0, 1.0, 0.25, 0.1] # [10.0, 2.0, 1.0, 0.25, 0.1] # [10.0, 2.0, 1.0, 0.25, 0.1]
    exfil_per_min_variance = [0.3, 0.2, 0.15, 0.08, 0.05] # [0.3. 0.2, 0.15, 0.08, 0.05] #[0.3, 0.2, 0.15, 0.08, 0.05]
    avg_pkt_size = [500.0, 500.0, 500.00, 500.00, 500.0]
    pkt_size_variance = [100, 100, 100, 100, 100]

    BytesPerMegabyte = 1000000
    avg_exfil_per_min = [BytesPerMegabyte * i for i in avg_exfil_per_min]
    exfil_per_min_variance = [BytesPerMegabyte * i for i in exfil_per_min_variance]
    ######

    calc_vals = False
    calculate_z_scores = True
    include_ide = False # include ide vals? this'll involve either calculating them (below) or grabbing them from the file location
    calc_ide = False
    only_ide = False ## ONLY calculate the ide values... this'll be useful if I wanna first calc all the other values and THEN ide...
    drop_pairwise_features = False # drops pairwise features (i.e. serviceX_to_serviceY_reciprocity)

    ####
    cur_experiment_name = "mark1_"
    base_output_location = '/Volumes/exM2/experimental_data/sockshop_summary_new_nonauto13/nonauto13_'# + 'lasso_roc'
    base_output_location += cur_experiment_name
    if drop_pairwise_features:
        base_output_location += 'dropPairWise_'

    #####

    skip_graph_injection = False
    get_endresult_from_memory = False # in this case, you'd skip literally the whole pipeline and just get the
                                      # trained model + the results (from that model) out of memory
                                      # I anticpate that this'll mostly be useful for working on generating
                                      # the final results report + the graphs + other stuff kinda...

    experiment_classes = [sockshop_thirteen_NOautoscale_mark1(training_window_size=training_window_size,
                                                size_of_neighbor_training_window=size_of_neighbor_training_window,
                                                calc_vals=calc_vals,
                                                time_of_synethic_exfil=time_of_synethic_exfil,
                                                time_interval_lengths=time_interval_lengths,
                                                window_size=window_size,
                                                minimum_training_window=minimum_training_window,
                                                startup_time=startup_time)]

    return multi_experiment_pipeline(experiment_classes, base_output_location, True, time_of_synethic_exfil,
                              goal_train_test_split_training, goal_attack_NoAttack_split_training, training_window_size,
                              size_of_neighbor_training_window, calc_vals, skip_model_part, ignore_physical_attacks_p,
                              calculate_z_scores_p=calculate_z_scores,
                              avg_exfil_per_min=avg_exfil_per_min, exfil_per_min_variance=exfil_per_min_variance,
                              avg_pkt_size=avg_pkt_size, pkt_size_variance=pkt_size_variance,
                              skip_graph_injection=skip_graph_injection,
                              get_endresult_from_memory=get_endresult_from_memory,
                              goal_attack_NoAttack_split_testing=goal_attack_NoAttack_split_testing,
                              calc_ide=calc_ide, include_ide=include_ide, only_ide=only_ide,
                              drop_pairwise_features=drop_pairwise_features)


def autoscaling_sockshop_recipe():
    skip_model_part = False
    ignore_physical_attacks_p = True

    time_of_synethic_exfil = 30 # sec
    goal_train_test_split_training = 0.5
    goal_attack_NoAttack_split_training = 0.6
    goal_attack_NoAttack_split_testing = 0.2

    time_interval_lengths = [30, 10]#, 10] #[30, 10, 1] #[30, 10, 1] #[30, 10, 1]#,

    #####
    # IN MEGABYTES / MINUTE
    avg_exfil_per_min = [10.0, 2.0, 1.0, 0.25] #, 0.1] #[10.0, 2.0, 1.0, 0.25, 0.1] # [10.0, 2.0, 1.0, 0.25, 0.1] # [10.0, 2.0, 1.0, 0.25, 0.1]
    exfil_per_min_variance = [0.3, 0.2, 0.15, 0.08] #, 0.05] #[0.3, 0.2, 0.15, 0.08, 0.05] # [0.3. 0.2, 0.15, 0.08, 0.05] #[0.3, 0.2, 0.15, 0.08, 0.05]
    avg_pkt_size = [500.0, 500.0, 500.00, 500.00, 500.0]
    pkt_size_variance = [100, 100, 100, 100, 100]

    BytesPerMegabyte = 1000000
    avg_exfil_per_min = [BytesPerMegabyte * i for i in avg_exfil_per_min]
    exfil_per_min_variance = [BytesPerMegabyte * i for i in exfil_per_min_variance]

    # max_number_of_paths = 20 ## not sure if I want to do this still...
    ######

    calc_vals = False
    calculate_z_scores = True
    include_ide = False # include ide vals? this'll involve either calculating them (below) or grabbing them from the file location
    calc_ide = False
    only_ide = False ## ONLY calculate the ide values... this'll be useful if I wanna first calc all the other values and THEN ide...
    ide_window_size = 10 # size of the sliding window over which ide operates
    drop_pairwise_features = False # drops pairwise features (i.e. serviceX_to_serviceY_reciprocity)
    drop_infra_from_graph = False ## TODO: doesn't do anything yet.

    ####
    cur_experiment_name = "mark4_24_adjAT_"
    base_output_location = '/Volumes/exM2/experimental_data/sockshop_summary_new/new_'# + 'lasso_roc'
    base_output_location += cur_experiment_name
    if drop_pairwise_features:
        base_output_location += 'dropPairWise_'

    #####

    skip_graph_injection = False
    get_endresult_from_memory = False # in this case, you'd skip literally the whole pipeline and just get the
                                      # trained model + the results (from that model) out of memory
                                      # I anticpate that this'll mostly be useful for working on generating
                                      # the final results report + the graphs + other stuff kinda...

    experiment_classes = [sockshop_thirteen_autoscale_mark4(calc_vals=calc_vals,
                                                time_of_synethic_exfil=time_of_synethic_exfil,
                                                time_interval_lengths=time_interval_lengths,
                                                ide_window_size=ide_window_size)]

    return multi_experiment_pipeline(experiment_classes, base_output_location, True, time_of_synethic_exfil,
                              goal_train_test_split_training, goal_attack_NoAttack_split_training, None,
                              None, calc_vals, skip_model_part, ignore_physical_attacks_p,
                              calculate_z_scores_p=calculate_z_scores,
                              avg_exfil_per_min=avg_exfil_per_min, exfil_per_min_variance=exfil_per_min_variance,
                              avg_pkt_size=avg_pkt_size, pkt_size_variance=pkt_size_variance,
                              skip_graph_injection=skip_graph_injection,
                              get_endresult_from_memory=get_endresult_from_memory,
                              goal_attack_NoAttack_split_testing=goal_attack_NoAttack_split_testing,
                              calc_ide=calc_ide, include_ide=include_ide, only_ide=only_ide,
                              drop_pairwise_features=drop_pairwise_features, drop_infra_from_graph=drop_infra_from_graph)


def new_wordpress_autoscaling_recipe():
    skip_model_part = False
    ignore_physical_attacks_p = True

    time_of_synethic_exfil = 30 # sec
    goal_train_test_split_training = 0.5
    goal_attack_NoAttack_split_training = 0.6
    goal_attack_NoAttack_split_testing = 0.2

    #time_interval_lengths = [10, 30]#, 10] #[30, 10, 1] #[30, 10, 1] #[30, 10, 1]#,
    time_interval_lengths = [10, 30]#, 10, 100]#, 10] #[30, 10, 1] #[30, 10, 1] #[30, 10, 1]#,

    # ide_window_size is for ide_angles and the other things that use the angle between the principal eigenvectors
    ide_window_size = 10

    #####
    # IN MEGABYTES / MINUTE
    avg_exfil_per_min = [0.25, 0.1] #[10.0, 1.0, 0.25, 0.1]#, 0.1 ] #[10.0, 2.0,
    exfil_per_min_variance = [0.08, 0.05] # [0.3, 0.15, 0.08, 0.05] #, 0.05] # 0.3, 0.2,
    avg_pkt_size = [500.0, 500.00, 500.00, 500.00]#, 500.0] # 500.0, 500.0,
    pkt_size_variance = [100, 100, 100, 100]#, 100] # 100, 100,

    BytesPerMegabyte = 1000000
    avg_exfil_per_min = [BytesPerMegabyte * i for i in avg_exfil_per_min]
    exfil_per_min_variance = [BytesPerMegabyte * i for i in exfil_per_min_variance]
    ######

    calc_vals = True
    calculate_z_scores = True
    include_ide = False # include ide vals? this'll involve either calculating them (below) or grabbing them from the file location
    calc_ide = False
    only_ide = False ## ONLY calculate the ide values... this'll be useful if I wanna first calc all the other values and THEN ide...
    drop_pairwise_features = False # drops pairwise features (i.e. serviceX_to_serviceY_reciprocity)

    ####
    cur_experiment_name = "autoscaling_mark7_orderMagTimeGran_"
    base_output_location = '/Volumes/exM2/experimental_data/wordpress_summary_new/new_'# + 'lasso_roc'
    base_output_location += cur_experiment_name
    if drop_pairwise_features:
        base_output_location += 'dropPairWise_'
    #####

    skip_graph_injection = False
    get_endresult_from_memory = False # in this case, you'd skip literally the whole pipeline and just get the
                                      # trained model + the results (from that model) out of memory
                                      # I anticpate that this'll mostly be useful for working on generating
                                      # the final results report + the graphs + other stuff kinda...

    experiment_classes = [wordpress_fourteen_mark7(calc_vals=calc_vals,
                                                time_of_synethic_exfil=time_of_synethic_exfil,
                                                time_interval_lengths=time_interval_lengths,
                                                ide_window_size=ide_window_size)]

    return multi_experiment_pipeline(experiment_classes, base_output_location, True, time_of_synethic_exfil,
                              goal_train_test_split_training, goal_attack_NoAttack_split_training, None,
                              None, calc_vals, skip_model_part, ignore_physical_attacks_p,
                              calculate_z_scores_p=calculate_z_scores,
                              avg_exfil_per_min=avg_exfil_per_min, exfil_per_min_variance=exfil_per_min_variance,
                              avg_pkt_size=avg_pkt_size, pkt_size_variance=pkt_size_variance,
                              skip_graph_injection=skip_graph_injection,
                              get_endresult_from_memory=get_endresult_from_memory,
                              goal_attack_NoAttack_split_testing=goal_attack_NoAttack_split_testing,
                              calc_ide=calc_ide, include_ide=include_ide, only_ide=only_ide,
                              drop_pairwise_features=drop_pairwise_features)

def new_wordpress_recipe():
    skip_model_part = False
    ignore_physical_attacks_p = True

    time_of_synethic_exfil = 30 # sec
    goal_train_test_split_training = 0.5
    goal_attack_NoAttack_split_training = 0.6
    goal_attack_NoAttack_split_testing = 0.2

    time_interval_lengths = [10, 30] #[30, 10] #[30, 10, 1] #[30, 10, 1] #[30, 10, 1]#,

    # this doesn't actually do anything
    size_of_neighbor_training_window = 0
    # window size is for ide_angles and the other things that use the angle between the principal
    # eigenvectors
    window_size = 12
    # these are for the moz-z-score-calculation
    training_window_size = 400
    minimum_training_window = 12
    # note: attack injection doesn't start until startup_time has elapsed
    startup_time = 25 * np.max(time_interval_lengths)
    ###

    #####
    # IN MEGABYTES / MINUTE
    avg_exfil_per_min =  [10.0, 1.0, 0.25, 0.1]#, 10.0 2.0, 1.0, 0.25, 0.1] #[100000000.0] # [100.0
    exfil_per_min_variance = [0.3, 0.15, 0.08, 0.05]# 0.3, 0.2, 0.15, 0.08, 0.05] #[100.0] # 1.0,
    avg_pkt_size = [500.0, 500.0, 500.0, 500.0] #500.0 , 500.0, 500.00, 500.00, 500.0] #[1000.0] # 500.0,
    pkt_size_variance = [100, 100, 100, 100] #100, 100, 100, 100, 100] #[100] #100,

    BytesPerMegabyte = 1000000
    avg_exfil_per_min = [BytesPerMegabyte * i for i in avg_exfil_per_min]
    exfil_per_min_variance = [BytesPerMegabyte * i for i in exfil_per_min_variance]
    ######

    calc_vals = False
    calculate_z_scores = False
    calc_ide = False
    include_ide = True
    only_ide = False ## ONLY calculate the ide values... this'll be useful if I wanna first calc all the other values and THEN ide...
    drop_pairwise_features = False # drops pairwise features (i.e. serviceX_to_serviceY_reciprocity)

    ###############

    ####
    cur_experiment_name = "v2_testingNewPipeline"  # can modify if you want, probably with:  new_wordpress_recipe.__name__
    base_output_location = '/Volumes/exM2/experimental_data/wordpress_summary_new/new_'# + 'lasso_roc'
    base_output_location += cur_experiment_name
    if drop_pairwise_features:
        base_output_location += 'dropPairWise_'
    #####

    skip_graph_injection = False
    get_endresult_from_memory = True # in this case, you'd skip literally the whole pipeline and just get the
                                      # trained model + the results (from that model) out of memory
                                      # I anticpate that this'll mostly be useful for working on generating
                                      # the final results report + the graphs + other stuff kinda...

    experiment_classes = [wordpress_thirteen_t2(training_window_size=training_window_size,
                                                size_of_neighbor_training_window=size_of_neighbor_training_window,
                                                calc_vals=calc_vals,
                                                time_of_synethic_exfil=time_of_synethic_exfil,
                                                time_interval_lengths=time_interval_lengths,
                                                window_size=window_size,
                                                minimum_training_window=minimum_training_window,
                                                startup_time=startup_time)

    return multi_experiment_pipeline(experiment_classes, base_output_location, True, time_of_synethic_exfil,
                              goal_train_test_split_training, goal_attack_NoAttack_split_training, training_window_size,
                              size_of_neighbor_training_window, calc_vals, skip_model_part, ignore_physical_attacks_p,
                              calculate_z_scores_p=calculate_z_scores,
                              avg_exfil_per_min=avg_exfil_per_min, exfil_per_min_variance=exfil_per_min_variance,
                              avg_pkt_size=avg_pkt_size, pkt_size_variance=pkt_size_variance,
                              skip_graph_injection=skip_graph_injection,
                              get_endresult_from_memory=get_endresult_from_memory,
                              goal_attack_NoAttack_split_testing=goal_attack_NoAttack_split_testing,
                              calc_ide=calc_ide, include_ide=include_ide, only_ide=only_ide,
                              drop_pairwise_features=drop_pairwise_features)

if __name__=="__main__":
    print "RUNNING"
    print sys.argv

    if len(sys.argv) == 1:
        print "running_preset..."
        autoscaling_sockshop_recipe()
    else:
        print "too many args!"
