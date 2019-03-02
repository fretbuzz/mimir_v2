import cPickle as pickle
import copy
import gc
import logging
import math
import multiprocessing
from itertools import groupby
from operator import itemgetter

import pandas as pd

import analysis_pipeline.generate_graphs
import analysis_pipeline.prepare_graph
from analysis_pipeline import gen_attack_templates, process_pcap, process_graph_metrics, simplified_graph_metrics
from analysis_pipeline.pcap_to_edgelists import create_mappings


## TODO: this function is an atrocity and should be converted into a snakemake spec so we can use that instead...###
## todo (aim to get it done today...) : change  run_data_analysis_pipeline signature plus the feeder...

# run_data_anaylsis_pipeline : runs the whole analysis_pipeline pipeline (or a part of it)
# (1) creates edgefiles, (2) creates communication graphs from edgefiles, (3) calculates (and stores) graph metrics
# (4) makes graphs of the graph metrics
# Note: see run_analysis_pipeline_recipes for pre-configured sets of parameters (there are rather a lot)
class data_anylsis_pipline(object):
    def __init__(self, pcap_paths, is_swarm, basefile_name, container_info_path, time_interval_lengths, ms_s,
                               make_edgefiles_p, basegraph_name, window_size, colors, exfil_start_time, exfil_end_time,
                               wiggle_room, start_time=None, end_time=None, calc_vals=True, graph_p=True,
                               kubernetes_svc_info=None, make_net_graphs_p=False, cilium_config_path=None,
                               rdpcap_p=False, kubernetes_pod_info=None, alert_file=None, ROC_curve_p=False,
                               calc_zscore_p=False, training_window_size=200, minimum_training_window=5,
                               sec_between_exfil_events=1, time_of_synethic_exfil=30,
                               size_of_neighbor_training_window=300,
                               end_of_training=None, injected_exfil_path='None', only_exp_info=False,
                               initiator_info_for_paths=None,
                               synthetic_exfil_paths_train=None, synthetic_exfil_paths_test=None,
                               skip_model_part=False, max_number_of_paths=None, netsec_policy=None,
                                startup_time=200):
        self.ms_s = ms_s
        print "log file can be found at: " + str(basefile_name) + '_logfile.log'
        logging.basicConfig(filename=basefile_name + '_logfile.log', level=logging.INFO)
        logging.info('run_data_anaylsis_pipeline Started')

        if 'kube-dns' not in ms_s:
            self.ms_s.append('kube-dns')  # going to put this here so I don't need to re-write all the recipes...

        gc.collect()

        print "starting pipeline..."

        # sub_path = 'sub_only_edge_corr_'  # NOTE: make this an empty string if using the full pipeline (and not the subset)
        # sub_path = 'sub_only_ide_'  # NOTE: make this an empty string if using the full pipeline (and not the subset)
        ### TODO put VVV back in...
        self.sub_path = 'sub_'  # NOTE: make this an empty string if using the full pipeline (and not the subset)
        self.mapping, self.list_of_infra_services = create_mappings(is_swarm, container_info_path, kubernetes_svc_info,
                                                          kubernetes_pod_info, cilium_config_path, ms_s)

        self.calc_zscore_p=calc_zscore_p
        self.is_swarm = is_swarm
        self.container_info_path = container_info_path
        self.kubernetes_svc_info = kubernetes_svc_info
        self.kubernetes_pod_info = kubernetes_pod_info
        self.cilium_config_path = cilium_config_path
        self.time_interval_lengths = time_interval_lengths
        self.basegraph_name = basegraph_name
        self.window_size = window_size
        self.colors = colors
        self.exfil_start_time = exfil_start_time
        self.exfil_end_time = exfil_end_time
        self.minimum_training_window = minimum_training_window
        self.experiment_folder_path = basefile_name.split('edgefiles')[0]
        self.pcap_file = pcap_paths[0].split('/')[-1]  # NOTE: assuming only a single pcap file...
        self.exp_name = basefile_name.split('/')[-1]
        self.base_exp_name = self.exp_name
        self.make_edgefiles_p = make_edgefiles_p and only_exp_info
        self.netsec_policy = netsec_policy
        self.make_edgefiles_p=make_edgefiles_p
        self.graph_p = graph_p
        self.sensitive_ms = None
        self.time_of_synethic_exfil = time_of_synethic_exfil
        self.injected_exfil_path = injected_exfil_path
        self.make_net_graphs_p=make_net_graphs_p
        self.alert_file=alert_file
        self.wiggle_room=wiggle_room
        self.sec_between_exfil_events=sec_between_exfil_events
        self.orig_alert_file = self.alert_file
        self.orig_basegraph_name = self.basegraph_name
        self.orig_exp_name = self.exp_name

        self.synthetic_exfil_paths = None
        self.initiator_info_for_paths = None
        self.training_window_size = training_window_size
        self.size_of_neighbor_training_window = size_of_neighbor_training_window
        print training_window_size,size_of_neighbor_training_window
        self.system_startup_time = start_time #training_window_size + size_of_neighbor_training_window
        self.calc_vals = calc_vals

        self.time_gran_to_feature_dataframe=None
        self.time_gran_to_attack_labels=None
        self.time_gran_to_synthetic_exfil_paths_series=None
        self.time_gran_to_list_of_concrete_exfil_paths  = None
        self.time_gran_to_list_of_exfil_amts=None
        self.time_gran_to_new_neighbors_outside=None
        self.time_gran_to_new_neighbors_dns=None
        self.time_gran_to_new_neighbors_all=None
        self.time_gran_to_list_of_amt_of_out_traffic_bytes = None
        self.time_gran_to_list_of_amt_of_out_traffic_pkts = None

        for ms in ms_s:
            if 'user' in ms and 'db' in ms:
                self.sensitive_ms = ms
            if 'my-release' in ms:
                self.sensitive_ms = ms

        self.process_pcaps()

    def generate_synthetic_exfil_paths(self, max_number_of_paths):
        self.netsec_policy = gen_attack_templates.parse_netsec_policy(self.netsec_policy)
        synthetic_exfil_paths, initiator_info_for_paths = \
            gen_attack_templates.generate_synthetic_attack_templates(self.mapping, self.ms_s, self.sensitive_ms,
                                                                     max_number_of_paths, self.netsec_policy)
        self.synthetic_exfil_paths = synthetic_exfil_paths
        self.initiator_info_for_paths = initiator_info_for_paths
        return synthetic_exfil_paths, initiator_info_for_paths

    def process_pcaps(self):
        self.interval_to_filenames = process_pcap.process_pcap(self.experiment_folder_path, self.pcap_file, self.time_interval_lengths,
                                                          self.exp_name, self.make_edgefiles_p, self.mapping)

    def get_exp_info(self):
        time_grans = [int(i) for i in self.interval_to_filenames.keys()]
        smallest_time_gran = min(time_grans)
        self.smallest_time_gran = smallest_time_gran
        self.total_experiment_length = len(self.interval_to_filenames[str(smallest_time_gran)]) * smallest_time_gran
        print "about to return from only_exp_info section", self.total_experiment_length, self.exfil_start_time, self.exfil_end_time, \
            self.system_startup_time, None
        #return total_experiment_length, self.exfil_start_time, self.exfil_end_time, self.system_startup_time
        return self.total_experiment_length, self.exfil_start_time, self.exfil_end_time, self.system_startup_time

    def correct_attacks_labels_using_exfil_amts(self, time_gran_to_attack_labels, time_gran_to_list_of_exfil_amts):
        time_gran_to_new_attack_labels = {}
        for time_gran, attack_labels in time_gran_to_attack_labels.iteritems():
            new_attack_labels = []
            list_of_exfil_amts = time_gran_to_list_of_exfil_amts[time_gran]
            for counter,label in enumerate(attack_labels):
                if list_of_exfil_amts[counter] == 0: # if it equals zero, then we know there isn't an actual attack
                    new_attack_labels.append(0)
                else:
                    new_attack_labels.append(label) # otherwise go w/ existing
            time_gran_to_new_attack_labels[time_gran] = new_attack_labels

        return time_gran_to_new_attack_labels

    def calculate_values(self,end_of_training, synthetic_exfil_paths_train, synthetic_exfil_paths_test,
                         avg_exfil_per_min, exfil_per_min_variance, avg_pkt_size, pkt_size_variance):
        self.end_of_training = end_of_training
        if self.calc_vals or self.graph_p:
            # TODO: 90% sure that there is a problem with this function...
            # largest_interval = int(min(interval_to_filenames.keys()))
            exp_length = len(self.interval_to_filenames[str(self.smallest_time_gran)]) * self.smallest_time_gran
            print "exp_length_ZZZ", exp_length, type(exp_length)
            # if not skip_model_part:
            time_gran_to_attack_labels = process_graph_metrics.generate_time_gran_to_attack_labels(
                self.time_interval_lengths,
                self.exfil_start_time, self.exfil_end_time,
                self.sec_between_exfil_events,
                exp_length)
            # else:
            # time_gran_to_attack_labels = {}
            # for time_gran in time_interval_lengths:
            #    time_gran_to_attack_labels[time_gran] = [(1,1)]
            # pass

            # print "interval_to_filenames_ZZZ",interval_to_filenames
            for interval, filenames in self.interval_to_filenames.iteritems():
                print "interval_ZZZ", interval, len(filenames)
            for time_gran, attack_labels in time_gran_to_attack_labels.iteritems():
                print "time_gran_right_after_creation", time_gran, "len of attack labels", len(attack_labels)

            print self.interval_to_filenames, type(self.interval_to_filenames), 'stufff', self.interval_to_filenames.keys()

            # most of the parameters are kinda arbitrary ATM...
            print "INITIAL time_gran_to_attack_labels", time_gran_to_attack_labels
            ## okay, I'll probably wanna write tests for the below function, but it seems to be working pretty well on my
            # informal tests...
            end_of_training = end_of_training
            synthetic_exfil_paths = []
            for path in synthetic_exfil_paths_train + synthetic_exfil_paths_test:
                if path not in synthetic_exfil_paths:
                    synthetic_exfil_paths.append(path)

            print "synthetic_exfil_paths_train", synthetic_exfil_paths_train
            print "synthetic_exfil_paths_test", synthetic_exfil_paths_test
            print "synthetic_exfil_paths", synthetic_exfil_paths
            time_gran_to_attack_labels, time_gran_to_attack_ranges, time_gran_to_physical_attack_ranges = \
                determine_attacks_to_times(time_gran_to_attack_labels, synthetic_exfil_paths,
                                           time_of_synethic_exfil=self.time_of_synethic_exfil,
                                           min_starting=self.system_startup_time, end_of_train=end_of_training,
                                           synthetic_exfil_paths_train=synthetic_exfil_paths_train,
                                           synthetic_exfil_paths_test=synthetic_exfil_paths_test)
            print "time_gran_to_attack_labels", time_gran_to_attack_labels
            print "time_gran_to_attack_ranges", time_gran_to_attack_ranges
            # time.sleep(50)

            time_gran_to_synthetic_exfil_paths_series = determine_time_gran_to_synthetic_exfil_paths_series(
                time_gran_to_attack_ranges,
                synthetic_exfil_paths, self.interval_to_filenames,
                time_gran_to_physical_attack_ranges, self.injected_exfil_path)

            print "time_gran_to_synthetic_exfil_paths_series", time_gran_to_synthetic_exfil_paths_series
            # time.sleep(50)

            # exit(200) ## TODO ::: <<<---- remove!!
            ### OKAY, this is where I'd need to add in the component that loops over the various injected exfil weights
            # OKAY, let's verify that this determine_attacks_to_times function is wokring before moving on to the next one...
            total_calculated_vals, time_gran_to_list_of_concrete_exfil_paths, time_gran_to_list_of_exfil_amts, \
            time_gran_to_new_neighbors_outside, time_gran_to_new_neighbors_dns, time_gran_to_new_neighbors_all, \
            time_gran_to_list_of_amt_of_out_traffic_bytes, time_gran_to_list_of_amt_of_out_traffic_pkts= \
                calculate_raw_graph_metrics(self.time_interval_lengths, self.interval_to_filenames, self.ms_s, self.basegraph_name,
                                            self.calc_vals,
                                            self.window_size, self.mapping, self.is_swarm, self.make_net_graphs_p,
                                            self.list_of_infra_services,
                                            synthetic_exfil_paths, self.initiator_info_for_paths, time_gran_to_attack_ranges,
                                            self.size_of_neighbor_training_window,
                                            avg_exfil_per_min, exfil_per_min_variance, avg_pkt_size, pkt_size_variance)

            ## time_gran_to_attack_labels needs to be corrected using time_gran_to_list_of_concrete_exfil_paths
            ## because just because it was assigned, doesn't mean that it is necessarily going to be injected (might
            ## have to wait...)
            time_gran_to_attack_labels = self.correct_attacks_labels_using_exfil_amts(time_gran_to_attack_labels,
                                                                                      time_gran_to_list_of_exfil_amts)

            time_gran_to_feature_dataframe = process_graph_metrics.generate_feature_dfs(total_calculated_vals,
                                                                                        self.time_interval_lengths)

            process_graph_metrics.save_feature_datafames(time_gran_to_feature_dataframe, self.alert_file + self.sub_path,
                                                         time_gran_to_attack_labels,
                                                         time_gran_to_synthetic_exfil_paths_series,
                                                         time_gran_to_list_of_concrete_exfil_paths,
                                                         time_gran_to_list_of_exfil_amts,
                                                         int(end_of_training), time_gran_to_new_neighbors_outside,
                                                         time_gran_to_new_neighbors_dns, time_gran_to_new_neighbors_all,
                                                         time_gran_to_list_of_amt_of_out_traffic_bytes,
                                                         time_gran_to_list_of_amt_of_out_traffic_pkts)

            try: # this thing returns some kinda error but i don't care.
                analysis_pipeline.generate_graphs.generate_feature_multitime_boxplots(total_calculated_vals, self.basegraph_name,
                                                                                  self.window_size, self.colors,
                                                                                  self.time_interval_lengths,
                                                                                  self.exfil_start_time, self.exfil_end_time,
                                                                                  self.wiggle_room)

            except:
                pass
        else:
            time_gran_to_feature_dataframe = {}
            time_gran_to_attack_labels = {}
            time_gran_to_synthetic_exfil_paths_series = {}
            time_gran_to_list_of_concrete_exfil_paths = {}
            time_gran_to_list_of_exfil_amts = {}
            time_gran_to_list_of_amt_of_out_traffic_bytes = {}
            time_gran_to_list_of_amt_of_out_traffic_pkts = {}
            time_gran_to_new_neighbors_outside, time_gran_to_new_neighbors_dns, time_gran_to_new_neighbors_all = {}, {}, {}
            min_interval = min(self.time_interval_lengths)
            for interval in self.time_interval_lengths:
                # if interval in time_interval_lengths:
                print "time_interval_lengths", self.time_interval_lengths, "interval", interval
                print "feature_df_path", self.alert_file + self.sub_path + str(interval) + '.csv'
                time_gran_to_feature_dataframe[interval] = pd.read_csv(self.alert_file + self.sub_path + str(interval) + '.csv',
                                                                       na_values='?')
                # time_gran_to_feature_dataframe[interval] = time_gran_to_feature_dataframe[interval].apply(lambda x: np.real(x))
                print "dtypes_of_df", time_gran_to_feature_dataframe[interval].dtypes
                time_gran_to_attack_labels[interval] = time_gran_to_feature_dataframe[interval]['labels']

                time_gran_to_list_of_amt_of_out_traffic_bytes[interval] = time_gran_to_feature_dataframe[interval]['amt_of_out_traffic_bytes']
                time_gran_to_list_of_amt_of_out_traffic_pkts[interval] = time_gran_to_feature_dataframe[interval]['amt_of_out_traffic_pkts']

                try:
                    time_gran_to_new_neighbors_outside[interval] = time_gran_to_feature_dataframe[interval][
                        'new_neighbors_outside']
                    time_gran_to_new_neighbors_dns[interval] = time_gran_to_feature_dataframe[interval][
                        'new_neighbors_dns']
                    time_gran_to_new_neighbors_all[interval] = time_gran_to_feature_dataframe[interval][
                        'new_neighbors_all']
                except:
                    time_gran_to_new_neighbors_outside[interval] = [[] for i in
                                                                    range(0, len(time_gran_to_attack_labels[interval]))]
                    time_gran_to_new_neighbors_dns[interval] = [[] for i in
                                                                range(0, len(time_gran_to_attack_labels[interval]))]
                    time_gran_to_new_neighbors_all[interval] = [[] for i in
                                                                range(0, len(time_gran_to_attack_labels[interval]))]

                time_gran_to_synthetic_exfil_paths_series[interval] = time_gran_to_feature_dataframe[interval][
                    'exfil_path']
                ##recover time_gran_to_list_of_concrete_exfil_paths, time_gran_to_list_of_exfil_amts
                time_gran_to_list_of_concrete_exfil_paths[interval] = time_gran_to_feature_dataframe[interval][
                    'concrete_exfil_path']
                list_of_exfil_amts = []
                for counter in range(0, len(time_gran_to_feature_dataframe[interval]['exfil_weight'])):
                    weight = time_gran_to_feature_dataframe[interval]['exfil_weight'][counter]
                    pkts = time_gran_to_feature_dataframe[interval]['exfil_pkts'][counter]
                    current_exfil_dict = {'weight': weight, 'frames': pkts}
                    list_of_exfil_amts.append(current_exfil_dict)
                time_gran_to_list_of_exfil_amts[interval] = list_of_exfil_amts
                if min_interval:
                    print time_gran_to_feature_dataframe[interval]['is_test'], type(
                        time_gran_to_feature_dataframe[interval]['is_test'])
                    self.end_of_training = time_gran_to_feature_dataframe[interval]['is_test'].tolist().index(
                        1) * min_interval

        print "about to calculate some alerts!"

        self.time_gran_to_feature_dataframe_copy = copy.deepcopy(time_gran_to_feature_dataframe)
        for time_gran, feature_dataframe in time_gran_to_feature_dataframe.iteritems():
            try:
                del feature_dataframe['exfil_path']
                del feature_dataframe['exfil_weight']
                del feature_dataframe['exfil_pkts']
                del feature_dataframe['concrete_exfil_path']
                del feature_dataframe['is_test']
            except:
                pass

            try:
                time_gran_to_feature_dataframe[time_gran] = time_gran_to_feature_dataframe[time_gran].drop(
                    columns=[u'new_neighbors_dns'])
            except:
                pass
            try:
                time_gran_to_feature_dataframe[time_gran] = time_gran_to_feature_dataframe[time_gran].drop(
                    columns=[u'new_neighbors_all '])
            except:
                pass
            try:
                time_gran_to_feature_dataframe[time_gran] = time_gran_to_feature_dataframe[time_gran].drop(
                    columns=[u'new_neighbors_outside'])
            except:
                pass
            print "feature_dataframe_columns", time_gran_to_feature_dataframe[time_gran].columns

        self.time_gran_to_feature_dataframe=time_gran_to_feature_dataframe
        self.time_gran_to_attack_labels=time_gran_to_attack_labels
        self.time_gran_to_synthetic_exfil_paths_series=time_gran_to_synthetic_exfil_paths_series
        self.time_gran_to_list_of_concrete_exfil_paths  = time_gran_to_list_of_concrete_exfil_paths
        self.time_gran_to_list_of_exfil_amts=time_gran_to_list_of_exfil_amts
        self.time_gran_to_new_neighbors_outside=time_gran_to_new_neighbors_outside
        self.time_gran_to_new_neighbors_dns=time_gran_to_new_neighbors_dns
        self.time_gran_to_new_neighbors_all=time_gran_to_new_neighbors_all
        self.time_gran_to_list_of_amt_of_out_traffic_bytes = time_gran_to_list_of_amt_of_out_traffic_bytes
        self.time_gran_to_list_of_amt_of_out_traffic_pkts = time_gran_to_list_of_amt_of_out_traffic_pkts

        return self.calculate_z_scores_and_get_stat_vals()

    def calculate_z_scores_and_get_stat_vals(self):
        time_gran_to_mod_zscore_df, time_gran_to_zscore_dataframe, time_gran_to_RobustScaler_df = \
            calc_zscores(self.alert_file, self.training_window_size, self.minimum_training_window, self.sub_path,
                         self.time_gran_to_attack_labels,
                         self.time_gran_to_feature_dataframe, self.calc_zscore_p, self.time_gran_to_synthetic_exfil_paths_series,
                         self.time_gran_to_list_of_concrete_exfil_paths, self.time_gran_to_list_of_exfil_amts, self.end_of_training,
                         self.time_gran_to_new_neighbors_outside, self.time_gran_to_new_neighbors_dns,
                         self.time_gran_to_new_neighbors_all,
                         self.time_gran_to_list_of_amt_of_out_traffic_bytes,
                         self.time_gran_to_list_of_amt_of_out_traffic_pkts)

        print "analysis_pipeline about to return!"


        for time_gran, mod_z_score_df in time_gran_to_mod_zscore_df.iteritems():
            time_gran_to_mod_zscore_df[time_gran] = mod_z_score_df.drop(mod_z_score_df.index[:self.minimum_training_window])

        return time_gran_to_mod_zscore_df, time_gran_to_zscore_dataframe, self.time_gran_to_feature_dataframe_copy, \
               self.time_gran_to_synthetic_exfil_paths_series, self.end_of_training


def process_one_set_of_graphs(time_interval_length, window_size,
                                filenames, svcs, is_swarm, ms_s, mapping,  list_of_infra_services,
                                synthetic_exfil_paths, initiator_info_for_paths, attacks_to_times,
                               collected_metrics_location, current_set_of_graphs_loc, calc_vals, out_q,
                              avg_exfil_per_min, exfil_per_min_variance, avg_pkt_size, pkt_size_variance):

    if calc_vals:
        current_set_of_graphs = simplified_graph_metrics.set_of_injected_graphs(time_interval_length, window_size,
                                         filenames, svcs, is_swarm, ms_s, mapping, list_of_infra_services,
                                         synthetic_exfil_paths, initiator_info_for_paths, attacks_to_times,
                                          collected_metrics_location, current_set_of_graphs_loc,
                                          avg_exfil_per_min, exfil_per_min_variance, avg_pkt_size, pkt_size_variance)
        ### TODO: if don't wanna redo the injection step (and why would you), then you can just go ahead
        ### and comment out the line below and comment in the two lines below that
        current_set_of_graphs.generate_injected_edgefiles()
        #with open(current_set_of_graphs_loc, mode='rb') as f:
        #    current_set_of_graphs_loc_contents = f.read()
        #    current_set_of_graphs = pickle.loads(current_set_of_graphs_loc_contents)


        current_set_of_graphs.calcuated_single_step_metrics()
        current_set_of_graphs.calc_serialize_metrics()
        current_set_of_graphs.save()
    else:
        with open(current_set_of_graphs_loc, mode='rb') as f:
            current_set_of_graphs_loc_contents = f.read()
            current_set_of_graphs = pickle.loads(current_set_of_graphs_loc_contents)
            print "current_set_of_graphs.list_of_injected_graphs_loc", current_set_of_graphs.list_of_injected_graphs_loc
            print "time_granularity", current_set_of_graphs.time_granularity
            print "current_set_of_graphs.raw_edgefile_names",current_set_of_graphs.raw_edgefile_names
        current_set_of_graphs.load_serialized_metrics()
    current_set_of_graphs.put_values_into_outq(out_q)


def calculate_raw_graph_metrics(time_interval_lengths, interval_to_filenames, ms_s, basegraph_name, calc_vals, window_size,
                                mapping, is_swarm, make_net_graphs_p, list_of_infra_services,synthetic_exfil_paths,
                                initiator_info_for_paths, time_gran_to_attacks_to_times, size_of_neighbor_training_window,
                                avg_exfil_per_min,
                                exfil_per_min_variance, avg_pkt_size, pkt_size_variance):
    total_calculated_vals = {}
    time_gran_to_list_of_concrete_exfil_paths = {}
    time_gran_to_list_of_exfil_amts = {}
    time_gran_to_new_neighbors_outside = {}
    time_gran_to_new_neighbors_dns = {}
    time_gran_to_new_neighbors_all = {}
    time_gran_to_list_of_amt_of_out_traffic_bytes = {}
    time_gran_to_list_of_amt_of_out_traffic_pkts = {}

    for time_interval_length in time_interval_lengths:
        print "analyzing edgefiles...", "timer_interval...", time_interval_length

        if is_swarm:
            svcs = analysis_pipeline.prepare_graph.get_svc_equivalents(is_swarm, mapping)
        else:
            print "this is k8s, so using these sevices", ms_s
            svcs = ms_s
        out_q = multiprocessing.Queue()

        collected_metrics_location = basegraph_name + 'collected_metrics_time_gran_' + str(time_interval_length) + '.csv'
        current_set_of_graphs_loc = basegraph_name + 'set_of_graphs' + str(time_interval_length) + '.csv'
        args = [time_interval_length, window_size,
                interval_to_filenames[str(time_interval_length)], svcs, is_swarm, ms_s, mapping,
                list_of_infra_services, synthetic_exfil_paths,  initiator_info_for_paths,
                time_gran_to_attacks_to_times[time_interval_length], collected_metrics_location, current_set_of_graphs_loc,
                calc_vals, out_q, avg_exfil_per_min, exfil_per_min_variance, avg_pkt_size, pkt_size_variance]
        p = multiprocessing.Process(
            target=process_one_set_of_graphs,
            args=args)
        p.start()
        total_calculated_vals[(time_interval_length, '')] = out_q.get()
        list_of_concrete_container_exfil_paths = out_q.get()
        list_of_exfil_amts = out_q.get()
        new_neighbors_outside =  out_q.get()
        new_neighbors_dns =  out_q.get()
        new_neighbors_all = out_q.get()
        list_of_amt_of_out_traffic_bytes = out_q.get()
        list_of_amt_of_out_traffic_pkts = out_q.get()

        p.join()

        print "process returned!"
        time_gran_to_list_of_concrete_exfil_paths[time_interval_length] = list_of_concrete_container_exfil_paths
        time_gran_to_list_of_exfil_amts[time_interval_length] = list_of_exfil_amts
        time_gran_to_new_neighbors_outside[time_interval_length] = None # no longer used
        time_gran_to_new_neighbors_dns[time_interval_length] = None # no longer used
        time_gran_to_new_neighbors_all[time_interval_length] = None # no longer used
        time_gran_to_list_of_amt_of_out_traffic_bytes[time_interval_length] = list_of_amt_of_out_traffic_bytes
        time_gran_to_list_of_amt_of_out_traffic_pkts[time_interval_length] = list_of_amt_of_out_traffic_pkts

        #total_calculated_vals.update(newly_calculated_values)
        gc.collect()
    return total_calculated_vals, time_gran_to_list_of_concrete_exfil_paths, time_gran_to_list_of_exfil_amts,\
        time_gran_to_new_neighbors_outside, time_gran_to_new_neighbors_dns, time_gran_to_new_neighbors_all,\
        time_gran_to_list_of_amt_of_out_traffic_bytes, time_gran_to_list_of_amt_of_out_traffic_pkts


def calc_zscores(alert_file, training_window_size, minimum_training_window,
                 sub_path, time_gran_to_attack_labels, time_gran_to_feature_dataframe, calc_zscore_p, time_gran_to_synthetic_exfil_paths_series,
                 time_gran_to_list_of_concrete_exfil_paths, time_gran_to_list_of_exfil_amts, end_of_training,
                 time_gran_to_new_neighbors_outside, time_gran_to_new_neighbors_dns, time_gran_to_new_neighbors_all,
                 time_gran_to_list_of_amt_of_out_traffic_bytes, time_gran_to_list_of_amt_of_out_traffic_pkts):

    #time_gran_to_mod_zscore_df = process_graph_metrics.calculate_mod_zscores_dfs(total_calculated_vals, minimum_training_window,
    #                                                                             training_window_size, time_interval_lengths)

    mod_z_score_df_basefile_name = alert_file + 'mod_z_score_' + sub_path
    #z_score_df_basefile_name = alert_file + 'norm_z_score_' + sub_path
    robustScaler_df_basefile_name = alert_file + 'robustScaler_score_' + sub_path

    if calc_zscore_p:
        time_gran_to_mod_zscore_df = process_graph_metrics.calc_time_gran_to_mod_zscore_dfs(time_gran_to_feature_dataframe,
                                                                                            training_window_size,
                                                                                            minimum_training_window)

        #print "end_of_training", end_of_training
        #exit(344)
        process_graph_metrics.save_feature_datafames(time_gran_to_mod_zscore_df, mod_z_score_df_basefile_name,
                                                     time_gran_to_attack_labels, time_gran_to_synthetic_exfil_paths_series,
                                                     time_gran_to_list_of_concrete_exfil_paths,
                                                     time_gran_to_list_of_exfil_amts, end_of_training,
                                                     time_gran_to_new_neighbors_outside, time_gran_to_new_neighbors_dns,
                                                     time_gran_to_new_neighbors_all,
                                                     time_gran_to_list_of_amt_of_out_traffic_bytes,
                                                     time_gran_to_list_of_amt_of_out_traffic_pkts)

        '''
        time_gran_to_zscore_dataframe = process_graph_metrics.calc_time_gran_to_zscore_dfs(time_gran_to_feature_dataframe,
                                                                                           training_window_size,
                                                                                           minimum_training_window)

        process_graph_metrics.save_feature_datafames(time_gran_to_zscore_dataframe, z_score_df_basefile_name,
                                                     time_gran_to_attack_labels, time_gran_to_synthetic_exfil_paths_series,
                                                     time_gran_to_list_of_concrete_exfil_paths,
                                                     time_gran_to_list_of_exfil_amts, end_of_training,
                                                     time_gran_to_new_neighbors_outside, time_gran_to_new_neighbors_dns,
                                                     time_gran_to_new_neighbors_all)
        '''
        '''
        time_gran_to_RobustScaler_df = process_graph_metrics.calc_time_gran_to_robustScaker_dfs(time_gran_to_feature_dataframe, training_window_size)

        process_graph_metrics.save_feature_datafames(time_gran_to_RobustScaler_df, robustScaler_df_basefile_name,
                                                     time_gran_to_attack_labels, time_gran_to_synthetic_exfil_paths_series,
                                                     time_gran_to_list_of_concrete_exfil_paths,
                                                     time_gran_to_list_of_exfil_amts, end_of_training,
                                                     time_gran_to_new_neighbors_outside, time_gran_to_new_neighbors_dns,
                                                     time_gran_to_new_neighbors_all)
        '''
    else:
        #time_gran_to_zscore_dataframe = {}
        time_gran_to_mod_zscore_df = {}
        #time_gran_to_RobustScaler_df = {}
        for interval in time_gran_to_feature_dataframe.keys():
            #time_gran_to_zscore_dataframe[interval] = pd.read_csv(z_score_df_basefile_name + str(interval) + '.csv', na_values='?')
            time_gran_to_mod_zscore_df[interval] = pd.read_csv(mod_z_score_df_basefile_name + str(interval) + '.csv', na_values='?')
            #time_gran_to_RobustScaler_df[interval] = pd.read_csv(robustScaler_df_basefile_name + str(interval) + '.csv', na_values='?')

            try:
                pass
                '''
                del time_gran_to_zscore_dataframe[interval]['exfil_path']
                del time_gran_to_mod_zscore_df[interval]['exfil_path']

                del time_gran_to_zscore_dataframe[interval]['concrete_exfil_path']
                del time_gran_to_mod_zscore_df[interval]['concrete_exfil_path']

                del time_gran_to_zscore_dataframe[interval]['exfil_weight']
                del time_gran_to_mod_zscore_df[interval]['exfil_weight']


                del time_gran_to_zscore_dataframe[interval]['exfil_pkts']
                del time_gran_to_mod_zscore_df[interval]['exfil_pkts']
                '''
                #del time_gran_to_zscore_dataframe[interval]['is_test']
                #del time_gran_to_mod_zscore_df[interval]['is_test']

                #def time_gran_to_RobustScaler_df[interval]['exfil_path']
                #del time_gran_to_RobustScaler_df[interval]['concrete_exfil_path']
                #del time_gran_to_RobustScaler_df[interval]['exfil_weight']
                #del time_gran_to_RobustScaler_df[interval]['exfil_pkts']
                #del time_gran_to_RobustScaler_df[interval]['is_test']

                ''' # we'll drop these in the other part of the program...
                del time_gran_to_mod_zscore_df[interval]['new_neighbors_dns']
                del time_gran_to_mod_zscore_df[interval]['new_neighbors_all']
                del time_gran_to_mod_zscore_df[interval]['new_neighbors_outside']

                del time_gran_to_zscore_dataframe[interval]['new_neighbors_dns']
                del time_gran_to_zscore_dataframe[interval]['new_neighbors_all']
                del time_gran_to_zscore_dataframe[interval]['new_neighbors_outside']
                '''
            except:
                pass

    return time_gran_to_mod_zscore_df, None, None# time_gran_to_RobustScaler_df # todo<-- put back
    #return time_gran_to_mod_zscore_df, time_gran_to_zscore_dataframe, None# time_gran_to_RobustScaler_df # todo<-- put back
    #return time_gran_to_RobustScaler_df, time_gran_to_zscore_dataframe, time_gran_to_RobustScaler_df

##### the goal needs to be some mapping of times to attacks to time (ranges) + updated attack labels
##### so, in effect, there are TWO outputs... and it makes a lot more sense to pick the range then modify
##### the labels
## NOTE: portion_for_training is the percentage to devote to using for the training period (b/c attacks will be injected
## into both the training period and the testing period)
def determine_attacks_to_times(time_gran_to_attack_labels, synthetic_exfil_paths, time_of_synethic_exfil, min_starting,
                               end_of_train, synthetic_exfil_paths_train, synthetic_exfil_paths_test):
    time_grans = time_gran_to_attack_labels.keys()
    largest_time_gran = sorted(time_grans)[-1]
    print "LARGEST_TIME_GRAN", largest_time_gran
    print "time_of_synethic_exfil",time_of_synethic_exfil
    time_periods_attack = float(time_of_synethic_exfil) / float(largest_time_gran)
    time_periods_startup = math.ceil(float(min_starting) / float(largest_time_gran))
    time_gran_to_attack_ranges = {} # a list that'll correspond w/ the synthetic exfil paths
    for time_gran in time_gran_to_attack_labels.keys():
        time_gran_to_attack_ranges[time_gran] = []

    ## assign injected attacks to times here...
    ### (a) add to time_gran_to_attack_ranges... just put the existing ranges w/ 'injection' as the marker'
    time_gran_to_physical_attack_ranges = {}
    for time_gran in time_gran_to_attack_labels.keys():
        time_gran_to_physical_attack_ranges[time_gran] = determine_physical_attack_ranges(time_gran_to_attack_labels[time_gran])
        print "physical_attack_ranges", time_gran_to_physical_attack_ranges[time_gran]

    # first, let's assign for the training period...
    counter = 0
    time_gran_to_attack_labels, time_gran_to_attack_ranges = assign_attacks_to_first_available_spots(time_gran_to_attack_labels, largest_time_gran, time_periods_startup,
                                            time_periods_attack, counter, time_gran_to_attack_ranges, synthetic_exfil_paths, synthetic_exfil_paths_train)
    # second, let's assign for the testing period...
    print end_of_train, largest_time_gran
    counter = int(math.ceil(end_of_train/largest_time_gran)) #int(math.ceil(len(time_gran_to_attack_labels[largest_time_gran]) * end_of_train - time_periods_startup))
    print "second_counter!!", counter, "attacks_to_assign",len(synthetic_exfil_paths_test), time_gran_to_attack_labels[time_gran][counter:],time_gran_to_attack_labels[time_gran][counter:].count(0)
    time_gran_to_attack_labels, time_gran_to_attack_ranges = assign_attacks_to_first_available_spots(time_gran_to_attack_labels, largest_time_gran, time_periods_startup,
                                            time_periods_attack, counter, time_gran_to_attack_ranges, synthetic_exfil_paths, synthetic_exfil_paths_test)

    # okay, so now we have the times selected for the largest time granularity... we have to make sure
    # that the other granularities agree...

    print "HIGHEST GRAN SYNTHETIC ATTACKS CHOSEN -- START MAPPING TO LOWER GRAN NOW!"
    for j in range(0, len(time_gran_to_attack_ranges[largest_time_gran])):
        for time_gran, attack_labels in time_gran_to_attack_labels.iteritems():
            if time_gran == largest_time_gran:
                continue
            attack_ranges_at_highest_gran = time_gran_to_attack_ranges[largest_time_gran]
            current_attack_range_at_highest_gran = attack_ranges_at_highest_gran[j]
            time_period_conversion_ratio = float(largest_time_gran) / float(time_gran)
            #print "TIME_PERIOD_CONVERSION_RATIO", time_period_conversion_ratio,  float(largest_time_gran), float(time_gran)
            current_start_of_attack = int(current_attack_range_at_highest_gran[0] * time_period_conversion_ratio)
            current_end_of_attack = int(current_attack_range_at_highest_gran[1] * time_period_conversion_ratio)
            time_gran_to_attack_ranges[time_gran].append( (current_start_of_attack, current_end_of_attack) )
            # also, modify the attack_labels
            for z in range(current_start_of_attack, current_end_of_attack):
                # print "z",z
                attack_labels[z] = 1
    return time_gran_to_attack_labels, time_gran_to_attack_ranges, time_gran_to_physical_attack_ranges


def assign_attacks_to_first_available_spots(time_gran_to_attack_labels, largest_time_gran, time_periods_startup, time_periods_attack,
                                            counter, time_gran_to_attack_ranges, synthetic_exfil_paths, current_exfil_paths):
    ## TODO: problem: this can only inject the attacks in once...
    for synthetic_exfil_path in current_exfil_paths: # synthetic_exfil_paths:

        print synthetic_exfil_path, synthetic_exfil_path in current_exfil_paths
        if synthetic_exfil_path in synthetic_exfil_paths: #current_exfil_paths:
            # randomly choose ranges using highest granularity (then after this we'll choose for the smaller granularities...)
            attack_spot_found = False
            number_free_spots = time_gran_to_attack_labels[largest_time_gran][int(time_periods_startup):].count(0)
            if number_free_spots < time_periods_attack:
                exit(1244) # should break now b/c infinite loop (note: we're not handling the case where it is fragmented...)
            while not attack_spot_found:
                ## NOTE: not sure if the -1 is necessary...
                # NOTE: this random thing causes all types of problems. Let's just ignore it and do it right after startup??, maybe?
                #potential_starting_point = random.randint(time_periods_startup,
                #                                len(time_gran_to_attack_labels[largest_time_gran]) - time_periods_attack - 1)
                potential_starting_point = int(time_periods_startup + counter)

                print "potential_starting_point", potential_starting_point
                attack_spot_found = exfil_time_valid(potential_starting_point, time_periods_attack,
                                                     time_gran_to_attack_labels[largest_time_gran])
                if attack_spot_found:
                    # if the time range is valid, we gotta store it...
                    time_gran_to_attack_ranges[largest_time_gran].append((int(potential_starting_point),
                                                                          int(potential_starting_point + time_periods_attack)))
                    # and also modify the attack labels
                    print "RANGE", potential_starting_point, int(potential_starting_point + time_periods_attack)
                    for i in range(potential_starting_point, int(potential_starting_point + time_periods_attack)):
                        #print i, time_gran_to_attack_labels[largest_time_gran]
                        print time_gran_to_attack_labels[largest_time_gran],i,len(time_gran_to_attack_labels[largest_time_gran])
                        time_gran_to_attack_labels[largest_time_gran][i] = 1
                #print "this starting point failed", potential_starting_point
                counter += 1
        else:
            ### by making these two points the same, this value will be 'passed over' by the other functions...
            potential_starting_point = int(time_periods_startup + counter)
            time_gran_to_attack_ranges[largest_time_gran].append((potential_starting_point,potential_starting_point))
    return time_gran_to_attack_labels, time_gran_to_attack_ranges


def determine_physical_attack_ranges(physical_attack_labels):
    ## determine the indexes of contiguous sets of 1's...
    # step 1: find indexes of all the ones (using list comprehension)
    indexes_of_attack_labels = [i for i,j in enumerate(physical_attack_labels) if j == 1]
    print "indexes_of_attack_labels", indexes_of_attack_labels
    # step 2: find contiguous size of contigous numbers
    ### a solution to this is in the docs, so let's just
    #### do it that way: https://docs.python.org/2.6/library/itertools.html#examples
    physical_attack_ranges = []
    for k, g in groupby(enumerate(indexes_of_attack_labels), lambda (i, x): i - x):
        attack_grp =  map(itemgetter(1), g) #groupby, itemgetter
        physical_attack_ranges.append((attack_grp[0], attack_grp[-1]))
    #print "physical_attack_ranges", physical_attack_ranges
    return physical_attack_ranges


def determine_time_gran_to_synthetic_exfil_paths_series(time_gran_to_attack_ranges, synthetic_exfil_paths,
                                                        interval_to_filenames, time_gran_to_physical_attack_ranges,
                                                        injected_exfil_path):
    time_gran_to_synthetic_exfil_paths_series = {}
    for time_gran, attack_ranges in time_gran_to_attack_ranges.iteritems():
        print interval_to_filenames.keys()
        time_steps = len(interval_to_filenames[str(time_gran)])
        current_exfil_path_series = pd.Series([0 for i in range(0,time_steps)])
        print "time_gran_attack_ranges", time_gran, attack_ranges

        # first add the physical attacks
        physical_attack_ranges = time_gran_to_physical_attack_ranges[time_gran]
        for attack_counter, attack_range in enumerate(physical_attack_ranges):
            for i in range(attack_range[0], attack_range[1]):
                current_exfil_path_series[i] = ['physical:'] + injected_exfil_path

        # then add the injected attacks
        for attack_counter, attack_range in enumerate(attack_ranges):
            for i in range(attack_range[0], attack_range[1]):
                current_exfil_path_series[i] = synthetic_exfil_paths[attack_counter % len(synthetic_exfil_paths)]
        #current_exfil_path_series.index *= 10
        time_gran_to_synthetic_exfil_paths_series[time_gran] = current_exfil_path_series
    #print "time_gran_to_synthetic_exfil_paths_series", time_gran_to_synthetic_exfil_paths_series

    #time.sleep(60)
    return time_gran_to_synthetic_exfil_paths_series

# returns whether the range does not already have an attack at that location... so if an attack is found
# then the range is not valid (So you'd wanna return false)
def exfil_time_valid(potential_starting_point, time_slots_attack, attack_labels):
    attack_found = False
    # now check if there's not already an attack selected for that time...
    #print potential_starting_point, potential_starting_point + time_slots_attack
    for i in attack_labels[potential_starting_point:int(potential_starting_point + time_slots_attack)]:
        if i:  # ==1
            attack_found = True
            break
    return not attack_found