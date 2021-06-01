import requests, json
from django.shortcuts import render
from django.http import HttpResponse

import pandas as pd
import xlsxwriter
import io
from pandas import json_normalize
from docx import Document

from collections import defaultdict
from gensim import corpora
from gensim import models
from SetSimilaritySearch import all_pairs
from fuzzywuzzy import fuzz

from ..forms import SearchForm
from .ct import *
from .lens_s import *
from .lens_p import *
from .nih import *

def search_tool(request):
    '''Queries information from clinicaltrials.gov, lens.org, Federal NIH reporter APIs.

    arguments from form:
    
    used in both CT and Lens:
        author, institution, keyword
    used only in CT:
        sponsor
    
    '''
    if request.method == 'POST': # user has submitted data
        form = SearchForm(request.POST)
        if form.is_valid():
            fields = ['author', 'institution', 'sponsor', 'city', 'state', 'keyword', 'lens_id']
            entries = {}
            for field in fields:
                entry = form.cleaned_data[field]
                if entry:
                    entries[field] = entry

            if 'all_data' in request.POST:
                return publications_request(entries)
            elif 'authors' in request.POST:
                return authors_request(entries)
            
    else: # show empty form
        form = SearchForm()

    return render(request, 'search.html', {'form': form})


def publications_request(entries):
    '''Queries information from clinicaltrials.gov, lens.org, Federal NIH reporter APIs.

    arguments from form:
    
    used in both CT and Lens:
        author, institution, keyword
    used only in CT:
        sponsor
    
    '''
    ct_df = get_ct_df(entries)
    lens_s_df = get_lens_s_df(entries)
    lens_p_df = get_lens_p_df(entries)
    nih_df = get_nih_df(entries)

    authors_df = make_author_df(ct_df, lens_s_df, lens_p_df, nih_df)
    claims_df = make_claims_df(lens_p_df)

    xlsx = create_xlsx(ct_df, lens_s_df, lens_p_df, nih_df, authors_df, claims_df)

    filename = 'query_results.xlsx'
    response = HttpResponse(
        xlsx,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=%s' % filename

    return response


def create_xlsx(ct_df, lens_s_df, lens_p_df, nih_df, authors_df, claims_df):
    '''Write dataframe to xlsx file.

    arguments:
    df -- populated dataframe

    '''
    xlsx = io.BytesIO()
    PandasWriter = pd.ExcelWriter(xlsx, engine='xlsxwriter')

    ct_df.to_excel(PandasWriter, sheet_name='clinical_trials_results')
    lens_s_df.to_excel(PandasWriter, sheet_name='lens_s_results')
    lens_p_df.to_excel(PandasWriter, sheet_name='lens_p_results')
    nih_df.to_excel(PandasWriter, sheet_name='nih_results')
    authors_df.to_excel(PandasWriter, sheet_name='authors')
    claims_df.to_excel(PandasWriter, sheet_name='claims')

    PandasWriter.save()
    xlsx.seek(0)

    return xlsx


def authors_request(entries):
    '''Queries information from clinicaltrials.gov API and lens.org API.

    arguments from form:
    
    used in both CT and Lens:
        author, institution, keyword
    used only in CT:
        sponsor
    
    '''
    ct_df = get_ct_df(entries)
    lens_s_df = get_lens_s_df(entries)
    lens_p_df = get_lens_p_df(entries)
    nih_df = get_nih_df(entries)

    author_df = make_author_df(ct_df, lens_s_df, lens_p_df, nih_df)
    author_xlsx = make_authors_xlsx(author_df)

    filename = 'author_results.xlsx'
    response = HttpResponse(
        author_xlsx,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=%s' % filename

    return response


def make_author_df(ct_df, lens_s_df, lens_p_df, nih_df):
    '''Sort and filter results for common authors.

    arguments:
    df -- populated dataframe

    '''
    translator = {
        'Clinical Trials': [ct_df, 'Authors', 0, -1],
        'Lens Scholar': [lens_s_df, 'Authors', 0, -1],
        'Lens Patent': [lens_p_df, 'Inventors', 1, 0],
        'Federal NIH': [nih_df, 'PI Names', 0, -1]
        }

    author_dict = populate_dict(translator)
    authors_sort_filt = sort_and_filter(author_dict)
    authors_df = make_authors_df(author_dict, authors_sort_filt)

    return authors_df

def populate_dict(translator):
    '''Creates dictionary mapping authors to work across different databases

    arguments:
    *_df: dataframe with data from the given database
    translator: info specific to each to database, such as author name arrangement, etc.
    
    '''
    author_dict = {}
    for db in translator:
        df, col_name, first, last = translator[db]
        for index, row in df.iterrows():
            if pd.isnull(df.loc[index, col_name]):
                continue
            entry = row[col_name]
            authors = entry.split(',')
            for author in authors:
                names = [n.strip() for n in author.split()]
                try:
                    name = (f'{names[first]} {names[last]}').title()
                except IndexError:
                    continue
                info = row["Title"].title()
                if name in author_dict:
                    if db in author_dict[name]:
                        author_dict[name][db].add(info)
                    else:
                        author_dict[name][db] = {info}
                else:
                    author_dict[name] = {db: {info}}

    return author_dict

def sort_and_filter(author_dict):
    authors_sort_filt = []
    for name in author_dict:
        # categories = len(list(author_dict[name].keys()))
        total = sum([len(list(author_dict[name][key])) for key in author_dict[name]])
        if total > 1:
            # authors_sort_filt.append((categories, total, name))
            authors_sort_filt.append((total, name))
    authors_sort_filt.sort(reverse=True)

    return authors_sort_filt

def make_authors_df(author_dict, authors_sort_filt):
    d = {'Name': [], 'Clinical Trials': [], 'Lens Scholar': [], 'Lens Patent': [], 'Federal NIH': []}
    df = pd.DataFrame(data=d)
    # for _, _, name in authors_sort_filt:
    for _, name in authors_sort_filt:
        row_data = {'Name': name}
        data = author_dict[name]
        for database in data:
            titles = '; '.join(data[database])
            row_data[database] = titles
        
        df = df.append(row_data, ignore_index=True)

    return df

def make_authors_xlsx(authors_df):
    xlsx = io.BytesIO()
    PandasWriter = pd.ExcelWriter(xlsx, engine='xlsxwriter')
    authors_df.to_excel(PandasWriter, sheet_name='authors')
    PandasWriter.save()

    xlsx.seek(0)

    return xlsx

def make_claims_df(lens_p_df):
    documents = []
    titles = []

    for index, row in lens_p_df.iterrows():
        if len(row['Claims']) > 20:
            documents.append(row['Claims'])
            titles.append(row['Title'])

    stop_words = 'a an and are at be by claim claims claimed for from i in is it its of or that the to where whereby which with'.split()
    stop_punc = '. , ; -'.split()
    num_str = [str(n) for n in range(100)]
    num_dot = [f'{str(n)}.' for n in range(100)]
    stoplist = set(stop_words + stop_punc + num_str + num_dot)

    texts = []
    for document in documents:
        terms = []
        doc_words = document.lower().split()
        for word in doc_words:
            term = word.strip('.,:;()%')
            if len(term) > 1 and term not in stoplist:
                terms.append(term)
        texts.append(terms)

    frequency = defaultdict(int)
    for text in texts:
        for token in text:
            frequency[token] += 1

    texts = [
        [token for token in text if frequency[token] > 1]
        for text in texts
    ]

    dictionary = corpora.Dictionary(texts)
    corpus = [dictionary.doc2bow(text) for text in texts]

    tfidf = models.TfidfModel(corpus)
    corpus_tfidf = tfidf[corpus]

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

    pairs = all_pairs(list_words, similarity_func_name="jaccard", similarity_threshold=0.1)
    pairs_1 = list(pairs)

    pairs_2 = []
    for pair in pairs_1:
        if pair[2] < 0.3:
            continue
        title_1 = title_and_vals[pair[0]]['title']
        title_2 = title_and_vals[pair[1]]['title']
        ratio = fuzz.ratio(title_1.lower(), title_2.lower())
        if ratio < 95:
            pairs_2.append(pair)

    sorted_pairs = sorted(pairs_2, key=lambda tup: tup[2], reverse=True)
    print(sorted_pairs)

    d = {'index1': [], 'index2': [], 'title1': [], 'title2': [], 'intersection': []}
    df = pd.DataFrame(data=d)

    for pair in sorted_pairs[:10]:
        one = pair[0]
        two = pair[1]

        title_1 = title_and_vals[one]['title']
        title_2 = title_and_vals[two]['title']

        freqs_1 = title_and_vals[one]['freqs']
        freqs_2 = title_and_vals[two]['freqs']
        combined_freqs = []
        for term in freqs_1:
            if term in freqs_2:
                combined_freqs.append((freqs_1[term] + freqs_2[term], term))
        sorted_freqs = sorted(combined_freqs, reverse=True)

        intersection = ', '.join([word for _, word in sorted_freqs])

        row = {'index1': one, 'index2': two, 'title1': title_1, 'title2': title_2, 'intersection': intersection}
        df = df.append(row, ignore_index=True)

    return df