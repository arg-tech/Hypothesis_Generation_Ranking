from flask import render_template, request, redirect, session, Markup
from . import application
import pandas as pd
from urllib.request import urlopen
import requests
import json
import urllib
import tempfile
import os
import uuid
from app.centrality import Centrality
from app.SentenceSimilarity import SentenceSimilarity
from itertools import combinations
import datetime
import copy
import re
from glob import glob
import spacy
import sys
import statistics
import os.path
from scipy import stats


@application.route('/')
@application.route('/index')
def index():
    return redirect('/question')

@application.route('/question')
def get_questions():
    return render_template('question.html')
@application.route('/form')
def my_form():
    return render_template('index.html')

@application.route('/question', methods=['POST'])
def question_post():
    iat_mode = 'false'
    text = request.form['question']
    session['text_var'] = text
    return redirect('/results')

@application.route('/form', methods=['POST'])
def my_form_post():
    iat_mode = 'false'
    text = request.form['text']
    session['text_var'] = text
    return redirect('/results')


@application.route('/process_list', methods=['POST'])
def process_list():
    data = request.get_json()
    aif_jsn = data['aif_json']
    removed_nodes = data['removed_nodes']
    alt_hyps = data['alt_hyps']
    text = data['text']
    hyps = data['hypotheses']
    hypoths = data['hyps']

    try:
        aif_jsn = json.loads(aif_jsn)
    except:
        pass

    cent = Centrality()
    for node in removed_nodes:
        aif_jsn = remove_nodes(aif_jsn, node)
    graph = cent.get_graph_string(aif_jsn)

    cent_i_nodes = cent.get_degree_centrality(graph)



    sorted_i_nodes = cent.sort_by_centrality(cent_i_nodes)
    incoming_nodes = cent.get_i_ra_nodes(graph, sorted_i_nodes)
    ranked_i_nodes = get_ranking(incoming_nodes)
    ranked_i_nodes = sort_by_rank(ranked_i_nodes)

    i_nodes_critical = get_critical_factors(graph, ranked_i_nodes)
    #hyp_explain = get_exps(alt_jsn_copy)
    #print(i_nodes_critical)
    #hyp_explain = get_exps(alt_jsn_copy)

    all_nodes_explain = get_full_struct_explanation(graph, i_nodes_critical)

    #hyp_explain = [hyp  for hyp in all_nodes_explain if 'H' in str(hyp[0])]

    #produce_explanation_from_structure(hyp_explain)
    #produce_explanation_from_rules(all_hypotheses)

    #explain_alt_hyps(alternative_hypotheses)
    hyp_rule_exp = produce_explanation_from_rules(hypoths)

    all_nodes = merge_explanations(all_nodes_explain, hyp_rule_exp)
    #all_nodes = merge_explanations(hyp_explain, hyp_rule_exp)
    first_word, context = parse_question(text)

    search_type = get_search_type(first_word)

    all_ns = perform_search(search_type, text, all_nodes, first_word, graph)

    #write_json_to_file(aif_jsn, 'generated_hyps.json')


    return render_template('main.html', hypothesis_list = all_ns, alt_hypoth = alt_hyps, hypotheses=hyps,question = text, aif_jsn = aif_jsn)

def generate_hypotheses(context, json_path, hevy_file_name, map_counter, count, nlp):


    graph, jsn = get_graph_json(json_path)
    target_schemes = get_arg_schemes_props(graph, jsn)

    if context == '':
        rules_path = 'rules/'
        hevy_rules_path = 'rules/hevy/'
    else:
        rules_path = 'rules/' + context + '/'
        hevy_rules_path = 'rules/hevy/' + context + '/'

    rules, full_scheme_data = get_rules_data(rules_path, hevy_rules_path)



    scheme_hypos = get_argument_scheme_hypotheses(nlp, 0.33, full_scheme_data, target_schemes)

    cent = Centrality()
    i_nodes = cent.get_i_node_list(graph)

    hevy_jsn = get_hevy_json(hevy_file_name, '')
    rule_hypos = get_hyps_from_rules(hevy_jsn, i_nodes, rules, 0.15, nlp)

    rule_hypo_list = remove_duplicate_hypos(rule_hypos)

    scheme_list, overall_rule_list = combine_hypothesis_lists(scheme_hypos, rule_hypo_list)

    all_hypotheses = scheme_list + overall_rule_list

    all_hypotheses_copy = copy.deepcopy(all_hypotheses)

    nodelst, edgelst = construct_aif_graph(all_hypotheses_copy, jsn, count)

    jsn_copy = copy.deepcopy(jsn)

    nodes_cp = jsn_copy['nodes']
    nodes_cp.extend(nodelst)
    jsn_copy['nodes'] = nodes_cp

    edges_cp = jsn_copy['edges']
    edges_cp.extend(edgelst)
    jsn_copy['edges'] = edges_cp

    hypoths_list = get_hypotheses_list(jsn_copy)

    alternative_hypotheses = generate_alternative_hypothesis(hypoths_list, nlp)

    alt_nodes, alt_edges = alternate_hyps_aif(alternative_hypotheses, count)

    alt_jsn_copy = copy.deepcopy(jsn_copy)

    nodes_cp = alt_jsn_copy['nodes']
    nodes_cp.extend(alt_nodes)
    alt_jsn_copy['nodes'] = nodes_cp

    edges_cp = alt_jsn_copy['edges']
    edges_cp.extend(alt_edges)
    alt_jsn_copy['edges'] = edges_cp

    graph2 = cent.get_graph_string(alt_jsn_copy)
    cent_i_nodes = cent.get_degree_centrality(graph2)



    sorted_i_nodes = cent.sort_by_centrality(cent_i_nodes)
    incoming_nodes = cent.get_i_ra_nodes(graph2, sorted_i_nodes)
    ranked_i_nodes = get_ranking(incoming_nodes)
    ranked_i_nodes = sort_by_rank(ranked_i_nodes)

    i_nodes_critical = get_critical_factors(graph2, ranked_i_nodes)
    #hyp_explain = get_exps(alt_jsn_copy)

    all_nodes_explain = get_full_struct_explanation(graph2, i_nodes_critical)

    #hyp_explain = [hyp  for hyp in all_nodes_explain if 'H' in str(hyp[0])]

    #produce_explanation_from_structure(hyp_explain)
    hyp_rule_exp = produce_explanation_from_rules(all_hypotheses)

    all_nodes = merge_explanations(all_nodes_explain, hyp_rule_exp)
    #all_nodes = merge_explanations(hyp_explain, hyp_rule_exp)
    #print(all_nodes)
    #explain_alt_hyps(alternative_hypotheses)
    #print('Explanations in text files structure_explanation.txt, rules_explanation.txt, alternative_hyps_explanation.txt')

    #write_json_to_file(alt_jsn_copy, 'generated_hyps.json')

    return all_hypotheses,alternative_hypotheses, alt_jsn_copy, all_nodes

@application.route('/results')
def render_text():
    text = session.get('text_var', None)

    first_word, context = parse_question(text)

    search_type = get_search_type(first_word)

    #context = 'militant'
    #20088_target
    nlp = spacy.load("en")
    overall_json = ''
    overall_hyp_explain = []
    overall_hyp_list = []
    overall_alt_hyp_list = []
    json_path = ''
    hevy_file_name = ''
    if context == '':
        json_path = 'target_data/'
        hevy_file_name = 'target_data/'
    else:

        json_path = 'target_data/' + context + '/'
        hevy_file_name = 'target_data/' + context + '/'
    for subdir, dirs, files in os.walk(os.path.join(application.static_folder, json_path)):
        for i, file_name in enumerate(files):
            if '.json' in file_name and 'hevy' not in file_name:
                base = subdir + file_name

                base_ext = os.path.splitext(base)[0]
                hevy_f_name = file_name.split('.')[0]

                jsn_path = base
                if context == '':
                    hevy_file_name = 'target_data/' + str(hevy_f_name) + '_target'
                else:
                    hevy_file_name = 'target_data/' + context + '/' + str(hevy_f_name) + '_target'

                hevy_file_name = os.path.join(application.static_folder, hevy_file_name)

                hyp_list,alternative_hypotheses, alt_jsn_copy, hyp_explain = generate_hypotheses(context, jsn_path, hevy_file_name, hevy_f_name, i, nlp)

                overall_hyp_explain.extend(hyp_explain)
                overall_hyp_list.extend(hyp_list)
                overall_alt_hyp_list.extend(alternative_hypotheses)



                if overall_json == '':
                    overall_json = alt_jsn_copy
                else:


                    jsn_copy = copy.deepcopy(alt_jsn_copy)
                    nodes_cp = jsn_copy['nodes']
                    edges_cp = jsn_copy['edges']
                    locs_cp = jsn_copy['locutions']

                    overall_nodes = overall_json['nodes']
                    overall_edges = overall_json['edges']
                    overall_locutions = overall_json['locutions']

                    overall_nodes.extend(nodes_cp)
                    overall_json['nodes'] = overall_nodes

                    overall_edges.extend(edges_cp)
                    overall_json['edges'] = overall_edges

                    overall_locutions.extend(locs_cp)
                    overall_json['locutions'] = overall_locutions


    #
    cent = Centrality()
    graph = cent.get_graph_string(overall_json)
    #return ''
    #Specifiy search her
    all_ns = perform_search(search_type, text, overall_hyp_explain, first_word, graph)

    #Where new foreign fighters being militant?

    return render_template('results.html', hypothesis_list = all_ns, hypotheses=overall_hyp_list, alt_hypoth = overall_alt_hyp_list, question = text, aif_jsn = overall_json)

def perform_search(search_type, question, all_nodes, question_type, graph):
    return_nodes = []
    nlp = spacy.load("en")
    entity = ''
    location = ''
    cent = Centrality()

    question_type = question_type.lower()

    entity_list, location_list = get_entity_from_question(nlp, question)
    if len(entity_list) > 0:
        entity = entity_list[0]
    if len(location_list) > 0:
        location = location_list[0]
    if search_type == 'hyp':

        hyp_explain = [hyp  for hyp in all_nodes if 'H' in str(hyp[0])]

        for hyp in hyp_explain:
            hyp_id = hyp[0]
            hyp_text = hyp[2]
            sim = get_alternate_wn_similarity(str(hyp_text), str(question))
            if entity.lower() in hyp_text.lower():
                if 'why' in question_type:
                    prems = cent.get_i_ra_nodes_ind(graph, all_nodes, hyp_id)
                    return_nodes.extend(prems)

                else:
                    return_nodes.append(hyp)
            elif 'who' in question_type:
                #get entity from hyp_text
                ent_list, loc_list = get_entity_from_question(nlp, hyp_text)
                if len(ent_list) > 0:
                    return_nodes.append(hyp)
            elif sim > 0.38 and len(entity_list) < 1:
                if 'why' in question_type:
                    prems = cent.get_i_ra_nodes_ind(graph, all_nodes, hyp_id)
                    return_nodes.extend(prems)
                else:
                    return_nodes.append(hyp)

    else:
        if 'why' in question_type:
            print('Get hypotheses from reasons')
        else:
            for hyp in all_nodes:
                hyp_id = hyp[0]
                hyp_text = hyp[2]
                sim = get_alternate_wn_similarity(str(hyp_text), str(question))
                if 'where' in question_type and 'H' not in str(hyp_id):
                    ent_list, loc_list = get_entity_from_question(nlp, hyp_text)
                    if len(loc_list) > 0:
                        return_nodes.append(hyp)
                elif sim > 0.5 and 'H' not in str(hyp_id):
                    return_nodes.append(hyp)
    return return_nodes



def merge_explanations(all_nodes, hyp_nodes_explained):
    for node in all_nodes:
        text = node[2]
        hyp_found = False
        for hyp in hyp_nodes_explained:
            hyp_text = hyp[0]
            hyp_exp = hyp[1]
            if text == hyp_text:
                hyp_found = True
                node.append(hyp_exp)
                break
        if not hyp_found:
            node.append('')
        else:
            hyp_found = False
    return all_nodes


def parse_question(question_text):
    first_word = question_text.split()[0]
    domain = check_domain(question_text)

    return first_word, domain

def check_domain(text):
    text = text.lower()
    if 'militant' in text:
        return 'militant'
    elif 'corporate' in text:
        return 'corporate'
    else:
        return ''

def get_json_string(node_path):
    dta = ''
    try:
        with application.open_resource(node_path) as j:
             dta = json.loads(j.read())
    except(IOError):
        print('File was not found:')
        print(node_path)

    return dta

def get_graph_json(json_path):
    cent = Centrality()

    json_data = get_json_string(json_path)
    graph = cent.get_graph_string(json_data)

    return graph, json_data

def get_arg_schemes_props(graph, json_data):
    cent = Centrality()

    i_nodes = cent.get_i_node_list(graph)

    schemes_list = []
    for node in i_nodes:
        node_id = node[0]
        node_text = node[1]

        schemes = identifyPremScheme(node_text)

        if len(schemes) < 1:
            continue
        else:
            ra_tup = (node_id,node_text, schemes)
            schemes_list.append(ra_tup)
            #get json string and replace text at ID then upload


    return schemes_list

def identifyPremScheme(premise):
    identifiedSchemes = []

    premise = premise.lower()

    if (" similar " in premise or " generally " in premise):
        identifiedSchemes.append("Analogy")

    if (" generally " in premise or " occur " in premise):
        identifiedSchemes.append("CauseToEffect")

    if(" goal " in premise or " action " in premise):
        identifiedSchemes.append("PracticalReasoning")

    if(" all " in premise or " if " in premise) :
        identifiedSchemes.append("VerbalClassification")

    if(" occur " in premise or " happen " in premise):
        identifiedSchemes.append("PositiveConsequences")

    if(((" expert " in premise or " experience " in premise or " skill " in premise) and " said " in premise)) :
        identifiedSchemes.append("ExpertOpinion")

    if(" said " in premise) :
        identifiedSchemes.append("PositionToKnow")



    return identifiedSchemes

def get_rules_data(rules_path, hevy_rules_path):
    data = []
    rules = []
    full_scheme_data = []
    for subdir, dirs, files in os.walk(os.path.join(application.static_folder, rules_path)):
        for file_name in files:

            if '.json' in file_name and not 'hevy' in file_name:
                #base = subdir + file_name
                base  = os.path.join(application.static_folder, rules_path)
                base = base + file_name
                base_ext = os.path.splitext(base)[0]
                schemes = get_arg_schemes_full_aif(base)
                rule = get_rules(base)
                hevy_file_name = file_name.split('.')[0]
                h_jsn = get_hevy_json(hevy_file_name, os.path.join(application.static_folder, hevy_rules_path))
                rule = get_hevy_rules(rule,h_jsn)

                rules.extend(rule)
                data.extend(schemes)
            full_scheme_data = [x for x in data if x]
    return rules, full_scheme_data

def get_arg_schemes_full_aif(json_path):
    cent = Centrality()


    graph, json_data = get_graph_json(json_path)


    ras = cent.get_ras(graph)
    ras_i_list = cent.get_full_ra_i_nodes(graph, ras)

    ra_changes = []
    for ns in ras_i_list:

        ra_id = ns[0]
        conc_id = ns[1]
        conc_text = ns[2]
        prem_id = ns[3]
        prem_text = ns[4]


        schemes = identifyFullScheme(prem_text, conc_text)

        if len(schemes) < 1:
            continue
        else:
            ra_tup = (ra_id, conc_text, prem_text,  schemes)
            ra_changes.append(ra_tup)



    return ra_changes

def get_rules(json_path):
    cent = Centrality()

    json_data = get_json_string(json_path)
    graph = cent.get_graph_string(json_data)


    ras = cent.get_ras(graph)
    ras_i_list = cent.extract_rule_structure(graph, ras)

    return ras_i_list

def get_hevy_json(file_name, file_path):
    try:

        json_path = file_path + file_name + '_hevy.json'
        json_data = get_json_string(json_path)
        return json_data
    except:
        return ''

def get_hevy_rules(rules, hevy_json):
    heavy_rule = []
    for rule in rules:
        hyp_id = rule[0]
        hyp_text = rule[1]
        premise_list = rule[2]


        for i, premise in enumerate(premise_list):
            premise_id = premise[0]
            premise_text = premise[1]
            if hevy_json == '':
                premise_list[i] = (premise_id, premise_text, '')
            else:
                premise_node = get_hevy_event(premise_id, hevy_json)
                premise_list[i] = (premise_id, premise_text, premise_node)
    return rules

def get_hevy_event(node_id, hevy_json):

    for edge in hevy_json['edges']:
        from_id = edge['fromID']
        to_id = edge['toID']
        if str(from_id) == str(node_id):
            for node in hevy_json['nodes']:
                node_id = node['nodeID']

                if str(node_id) == str(to_id):
                    node_type = ''
                    try:
                        node_type = node['type']
                    except:
                        pass

                    if node_type == 'Event':
                        return node

    return ''

def identifyFullScheme(premise, conclusion):
    identifiedSchemes = []
    premise = premise.lower()
    conclusion = conclusion.lower()

    if (("similar" in premise or "generally" in premise) and ("be" in conclusion or "to be" in conclusion)):
        identifiedSchemes.append("Analogy")

    elif ("generally" in premise or "occur" in premise) or ("occur" in conclusion) :
        identifiedSchemes.append("CauseToEffect")

    elif("goal" in premise or "action" in premise) or ("ought" in conclusion or "perform" in conclusion) :
        identifiedSchemes.append("PracticalReasoning")

    elif(("all" in premise or "if" in premise) and ("be" in conclusion or "to be" in conclusion)) :
        identifiedSchemes.append("VerbalClassification")

    elif((("expert" in premise or "experience" in premise or "skill" in premise) and "said" in premise) and ("be" in conclusion or "to be" in conclusion)) :
        identifiedSchemes.append("ExpertOpinion")

    elif(("said" in premise)) :
        identifiedSchemes.append("PositionToKnow")

    elif(("occur" in premise or "happen" in premise) and ("should" in conclusion or "must" in conclusion)) :
        identifiedSchemes.append("PositiveConsequences")

    return identifiedSchemes

def get_argument_scheme_hypotheses(nlp, threshold, full_scheme_data, target_schemes):
    hyps = []
    new_hyps = []
    for scheme_tup in target_schemes:

        node_id = scheme_tup[0]
        node_text = scheme_tup[1]
        scheme_list = scheme_tup[2]
        agent_list = []
        org_list = []
        speaker = ''
        if 'said' in node_text.lower():
            sep = 'said'
            speaker = node_text.lower().split(sep, 1)[0]
            stripped = node_text.lower().split(sep, 1)[1]
            agent_list, org_list = get_entity_from_text(nlp, stripped)
        else:
            stripped = node_text
            agent_list, org_list = get_entity_from_text(nlp, stripped)


        output_hyps = compare_schemes(full_scheme_data, scheme_list, hyps, speaker, node_text, node_id, threshold, agent_list)
        new_hyps.extend(output_hyps)

    new_hyps = list(set(new_hyps))
    return new_hyps

def get_entity_from_text(nlp, text):
    if text.isupper():
        text = text.lower()
    doc = nlp(text)
    person_list=[]
    org_list = []
    place_list = []
    for ent in doc.ents:
        if ent.label_ == 'PERSON':
            person_list.append(ent.text)
        if ent.label_ == 'ORG':
            org_list.append(ent.text)
        if ent.label_ == 'GPE':
            place_list.append(ent.text)
    for token in doc:
        if token.pos_ == 'PROPN' and token.text not in person_list and token.text not in org_list and token.text not in place_list:
            person_list.append(token.text)
    return person_list, org_list

def get_entity_from_question(nlp, text):
    if text.isupper():
        text = text.lower()
    doc = nlp(text)
    person_list=[]
    org_list = []
    place_list = []
    for ent in doc.ents:
        if ent.label_ == 'PERSON':
            person_list.append(ent.text)
        if ent.label_ == 'ORG':
            person_list.append(ent.text)
        if ent.label_ == 'GPE':
            place_list.append(ent.text)
    for token in doc:
        if token.pos_ == 'PROPN' and token.text not in person_list and token.text not in org_list and token.text not in place_list:
            person_list.append(token.text)
    return person_list, place_list

def compare_schemes(full_scheme_data, scheme_list, hyps, speaker, node_text, node_id, threshold, agent_list):
    for scheme in scheme_list:
            if len(full_scheme_data) > 0:
                for full_scheme in full_scheme_data:
                    ra_id = full_scheme[0]
                    hypothesis = full_scheme[1]
                    premise = full_scheme[2]
                    full_scheme_list = full_scheme[3]

                    for s in full_scheme_list:
                        if s == scheme:
                            sim = get_alternate_wn_similarity(str(node_text), str(premise))
                            if sim >= threshold:
                                if len(agent_list) < 1:
                                    hypothesis = hypothesis.replace('Person X', org_list[0])
                                    hyps.append((hypothesis, node_text, node_id, scheme))
                                else:
                                    hypothesis = hypothesis.replace('Person X', agent_list[0])
                                    hyps.append((hypothesis, node_text, node_id, scheme))
            if speaker == '':
                hyps.extend(get_scheme_cq_hypothesis(scheme, node_text,node_id, agent_list[0], False, ''))
            else:
                hyps.extend(get_scheme_cq_hypothesis(scheme, node_text,node_id, speaker, False, ''))
    return hyps

def get_alternate_wn_similarity(sent1, sent2):
    sent_sim = SentenceSimilarity()
    similarity = sent_sim.symmetric_sentence_similarity(sent1, sent2)
    return similarity

def get_scheme_cq_hypothesis(scheme_type, text,node_id, agent, match, matching_proposition):

    scheme_hyps = []

    if scheme_type == "CauseToEffect":
        scheme_hyps.append("There is no other cause for effect " + text, text, node_id, scheme_type)
    if scheme_type == "PracticalReasoning":
        scheme_hyps.append((agent + " has the means to carry out the action", text ,node_id, scheme_type))
        scheme_hyps.append((agent + " does not have other conflicting goals", text ,node_id, scheme_type))

    if scheme_type == "VerbalClassification":
        scheme_hyps.append(("There is doubt that " + agent + " has property " + text, text ,node_id, scheme_type))
    if scheme_type == "ExpertOpinion":
        scheme_hyps.append((agent + " is a credible expert", text ,node_id, scheme_type))
        scheme_hyps.append((agent + " is an expert in the field", text ,node_id, scheme_type))
        scheme_hyps.append((agent + " is a trusted source of information", text ,node_id, scheme_type))
        scheme_hyps.append((agent + " provides consistent information", text ,node_id, scheme_type))
        scheme_hyps.append((agent + " has provided proof", text ,node_id, scheme_type))
    if scheme_type == "PositionToKnow":
        scheme_hyps.append((agent + " provides consistent information", text ,node_id, scheme_type))
        scheme_hyps.append((agent + " is in a position to know the truth", text ,node_id, scheme_type))
        scheme_hyps.append((agent + " is a trusted source of information", text ,node_id, scheme_type))
        scheme_hyps.append((agent + " has provided proof", text ,node_id, scheme_type))


    if scheme_type == "PositiveConsequences":
        scheme_hyps.append(("There is a high chance that " + text + ' will occur', text ,node_id, scheme_type))
        scheme_hyps.append(("There are not other releveant consequences of " + text, text ,node_id, scheme_type))
    return scheme_hyps

def get_hyps_from_rules(hevy_jsn, i_nodes, rules, threshold, nlp):
    all_hypothesis_list = []
    for rule in rules:
        rule_id = rule[0]
        rule_hyp = rule[1]
        rule_premises = rule[2]
        premise_volume = len(rule_premises)


        target_nodes = get_prop_pairs(i_nodes, premise_volume)

        hypothesis_list = compare_rules_to_props(target_nodes, rule_premises, rule_id, rule_hyp, nlp, hevy_jsn, threshold)
        all_hypothesis_list.extend(hypothesis_list)
    return all_hypothesis_list

def get_prop_pairs(props, volume):
    pairs = list(combinations(props,volume))
    return pairs

def compare_rules_to_props(target_nodes, rule_premises, rule_id, rule_hyp, nlp, hevy_jsn, threshold):
    overall_hyp_list = []
    for target in target_nodes:

        rule_flag = True
        score_store = []
        for prem in target:
            l = [None] * len(target)
            counter = 0
            for r in rule_premises:
                rule_text = r[1]
                rule_event = r[2]
                prem_id = prem[0]
                prem_text = prem[1]
                prem_event = ''
                try:
                    prem_event = get_hevy_event(prem_id, hevy_jsn)
                except:
                    pass
                sim = 0
                event_flag = False
                if prem_event == '' or rule_event == '':
                    sim = get_alternate_wn_similarity(prem[1], rule_text)
                else:
                    sim = get_event_similarity(prem_event, rule_event)
                    event_flag = True

                if event_flag:
                    if sim >= (threshold): #threshold * 2

                        score_store.append((prem_text, rule_text, sim, 'EVENT RULE', prem_event))

                        l[counter] = 1
                    else:
                        l[counter] = 0
                    counter = counter + 1
                else:
                    if sim >= (threshold * 2):

                        score_store.append((prem_text, rule_text, sim, 'SIM RULE', ''))

                        l[counter] = 1
                    else:
                        l[counter] = 0
                    counter = counter + 1
            if sum(l) < 1:
                rule_flag = False
                break

        if rule_flag:

            hyps = create_rule_hypothesis(score_store, rule_id, rule_hyp, prem_id, nlp)
            overall_hyp_list.extend(hyps)

    return overall_hyp_list

def create_rule_hypothesis(score_store, rule_id, rule_hyp, prem_id, nlp):

    overall_hypothesis_list = []

    for score in score_store:

        matched_premise = score[0]
        matched_rule_premise = score[1]
        sim = score[2]
        rule_type = score[3]
        agent = ''
        agent_list = []
        org_list = []
        overall_hyp = ''



        if rule_type == 'EVENT RULE':
            ev_premise = score[4]
            agent = ev_premise['involvedAgent']
            if not isinstance(agent, str):
                agent = agent[0]
            if agent == '':
                agent_list, org_list = get_entity_from_text(nlp, matched_premise)
        else:


            agent_list, org_list = get_entity_from_text(nlp, matched_premise)
        if 'Person X' in rule_hyp and len(agent_list) > 0:
            agent = agent_list[0]
            overall_hyp = rule_hyp.replace('Person X', agent)
            #overall_hypothesis_list.append(overall_hyp)
        elif 'Person X' in rule_hyp:
            overall_hyp = rule_hyp.replace('Person X', agent)
            #overall_hypothesis_list.append(overall_hyp)

        overall_hypothesis_list.append([overall_hyp,rule_id, matched_premise, matched_rule_premise, sim, rule_type, prem_id, 'Default Inference'])
    return overall_hypothesis_list

def get_event_similarity(e1, e2):

    sim_list = []


    e1_name = ''
    e2_name = ''
    e1_circa = ''
    e2_circa = ''

    e1_inSpace = ''
    e2_inSpace = ''

    e1_agent = ''
    e2_agent = ''

    e1_involved = ''
    e2_involved = ''

    e1_time = ''
    e2_time = ''


    e1_place = ''
    e2_place = ''

    e1_ill = ''
    e2_ill = ''



    try:
        e1_name = e1['name']
        e2_name = e2['name']
    except:
        pass

    try:
        e1_circa = e1['circa']
        e2_circa = e2['circa']
    except:
        pass

    try:
        e1_inSpace = e1['inSpace']
        e2_inSpace = e2['inSpace']
    except:
        pass

    try:
        e1_agent = e1['involvedAgent']
        e2_agent = e2['involvedAgent']
    except:
        pass

    try:

        e1_involved = e1['involved']
        e2_involved = e2['involved']
    except:
        pass

    try:
        e1_time = e1['atTime']
        e2_time = e2['atTime']
    except:
        pass

    try:
        e1_place = e1['atPlace']
        e2_place = e2['atPlace']
    except:
        pass

    try:
        e1_ill = e1['illustrate']
        e2_ill = e2['illustrate']
    except:
        pass

    if e1_name == '' or e2_name == '':
        pass
    elif e1_name == e2_name:
        sim_list.append(1)
    else:
        name_sim = get_alternate_wn_similarity(e1_name, e2_name)
        sim_list.append(name_sim)

    if e1_circa == '' or e2_circa == '':
        pass
    elif e1_circa == e2_circa:
        sim_list.append(1)
    else:
        circa_sim = get_alternate_wn_similarity(e1_circa, e2_circa)
        sim_list.append(circa_sim)

    if e1_inSpace == '' or  e2_inSpace == '':
        pass

    elif e1_inSpace == e2_inSpace:
        sim_list.append(1)
    else:
        space_sim = get_alternate_wn_similarity(e1_inSpace, e2_inSpace)
        sim_list.append(space_sim)

    if isinstance(e1_agent, str) and isinstance(e2_agent, str):
        if e1_agent == '' or e2_agent == '':
            pass
        elif e1_agent == e2_agent:
            sim_list.append(1)
        else:
            agent_sim = get_alternate_wn_similarity(e1_agent, e2_agent)
            sim_list.append(agent_sim)
    else:
        e1_agent = ' '.join(e1_agent)
        if e1_agent == '' or e2_agent == '':
            pass
        elif e1_agent == e2_agent:
            sim_list.append(1)
        else:
            agent_sim = get_alternate_wn_similarity(e1_agent, e2_agent)
            sim_list.append(agent_sim)

    if e1_involved == '' or e2_involved == '':
        pass
    elif e1_involved == e2_involved:
        sim_list.append(1)
    else:
        inv_sim = get_alternate_wn_similarity(e1_involved, e2_involved)
        sim_list.append(inv_sim)

    if e1_time == '' or e2_time == '':
        pass
    elif e1_time == e2_time:
        sim_list.append(1)
    else:
        time_sim = get_alternate_wn_similarity(e1_time, e2_time)
        sim_list.append(time_sim)

    if e1_place == '' or e2_place == '':
        pass
    elif e1_place == e2_place:
        sim_list.append(1)
    else:
        place_sim = get_alternate_wn_similarity(e1_place, e2_place)
        sim_list.append(place_sim)

    if e1_ill == '' or  e2_ill == '':
        pass
    elif e1_ill == e2_ill:
        sim_list.append(1)
    else:
        ill_sim = get_alternate_wn_similarity(e1_ill, e2_ill)
        sim_list.append(ill_sim)



    harm_mean = statistics.mean(sim_list)

    return harm_mean

def remove_duplicate_hypos(overall_hypothesis_list):
    d = {}
    for sub in overall_hypothesis_list:
        hyp_name = sub[0]
        hyp_id = sub[1]
        prem = sub[2]
        sim = sub[4]
        hyp_name = hyp_name.lower()
        key_string = str(hyp_name) + str(hyp_id) + str(prem)

        if key_string in d:
            if sim > d[key_string][4]:
                d[key_string] = sub
        else:

            d[key_string] = sub
    return list(d.values())

def combine_hypothesis_lists(arg_schemes_hyps, rules_hyps):
    new_arg_scheme_list = []
    for hyp in arg_schemes_hyps:
        hypothesis = hyp[0].lower()
        premise = hyp[1].lower()
        premise_id = hyp[2]
        scheme_type = hyp[3]
        rule_flag = False
        for i,hyp1 in enumerate(rules_hyps):
            hypothesis1 = hyp1[0].lower()
            rules_hyps[i][0] = hypothesis1
            premise1 = hyp1[2].lower()
            scheme_type1 = hyp1[7]
            if hypothesis == hypothesis1 and premise == premise1:
                rule_flag = True
                rules_hyps[i][7] = scheme_type

        if not rule_flag:
            new_arg_scheme_list.append([hypothesis, '', premise, '', 0, 'SCHEME RULE', premise_id, scheme_type])

    return new_arg_scheme_list, rules_hyps

def construct_aif_graph(hypotheses, jsn, counter):
    new_node_list = []
    new_edge_list = []
    rule_lst = []

    for i, hyp in enumerate(hypotheses):
        hypothesis = hyp[0]
        rule_number = hyp[1]
        premise = hyp[2]
        rule_premise = hyp[3]
        sim = hyp[4]
        rule_type = hyp[5]
        p_id = hyp[6]
        ra_type = hyp[7]

        #n_id = get_node_ID(jsn, hypothesis)
        #n_id == '' and
        if not any(d['text'] == hypothesis for d in new_node_list):
            #create node
            n_id = str(counter)+"H" + str(i)
            node_id = str(counter)+"H" + str(i)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            node_dict = {"nodeID": node_id, "text": hypothesis, "type":"I", "timestamp":timestamp}
            ya_id = str(counter)+"YA" + str(i)
            ya_node = create_hyp_ya(ya_id)
            l_id = str(counter)+"L" + str(i)
            L_node = create_l_node(l_id, hypothesis)
            edge1_id = str(counter)+'E1H' + str(i)
            edge_1 = create_edge(edge1_id, l_id, ya_id)

            edge2_id = str(counter)+'E2H' + str(i)
            edge_2 = create_edge(edge2_id, ya_id, node_id)

            new_node_list.append(node_dict)
            new_node_list.append(ya_node)
            new_node_list.append(L_node)

            new_edge_list.append(edge_1)
            new_edge_list.append(edge_2)

        check_bool = False
        id_str = ''

        #Here create RAS and edges from premises to the RAs
        premise_id = get_node_ID(jsn, premise)
        if len(rule_lst) > 0:
            check_bool, id_str = check_hyp_list(hyp, rule_lst)

        if rule_number == '':
            ra_id = str(counter)+'RA' + str(i)
            new_ra_node = create_ra_node(ra_id, ra_type)

            edge1_id = str(counter)+'EH' + str(i)
            edge_1 = create_edge(edge1_id, p_id, ra_id)

            edge2_id = str(counter)+'EHT' + str(i)
            edge_2 = create_edge(edge2_id, ra_id, n_id)


            new_node_list.append(new_ra_node)
            new_edge_list.append(edge_1)
            new_edge_list.append(edge_2)

        elif len(rule_lst) < 1:
            ra_id = str(counter)+'RA' + str(i)
            new_ra_node = create_ra_node(ra_id, ra_type)

            edge1_id = str(counter)+'EH' + str(i)
            edge_1 = create_edge(edge1_id, premise_id, ra_id)

            edge2_id = str(counter)+'EHT' + str(i)
            edge_2 = create_edge(edge2_id, ra_id, n_id)


            hyp.append(ra_id)
            rule_lst.append(hyp)

            new_node_list.append(new_ra_node)
            new_edge_list.append(edge_1)
            new_edge_list.append(edge_2)

        elif not check_bool and id_str == 'False':
            pass
        elif check_bool:

            #GET RA TO CHECK TYPE
            change_ra_type(id_str,new_node_list, ra_type)

            edge1_id = str(counter)+'EH' + str(i)
            edge_1 = create_edge(edge1_id, premise_id, id_str)


            hyp.append(id_str)
            rule_lst.append(hyp)
            new_edge_list.append(edge_1)
        elif not check_bool and id_str == '':
            ra_id = str(counter)+'RA' + str(i)
            new_ra_node = create_ra_node(ra_id, ra_type)

            edge1_id = str(counter)+'EH' + str(i)
            edge_1 = create_edge(edge1_id, premise_id, ra_id)

            edge2_id = str(counter)+'EHT' + str(i)
            edge_2 = create_edge(edge2_id, ra_id, n_id)

            hyp.append(ra_id)
            rule_lst.append(hyp)

            new_node_list.append(new_ra_node)
            new_edge_list.append(edge_1)
            new_edge_list.append(edge_2)

    return new_node_list, new_edge_list

def get_hypotheses_list(jsn_data):
    nodes = jsn_data['nodes']
    edges = jsn_data['edges']

    hypothesis_list = []

    for node in nodes:
        node_id = node['nodeID']
        if node['text'] == 'Hypothesising':
            for edge in edges:
                if str(edge['fromID']) == str(node_id):
                    hyp_id = edge['toID']
                    for n in nodes:
                        n_id = n['nodeID']
                        n_text = n['text']
                        if str(n_id) == hyp_id:
                            hypothesis_list.append([hyp_id, n_text])
    return hypothesis_list

def generate_alternative_hypothesis(hypotheses, nlp):
    negative_hyps = []
    for hyp in hypotheses:
        h_id = hyp[0]
        h_text = hyp[1]
        doc = nlp(h_text)
        negation = [tok for tok in doc if tok.dep_ == 'neg']
        neg_flag = check_for_negation(negation)
        if neg_flag:
            pos_form = convert_to_positive_form(negation, h_text)
            negative_hyps.append([pos_form, h_id, h_text])

        else:
            neg_form = convert_to_negative_form(h_text, doc)
            negative_hyps.append([neg_form, h_id, h_text])
    return negative_hyps

def check_for_negation(negation_list):
    if len(negation_list) < 1:
        return False
    else:
        return True

def convert_to_positive_form(negation_list, sentence):
    negation_list = [str(x).lower() for x in negation_list]
    resultwords  = [word for word in re.split("\W+",sentence) if word.lower() not in negation_list]
    result = ' '.join(resultwords)
    return result

def convert_to_negative_form(sent, doc):
    for token in doc:
        if token.dep_ == 'ROOT' or token.dep_ == 'aux':
            if 'VB' in token.tag_:
                if token.tag_ == 'VBZ':
                #insert Not after
                    negation = 'not'
                    word_list = [token.text]
                    word_list = [str(x).lower() for x in word_list]
                    sent_words = re.split("\W+",sent)
                    resultwords  = [word.lower() + ' ' + negation + ' ' if word.lower() in word_list else word.lower() for word in sent_words ]
                    result = ' '.join(resultwords)
                    return result
                else:
                    negation = 'did not'
                    word_list = [token.text]
                    word_list = [str(x).lower() for x in word_list]
                    sent_words = re.split("\W+",sent)
                    resultwords  = [' ' + negation + ' ' + str(token.lemma_) if word.lower() in word_list else word.lower() for word in sent_words ]
                    result = ' '.join(resultwords)
                    return result
    return 'not ' + sent.lower()

def create_ca_node(node_id, text):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ca_dict = {"nodeID":node_id,"text":text,"type":"CA","timestamp":timestamp}
    return ca_dict

def get_node_ID(graph_jsn, text):
    for node in graph_jsn['nodes']:
        n_text = node['text']
        n_id = node['nodeID']
        if text == n_text:
            return n_id

    return ''

def create_hyp_ya(node_id):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ya_dict = {"nodeID":node_id,"text":"Hypothesising","type":"YA","timestamp":timestamp,"scheme":"Hypothesising","schemeID":"410"}
    return ya_dict

def create_l_node(node_id, text):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    l_text = 'Hypothesis Generator : ' + text
    l_dict = {"nodeID":node_id,"text":l_text,"type":"L","timestamp":timestamp}
    return l_dict

def create_ra_node(node_id, text):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ra_dict = {"nodeID":node_id,"text":text,"type":"RA","timestamp":timestamp}
    return ra_dict

def create_edge(edge_id, fromID, toID):
    edge_dict = {"edgeID":edge_id,"fromID":fromID,"toID":toID}
    return edge_dict

def check_hyp_list(hyp, rule_list):


    hypothesis = hyp[0]
    rule_number = hyp[1]
    premise = hyp[2]
    rule_premise = hyp[3]
    sim = hyp[4]
    rule_type = hyp[5]
    ra_type = hyp[7]

    hyp_check = True
    rule_check = True
    prem_check = True

    for rule in rule_list:



        r_hypothesis = rule[0]
        r_rule_number = rule[1]
        r_premise = rule[2]
        r_rule_premise = rule[3]
        r_sim = rule[4]
        r_rule_type = rule[5]
        r_ra_type = rule[7]
        r_ra_id = rule[8]



        if hypothesis == r_hypothesis and rule_number == r_rule_number and premise == r_premise:
            #Already a connected made so return all false
            return False,'False'

        if hypothesis == r_hypothesis and rule_number == r_rule_number and premise != r_premise:
            return True, r_ra_id

        if hypothesis != r_hypothesis:
            hyp_check = False

        if hypothesis == r_hypothesis and rule_number != r_rule_number:
            rule_check = False

    if not hyp_check:
        return False, ''

    if not rule_check:
        return False, ''

    return False,'False'

def change_ra_type(ra_id, node_list, ra_type):
    for node in node_list:
        if node['nodeID'] == ra_id:
            curr_ra_text = node['text']
            if curr_ra_text == 'Default Inference' and ra_type != 'Default Inference':
                node['text'] = ra_type

def alternate_hyps_aif(alt_hyps,counter):
    new_node_list = []
    new_edge_list = []

    for i, hyp in enumerate(alt_hyps):
        alt_text = hyp[0]
        hyp_id = hyp[1]

        n_id = str(counter)+"AH" + str(i)
        node_id = str(counter)+"AH" + str(i)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        node_dict = {"nodeID": node_id, "text": alt_text, "type":"I", "timestamp":timestamp}
        ya_id = str(counter)+"AYA" + str(i)
        ya_node = create_hyp_ya(ya_id)

        l_id = hyp_id.replace('H', 'L')

        edge1_id = str(counter)+'EA' + str(i)
        edge_1 = create_edge(edge1_id, l_id, ya_id)

        edge2_id = str(counter)+'EA' + str(i)
        edge_2 = create_edge(edge2_id, ya_id, node_id)

        ca_1_id = str(counter)+'CA' + str(i)
        ca_2_id = str(counter)+'ACA' + str(i)

        ca_text = 'Default Conflict'

        ca_1_node = create_ca_node(ca_1_id, ca_text)
        ca_2_node = create_ca_node(ca_2_id, ca_text)

        CAedge1_id = str(counter)+'CAE' + str(i)
        CAedge_1 = create_edge(CAedge1_id, hyp_id, ca_1_id)

        CAedge2_id = str(counter)+'CAAE' + str(i)
        CAedge_2 = create_edge(CAedge2_id, ca_1_id, node_id)


        Cedge1_id = str(counter)+'CE' + str(i)
        Cedge_1 = create_edge(Cedge1_id, node_id, ca_2_id)

        Cedge2_id = str(counter)+'CEE' + str(i)
        Cedge_2 = create_edge(CAedge2_id, ca_2_id, hyp_id)

        new_node_list.append(node_dict)
        new_node_list.append(ya_node)
        new_node_list.append(ca_1_node)
        new_node_list.append(ca_2_node)

        new_edge_list.append(edge_1)
        new_edge_list.append(edge_2)
        new_edge_list.append(CAedge_1)
        new_edge_list.append(CAedge_2)

        new_edge_list.append(Cedge_1)
        new_edge_list.append(Cedge_2)

    return new_node_list, new_edge_list

def get_exps(json_data):
    cent = Centrality()

    graph = cent.get_graph_string(json_data)


    ras = cent.get_ras(graph)
    ras_i_list = cent.extract_rule_structure(graph, ras)

    return ras_i_list

def get_full_struct_explanation(graph, i_nodes):
    cent = Centrality()
    i_list = cent.get_i_ra_nodes_full(graph, i_nodes)
    return i_list

def produce_explanation_from_structure(hyp_explain):

    f = open('structure_explanation.txt', 'a')


    for hyp in hyp_explain:
        hyp_id = hyp[0]
        hyp_text = hyp[1]
        hyp_prem = hyp[2]
        print('', file=f)
        if len(hyp_prem) > 0:
            for prem in hyp_prem:
                print(hyp_text + ' was automatically generated because ' + prem[1], file=f)

    f.close()


def produce_explanation_from_rules(all_hyps):
    rule_explanation = []
    for hyp in all_hyps:
        text = hyp[0]
        rule_id = hyp[1]
        premise = hyp[2]
        rule_premise = hyp[3]
        sim = hyp[4]
        rule_type = hyp[5]
        scheme = hyp[7]

        if rule_type == 'SIM RULE':
            explain_text = text + ' was generated automatically BECAUSE there was a textual similarity match with rule ' + str(rule_id) + '. The Similarity was ' + str(sim) + ' between ' + premise + ' and ' + rule_premise
            rule_explanation.append([hyp[0], explain_text])
        elif rule_type == 'EVENT RULE':
            explain_text = text + ' was generated automatically BECAUSE there was an event similarity match with rule ' + str(rule_id) + '. The Similarity was ' + str(sim) + ' between ' + premise + ' and ' + rule_premise
            rule_explanation.append([hyp[0], explain_text])
        elif rule_type == 'SCHEME RULE':
            explain_text = text + ' was generated automatically BECAUSE there was an argument scheme similarity match. The scheme was identified through argument from ' + str(scheme) + ' and premise: ' + premise
            rule_explanation.append([hyp[0], explain_text])

    return rule_explanation


def explain_alt_hyps(alt_hyps):
    f = open('alternative_hyps_explanation.txt', 'a')
    for alt_hyp in alt_hyps:

        print(str(alt_hyp[0]) + ' was generated because it is the alternative hypothesis to ' +  str(alt_hyp[2]), file=f)
        print('', file=f)
    f.close()

def write_json_to_file(jsn, path):

    with open(path, 'w') as fp:
        json.dump(jsn, fp)

def get_ranking(cent_i_nodes):
    i_nodes_df = pd.DataFrame(cent_i_nodes, columns=['ID','centrality','text', 'count'])
    i_nodes_df['ranking'] = (i_nodes_df['centrality'] + i_nodes_df['count'])/2
    i_nodes_list = i_nodes_df.values.tolist()
    return i_nodes_list

def remove_node(jsn, node_id):
    for i, node in enumerate(jsn['nodes']):
        n_id = node['nodeID']
        if str(n_id) == str(node_id):
            del jsn['nodes'][i]
            break

def remove_edge(jsn, node_id):
    other_nodes = []
    for i, node in reversed(list(enumerate(jsn['edges']))):
        to_id = node['toID']
        from_id = node['fromID']
        if str(to_id) == str(node_id):
            other_nodes.append(from_id)
            del jsn['edges'][i]

        elif str(from_id) == str(node_id):
            other_nodes.append(to_id)
            del jsn['edges'][i]
    return other_nodes

def remove_nodes(jsn, node_id):
    remove_node(jsn, node_id)
    other_nodes_list = remove_edge(jsn, node_id)
    for node in other_nodes_list:
        remove_node(jsn, node)
        other_nodes_lst = remove_edge(jsn, node)
        #for n in other_nodes_lst:
            #other_lst = remove_edge(jsn, n)
    return jsn

def sort_by_rank(i_nodes):
    i_nodes.sort(key = lambda x: x[4], reverse=True)
    return i_nodes

def get_critical_factors(graph, i_nodes):
    critical_facts = []
    for i_node in i_nodes:
        i_node_ID = i_node[0]
        i_node_text = i_node[2]
        ra_i_nodes = get_incoming_ra_nodes_with_i(graph, i_node_ID)
        ra_i_len = len(ra_i_nodes)

        if ra_i_len < 1:
            crit_text = 'No Evidence for ' + str(i_node_text)
            i_node.append(crit_text)
            critical_facts.append(i_node)
        if ra_i_len == 1:
            crit_text = str(ra_i_nodes[0][1]) + ' is critical to the truth of ' + str(i_node_text)
            i_node.append(crit_text)
            critical_facts.append(i_node)
        if ra_i_len > 1:
            for i, ra_i in reversed(list(enumerate(ra_i_nodes))):
                ca_i_nodes = get_incoming_ca_nodes_with_i(graph, ra_i[0])
                ca_i_len = len(ca_i_nodes)

                if ca_i_len >= 1:
                    del ra_i_nodes[1]

            if len(ra_i_nodes) < 1:
                crit_text = 'No Concrete Evidence for ' + str(i_node_text)
                i_node.append(crit_text)
                critical_facts.append(i_node)
            if len(ra_i_nodes) == 1:
                crit_text = str(ra_i_nodes[0][1]) + ' is critical to the truth of ' + str(i_node_text)
                i_node.append(crit_text)
                critical_facts.append(i_node)
            if len(ra_i_nodes) > 1:
                crit_text = str(i_node_text) + ' can be considered acceptable'
                i_node.append(crit_text)
                critical_facts.append(i_node)
    return critical_facts

def get_incoming_ra_nodes_with_i(graph, i_node):
    i_list = []
    node_succ = list(graph.predecessors(i_node))
    ra_list = []
    for n in node_succ:
        n_type = graph.nodes[n]['type']
        if n_type == 'RA':
            node_I = list(graph.predecessors(n))
            for i_node in node_I:
                node_type = graph.nodes[i_node]['type']
                node_text = graph.nodes[i_node]['text']
                if node_type == 'I':
                    ra_list.append([i_node, node_text])

    return ra_list

def get_incoming_ca_nodes_with_i(graph, i_node):
    i_list = []
    node_succ = list(graph.predecessors(i_node))
    ra_list = []
    for n in node_succ:
        n_type = graph.nodes[n]['type']
        if n_type == 'CA':
            node_I = list(graph.predecessors(n))
            for i_node in node_I:
                node_type = graph.nodes[i_node]['type']
                node_text = graph.nodes[i_node]['text']
                if node_type == 'I':
                    ra_list.append([i_node, node_text])

    return ra_list

def get_search_type(question_type):
    question_type = question_type.lower()
    search_type = ''
    if 'is/are' in question_type or 'do/does' in question_type or 'has/have' in question_type or 'why' in question_type or 'who' in question_type:
        search_type = 'hyp'
    else:
        search_type = 'all'
    return search_type
