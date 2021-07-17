import requests, json
from django.shortcuts import render
from django.http import HttpResponse

import pandas as pd
import numpy as np
import xlsxwriter
import io
from pandas import json_normalize

from ..forms import SearchForm
from .ct import *
from .lens_s import *
from .lens_p import *
from .nih import *
from .authors import *
from .claims import *
from .compare_all import *

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

            if 'authors' in request.POST:
                return publications_request(entries, 'authors')
            elif 'claims' in request.POST:
                return publications_request(entries, 'claims')
            
    else: # show empty form
        form = SearchForm()

    return render(request, 'search.html', {'form': form})


def publications_request(entries, analysis):
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

    database_dfs = {'clinical_trials_results': ct_df, 'lens_s_results': lens_s_df, 'lens_p_results': lens_p_df, 'nih_results': nih_df}

    if analysis == 'authors':    
        authors_df = make_author_df(ct_df, lens_s_df, lens_p_df, nih_df)
        database_dfs['authors'] = authors_df
    elif analysis == 'claims':
        claims_df = make_claims_df(lens_p_df)
        database_dfs['authors'] = claims_df

    xlsx = create_xlsx(database_dfs)

    filename = 'query_results.xlsx'
    response = HttpResponse(
        xlsx,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=%s' % filename

    return response


def create_xlsx(database_dfs):
    '''Write dataframe to xlsx file.

    arguments:
    df -- populated dataframe

    '''
    xlsx = io.BytesIO()
    PandasWriter = pd.ExcelWriter(xlsx, engine='xlsxwriter')

    for db, df in database_dfs.items():
        df.to_excel(PandasWriter, sheet_name=db)

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