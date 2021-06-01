import pandas as pd
import numpy as np
from collections import defaultdict
from gensim import corpora
from gensim import models
from SetSimilaritySearch import all_pairs
from fuzzywuzzy import fuzz

def make_claims_df(lens_p_df):
    documents = []
    titles = []

    # populate lists with claims info and titles of patents
    for index, row in lens_p_df.iterrows():
        if len(row['Claims']) > 20: # some just say 'claims:' or 'what was claimed' etc.
            documents.append(row['Claims'])
            titles.append(row['Title'])

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

    # build accessible structure- {INDEX: {'title': TITLE, 'freqs': {TERM: FREQUENCY, TERM: FREQUENCY, etc.}}}
    list_words = []
    title_and_vals = {}
    index = 0
    for doc in corpus_tfidf:
        sub_list = []
        info = {'title': titles[index]}
        freqs = {}

        for id, freq in doc:
            term = dictionary[id]
            freqs[term] = np.around(freq, decimals=4)
            sub_list.append(term)

        info['freqs'] = freqs
        title_and_vals[index] = info
        list_words.append(sub_list)
        index += 1

    # find document pairs where term overlap > 0.3
    pairs = all_pairs(list_words, similarity_func_name="jaccard", similarity_threshold=0.3)
    pairs_1 = list(pairs)

    # get rid of pairs where titles are the same
    pairs_2 = []
    for pair in pairs_1:
        title_1 = title_and_vals[pair[0]]['title']
        title_2 = title_and_vals[pair[1]]['title']
        ratio = fuzz.ratio(title_1.lower(), title_2.lower())
        if ratio < 95:
            pairs_2.append(pair)

    # sort pairs by overlap
    sorted_pairs = sorted(pairs_2, key=lambda tup: tup[2], reverse=True)

    d = {'ratio': [], 'index1': [], 'index2': [], 'title1': [], 'title2': [], 'intersection': []}
    df = pd.DataFrame(data=d)

    for pair in sorted_pairs:
        one, two, overlap = pair

        title_1 = title_and_vals[one]['title']
        title_2 = title_and_vals[two]['title']

        freqs_1 = title_and_vals[one]['freqs']
        freqs_2 = title_and_vals[two]['freqs']
        combined_freqs = []
        for term in freqs_1:
            if term in freqs_2:
                combined_freqs.append((freqs_1[term] + freqs_2[term], term))

        sorted_freqs = sorted(combined_freqs, reverse=True) # least common word should appear first
        intersection = ', '.join([word for _, word in sorted_freqs]) # put in string format

        row = {'ratio': overlap, 'index1': one, 'index2': two, 'title1': title_1, 'title2': title_2, 'intersection': intersection}
        df = df.append(row, ignore_index=True)

    return df