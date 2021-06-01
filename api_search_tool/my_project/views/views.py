import requests, json
from django.shortcuts import render
from django.http import HttpResponse

import pandas as pd
import numpy as np
import xlsxwriter
import io
from pandas import json_normalize
from docx import Document

from ..forms import SearchForm
from .ct import *
from .lens_s import *
from .lens_p import *
from .nih import *
from .authors import *
from .claims import *

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
            # elif 'authors' in request.POST:
            #     return authors_request(entries)
            
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