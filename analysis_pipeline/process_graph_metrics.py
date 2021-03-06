import numpy as np
import csv
import math
import ast
import matplotlib.pyplot as plt
import pandas
import time
import scipy.stats
import logging
from sklearn.preprocessing import RobustScaler

# exfil_rate used to determine if there should be a gap between exfil labels
def generate_attack_labels(time_gran, exfil_startEnd_times, exp_length):
    # let's find the specific time intervals during the exfil period (note: potentially not all of the time intervals
    # actually have exfil occur during them)

    current_time_counter = 0
    cur_attack_labels = [] # does a zero go in here??
    if exfil_startEnd_times != [[]]:
        for exfil_start_end in exfil_startEnd_times:
            exfil_start = exfil_start_end[0]
            exfil_end = exfil_start_end[1]
            cur_attack_labels.extend( [0 for i in range(current_time_counter, exfil_start/time_gran)] )
            cur_attack_labels.extend( [1 for i in range( exfil_start/time_gran,  exfil_end/time_gran)] )
            current_time_counter = exfil_end/time_gran

    cur_attack_labels.extend([0 for i in range(current_time_counter, int(math.ceil(float(exp_length)/time_gran)))])

    return cur_attack_labels

def generate_time_gran_to_attack_labels(time_interval_lengths, exfil_startEnd_times, exp_length):
    time_gran_to_attack_lables = {}
    for time_gran in time_interval_lengths:
        #exp_length = exfil_end - exfil_start
        attack_labels = generate_attack_labels(time_gran, exfil_startEnd_times, exp_length)
        time_gran_to_attack_lables[time_gran] = attack_labels
    return time_gran_to_attack_lables


def generate_mod_z_score_dataframes(time_gran_to_list_of_anom_values, time_gran_to_list_of_anom_metrics_applied, time_grans):
    time_gran_to_mod_z_score_dataframe = {}
    for time_gran in time_grans:

        list_of_anom_values = time_gran_to_list_of_anom_values[time_gran]
        list_of_anom_metrics_applied = time_gran_to_list_of_anom_metrics_applied[time_gran]
        print "list_of_anom_values", list_of_anom_values
        print "list_of_anom_metrics_applied", list_of_anom_metrics_applied
        mod_z_score_array = np.array(list_of_anom_values)
        mod_z_score_array = mod_z_score_array.T
        p = 0
        for series in mod_z_score_array:
            print len(series),
            try:
                print list_of_anom_metrics_applied[p]
            except:
                print ''
            if len(series) < 90:
                print series
            p += 1
        print mod_z_score_array.shape
        times = [i * time_gran for i in range(0, len(mod_z_score_array[:, 0]))]
        mod_z_score_dataframe = pandas.DataFrame(data=mod_z_score_array, columns=list_of_anom_metrics_applied,
                                                 index=times)
        time_gran_to_mod_z_score_dataframe[time_gran] = mod_z_score_dataframe
    return time_gran_to_mod_z_score_dataframe

def generate_feature_dfs(calculated_vals, time_interval_lengths):
    time_gran_to_feature_dataframe = {}
    #for time_gran in time_grans:
    list_of_metric_val_lists = {}
    list_of_metric_names = {}
    time_grans = []
    for label, metric_time_series in calculated_vals.iteritems():
        container_or_class = label[1]
        time_interval = int(label[0])
        #if time_interval != time_gran:
        #    continue
        if time_interval not in time_interval_lengths:
            continue
        else:
            time_grans.append(time_interval)
            if time_interval not in list_of_metric_val_lists:
                list_of_metric_val_lists[time_interval] = []
                list_of_metric_names[time_interval] = []

        for current_metric_name, current_metric_time_series in calculated_vals[label].iteritems():
            list_of_metric_names[time_interval].append(current_metric_name + '_' + container_or_class)
            list_of_metric_val_lists[time_interval].append(current_metric_time_series)

    for time_gran, metric_val_lists in list_of_metric_val_lists.iteritems():
        metric_names = list_of_metric_names[time_gran]
        # okay, so now that we have the lists with the values, we can make some matrixes (And then tranpose them :))
        feature_array = np.array(metric_val_lists)
        feature_array = feature_array.T

        # okay, so now we have the matrix along with the list we can do what we actually wanted to do:
        # (1) run some anom detection algos
        # (2) save in handy-csv format for processing by other software, potentially
        # let's start start with (2). Columns should be times

        #print feature_array
        #print list_of_metric_names
        for counter, feature_vector in enumerate(metric_val_lists):
            #print metric_names[counter], feature_vector, len(feature_vector)
            print metric_names[counter], len(feature_vector)

        ####print "feature_array", feature_array.shape, feature_array['attack_labels']
        times = [i * time_gran for i in range(0,len(feature_array[:,0]))]
        print feature_array
        feature_dataframe = pandas.DataFrame(data=feature_array, columns=metric_names, index=times)
        ##feature_dataframe.index.name = 'time' ## i think this should solve the problem of the time column not being labeled
        time_gran_to_feature_dataframe[time_gran] = feature_dataframe
    return time_gran_to_feature_dataframe

def save_feature_datafames(time_gran_to_feature_dataframe, csv_path, time_gran_to_attack_labels, time_gran_to_synthetic_exfil_paths_series,
                           time_gran_to_list_of_concrete_exfil_paths, time_gran_to_list_of_exfil_amts, end_of_training,
                           time_gran_to_new_neighbors_outside,
                           time_gran_to_new_neighbors_dns, time_gran_to_new_neighbors_all,
                           time_gran_to_list_of_amt_of_out_traffic_bytes, time_gran_to_list_of_amt_of_out_traffic_pkts):

    print "time_gran_to_feature_dataframe","----",time_gran_to_feature_dataframe, "-----"
    print "time_gran_to_feature_dataframe",time_gran_to_feature_dataframe.keys()
    for time_gran, attack_labels in time_gran_to_attack_labels.iteritems():
        print "time_gran", time_gran, "len of attack labels", len(attack_labels)
    max_time_gran = max(time_gran_to_feature_dataframe.keys())
    for time_gran, feature_dataframe in time_gran_to_feature_dataframe.iteritems():
        attack_labels = time_gran_to_attack_labels[time_gran]
        #print "feature_dataframe",feature_dataframe,feature_dataframe.index

        print time_gran_to_new_neighbors_outside[time_gran]
        print time_gran_to_new_neighbors_dns[time_gran]
        print time_gran_to_new_neighbors_dns[time_gran]
        feature_dataframe['new_neighbors_outside'] = pandas.Series(time_gran_to_new_neighbors_outside[time_gran], index=feature_dataframe.index)
        feature_dataframe['new_neighbors_dns'] = pandas.Series(time_gran_to_new_neighbors_dns[time_gran], index=feature_dataframe.index)
        feature_dataframe['new_neighbors_all ']= pandas.Series(time_gran_to_new_neighbors_all[time_gran], index=feature_dataframe.index)

        # make sure there's no stupid complex numbers here...
        for column in feature_dataframe:
            feature_dataframe[column] = feature_dataframe[column].apply(lambda x: np.real(x))

        #print "attack_labels",attack_labels, len(attack_labels), "time_gran", time_gran
        feature_dataframe['labels'] = pandas.Series(attack_labels, index=feature_dataframe.index)
        print "time_gran_to_synthetic_exfil_paths_series[time_gran]", time_gran_to_synthetic_exfil_paths_series[time_gran]
        if len(time_gran_to_synthetic_exfil_paths_series[time_gran].index.values) > len(feature_dataframe.index.values):
            time_gran_to_synthetic_exfil_paths_series[time_gran] = time_gran_to_synthetic_exfil_paths_series[time_gran][:len(feature_dataframe.index.values)]
        time_gran_to_synthetic_exfil_paths_series[time_gran].index = feature_dataframe.index[:len(time_gran_to_synthetic_exfil_paths_series[time_gran])]
        feature_dataframe['exfil_path'] = pandas.Series(time_gran_to_synthetic_exfil_paths_series[time_gran], index=feature_dataframe.index)
        feature_dataframe['concrete_exfil_path'] = pandas.Series(time_gran_to_list_of_concrete_exfil_paths[time_gran], index=feature_dataframe.index)
        feature_dataframe['exfil_weight'] = pandas.Series([i['weight'] for i in time_gran_to_list_of_exfil_amts[time_gran]], index=feature_dataframe.index)
        feature_dataframe['exfil_pkts'] = pandas.Series([i['frames'] for i in time_gran_to_list_of_exfil_amts[time_gran]], index=feature_dataframe.index)

        feature_dataframe['amt_of_out_traffic_bytes'] = pandas.Series(time_gran_to_list_of_amt_of_out_traffic_bytes[time_gran], index=feature_dataframe.index)
        feature_dataframe['amt_of_out_traffic_pkts'] = pandas.Series(time_gran_to_list_of_amt_of_out_traffic_pkts[time_gran], index=feature_dataframe.index)

        print "feature_dataframe", feature_dataframe

        ### now let's store an indicator of when the training set ends... end_of_training indicates the first member
        ### of the training dataset...
        print end_of_training, time_gran

        ## TODO: this function needs to be fixed so that everything can work.... okay. It's pretty clear to me that
        ## we need to determine the split based off of the max time granularity and then set the other thing srelative to that

        current_end_of_train = int(end_of_training / max_time_gran) * int(max_time_gran/time_gran)

        test_period_list = [0 for i in range(0,int(current_end_of_train))] + \
                           [1 for i in range(int(current_end_of_train), len(feature_dataframe.index))]

        test_period_series = pandas.Series(test_period_list, index=feature_dataframe.index)
        feature_dataframe['is_test'] = test_period_series


        feature_dataframe.to_csv(csv_path + str(time_gran) + '.csv', na_rep='?')


def add_additional_features(feature_df):
    for column in feature_df:
        if 'class_current_flow_bc_sub_' in column or 'class_harmonic_centrality_' in column:
            feature_df['abs_' + column ] = abs(feature_df[column])
            feature_df.drop(columns=column, inplace=True)
    return feature_df

def normalize_data_v2(time_gran_to_feature_dataframe, time_gran_to_attack_labels, end_of_training, pretrained_min_pipeline=None):
    time_gran_to_normalized_df = {}
    time_gran_to_transformer = {}
    for time_gran, feature_dataframe in time_gran_to_feature_dataframe.iteritems():
        current_attack_labels = time_gran_to_attack_labels[time_gran]
        feature_dataframe['attack_labels'] = current_attack_labels
        last_label_in_training = int(math.floor(float(end_of_training) / time_gran))

        ####################
        feature_dataframe = np.minimum(feature_dataframe,  1000000000) # handles inf's
        feature_dataframe = np.maximum(feature_dataframe, -1000000000) # handles inf's
        ####################

        training_values = feature_dataframe.iloc[:last_label_in_training]
        training_noAttack_values = training_values.loc[training_values['attack_labels'] == 0]

        if 'attack_labels' not in training_values:
            print "attack_labels non in training_values"
            exit(3)

        #transformer = RobustScaler().fit(training_noAttack_values)

        # min_stats_pipeline will be None when this isn't an eval portion...
        if not pretrained_min_pipeline:
            print "pretrained_min_pipeline",pretrained_min_pipeline
            transformer = RobustScaler().fit(training_noAttack_values)
        else:
            ## if min_stats_pipeline exists here, then it is an eval portion, and we need to handle it
            ## accordingly... two steps:
            ## (1) sync up the dataframes --> same # of columns and NaN's where appropriate
            ## (2) get the robustscaler
            # (1)
            corresponding_pretrained =  pretrained_min_pipeline.Xs[time_gran][0]
            corresponding_pretrained,feature_dataframe = corresponding_pretrained.align(feature_dataframe, join="left", axis=1)
            '''
            # (2)
            # need to generate the relevant robust scaler on the spot
            attack_labels = pretrained_min_pipeline.time_gran_to_aggregate_mod_score_dfs[time_gran]['attack_labels'][0:corresponding_pretrained.shape[0]]
            pretrained_noexfil_vals = corresponding_pretrained.loc[ attack_labels == 0]
            transformer = RobustScaler().fit(pretrained_noexfil_vals)
            '''

            #feature_dataframe = np.minimum(feature_dataframe, 1000000)  # 100
            #feature_dataframe = np.maximum(feature_dataframe, -10000000)  # 100
            #feature_dataframe = feature_dataframe.clip(upper=1000000, lower=-10000000, axis=1)

            #### TODO: probably want to normalize based off of the model's data... not the current data
            ## (note: all this code below exists b/c I'm normalizing using the current feature set instead of the model's)
            feature_dataframe = feature_dataframe.fillna(feature_dataframe.median()) # TODO: is this is the right way? I'm thinking stick a zero or something?? Or should I just not include for this
            # TODO: ^^ should just not run w/ the incomplete data... (so adjust in the ensemble model)...^^^
            feature_dataframe = feature_dataframe.fillna(0.0) # maybe? (once done w/ overhaul of graph gen, should never trigger anyway...)
            feature_dataframe = np.minimum(feature_dataframe, 1000000)  # 100
            feature_dataframe = np.maximum(feature_dataframe, -10000000)  # 100
            transformer = RobustScaler().fit(feature_dataframe) # NOTE: doing an experiment...
            ####
            # (3) setup appropriate values for other purposes...
            training_values = feature_dataframe
            training_noAttack_values = training_values

            print "timegran", time_gran
            print "old_data_Shape", pretrained_min_pipeline.Xs[time_gran][0].shape
            print "new_data_shape", transformer.transform(feature_dataframe).shape

        # normalizes each column of the input matrix
        transformed_data = transformer.transform(feature_dataframe)
        transformed_training_noAttack_values = transformer.transform(training_noAttack_values)

        # might modify this at some point-- prob not the way to do it at the end...
        ## actually, several statistics professors tell me that this is indeed a property of the LASSO- you need to
        # bound it for extreme values.
        transformed_data = np.minimum(transformed_data, 100) #100
        transformed_data = np.maximum(transformed_data, -100) #100

        time_gran_to_normalized_df[time_gran] = pandas.DataFrame(transformed_data, index=feature_dataframe.index,\
                                                                 columns=feature_dataframe.columns.values) #df_normalized



        # note whether or not I actually want to do this is TBD...
        ## TODO: might want to change this for the eval case...
        time_gran_to_normalized_df[time_gran] = time_gran_to_normalized_df[time_gran].fillna( \
            pandas.DataFrame(transformed_training_noAttack_values, columns=feature_dataframe.columns.values).median())

        ## create some other features here... in particular the abs value (at the moment...)
        ## this seems to make things WAAAAY worse??
        #time_gran_to_normalized_df[time_gran] = add_additional_features(time_gran_to_normalized_df[time_gran])

        if not pretrained_min_pipeline:
            time_gran_to_normalized_df[time_gran] = time_gran_to_normalized_df[time_gran].dropna(axis=1)
        else:
            # in this case dimensionality is important...
            time_gran_to_normalized_df[time_gran] = time_gran_to_normalized_df[time_gran].fillna(0.0)


        print "final_shape", time_gran_to_normalized_df[time_gran].shape
        time_gran_to_transformer[time_gran] = transformer

    #time.sleep(60)
    return time_gran_to_normalized_df, time_gran_to_transformer