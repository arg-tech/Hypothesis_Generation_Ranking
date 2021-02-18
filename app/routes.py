from flask import render_template, request, redirect, session, Markup
from . import app
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


@app.route('/')
@app.route('/index')
def index():
    return redirect('/form')


@app.route('/form')
def my_form():
    return render_template('index.html')

@app.route('/form', methods=['POST'])
def my_form_post():
    iat_mode = 'false'
    text = request.form['text']
    session['text_var'] = text
    return redirect('/results')

@app.route('/results')
def render_text():
    text = session.get('text_var', None)

    context = 'militant'

    json_path = 'static/target_data/' + context + '/20088.json'
    hevy_file_name = 'static/target_data/' + context + '/20088_target.json'
    graph, jsn = get_graph_json(json_path)
    target_schemes = get_arg_schemes_props(graph, jsn)



    if context == '':
        rules_path = 'rules/'
        hevy_rules_path = 'rules/hevy/'
    else:
        rules_path = 'rules/' + context + '/'
        hevy_rules_path = 'rules/hevy/' + context + '/'


    rules, full_scheme_data = get_rules_data(rules_path, hevy_rules_path)

    nlp = spacy.load("en_core_web_sm")

    #0.33
    scheme_hypos = get_argument_scheme_hypotheses(nlp, 0.33, full_scheme_data, target_schemes)

    print(scheme_hypos)

    return render_template('results.html')

def get_json_string(node_path):
    dta = ''
    try:
        with app.open_resource(node_path) as j:
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
    for subdir, dirs, files in os.walk(os.path.join(app.static_folder, rules_path)):
        for file_name in files:

            if '.json' in file_name:
                base = subdir + file_name

                base_ext = os.path.splitext(base)[0]
                schemes = get_arg_schemes_full_aif(base)
                rule = get_rules(base)
                hevy_file_name = file_name.split('.')[0]
                h_jsn = get_hevy_json(hevy_file_name, os.path.join(app.static_folder, hevy_rules_path))
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
