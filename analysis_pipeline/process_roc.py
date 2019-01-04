#########
## These functions process the ROC generated by the multi-experiment coordinator.
## Therefore, they are relatively abstract.
#########

import sklearn
import pandas as pd
import ast

def determine_optimal_threshold(y_true, test_predictions, thresholds):
    list_of_f1_scores = []
    for counter,threshold in enumerate(thresholds):
        y_pred = [int(i > threshold) for i in test_predictions]
        f1_score = sklearn.metrics.f1_score(y_true, y_pred, pos_label=1, average='binary')
        list_of_f1_scores.append(f1_score)
    max_f1_score = max(list_of_f1_scores)
    max_f1_score_threshold_pos = [i for i,j in enumerate(list_of_f1_scores) if j == max_f1_score]
    threshold_corresponding_max_f1 = thresholds[max_f1_score_threshold_pos[0]]

    return max_f1_score, threshold_corresponding_max_f1

def determine_categorical_labels(y_test, optimal_predictions, exfil_paths):
    attack_type_to_predictions = {}
    attack_type_to_truth = {}
    types_of_exfil_paths = list(set(exfil_paths.tolist()))
    print "types_of_exfil_paths", types_of_exfil_paths
    types_of_exfil_paths = [ast.literal_eval(i) for i in types_of_exfil_paths]
    print "types_of_exfil_paths", types_of_exfil_paths
    types_of_exfil_paths = [i if i != 0 else [] for i in types_of_exfil_paths]
    print "types_of_exfil_paths", types_of_exfil_paths
    attack_type_to_index = {}
    for exfil_type in types_of_exfil_paths:
        print "exfil_type",exfil_type, type(exfil_type), "tuple(exfil_type)",tuple(exfil_type), type(tuple(exfil_type))
        current_indexes = []
        ## TODO: this function is all kinds of broken.... VVVV .... VVV ... the == is never true b/c I'm messing w/ exfil paths
        #for i,j in enumerate(exfil_paths):
        #    if j == exfil_type
        current_indexes = [i for i, j in enumerate(exfil_paths) if j == str(exfil_type)]
        print "current_indexes", current_indexes
        attack_type_to_index[tuple(exfil_type)] = current_indexes
    print "optimal_predictions", len(optimal_predictions)
    print "attack_type_to_index",attack_type_to_index
    #print "y_test", y_test['labels'], type(y_test['labels'])
    for exfil_type,indexes in attack_type_to_index.iteritems():
        attack_type_to_predictions[exfil_type] = [optimal_predictions[i] for i in indexes]
        attack_type_to_truth[exfil_type] = [y_test[i] for i in indexes]
    return attack_type_to_predictions, attack_type_to_truth

def determine_cm_vals_for_categories(attack_type_to_predictions, attack_type_to_truth):
    attack_type_to_confusion_matrix_values = {}
    for attack_type, predictions in attack_type_to_predictions.iteritems():
        truth = attack_type_to_truth[attack_type]
        print "attack_type", attack_type
        print "truth", truth
        print "predictions", predictions
        if truth != [] and predictions != []:
            print "truth_and_predictions_not_empty"
            print sklearn.metrics.confusion_matrix(truth, predictions,labels=[0,1]).ravel()
            tn, fp, fn, tp = sklearn.metrics.confusion_matrix(truth, predictions, labels=[0,1]).ravel()
        else:
            print "truth_and_predictions_empty"
            tn, fp, fn, tp = 0, 0, 0, 0
        attack_type_to_confusion_matrix_values[attack_type] = {}
        attack_type_to_confusion_matrix_values[attack_type]['tn'] = tn
        attack_type_to_confusion_matrix_values[attack_type]['tp'] = tp
        attack_type_to_confusion_matrix_values[attack_type]['fp'] = fp
        attack_type_to_confusion_matrix_values[attack_type]['fn'] = fn
    return attack_type_to_confusion_matrix_values

def determine_categorical_cm_df(attack_type_to_confusion_matrix_values):
    print "attack_type_to_confusion_matrix_values", attack_type_to_confusion_matrix_values
    index = attack_type_to_confusion_matrix_values.keys()
    columns = attack_type_to_confusion_matrix_values[index[0]].keys()
    categorical_cm_df = pd.DataFrame(0, index=index, columns=columns)
    for attack_type, confusion_matrix_values in attack_type_to_confusion_matrix_values.iteritems():
        for cm_value_types, cm_values in confusion_matrix_values.iteritems():
            print "attack_type", attack_type
            print "df_indexes", categorical_cm_df.index
            print attack_type in categorical_cm_df.index
            print categorical_cm_df[cm_value_types]
            categorical_cm_df[cm_value_types][attack_type] = cm_values
    return categorical_cm_df