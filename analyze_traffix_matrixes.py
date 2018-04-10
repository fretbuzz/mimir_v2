import pickle
import pandas as pd
import numpy as np
import sys
#from Tkinter import *
import matplotlib
#matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
#from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
#from matplotlib.backend_bases import key_press_handler
#from matplotlib.figure import Figure
import parameters
from sklearn.decomposition import PCA

'''
USAGE: python analyze_traffic_matrixes.py [recieved_matrix_location] [sent_matrix_location]

## Note: if the rec/sent matrix locations aren't given, will use defaults
## Other note: the import order above is important if I end up deciding to use Tkinter
'''

services = [
        'carts',
        'carts-db',
        'catalogue',
        'catalogue-db',
        'front-end',
        'orders',
        'orders-db',
        'payment',
        'queue-master',
        'rabbitmq',
        'session-db',
        'shipping',
        'user',
        'user-db',
        'load-test',
        '127.0.0.1', #it's always there, so I guess we should treat it like a normal thing
        '172.17.0.1' # also this one too
]

def main(rec_matrix_location, send_matrix_location):
    simulate_incoming_data(rec_matrix_location, send_matrix_location)

# This function reads pickle files corresponding to the send/received traffic matrices
# and then iterates through them by the time stamps, letting us pretend that the data
# is coming from an actively running system
def simulate_incoming_data(rec_matrix_location, send_matrix_location):
    print "hello world"
    df_sent = pd.read_pickle(send_matrix_location)
    df_rec = pd.read_pickle(rec_matrix_location)
    print "df_sent:", df_sent
    print "df_rec:", df_rec
    df_sent_time_slices = generate_time_slice_dfs(df_sent)
    df_rec_time_slices = generate_time_slice_dfs(df_rec)
    df_sent_control_stats = []
    df_rec_control_stats = []
    for df in df_sent_time_slices:
        df_sent_control_stats.append(control_charts(df, True))
        #print df
    for df in df_rec_time_slices:
        df_rec_control_stats.append(control_charts(df, False))
    #print df_sent_control_stats
    
    # check when control charts would give a warning
    # just going to use sent for now, could use reciever later
    times = get_times(df_sent)
    # starts at 1, b/c everyting has time stddev 0 at time 0, so everything would trigger a warning
    control_charts_warning_sent = []
    control_charts_warning_rec = []
    for time in range(1,len(times)-1):
        next_df_sent = df_sent[ df_sent['time'].isin([times[time]])]
        next_df_rec = df_rec[ df_rec['time'].isin([times[time]])]
        warnings_sent = next_value_trigger_control_charts(next_df_sent, df_sent_control_stats[time], times[time])
        warnings_rec = next_value_trigger_control_charts(next_df_rec, df_rec_control_stats[time], times[time])
        control_charts_warning_sent.append(warnings_sent)
        control_charts_warning_rec.append(warnings_rec)
    print "these are the warnings from the control charts: (for data that is sent): "
    print control_charts_warning_sent

    # okay, we are going to try PCA-based analysis here
    print "about to try PCA anom detection!"
    pca_anom_detect(df_sent)

    svc_pair_to_sent_control_charts = generate_service_pair_arrays(df_sent_control_stats, times)
    svc_pair_to_sent_bytes = traffic_matrix_to_svc_pair_list(df_sent)
    print svc_pair_to_sent_control_charts['front-end', 'user']
    sent_data_for_display = {'raw': svc_pair_to_sent_bytes, 'control-charts':svc_pair_to_sent_control_charts}
    generate_graphs(sent_data_for_display, times, parameters.display_sent_svc_pair, True)

    svc_pair_to_rec_control_charts = generate_service_pair_arrays(df_rec_control_stats, times)
    svc_pair_to_rec_bytes = traffic_matrix_to_svc_pair_list(df_rec)
    #print svc_pair_to_rec_control_charts['front-end', 'user']
    rec_data_for_display = {'raw': svc_pair_to_rec_bytes, 'control-charts':svc_pair_to_rec_control_charts}
    generate_graphs(rec_data_for_display, times, parameters.display_rec_svc_pair, False)



# this function just generates graphs
# sent_data_for_display is a dictionary of data about the sent traffic matrixc
# currently the indexes are: 'control-charts' and 'raw'. Each of these is a dicitonary
# of the below form
# assumes the form {['src', 'dst']: [list of time-ordered values]
def generate_graphs(data_for_display, times, src_pairs_to_display, is_sent):

    svc_pair_to_control_charts = data_for_display['control-charts'] 
    svc_pair_to_raw = data_for_display['raw']

    if len(src_pairs_to_display) == 1:
        columns,rows = 1,1
        plt.figure(figsize=(5, 4))
    elif len(src_pairs_to_display) == 2:
        rows = 2
        columns = 1
        plt.figure(figsize=(8, 7.5))
    elif len(src_pairs_to_display) == 4:
        columns = 2
        rows = 2
        plt.figure(figsize=(12, 7.5))
    else:
        print "about to crash because invalid size of list of objects to graph"    

    for i in range(0, len(parameters.display_sent_svc_pair)):
        plt.subplot(rows,columns,i+1)

        cur_src_svc = src_pairs_to_display[i][0]
        cur_dst_svc = src_pairs_to_display[i][1]
        avg_line, = plt.plot(times, [item[0] for item in svc_pair_to_control_charts[cur_src_svc, cur_dst_svc]], label='mean')
        avg_plus_one_stddev = [item[0] + item[1] for item in svc_pair_to_control_charts[cur_src_svc, cur_dst_svc]]
        control_chart_above, = plt.plot(times, avg_plus_one_stddev, label='mean + 1 * stddev')
        avg_minus_one_stddev = [item[0] - item[1] for item in svc_pair_to_control_charts[cur_src_svc, cur_dst_svc]]
        control_chart_below, = plt.plot(times, avg_minus_one_stddev, label='mean - 1 * stddev')
        avg_plus_two_stddev = [item[0] + 2 * item[1] for item in svc_pair_to_control_charts[cur_src_svc, cur_dst_svc]]
        control_chart_two_above, = plt.plot(times, avg_plus_two_stddev, label='mean + 2 * stddev')
        avg_minus_two_stddev = [item[0] - 2 * item[1] for item in svc_pair_to_control_charts[cur_src_svc, cur_dst_svc]]
        control_chart_two_below, = plt.plot(times, avg_minus_two_stddev, label='mean - 2 * stddev')    
        raw_line, = plt.plot(times, svc_pair_to_raw['front-end', 'user'], label='sent bytes')
        graph_ready_times = [int(i) for i in times] # floats are hard to read
        plt.xticks(times, graph_ready_times)
        if is_sent:
            plt.title(cur_src_svc + ' SENT TO ' + cur_dst_svc)
        else:
            plt.title(cur_src_svc + ' RECIEVED FROM ' + cur_dst_svc)
        plt.xlabel('seconds from start of experiment')
        plt.ylabel('bytes')
        # some of the lines are obvious just by looking at it, so let's not show those
        #plt.legend(handles=[avg_line, control_chart_two_above, control_chart_two_below, control_chart_above, control_chart_below,  raw_line])
        plt.legend(handles=[avg_line, raw_line])
    plt.subplots_adjust(hspace=.3) # too close by default
    plt.show()

# df -> {[src_svc, dst_svc] : [list of values in order of time]} 
def traffic_matrix_to_svc_pair_list(df):
    svcs_to_val_list = {}
    for src_svc in services:
        for dst_svc in services:
            svcs_to_val_list[src_svc, dst_svc] = df.loc[src_svc, dst_svc].tolist()
    return svcs_to_val_list

# result is {['src', 'dst'] : [list of values at the time intervals]}
# at the moment, it is going to deal soley with the control_chart_stats stuff
def generate_service_pair_arrays(stats, times):
    svc_to_vals = {}
    for sending_svc in services:
        for dst_svc in services:
            svc_to_vals[sending_svc, dst_svc] = []
    #print stats
    #print svc_to_vals
    for time_slice in stats:
        for svc_dst_pair, vals in time_slice.iteritems():
            #print svc_dst_pair, vals
            svc_to_vals[svc_dst_pair[0], svc_dst_pair[1]].append(vals)
    #print "I hope this worked!!!!"
    #print svc_to_vals
    return svc_to_vals

# DF(with lots of times) -> [DF(time A), DF(time A and B), DF(time A,B,C), etc.]
def generate_time_slice_dfs(df):
    times = get_times(df)
    elapsed_time = []
    #print times
    time_slices = []
    for time_index in range(0,len(times)):
        time = times[time_index]
        elapsed_time.append(time)
        df_so_far = df[ df['time'].isin(elapsed_time)]
        time_slices.append(df_so_far)
        #print elapsed_time, time_index, len(times)
        #print df_so_far
    return time_slices

# this is the function to implement control channels
# i.e. compute mean and standard deviation for each pod-pair
# Note: is_send is 1 if it is the "send matrix", else zero
def control_charts(df, is_send):
    ## going to return data in the form {[src_svc, dest_svc]: [mean, stddev]}
    data_stats = {} #[]
    for index_service in services:
        for column_service in services:
            relevant_traffic_values = df.loc[index_service, column_service]
            #print relevant_traffic_values, type(relevant_traffic_values)
            #if relevant_traffic_values.mean() != 0:
            data_stats[index_service, column_service] = [relevant_traffic_values.mean(), relevant_traffic_values.std()]
    return data_stats

# might want to expand to a more generalized printing function at some stage
def print_control_charts_process(relevant_traffic_values, is_send, index_service, column_service):
    if is_send:
        print "\n", index_service, " SENT TO ", column_service
    else:
        print "\n", index_service, " RECEIVE FROM ", column_service
    #print relevant_traffic_values.describe()
    print "Mean: ", relevant_traffic_values.mean()
    print "Stddev: ", relevant_traffic_values.std()

def get_times(df):
    times = []
    for x in df.loc[:, 'time']:
        times.append(x)
    times = sorted(list(set(times)))
    return times

# this function uses the statistics that are in data_stats to
# see if the next value for a service pair causes 
# an alarm via control chart anomaly detection
def next_value_trigger_control_charts(next_df, data_stats, time):
    warnings_triggered = []
    ## iterate through values of data_stats
    ## get value from traffic matrix
    ## if outside of bounds, print something in capital letters
    for src_dst, mean_stddev in data_stats.iteritems():
        #print "src_dst value: ", src_dst, "mean_stddev value: ", mean_stddev
        next_val = next_df.loc[ src_dst[0], src_dst[1] ]
        mean, stddev = mean_stddev[0], mean_stddev[1]
        if abs(next_val - mean) > (2 * stddev):
            #print "THIS IS THE POOR MAN'S EQUIVALENT OF AN ALARM!!", src_dst, mean_stddev
            warnings_triggered.append([src_dst, mean_stddev, time])
    return warnings_triggered

# this function will determine how well PCA can fit the data
# okay, I'm going to follow the method from Ding's 'PCA-based
# Network Traffic Anomaly Detection', even though I think it may
# or may not be nonsense
def pca_anom_detect(df):
    # arbitrarily choosing 5 for now, will investigate in more detail later
    n_components = 5
    pca = PCA(n_components=n_components)
    pca.fit(df)
    pca_compon = pd.DataFrame(pca.transform(df), columns=['PCA%i' % i for i in range(n_components)], index=df.index)
    print "pca components", pca_compon
    print "pca explained var", pca.explained_variance_
    return

if __name__=="__main__":
    rec_matrix_location = './experimental_data/' + parameters.rec_matrix_location
    send_matrix_location = './experimental_data/' + parameters.sent_matrix_location
    if len(sys.argv) > 2:
        rec_matrix_location = sys.argv[1]
        send_matrix_location = sys.argv[2]
    main(rec_matrix_location, send_matrix_location)
