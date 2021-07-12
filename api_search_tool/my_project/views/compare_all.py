import pandas as pd
import numpy as np
from collections import defaultdict
from gensim import corpora
from gensim import models
from SetSimilaritySearch import all_pairs
from fuzzywuzzy import fuzz

def compare_dfs(ct_df, lens_s_df, lens_p_df, nih_df):
    info, documents = make_lists(ct_df, lens_s_df, lens_p_df, nih_df)
    dictionary, corpus_tfidf = make_dict(documents)
    list_words, title_and_vals = build_structure(dictionary, corpus_tfidf, info)
    sorted_pairs = find_and_sort_pairs(list_words, title_and_vals)
    df = build_df(sorted_pairs, title_and_vals)
    return df

def make_lists(ct_df, lens_s_df, lens_p_df, nih_df):
    info = []
    documents = []
    
     # populate lists with info from all dfs
    for index, row in ct_df.iterrows():
        info.append((row['Title'], 'CT', row['NCTId']))
        documents.append(row['BriefSummary'])
    
    for index, row in lens_p_df.iterrows():
        info.append((row['Title'], 'L-P', row['lens_id']))
        documents.append(row['Claims'])
    
    for index, row in nih_df.iterrows():
        info.append((row['Title'], 'NIH', row['smApplId']))
        documents.append(row['Summary'])

    return info, documents

def make_dict(documents):

    # build list of words to drop
    stop_words = 'a an and are at be by claim claims claimed for from i in is it its of or that the to where whereby which with'.split()
    stop_punc = '. , ; -'.split()
    num_str = [str(n) for n in range(100)]
    stoplist = set(stop_words + stop_punc + num_str)

    # filter words and put in list of lists
    texts = []
    for document in documents:
        terms = []
        doc_words = document.lower().split()
        for word in doc_words:
            term = word.strip('.,:;()%') # get rid of trailing punctuation
            if len(term) > 1 and term not in stoplist: # get rid of single letters and meaningless words
                terms.append(term)
        texts.append(terms)

    # build frequency dictionary (copy pasted from tutorial)
    frequency = defaultdict(int)
    for text in texts:
        for token in text:
            frequency[token] += 1

    # retain only words appearing more than once
    texts = [
        [token for token in text if frequency[token] > 1]
        for text in texts
    ]

    # change to structures used by gensim (copy pasted from tutorial)
    dictionary = corpora.Dictionary(texts)
    corpus = [dictionary.doc2bow(text) for text in texts]

    # create model
    tfidf = models.TfidfModel(corpus)
    corpus_tfidf = tfidf[corpus]

    return dictionary, corpus_tfidf

def build_structure(dictionary, corpus_tfidf, info):

    # build accessible structure- {INDEX: {'title': TITLE, 'freqs': {TERM: FREQUENCY, TERM: FREQUENCY, etc.}}}
    list_words = []
    title_and_vals = {}
    index = 0
    for doc in corpus_tfidf:
        sub_list = []
        data = {'info': info[index]}
        freqs = {}

        for id, freq in doc:
            term = dictionary[id]
            freqs[term] = np.around(freq, decimals=4)
            sub_list.append(term)

        data['freqs'] = freqs
        title_and_vals[index] = data
        list_words.append(sub_list)
        index += 1

    return list_words, title_and_vals

def find_and_sort_pairs(list_words, title_and_vals):
    
    # find document pairs where term overlap > 0.3
    pairs = all_pairs(list_words, similarity_func_name="jaccard", similarity_threshold=0.3)
    pairs_1 = list(pairs)

    # get rid of pairs where titles are the same
    pairs_2 = []
    for pair in pairs_1:
        title_1, _, _ = title_and_vals[pair[0]]['info']
        title_2, _, _ = title_and_vals[pair[1]]['info']
        ratio = fuzz.ratio(title_1.lower(), title_2.lower())
        if ratio < 95:
            pairs_2.append(pair)

    # sort pairs by overlap
    sorted_pairs = sorted(pairs_2, key=lambda tup: tup[2], reverse=True)
    return sorted_pairs

def build_df(sorted_pairs, title_and_vals):
    d = {'ratio': [], 'id1': [], 'id2': [], 'title1': [], 'title2': [], 'intersection': []}
    df = pd.DataFrame(data=d)

    for pair in sorted_pairs:
        one, two, overlap = pair

        title_1, database_1, identifier_1 = title_and_vals[one]['info']
        title_2, database_2, identifier_2 = title_and_vals[two]['info']

        freqs_1 = title_and_vals[one]['freqs']
        freqs_2 = title_and_vals[two]['freqs']
        combined_freqs = []
        for term in freqs_1:
            if term in freqs_2:
                combined_freqs.append((freqs_1[term] + freqs_2[term], term))

        sorted_freqs = sorted(combined_freqs, reverse=True) # least common word should appear first
        intersection = ', '.join([word for _, word in sorted_freqs]) # put in string format

        row = {'ratio': overlap, 'id1': identifier_1, 'id2': identifier_2, 'title1': f'({database_1}) {title_1}', 'title2': f'({database_2}) {title_2}', 'intersection': intersection}
        df = df.append(row, ignore_index=True)

    return df